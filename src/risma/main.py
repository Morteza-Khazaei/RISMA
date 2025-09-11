#!/usr/bin/env python3
"""
RISMA CLI - Interactive Step-by-Step Command Line Interface
"""

import os
import sys
import shlex
import argparse
import json
from urllib.parse import urlparse
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import pandas as pd

# Optional interactive UI support via questionary
try:
    import questionary  # type: ignore
    from questionary import Choice, Separator  # type: ignore
    HAS_QUESTIONARY = True
except Exception:  # optional dependency
    questionary = None
    Choice = None
    Separator = None
    HAS_QUESTIONARY = False

from risma import AquariusWebPortal


class RISMASession:
    """Session class to maintain state across interactive steps"""
    def __init__(self, portal: AquariusWebPortal, verbose: bool = False):
        self.portal = portal
        self.verbose = verbose
        
        # User selections stored as we progress
        self.selected_params: List[str] = []
        self.selected_stations: List[str] = []
        self.selected_sensors: List[str] = []
        self.selected_depths: List[str] = []
        self.selected_datasets: pd.DataFrame = pd.DataFrame()
        self.selected_start_date: Optional[datetime] = None
        self.selected_end_date: Optional[datetime] = None
        self.selected_date_mode: Optional[str] = None  # 'custom' | 'last7' | 'entire'
        self.selected_output_dir: Optional[str] = None
        # Export options
        self.export_timezone: Optional[int] = 0
        self.export_calendar: Optional[str] = "CALENDARYEAR"
        self.export_interval: Optional[str] = "PointsAsRecorded"
        self.export_step: Optional[int] = 1
        self.export_time_aligned: Optional[bool] = True
        self.export_round_data: Optional[bool] = True
        self.export_calculation: Optional[str] = "Instantaneous"
        self.export_format: Optional[str] = "csv"
        self.export_extra_types: List[str] = []
        
        # Available data loaded as needed
        self.available_params: pd.DataFrame = pd.DataFrame()
        self.available_locations: pd.DataFrame = pd.DataFrame()
        self.available_datasets: pd.DataFrame = pd.DataFrame()

    def load_params(self):
        """Load available parameters"""
        if self.verbose:
            print(f"Loading parameters from {self.portal.server}...")
        self.available_params = self.portal.params
        return self.available_params

    def load_locations(self, stations: Optional[List[str]] = None):
        """Load available locations"""
        if self.verbose:
            print(f"Loading locations from {self.portal.server}...")
        self.available_locations = self.portal.fetch_locations(stations=stations)
        return self.available_locations

    def load_datasets(self):
        """Load datasets based on current selections"""
        if self.verbose:
            print("Loading datasets based on selections...")
        # Do not use hidden defaults; rely on explicit selections
        param_names = self.selected_params
        stations = self.selected_stations if self.selected_stations else None
        sensors = self.selected_sensors if self.selected_sensors else None
        depths = self.selected_depths if self.selected_depths else None

        self.available_datasets = self.portal.fetch_datasets(
            param_names=param_names,
            stations=stations,
            sensors=sensors,
            depths=depths
        )
        return self.available_datasets

    def reset_selections(self):
        """Reset all user selections"""
        self.selected_params = []
        self.selected_stations = []
        self.selected_sensors = []
        self.selected_depths = []
        self.selected_datasets = pd.DataFrame()
        self.selected_start_date = None
        self.selected_end_date = None
        self.selected_date_mode = None
        self.selected_output_dir = None
        self.export_timezone = 0
        self.export_calendar = "CALENDARYEAR"
        self.export_interval = "PointsAsRecorded"
        self.export_step = 1
        self.export_time_aligned = True
        self.export_round_data = True
        self.export_calculation = "Instantaneous"
        self.export_format = "csv"
        self.export_extra_types = []


def _print_table(headers: List[str], rows: List[List[str]]):
    """Pretty-print a table with dynamic column widths based on content."""
    # Ensure string conversion
    rows = [["" if v is None else str(v) for v in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))
            else:
                widths.append(len(cell))
    # Build format strings
    sep = "  "
    def fmt_line(vals):
        return sep.join(f"{val:<{w}}" for val, w in zip(vals, widths))
    # Print header
    print(fmt_line(headers))
    print("".join(["-" * w + (sep if i < len(widths)-1 else "") for i, w in enumerate(widths)]))
    # Print rows
    for row in rows:
        print(fmt_line(row))


def _parse_selection_indices(inp: str, max_index: int) -> List[int]:
    """Parse a selection string like '1 2 5-8' into 0-based indices.
    Supports 'a' or 'all' for full selection.
    """
    inp = inp.strip().lower()
    if inp in ("a", "all"):
        return list(range(max_index))
    sel: List[int] = []
    tokens = [t for t in inp.replace(",", " ").split() if t]
    for t in tokens:
        if "-" in t:
            try:
                start_s, end_s = t.split("-", 1)
                start = int(start_s)
                end = int(end_s)
            except ValueError:
                continue
            if start <= 0 or end <= 0:
                continue
            for i in range(start, end + 1):
                if 1 <= i <= max_index:
                    sel.append(i - 1)
        else:
            try:
                i = int(t)
                if 1 <= i <= max_index:
                    sel.append(i - 1)
            except ValueError:
                continue
    # Deduplicate preserving order
    seen = set()
    out: List[int] = []
    for i in sel:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _interactive_select_params_with_questionary(params_df: pd.DataFrame) -> List[str]:
    """Use questionary to interactively select parameters by name.
    Returns list of param_name.
    """
    if not HAS_QUESTIONARY:
        return []
    choices = []
    for _, row in params_df.iterrows():
        label = f"{row.param_name} — {row.param_desc}"
        choices.append(Choice(title=label, value=row.param_name))
    if not choices:
        return []
    answer = questionary.checkbox(
        "Select parameters (space to toggle, enter to confirm):",
        choices=choices,
        qmark="⚙",
        validate=lambda sel: True if len(sel) > 0 else "Select at least one",
    ).ask()
    return answer or []


def _interactive_select_stations_with_questionary(loc_df: pd.DataFrame, prompt_filter: bool = False) -> List[str]:
    """Use questionary to interactively select station IDs, grouped by province and
    sorted by natural station ID order. Returns list of loc_id.
    """
    if not HAS_QUESTIONARY:
        return []

    def natural_key(s: str):
        import re as _re
        return [int(t) if t.isdigit() else t.lower() for t in _re.findall(r"\d+|\D+", s or "")]

    df = loc_df.copy()

    # Group by province (fallback to 'Unknown') and sort province names
    def _prov(val):
        try:
            return str(val) if pd.notna(val) and str(val).strip() else 'Unknown'
        except Exception:
            return 'Unknown'

    if 'province' not in df.columns:
        df['province'] = None

    grouped = {}
    for _, row in df.iterrows():
        prov = _prov(row.get('province') if hasattr(row, 'get') else getattr(row, 'province', None))
        grouped.setdefault(prov, []).append(row)

    choices: List = []
    for prov in sorted(grouped.keys(), key=lambda x: (x is None, str(x))):
        rows = grouped[prov]
        # Sort by natural station ID
        rows_sorted = sorted(rows, key=lambda r: natural_key(str(r.loc_id)))
        if Separator is not None:
            choices.append(Separator(f"— {prov} —"))
        for row in rows_sorted:
            lat = f"{row.lat:.4f}" if pd.notna(row.lat) else "N/A"
            lon = f"{row.lon:.4f}" if pd.notna(row.lon) else "N/A"
            province = prov
            title = f"{row.loc_id} — {row.loc_name} ({row.loc_type}, {lat},{lon}, {province})"
            choices.append(Choice(title=title, value=row.loc_id))

    if not choices:
        print("⚠️  No stations available.")
        return []

    answer = questionary.checkbox(
        "Select stations (space to toggle, enter to confirm):",
        choices=choices,
        qmark="📍",
        validate=lambda sel: True if len(sel) > 0 else "Select at least one",
    ).ask()
    return answer or []


def _auto_show_datasets_and_select_filters(session: RISMASession) -> bool:
    """Show datasets overview, then prompt for sensors/depths filters, then refresh and show final list."""
    try:
        # Initial unfiltered load for overview and to collect available filters
        session.selected_sensors = []
        session.selected_depths = []
        df = session.load_datasets()
        if df.empty:
            print("⚠️  No datasets found for current parameters and stations.")
            return False

        # Overview table
        print("\n📊 Available datasets (overview):")
        print(f"   Parameters: {session.selected_params}")
        print(f"   Stations: {session.selected_stations}")
        headers = ["Station", "Parameter", "Label", "Type", "Sensor", "Depth", "Start", "End"]
        rows = []
        for _, ds in df.iterrows():
            sensor = getattr(ds, 'sensor', 'N/A')
            depth = getattr(ds, 'depth', 'N/A')
            dtype = getattr(ds, 'type', 'N/A')
            start = str(ds.dset_start)[:10] if pd.notna(ds.dset_start) else "N/A"
            end = str(ds.dset_end)[:10] if pd.notna(ds.dset_end) else "N/A"
            rows.append([str(ds.loc_id), str(ds.param), str(ds.label), str(dtype), str(sensor), str(depth), start, end])
        _print_table(headers, rows)

        # Prompt for sensors/depths filters (only from soil datasets)
        df_soil = df[df.get('type').eq('soil')] if 'type' in df.columns else df.head(0)
        sensors = sorted(set([s for s in df_soil.get('sensor', pd.Series(dtype=str)).dropna().astype(str).tolist() if s]))
        depths = sorted(set([d for d in df_soil.get('depth', pd.Series(dtype=str)).dropna().astype(str).tolist() if d]))

        # If no soil filters available, skip filtering
        selected_sensors: List[str] = []
        selected_depths: List[str] = []
        if HAS_QUESTIONARY and (sensors or depths):
            if sensors:
                selected_sensors = questionary.checkbox(
                    "Select sensors to include (Enter for all):",
                    choices=[Choice(title=s, value=s) for s in sensors],
                    qmark="🧪",
                ).ask() or []
            if depths:
                selected_depths = questionary.checkbox(
                    "Select depths to include (Enter for all):",
                    choices=[Choice(title=d, value=d) for d in depths],
                    qmark="📏",
                ).ask() or []

        # Apply filters if selected
        session.selected_sensors = selected_sensors
        session.selected_depths = selected_depths
        df_final = session.load_datasets()
        if df_final.empty:
            print("⚠️  No datasets after applying filters.")
            return False

        # Show final datasets
        print("\n📊 Datasets after filters:")
        headers = ["Station", "Parameter", "Label", "Type", "Sensor", "Depth", "Start", "End"]
        rows = []
        for _, ds in df_final.iterrows():
            sensor = getattr(ds, 'sensor', 'N/A')
            depth = getattr(ds, 'depth', 'N/A')
            dtype = getattr(ds, 'type', 'N/A')
            start = str(ds.dset_start)[:10] if pd.notna(ds.dset_start) else "N/A"
            end = str(ds.dset_end)[:10] if pd.notna(ds.dset_end) else "N/A"
            rows.append([str(ds.loc_id), str(ds.param), str(ds.label), str(dtype), str(sensor), str(depth), start, end])
        _print_table(headers, rows)

        # Cache for next steps
        session.selected_datasets = df_final
        save_session_state(session)
        print("\n💡 Next step: Configure export options and date range with 'export', then run 'download'")
        return True
    except Exception as e:
        print(f"❌ Error preparing datasets: {e}")
        return False


def _interactive_download_prompt(session: RISMASession) -> Optional[argparse.Namespace]:
    """Prompt for (or reuse) date range and output folder; return argparse-like args namespace.
    If a date range was already chosen in datasets, reuse it and do not prompt again.
    """
    if not HAS_QUESTIONARY:
        print("❌ Interactive download requires 'questionary'. Install with: pip install questionary")
        return None

    # Reuse previously selected date range to avoid double prompting
    start_date = session.selected_start_date
    end_date = session.selected_end_date
    choice = session.selected_date_mode

    if choice is None:
        # No prior selection; prompt now
        choice = questionary.select(
            "Select date range:",
            choices=[
                Choice(title="Last 7 days", value="last7"),
                Choice(title="Custom range", value="custom"),
                Choice(title="Entire period of record", value="entire"),
            ],
            qmark="📅",
        ).ask()
        if choice == "last7":
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
        elif choice == "custom":
            s = questionary.text("Start date (YYYY-MM-DD):", qmark="📅").ask()
            e = questionary.text("End date (YYYY-MM-DD):", qmark="📅").ask()
            try:
                start_date = datetime.strptime(s, "%Y-%m-%d") if s else None
                end_date = datetime.strptime(e, "%Y-%m-%d") if e else None
            except Exception:
                print("❌ Invalid date format.")
                return None
            if not start_date or not end_date or start_date > end_date:
                print("❌ Invalid custom date range.")
                return None
        elif choice == "entire":
            # Let download step compute bounds from datasets if needed
            start_date = None
            end_date = None
    else:
        # Show a brief note about reused date selection
        if choice == 'entire':
            if start_date and end_date:
                print(f"📅 Using previously selected entire period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            else:
                print("📅 Using previously selected entire period of record")
        elif start_date and end_date:
            print(f"📅 Using previously selected date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # Output directory
    default_dir = session.selected_output_dir or os.path.join(os.path.expanduser("~"), "RISMA_data")
    out_dir = questionary.text(
        f"Output directory:", default=default_dir, qmark="📁"
    ).ask() or default_dir

    # Extra data types: reuse previously selected in export step (avoid duplicate prompt)
    extra = session.export_extra_types or []

    return argparse.Namespace(
        start_date=start_date,
        end_date=end_date,
        output=out_dir,
        extra_data_types=extra,
        date_mode=choice,
        entire_period=True if choice == "entire" else False,
    )


def _interactive_select_date_range(session: RISMASession, datasets_df: Optional[pd.DataFrame] = None) -> bool:
    """Prompt the user to choose a date range and save it to the session."""
    if not HAS_QUESTIONARY:
        print("❌ Interactive date selection requires 'questionary'. Install with: pip install questionary")
        return False
    choice = questionary.select(
        "Select date range:",
        choices=[
            Choice(title="Last 7 days", value="last7"),
            Choice(title="Last 30 days", value="days30"),
            Choice(title="Last 6 months", value="months6"),
            Choice(title="Last 1 year", value="years1"),
            Choice(title="Custom range", value="custom"),
            Choice(title="Entire period of record", value="entire"),
            Choice(title="Overlapping period of record (intersection)", value="overlapping"),
        ],
        qmark="📅",
    ).ask()
    start_date = None
    end_date = None
    if choice == "last7":
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
    elif choice == "days30":
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
    elif choice == "months6":
        end_date = datetime.now()
        start_date = end_date - timedelta(days=182)
    elif choice == "years1":
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
    elif choice == "custom":
        s = questionary.text("Start date (YYYY-MM-DD):", qmark="📅").ask()
        st = questionary.text("Start time (HH:MM, default 00:00):", default="00:00", qmark="⏱").ask() or "00:00"
        e = questionary.text("End date (YYYY-MM-DD):", qmark="📅").ask()
        et = questionary.text("End time (HH:MM, default 00:00):", default="00:00", qmark="⏱").ask() or "00:00"
        try:
            start_date = datetime.strptime(f"{s} {st}", "%Y-%m-%d %H:%M") if s else None
            end_date = datetime.strptime(f"{e} {et}", "%Y-%m-%d %H:%M") if e else None
        except Exception:
            print("❌ Invalid date/time format.")
            return False
        if not start_date or not end_date or start_date > end_date:
            print("❌ Invalid custom date range.")
            return False
    elif choice == "entire":
        # Use per-dataset default start/end by leaving dates unset
        start_date = None
        end_date = None
    elif choice == "overlapping":
        # Server computes intersection across datasets; leave dates unset
        start_date = None
        end_date = None

    session.selected_start_date = start_date
    session.selected_end_date = end_date
    session.selected_date_mode = choice
    save_session_state(session)
    if choice == 'entire':
        print("📅 Date range set: Entire period of record")
    elif choice == 'overlapping':
        print("📅 Date range set: Overlapping period of record (intersection)")
    elif choice in ("days30", "months6", "years1"):
        label = {
            "days30": "Last 30 days",
            "months6": "Last 6 months",
            "years1": "Last 1 year",
        }[choice]
        print(f"📅 Date range set: {label}")
    else:
        # Show time if provided
        def _fmt(dt: datetime) -> str:
            return dt.strftime('%Y-%m-%d %H:%M') if (dt.hour or dt.minute) else dt.strftime('%Y-%m-%d')
        print(f"📅 Date range set: {_fmt(start_date)} to {_fmt(end_date)}")
    return True


def _interactive_select_export_options(session: RISMASession) -> bool:
    """Prompt for export options such as TimeZone, Calendar, Interval, etc., and persist them."""
    if not HAS_QUESTIONARY:
        print("❌ Interactive export options require 'questionary'. Install with: pip install questionary")
        return False
    # TimeZone friendly list
    def _format_tz_label(offset: int) -> str:
        names = { -10: "HST", -9: "AKST", -8: "PST", -7: "MST", -6: "CST", -5: "EST", 0: "UTC", 1: "CET", 2: "EET", 3: "MSK", 8: "CST(China)", 9: "JST", 10: "AEST", 12: "NZST" }
        if offset == 0:
            return "UTC"
        sign = "+" if offset > 0 else "-"
        abbr = names.get(offset)
        return f"UTC{sign}{abs(offset)}" + (f" ({abbr})" if abbr else "")

    def _tz_choices():
        # Integer offsets typically supported by AQWP
        offsets = list(range(-12, 15))
        return [Choice(title=_format_tz_label(o), value=o) for o in offsets]

    tz_choices = [Choice(title="Server default (undefined)", value=None)] + _tz_choices()
    session.export_timezone = questionary.select(
        "Time zone:",
        choices=tz_choices,
        default=(session.export_timezone if session.export_timezone is not None else None),
        qmark="⏱ ",
    ).ask()

    # Calendar
    calendars = [Choice("Server default (undefined)", None), "CALENDARYEAR", "CALENDARMONTH", "CALENDARWEEK", "CALENDARDAY"]
    session.export_calendar = questionary.select(
        "Calendar grouping:", choices=calendars, default=(session.export_calendar if session.export_calendar is not None else None), qmark="📅"
    ).ask()

    # Interval (align with API naming)
    intervals = [Choice("Server default (undefined)", None), "PointsAsRecorded", "Hourly", "Daily", "Weekly", "Monthly"]
    session.export_interval = questionary.select(
        "Interval:", choices=intervals, default=(session.export_interval if session.export_interval is not None else None), qmark="⏲ "
    ).ask()

    # Step
    step_text = questionary.text(
        "Step (integer, leave empty for undefined):",
        default=(str(session.export_step) if session.export_step is not None else ""),
        qmark="➕",
    ).ask()
    try:
        session.export_step = int(step_text) if step_text is not None and step_text != "" else None
    except Exception:
        session.export_step = None

    # TimeAligned, RoundData
    session.export_time_aligned = questionary.select(
        "Time aligned?",
        choices=[Choice("Server default (undefined)", None), Choice("True", True), Choice("False", False)],
        default=(session.export_time_aligned if isinstance(session.export_time_aligned, bool) else None),
        qmark="🧭",
    ).ask()
    session.export_round_data = questionary.select(
        "Round data?",
        choices=[Choice("Server default (undefined)", None), Choice("True", True), Choice("False", False)],
        default=(session.export_round_data if isinstance(session.export_round_data, bool) else None),
        qmark="⚙ ",
    ).ask()

    # Calculation
    calcs = [Choice("Server default (undefined)", None), "Instantaneous", "Mean", "Sum", "Min", "Max"]
    session.export_calculation = questionary.select(
        "Calculation:", choices=calcs, default=(session.export_calculation if session.export_calculation is not None else None), qmark="🧮"
    ).ask()

    # Extra data types
    session.export_extra_types = questionary.checkbox(
        "Include extra data types (optional):",
        choices=[
            Choice("grade"),
            Choice("approval"),
            Choice("qualifier"),
            Choice("interpolation_type"),
        ],
        qmark="➕",
    ).ask() or []

    # Export format choices
    formats = [Choice("Server default (undefined)", None), "csv", "excel", "json"]
    session.export_format = questionary.select(
        "Export format:", choices=formats, default=(session.export_format if session.export_format is not None else None), qmark="📄"
    ).ask()

    # Output directory (move here to avoid prompting again during download)
    default_dir = session.selected_output_dir or os.path.join(os.path.expanduser("~"), "RISMA_data")
    session.selected_output_dir = questionary.text(
        "Output directory:", default=default_dir, qmark="📁"
    ).ask() or default_dir

    save_session_state(session)
    return True


def run_wizard(session: RISMASession) -> None:
    """Run the end-to-end interactive wizard: params → stations → datasets/filters → download."""
    if not HAS_QUESTIONARY:
        print("❌ The interactive wizard requires 'questionary'. Install with: pip install questionary")
        return
    print("\n" + "=" * 80)
    print("🌱 RISMA CLI - Guided Wizard")
    print(f"   Connected to: {session.portal.server}")
    print("=" * 80)
    try:
        # 1) Parameters
        params = session.load_params()
        selected_params = _interactive_select_params_with_questionary(params)
        if not selected_params:
            print("❌ No parameters selected. Exiting.")
            return
        session.selected_params = selected_params
        save_session_state(session)
        print(f"✅ Selected parameters: {session.selected_params}")

        # 2) Stations
        locations = session.load_locations()
        selected_stations = _interactive_select_stations_with_questionary(locations)
        if not selected_stations:
            print("❌ No stations selected. Exiting.")
            return
        session.selected_stations = selected_stations
        save_session_state(session)
        print(f"✅ Selected stations: {session.selected_stations}")

        # 3) Datasets overview + optional sensor/depth filters
        if not _auto_show_datasets_and_select_filters(session):
            print("❌ No datasets available for the chosen filters. Exiting.")
            return

        # 4) Export options + date range
        if not handle_export_step(session, argparse.Namespace(list_only=False)):
            print("❌ Export configuration not completed. Exiting.")
            return

        # 5) Confirm and prompt download options
        proceed = questionary.confirm(
            "Proceed to download with current selections?",
            default=True,
            qmark="⬇️",
        ).ask()
        if not proceed:
            print("👋 Aborted before download.")
            return
        dl_args = _interactive_download_prompt(session)
        if dl_args is None:
            print("👋 Aborted before download.")
            return
        handle_download_step(session, dl_args)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Wizard error: {e}")


# ----------------------
# Simple state persistence
# ----------------------
def _state_dir() -> str:
    path = os.path.expanduser("~/.risma")
    os.makedirs(path, exist_ok=True)
    return path


def _state_path_for_server(server: str) -> str:
    try:
        host = urlparse(server).netloc or server
        host = host.replace(":", "_")
    except Exception:
        host = "default"
    return os.path.join(_state_dir(), f"state_{host}.json")


def load_session_state(session: RISMASession) -> None:
    path = _state_path_for_server(session.portal.server)
    if not os.path.exists(path):
        return
    try:
        with open(path, "r") as f:
            data = json.load(f)
        session.selected_params = data.get("selected_params", [])
        session.selected_stations = data.get("selected_stations", [])
        session.selected_sensors = data.get("selected_sensors", [])
        session.selected_depths = data.get("selected_depths", [])
        # Dates are stored as ISO strings YYYY-MM-DD
        s = data.get("selected_start_date")
        e = data.get("selected_end_date")
        try:
            session.selected_start_date = datetime.strptime(s, "%Y-%m-%d") if s else None
        except Exception:
            session.selected_start_date = None
        try:
            session.selected_end_date = datetime.strptime(e, "%Y-%m-%d") if e else None
        except Exception:
            session.selected_end_date = None
        session.selected_date_mode = data.get("selected_date_mode")
        session.selected_output_dir = data.get("selected_output_dir")
        session.export_timezone = data.get("export_timezone", session.export_timezone)
        session.export_calendar = data.get("export_calendar", session.export_calendar)
        session.export_interval = data.get("export_interval", session.export_interval)
        session.export_step = data.get("export_step", session.export_step)
        session.export_time_aligned = data.get("export_time_aligned", session.export_time_aligned)
        session.export_round_data = data.get("export_round_data", session.export_round_data)
        session.export_calculation = data.get("export_calculation", session.export_calculation)
        session.export_format = data.get("export_format", session.export_format)
        session.export_extra_types = data.get("export_extra_types", session.export_extra_types)

        # Rehydrate datasets if previously cached
        if data.get("has_selected_datasets"):
            try:
                ds = session.load_datasets()
                session.selected_datasets = ds
            except Exception:
                session.selected_datasets = pd.DataFrame()
    except Exception:
        # Corrupt or unreadable state: ignore silently for robustness
        return


def save_session_state(session: RISMASession) -> None:
    path = _state_path_for_server(session.portal.server)
    data = {
        "selected_params": session.selected_params,
        "selected_stations": session.selected_stations,
        "selected_sensors": session.selected_sensors,
        "selected_depths": session.selected_depths,
        "has_selected_datasets": not session.selected_datasets.empty,
        "selected_start_date": session.selected_start_date.strftime("%Y-%m-%d") if session.selected_start_date else None,
        "selected_end_date": session.selected_end_date.strftime("%Y-%m-%d") if session.selected_end_date else None,
        "selected_date_mode": session.selected_date_mode,
        "selected_output_dir": session.selected_output_dir,
        "export_timezone": session.export_timezone,
        "export_calendar": session.export_calendar,
        "export_interval": session.export_interval,
        "export_step": session.export_step,
        "export_time_aligned": session.export_time_aligned,
        "export_round_data": session.export_round_data,
        "export_calculation": session.export_calculation,
        "export_format": session.export_format,
        "export_extra_types": session.export_extra_types,
    }
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception:
        # Best-effort persistence; do not crash CLI on save failure
        pass


def create_portal(server: str, no_disclaimer: bool, verbose: bool) -> AquariusWebPortal:
    """Create portal object with given parameters"""
    if verbose:
        print(f"Connecting to {server}...")
    
    try:
        portal = AquariusWebPortal(
            server=server,
            auto_accept_disclaimer=not no_disclaimer
        )
        if verbose:
            print("✓ Connected successfully!")
        return portal
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        sys.exit(1)


def create_parser():
    """Create the argument parser"""
    parser = argparse.ArgumentParser(
        description='RISMA CLI - Interactive Real-time In-Situ Soil Monitoring for Agriculture'
    )
    
    # Global options
    parser.add_argument('--server', '-s', 
                       default='agrifood.aquaticinformatics.net',
                       help='Aquarius Web Portal server URL')
    parser.add_argument('--no-disclaimer', 
                       action='store_true',
                       help='Do not automatically accept disclaimers')
    parser.add_argument('--verbose', '-v', 
                       action='store_true',
                       help='Enable verbose output')
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Step 1: Load and select parameters
    params_parser = subparsers.add_parser('params', help='Step 1: Load and select parameters')
    params_parser.add_argument('--select', 
                              nargs='*',
                              help='Parameter names to select (space-separated)')
    params_parser.add_argument('--list-only', 
                              action='store_true',
                              help='Just list available parameters without selection')
    
    # Step 2: Load and select stations
    stations_parser = subparsers.add_parser('stations', help='Step 2: Load and select stations/locations')
    stations_parser.add_argument('--select', 
                                nargs='*',
                                help='Station IDs to select (space-separated)')
    stations_parser.add_argument('--list-only', 
                                action='store_true',
                                help='Open interactive station selection immediately')
    
    # Step 3: Load and select datasets
    datasets_parser = subparsers.add_parser('datasets', help='Step 3: Load and select datasets')
    datasets_parser.add_argument('--sensors', 
                                nargs='*',
                                help='Sensor IDs to filter by')
    datasets_parser.add_argument('--depths', 
                                nargs='*',
                                help='Depth ranges to filter by')
    datasets_parser.add_argument('--list-only', 
                                action='store_true',
                                help='Just list available datasets without selection')

    # Step 4: Export options
    export_parser = subparsers.add_parser('export', help='Step 4: Configure export options and date range')
    export_parser.add_argument('--list-only', action='store_true', help='Show current export options and date range')
    
    # Step 5: Download data
    download_parser = subparsers.add_parser('download', help='Step 5: Download selected data')
    download_parser.add_argument('--start-date', 
                               type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                               help='Start date (YYYY-MM-DD)')
    download_parser.add_argument('--end-date', 
                               type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                               help='End date (YYYY-MM-DD)')
    download_parser.add_argument('--output', '-o', 
                               default='RISMA_data',
                               help='Output directory (default: RISMA_data)')
    download_parser.add_argument('--extra-data-types', 
                               nargs='*',
                               choices=['grade', 'approval', 'qualifier', 'interpolation_type', 'all'],
                               help='Additional data types to include')
    
    # Utility commands
    status_parser = subparsers.add_parser('status', help='Show current selections')
    reset_parser = subparsers.add_parser('reset', help='Reset all selections')
    
    return parser


def handle_params_step(session: RISMASession, args) -> bool:
    """Handle Step 1: Parameter loading and selection"""
    try:
        # Load parameters
        params = session.load_params()
        
        if args.list_only:
            # Directly open interactive selection and then auto-advance
            if not HAS_QUESTIONARY:
                print("❌ Interactive selection requires 'questionary'. Install with: pip install questionary")
                return False
            selected_names = _interactive_select_params_with_questionary(params)
            if not selected_names:
                print("❌ No valid selections.")
                return False
            session.selected_params = selected_names
            print(f"✅ Selected parameters: {session.selected_params}")
            save_session_state(session)
            # Auto-advance to stations selection
            print("\n➡️  Continuing to station selection...")
            _ = handle_stations_step(session, argparse.Namespace(select=None, list_only=True))
            return True

        # Default to interactive selection when no explicit --select values
        if (not args.list_only) and ((args.select is None) or (len(args.select) == 0)):
            if not HAS_QUESTIONARY:
                print("❌ Interactive selection requires 'questionary'. Install with: pip install questionary")
                return False
            selected_names = _interactive_select_params_with_questionary(params)
            if not selected_names:
                print("❌ No valid selections.")
                return False
            session.selected_params = selected_names
            print(f"✅ Selected parameters: {session.selected_params}")
            save_session_state(session)
            save_session_state(session)
            print("\n➡️  Continuing to station selection...")
            _ = handle_stations_step(session, argparse.Namespace(select=None, list_only=True))
            return True
        
        if args.select:
            # Validate selections
            available_names = params.param_name.tolist()
            invalid_params = [p for p in args.select if p not in available_names]
            
            if invalid_params:
                print(f"❌ Invalid parameters: {invalid_params}")
                print(f"Available parameters: {available_names}")
                return False
            
            session.selected_params = args.select
            print(f"✅ Selected parameters: {session.selected_params}")
            save_session_state(session)
            save_session_state(session)
            print("\n➡️  Continuing to station selection...")
            _ = handle_stations_step(session, argparse.Namespace(select=None, list_only=True))
            return True
        
        # If we reach here, it's because args.select has values and was invalid
        # or no valid path matched. Show a helpful hint.
        print("\n💡 Tip: Run 'params' for interactive selection, or use '--list-only' to view options.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    return True


def handle_stations_step(session: RISMASession, args) -> bool:
    """Handle Step 2: Station loading and selection"""
    try:
        if not session.selected_params:
            print("⚠️  Please select parameters first using 'params --select <param_names>'")
            return False
        
        # Load locations
        locations = session.load_locations()

        # Default to interactive selection when no explicit --select values
        if (args.select is None) or (len(args.select) == 0):
            if not HAS_QUESTIONARY:
                print("❌ Interactive selection requires 'questionary'. Install with: pip install questionary")
                return False
            selected_ids = _interactive_select_stations_with_questionary(locations)
            if not selected_ids:
                print("❌ No valid selections.")
                return False
            session.selected_stations = selected_ids
            print(f"✅ Selected stations: {session.selected_stations}")
            save_session_state(session)
            # Auto-advance: show datasets, filters, then export options and download
            if _auto_show_datasets_and_select_filters(session):
                if handle_export_step(session, argparse.Namespace(list_only=False)):
                    proceed = True
                    if HAS_QUESTIONARY:
                        proceed = questionary.confirm(
                            "Proceed to download with current selections?",
                            default=True,
                            qmark="⬇️",
                        ).ask()
                    if proceed:
                        download_args = _interactive_download_prompt(session)
                        if download_args is not None:
                            handle_download_step(session, download_args)
            return True
        
        if args.list_only:
            if not HAS_QUESTIONARY:
                print("❌ Interactive selection requires 'questionary'. Install with: pip install questionary")
                return False
            selected_ids = _interactive_select_stations_with_questionary(locations, prompt_filter=False)
            if not selected_ids:
                print("❌ No valid selections.")
                return False
            session.selected_stations = selected_ids
            print(f"✅ Selected stations: {session.selected_stations}")
            save_session_state(session)
            # Auto-advance: show datasets, filters, then export options and download
            if _auto_show_datasets_and_select_filters(session):
                if handle_export_step(session, argparse.Namespace(list_only=False)):
                    proceed = True
                    if HAS_QUESTIONARY:
                        proceed = questionary.confirm(
                            "Proceed to download with current selections?",
                            default=True,
                            qmark="⬇️",
                        ).ask()
                    if proceed:
                        download_args = _interactive_download_prompt(session)
                        if download_args is not None:
                            handle_download_step(session, download_args)
            return True
        
        if args.select:
            # Validate selections
            available_ids = locations.loc_id.tolist()
            invalid_stations = [s for s in args.select if s not in available_ids]
            
            if invalid_stations:
                print(f"❌ Invalid stations: {invalid_stations}")
                print(f"Available stations: {available_ids}")
                return False
            
            session.selected_stations = args.select
            print(f"✅ Selected stations: {session.selected_stations}")
            save_session_state(session)
            print(f"💡 Next step: Run 'datasets --list-only' to load datasets based on your selections")
            return True
        
        print("\n💡 Tip: Run 'stations' for interactive selection, or use '--list-only' to view options.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    return True


def handle_datasets_step(session: RISMASession, args) -> bool:
    """Handle Step 3: Dataset loading and selection"""
    try:
        # Enforce step order for predictability
        if not session.selected_params:
            print("⚠️  Please select parameters first using 'params --select <param_names>'")
            return False
        
        if not session.selected_stations:
            print("⚠️  Please select stations first using 'stations --select <station_ids>'")
            return False
        
        # Update sensor and depth selections if provided
        if args.sensors:
            session.selected_sensors = args.sensors
        if args.depths:
            session.selected_depths = args.depths
        
        # Load datasets
        datasets = session.load_datasets()
        if datasets.empty:
            print("⚠️  No datasets found matching your selections")
            return False

        # If list-only, just show and cache
        if args.list_only:
            print(f"\n📊 Available datasets based on your selections:")
            print(f"   Parameters: {session.selected_params}")
            print(f"   Stations: {session.selected_stations}")
            headers = ["Station", "Parameter", "Label", "Type", "Sensor", "Depth", "Start", "End"]
            rows = []
            for _, ds in datasets.iterrows():
                sensor = getattr(ds, 'sensor', 'N/A')
                depth = getattr(ds, 'depth', 'N/A')
                dtype = getattr(ds, 'type', 'N/A')
                start = str(ds.dset_start)[:10] if pd.notna(ds.dset_start) else "N/A"
                end = str(ds.dset_end)[:10] if pd.notna(ds.dset_end) else "N/A"
                rows.append([
                    str(ds.loc_id), str(ds.param), str(ds.label), str(dtype), str(sensor), str(depth), start, end
                ])
            _print_table(headers, rows)
            print(f"\nTotal: {len(datasets)} datasets")
            session.selected_datasets = datasets
            save_session_state(session)
            return True

        # Interactive filtering and date selection via questionary
        if HAS_QUESTIONARY:
            # Build filter choices
            df_soil = datasets[datasets.get('type').eq('soil')] if 'type' in datasets.columns else datasets.head(0)
            sensors = sorted(set([s for s in df_soil.get('sensor', pd.Series(dtype=str)).dropna().astype(str).tolist() if s]))
            depths = sorted(set([d for d in df_soil.get('depth', pd.Series(dtype=str)).dropna().astype(str).tolist() if d]))
            selected_sensors: List[str] = []
            selected_depths: List[str] = []
            if sensors:
                selected_sensors = questionary.checkbox(
                    "Select sensors to include (Enter for all):",
                    choices=[Choice(title=s, value=s) for s in sensors],
                    qmark="🧪",
                ).ask() or []
            if depths:
                selected_depths = questionary.checkbox(
                    "Select depths to include (Enter for all):",
                    choices=[Choice(title=d, value=d) for d in depths],
                    qmark="📏",
                ).ask() or []
            session.selected_sensors = selected_sensors
            session.selected_depths = selected_depths
            # Reload with filters and show final table
            datasets = session.load_datasets()
            if datasets.empty:
                print("⚠️  No datasets after applying filters.")
                return False
            headers = ["Station", "Parameter", "Label", "Type", "Sensor", "Depth", "Start", "End"]
            rows = []
            for _, ds in datasets.iterrows():
                sensor = getattr(ds, 'sensor', 'N/A')
                depth = getattr(ds, 'depth', 'N/A')
                dtype = getattr(ds, 'type', 'N/A')
                start = str(ds.dset_start)[:10] if pd.notna(ds.dset_start) else "N/A"
                end = str(ds.dset_end)[:10] if pd.notna(ds.dset_end) else "N/A"
                rows.append([
                    str(ds.loc_id), str(ds.param), str(ds.label), str(dtype), str(sensor), str(depth), start, end
                ])
            print("\n📊 Datasets after filters:")
            _print_table(headers, rows)

            # Cache datasets before date prompt to compute 'entire' bounds
            session.selected_datasets = datasets
            # Date range selection as part of datasets command
            if not _interactive_select_date_range(session, datasets):
                return False
            # Export options selection
            if not _interactive_select_export_options(session):
                return False
        else:
            print("ℹ️  Tip: Install 'questionary' to choose sensors, depths, and dates interactively.")

        # Cache for download and show summary
        session.selected_datasets = datasets
        print(f"\nTotal: {len(datasets)} datasets ready for export configuration")
        print("\n💡 Next step: Run 'export' to configure export options and date range, then 'download'")
        save_session_state(session)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    return True


def handle_download_step(session: RISMASession, args) -> bool:
    """Handle Step 4: Download data"""
    try:
        if session.selected_datasets.empty:
            print("⚠️  No datasets selected. Please run through the steps: params → stations → datasets")
            return False
        
        # Determine date mode and effective dates
        arg_start = getattr(args, 'start_date', None)
        arg_end = getattr(args, 'end_date', None)
        arg_entire = getattr(args, 'entire_period', False)
        start_date = None
        end_date = None
        date_mode = None

        if arg_entire:
            # Explicit entire period selection
            start_date = None
            end_date = None
            date_mode = 'entire'
        elif arg_start or arg_end:
            # Custom range provided on CLI
            now = datetime.now()
            start_date = arg_start
            end_date = arg_end
            if start_date and not end_date:
                end_date = now
            elif end_date and not start_date:
                start_date = end_date - timedelta(days=7)
            date_mode = 'custom'
        elif session.selected_date_mode == 'entire':
            # Use previously chosen entire period
            start_date = None
            end_date = None
            date_mode = 'entire'
        elif session.selected_date_mode == 'overlapping':
            # Use server-side overlapping period
            start_date = None
            end_date = None
            date_mode = 'overlapping'
        elif session.selected_date_mode in ('days30','months6','years1','last7'):
            # Use server-side presets for relative ranges
            start_date = None
            end_date = None
            date_mode = session.selected_date_mode
        elif session.selected_start_date or session.selected_end_date:
            # Use previously saved custom range
            start_date = session.selected_start_date
            end_date = session.selected_end_date
            date_mode = 'custom'
        else:
            # Default to last 7 days
            now = datetime.now()
            end_date = now
            start_date = end_date - timedelta(days=7)
            date_mode = 'last7'
        
        if date_mode == 'entire':
            # Use per-dataset entire period by leaving dates unset
            print("📅 Using entire period of record")
        elif date_mode == 'overlapping':
            print("📅 Using overlapping period of record (intersection)")
        elif date_mode in ('days30','months6','years1','last7'):
            label = {
                'last7': 'Last 7 days',
                'days30': 'Last 30 days',
                'months6': 'Last 6 months',
                'years1': 'Last 1 year',
            }[date_mode]
            print(f"📅 Using preset range: {label}")
        elif start_date and end_date:
            print(f"📅 Using date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        # Validate date order
        if (start_date is not None and end_date is not None) and start_date > end_date:
            print("❌ Start date must be on or before end date.")
            return False

        # Persist the effective date range (custom or entire-overlap leave None)
        session.selected_start_date = start_date
        session.selected_end_date = end_date
        session.selected_date_mode = date_mode
        save_session_state(session)
        
        # Create output directory
        home_directory = os.path.expanduser("~")
        out_dir = os.path.join(home_directory, args.output)
        os.makedirs(out_dir, exist_ok=True)

        print(f"📁 Output directory: {out_dir}")
        print(f"⬇️  Downloading {len(session.selected_datasets)} datasets...")
        
        # Group by station and download
        grouped = session.selected_datasets.groupby('loc_id')
        
        success_count = 0
        for station_id, station_datasets in grouped:
            fmt = (session.export_format or "csv").lower()
            ext = ".csv" if fmt == "csv" else (".xlsx" if fmt == "excel" else ".json")
            output_file = os.path.join(out_dir, f"{station_id}{ext}")
            
            try:
                # Determine DateRange override
                date_range_override = None
                if session.selected_date_mode == 'overlapping':
                    date_range_override = 'OverlappingPeriodOfRecord'
                elif session.selected_date_mode == 'last7':
                    date_range_override = 'Days7'
                elif session.selected_date_mode == 'days30':
                    date_range_override = 'Days30'
                elif session.selected_date_mode == 'months6':
                    date_range_override = 'Months6'
                elif session.selected_date_mode == 'years1':
                    date_range_override = 'Years1'

                data = session.portal.fetch_dataset(
                    dset_names=station_datasets.dset_name.tolist(),
                    start=start_date.strftime('%Y-%m-%d') if start_date and not date_range_override else None,
                    end=end_date.strftime('%Y-%m-%d') if end_date and not date_range_override else None,
                    date_range=date_range_override,
                    extra_data_types=(args.extra_data_types if args.extra_data_types else session.export_extra_types or None),
                    timezone=session.export_timezone,
                    calendar=session.export_calendar,
                    interval=session.export_interval,
                    step=session.export_step,
                    time_aligned=session.export_time_aligned,
                    round_data=session.export_round_data,
                    calculation=session.export_calculation,
                    export_format=session.export_format
                )
                
                # Save according to format
                if fmt == "csv":
                    # data is a DataFrame
                    data.to_csv(output_file, index=False)
                    print(f"  ✅ {station_id}: {len(data)} records → {output_file}")
                else:
                    # data is raw bytes
                    with open(output_file, "wb") as f:
                        f.write(data)
                    print(f"  ✅ {station_id}: saved → {output_file}")
                
                success_count += 1
                
            except Exception as e:
                print(f"  ❌ {station_id}: Error - {e}")
        
        print(f"\n🎉 Download complete!")
        print(f"   Successfully downloaded: {success_count}/{len(grouped)} stations")
        print(f"   Files saved to: {out_dir}")
        
        # Persist output directory
        session.selected_output_dir = out_dir
        save_session_state(session)
        
        # Show summary
        print(f"\n📊 Summary:")
        print(f"   Parameters: {session.selected_params}")
        print(f"   Stations: {session.selected_stations}")
        def _fmt(dt):
            if not dt:
                return 'N/A'
            return dt.strftime('%Y-%m-%d %H:%M') if (dt.hour or dt.minute) else dt.strftime('%Y-%m-%d')
        print(f"   Date range: {_fmt(start_date)} to {_fmt(end_date)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    return True


def handle_status(session: RISMASession) -> bool:
    """Show current session status"""
    print(f"\n📊 Current Session Status:")
    print(f"   Server: {session.portal.server}")
    print(f"   Selected Parameters: {session.selected_params if session.selected_params else 'None'}")
    print(f"   Selected Stations: {session.selected_stations if session.selected_stations else 'None'}")
    print(f"   Selected Sensors: {session.selected_sensors if session.selected_sensors else 'Default'}")
    print(f"   Selected Depths: {session.selected_depths if session.selected_depths else 'Default'}")
    print(f"   Available Datasets: {len(session.selected_datasets) if not session.selected_datasets.empty else 0}")
    # Dates
    if session.selected_date_mode == 'entire':
        print("   Selected Date Range: Entire period of record")
    elif session.selected_date_mode == 'overlapping':
        print("   Selected Date Range: Overlapping period of record")
    elif session.selected_date_mode in ('last7','days30','months6','years1'):
        label = {
            'last7': 'Last 7 days',
            'days30': 'Last 30 days',
            'months6': 'Last 6 months',
            'years1': 'Last 1 year',
        }[session.selected_date_mode]
        print(f"   Selected Date Range: {label}")
    elif session.selected_start_date or session.selected_end_date:
        s = session.selected_start_date.strftime('%Y-%m-%d') if session.selected_start_date else 'N/A'
        e = session.selected_end_date.strftime('%Y-%m-%d') if session.selected_end_date else 'N/A'
        print(f"   Selected Date Range: {s} to {e}")
    else:
        print("   Selected Date Range: None")
    print(f"   Output Folder: {session.selected_output_dir if session.selected_output_dir else 'None'}")
    # Friendly timezone label
    def _fmt_tz(o):
        if o is None:
            return "Server default"
        if o == 0:
            return "UTC"
        sign = "+" if o and o > 0 else "-"
        return f"UTC{sign}{abs(o)}"
    print("   Export Options: "
          f"TimeZone={_fmt_tz(session.export_timezone)}, "
          f"Calendar={session.export_calendar or 'Server default'}, Interval={session.export_interval or 'Server default'}, Step={session.export_step if session.export_step is not None else 'Server default'}, "
          f"TimeAligned={session.export_time_aligned if session.export_time_aligned is not None else 'Server default'}, RoundData={session.export_round_data if session.export_round_data is not None else 'Server default'}, "
          f"Calculation={session.export_calculation or 'Server default'}, Extra={session.export_extra_types or []}")
    
    # Show next step
    if not session.selected_params:
        print(f"\n💡 Next step: Run 'params' to select parameters")
    elif not session.selected_stations:
        print(f"\n💡 Next step: Run 'stations' to select stations")
    elif session.selected_datasets.empty:
        print(f"\n💡 Next step: Run 'datasets' to load datasets")
    else:
        print(f"\n💡 Next step: Run 'download' to download data")
    
    return True


def handle_export_step(session: RISMASession, args) -> bool:
    """Configure export options and date range."""
    if session.selected_datasets.empty:
        print("⚠️  No datasets selected. Run 'datasets' first.")
        return False
    if getattr(args, 'list_only', False):
        print("\n🧰 Current export options:")
        print(f"   TimeZone: {session.export_timezone}")
        print(f"   Calendar: {session.export_calendar}")
        print(f"   Interval: {session.export_interval}")
        print(f"   Step: {session.export_step}")
        print(f"   TimeAligned: {session.export_time_aligned}")
        print(f"   RoundData: {session.export_round_data}")
        print(f"   Calculation: {session.export_calculation}")
        if session.selected_date_mode == 'entire':
            print("   Date Range: Entire period of record")
        elif session.selected_start_date or session.selected_end_date:
            s = session.selected_start_date.strftime('%Y-%m-%d') if session.selected_start_date else 'N/A'
            e = session.selected_end_date.strftime('%Y-%m-%d') if session.selected_end_date else 'N/A'
            print(f"   Date Range: {s} to {e}")
        else:
            print("   Date Range: None")
        print(f"   Extra data types: {session.export_extra_types or []}")
        return True

    # Interactive export options (date + options)
    if not HAS_QUESTIONARY:
        print("❌ Interactive export options require 'questionary'. Install with: pip install questionary")
        return False
    # Date first
    if not _interactive_select_date_range(session, session.selected_datasets):
        return False
    # Then other export options
    ok = _interactive_select_export_options(session)
    if ok:
        print("✅ Export options saved.")
    return ok


def handle_reset(session: RISMASession) -> bool:
    """Reset all selections"""
    session.reset_selections()
    print("🔄 All selections have been reset")
    print("💡 Next step: Run 'params' to start over")
    save_session_state(session)
    return True


def run_interactive_mode(session: RISMASession, args):
    """Run interactive mode with step-by-step guidance"""
    print(f"\n{'='*80}")
    print(f"🌱 RISMA CLI - Interactive Mode")
    print(f"   Connected to: {session.portal.server}")
    print(f"{'='*80}")
    print("📋 Step-by-Step Workflow:")
    print("  1. params   - Load and select parameters")
    print("  2. stations - Load and select stations/locations")
    print("  3. datasets - Load datasets based on selections")
    print("  4. download - Download selected data")
    print("")
    print("🛠️  Utility Commands:")
    print("  status - Show current selections")
    print("  reset  - Reset all selections")
    print("  help   - Show this help message")
    print("  exit   - Exit the program")
    print("="*80)
    
    while True:
        try:
            command_input = input("\n🔍 Enter command: ").strip()
            if not command_input:
                continue
            
            if command_input.lower() in ['exit', 'quit']:
                print("👋 Goodbye!")
                break
            
            if command_input.lower() == 'help':
                print("\n📋 Step-by-Step Workflow:")
                print("  1. params   - Load and select parameters")
                print("  2. stations - Load and select stations/locations")
                print("  3. datasets - Load datasets based on selections")
                print("  4. download - Download selected data")
                print("")
                print("🛠️  Utility Commands:")
                print("  status - Show current selections")
                print("  reset  - Reset all selections")
                print("")
                print("💡 Example usage:")
                print("  params --select 'Air Temp' 'Soil Moisture'")
                print("  stations --select RISMA_MB1 RISMA_MB2")
                print("  datasets")
                print("  download --start-date 2024-01-01 --end-date 2024-01-31")
                continue
            
            # Parse the command
            try:
                parser = create_parser()
                cmd_args = shlex.split(command_input)
                
                # # Add global args
                # if not any(arg in cmd_args for arg in ['--server', '-s']):
                #     cmd_args.extend(['--server', args.server])
                # if args.no_disclaimer and '--no-disclaimer' not in cmd_args:
                #     cmd_args.append('--no-disclaimer')
                # if args.verbose and '--verbose' not in cmd_args and '-v' not in cmd_args:
                #     cmd_args.append('--verbose')
                
                parsed_args = parser.parse_args(cmd_args)
                
                # Execute the command
                if parsed_args.command == 'params':
                    handle_params_step(session, parsed_args)
                elif parsed_args.command == 'stations':
                    handle_stations_step(session, parsed_args)
                elif parsed_args.command == 'datasets':
                    handle_datasets_step(session, parsed_args)
                elif parsed_args.command == 'download':
                    handle_download_step(session, parsed_args)
                elif parsed_args.command == 'status':
                    handle_status(session)
                elif parsed_args.command == 'reset':
                    handle_reset(session)
                else:
                    print("❌ Unknown command. Type 'help' for available commands.")
                    
            except SystemExit:
                print("❌ Invalid command or arguments. Type 'help' for usage.")
                continue
            except Exception as e:
                print(f"❌ Error executing command: {e}")
                continue
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            print("\n👋 Goodbye!")
            break


def cli():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Create portal and session
    portal = create_portal(args.server, args.no_disclaimer, args.verbose)
    session = RISMASession(portal, args.verbose)
    # Load any prior selections for this server
    load_session_state(session)
    
    # Check if a command was provided
    if args.command:
        # Execute the specific command
        if args.command == 'params':
            handle_params_step(session, args)
        elif args.command == 'stations':
            handle_stations_step(session, args)
        elif args.command == 'datasets':
            handle_datasets_step(session, args)
        elif args.command == 'export':
            handle_export_step(session, args)
        elif args.command == 'download':
            handle_download_step(session, args)
        elif args.command == 'status':
            handle_status(session)
        elif args.command == 'reset':
            handle_reset(session)
        else:
            print("❌ Unknown command.")
            sys.exit(1)
    else:
        # Default to guided wizard flow
        run_wizard(session)


if __name__ == '__main__':
    cli()
