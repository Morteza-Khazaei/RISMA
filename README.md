# Real‐Time In‐Situ Soil Monitoring for Agriculture (RISMA) network

## Overview

The Real-time In-Situ Soil Monitoring for Agriculture (RISMA) network provides accurate, near real-time soil and weather data from various agricultural regions across Canada. Established in 2010, RISMA is a collaborative effort between Agriculture and Agri-Food Canada (AAFC) and its partners, including Environment Canada, the Global Institute for Water Security (University of Saskatchewan), and the University of Guelph.

The network captures a wide range of data points every 15 minutes, including:
*   **Soil Conditions:** Soil moisture and temperature at multiple depths (0-5cm, 5cm, 20cm, 50cm, 100cm, and 150cm).
*   **Meteorological Data:** Precipitation, air temperature, relative humidity, wind speed, and wind direction.

As of 2015, the network consists of 22 stations located in Manitoba, Saskatchewan, and Ontario. The data from these stations is crucial for applications such as flood and yield forecasting, as well as for validating satellite-based environmental products.

Please see the quick user guide for more information on how to use this Portal by [clicking here](https://agrifood.aquaticinformatics.net/AQWebPortal/Data/GetFile/GettingStartedGuide)

## Getting Started

To get started with RISMA, follow the steps below.

### Prerequisites

*   Python 3.8 or higher
*   Jupyter Notebook or JupyterLab
*   Git

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/morteza-khazaei/RISMA.git
    cd RISMA
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: `venv\Scripts\activate`
    ```

3. **Install RISMA:**

    ```bash
    pip install .
    ```

### Running the Tutorial

The `tutorial.ipynb` notebook provides a comprehensive guide to using RISMA. To run it:

1.  **Start Jupyter:**

    ```bash
    jupyter notebook
    ```

2.  **Open the `tutorial.ipynb` notebook:**

## Usage

### Command-Line Interface (CLI)

RISMA ships with an interactive CLI that guides you from choosing parameters all the way to downloading data. You can use the guided wizard, or run individual subcommands.

Run the guided wizard:

```bash
risma
```

This launches a fully interactive (arrow keys/checkboxes) flow:

1) Select parameters → 2) Select stations (grouped by province) → 3) Review/filter datasets (sensors, depths) → 4) Configure export options (date range, format, time zone, etc.) → 5) Download.

Selections persist per server under `~/.risma/state_<host>.json`. You can resume later and `risma status` will show your current selections.

Alternatively, you can use subcommands directly:

- Global options:
  - `--server`, `-s`: Aquarius server (default: `agrifood.aquaticinformatics.net`)
  - `--verbose`, `-v`: Verbose output

Get help:

```bash
risma --help
risma params --help
```

#### Workflow (subcommands)

1. Parameters (`params`)
- Interactive (default): `risma params`
- Select explicitly: `risma params --select "Air Temp" "Soil Moisture"`
- List only: `risma params --list-only`

2. Stations (`stations`)
- Interactive (default): `risma stations`
  - Stations are grouped by Province and naturally sorted by ID (e.g., MB1, MB2, …, MB10)
- Select explicitly: `risma stations --select RISMA_MB1 RISMA_MB2`

3. Datasets (`datasets`)
- Interactive filtering: `risma datasets`
  - Shows datasets for your selections
  - Optional filters: sensors and depths
- List only: `risma datasets --list-only`

4. Export Options (`export`)
- Configure everything needed for export and reuse later:
  - Date range: Entire, Overlapping, Last 7/30 days, Last 6 months, Last 1 year, or Custom (with HH:MM times)
  - TimeZone: friendly list (UTC, UTC-6 (CST), UTC+10 (AEST), …) or “Server default (undefined)”
  - Calendar: CALENDARYEAR/MONTH/WEEK/DAY or undefined
  - Interval: PointsAsRecorded/Hourly/Daily/Weekly/Monthly or undefined
  - Step: integer (leave empty for undefined)
  - TimeAligned: True/False/undefined
  - RoundData: True/False/undefined
  - Calculation: Instantaneous/Mean/Sum/Min/Max or undefined
  - Extra data types: grade, approval, qualifier, interpolation_type (multi-select)
  - Export format: csv, excel, json (or undefined)
  - Output folder: where files will be written

5. Download (`download`)
- Uses your saved export options. You can still override with flags (e.g., `--start-date/--end-date`).
- Files are written per-station; extension matches selected format (`.csv`, `.xlsx`, `.json`).
- Date range behavior:
  - Entire: each dataset’s full period (per-dataset start/end)
  - Overlapping: intersection across selected datasets
  - Presets: Days7/Days30/Months6/Years1 map to the server’s DateRange
  - Custom: sends `StartTime`/`EndTime` with HH:MM precision

#### Status and Reset

```bash
risma status  # Show server, selections, date range, export options, and output folder
risma reset   # Clear all selections and export options
```

### Notes

- Interactive UI requires the `questionary` library (installed with RISMA).
- “Server default (undefined)” means the option is omitted in the export request so the server uses its default.
- The CLI stores state per server at `~/.risma/state_<host>.json`.
