#!/usr/bin/env python3
"""
RISMA CLI - Interactive Step-by-Step Command Line Interface
"""

import os
import sys
import shlex
import argparse
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import pandas as pd

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
        
        param_names = self.selected_params if self.selected_params else ['Air Temp', 'Soil temperature', 'Soil Moisture']
        stations = self.selected_stations if self.selected_stations else None
        sensors = self.selected_sensors if self.selected_sensors else ['average']
        depths = self.selected_depths if self.selected_depths else ['0 to 5 cm', '5 cm']
        
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
                                help='Just list available stations without selection')
    
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
    
    # Step 4: Download data
    download_parser = subparsers.add_parser('download', help='Step 4: Download selected data')
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
                               choices=['grade', 'approval', 'qualifier', 'interpolation_type', 'gaplevel', 'all'],
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
            print(f"\n📋 Available parameters from {session.portal.server}:")
            print("-" * 80)
            print(f"{'ID':<5} {'Name':<25} {'Description':<40}")
            print("-" * 80)
            
            for _, param in params.iterrows():
                desc = param.param_desc[:37] + "..." if len(param.param_desc) > 40 else param.param_desc
                print(f"{param.param_id:<5} {param.param_name:<25} {desc:<40}")
            
            print(f"\nTotal: {len(params)} parameters")
            print("\n💡 Next step: Run 'params --select <param_names0> <param_names1> ...' to select parameters")
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
            print(f"\n💡 Next step: Run 'stations --list-only' to load and select stations")
            return True
        
        # Show current selections if any
        if session.selected_params:
            print(f"✅ Currently selected parameters: {session.selected_params}")
        
        # Interactive selection
        print(f"\n📋 Available parameters from {session.portal.server}:")
        print("-" * 80)
        print(f"{'ID':<5} {'Name':<25} {'Description':<40}")
        print("-" * 80)
        
        for _, param in params.iterrows():
            desc = param.param_desc[:37] + "..." if len(param.param_desc) > 40 else param.param_desc
            marker = "✓" if param.param_name in session.selected_params else " "
            print(f"{marker} {param.param_id:<5} {param.param_name:<25} {desc:<40}")
        
        print(f"\nTotal: {len(params)} parameters")
        print("\n💡 Usage: 'params --select <param_names>' or 'params --list-only'")
        
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
        
        if args.list_only:
            print(f"\n🏢 Available stations from {session.portal.server}:")
            print("-" * 100)
            print(f"{'ID':<15} {'Name':<30} {'Type':<15} {'Lat':<10} {'Lon':<10} {'Province':<10}")
            print("-" * 100)
            
            for _, loc in locations.iterrows():
                lat = f"{loc.lat:.4f}" if pd.notna(loc.lat) else "N/A"
                lon = f"{loc.lon:.4f}" if pd.notna(loc.lon) else "N/A"
                province = getattr(loc, 'province', 'N/A')
                print(f"{loc.loc_id:<15} {loc.loc_name:<30} {loc.loc_type:<15} {lat:<10} {lon:<10} {province:<10}")
            
            print(f"\nTotal: {len(locations)} stations")
            print("\n💡 Next step: Run 'stations --select <station_ids>' to select stations")
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
            print(f"💡 Next step: Run 'datasets --list-only' to load datasets based on your selections")
            return True
        
        # Show current selections
        if session.selected_stations:
            print(f"✅ Currently selected stations: {session.selected_stations}")
        
        # Interactive display
        print(f"\n🏢 Available stations from {session.portal.server}:")
        print("-" * 100)
        print(f"{'ID':<15} {'Name':<30} {'Type':<15} {'Lat':<10} {'Lon':<10} {'Province':<10}")
        print("-" * 100)
        
        for _, loc in locations.iterrows():
            lat = f"{loc.lat:.4f}" if pd.notna(loc.lat) else "N/A"
            lon = f"{loc.lon:.4f}" if pd.notna(loc.lon) else "N/A"
            province = getattr(loc, 'province', 'N/A')
            marker = "✓" if loc.loc_id in session.selected_stations else " "
            print(f"{marker} {loc.loc_id:<15} {loc.loc_name:<30} {loc.loc_type:<15} {lat:<10} {lon:<10} {province:<10}")
        
        print(f"\nTotal: {len(locations)} stations")
        print("\n💡 Usage: 'stations --select <station_ids>' or 'stations --list-only'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    return True


def handle_datasets_step(session: RISMASession, args) -> bool:
    """Handle Step 3: Dataset loading and selection"""
    try:
        # if not session.selected_params:
        #     print("⚠️  Please select parameters first using 'params --select <param_names>'")
        #     return False
        
        # if not session.selected_stations:
        #     print("⚠️  Please select stations first using 'stations --select <station_ids>'")
        #     return False
        
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
        
        if args.list_only:
            print(f"\n📊 Available datasets based on your selections:")
            print(f"   Parameters: {session.selected_params}")
            print(f"   Stations: {session.selected_stations}")
            print("-" * 130)
            print(f"{'Station':<12} {'Parameter':<15} {'Label':<25} {'Type':<10} {'Sensor':<8} {'Depth':<12} {'Start':<12} {'End':<12}")
            print("-" * 130)
            
            for _, ds in datasets.iterrows():
                sensor = getattr(ds, 'sensor', 'N/A')
                depth = getattr(ds, 'depth', 'N/A')
                dtype = getattr(ds, 'type', 'N/A')
                start = str(ds.dset_start)[:10] if pd.notna(ds.dset_start) else "N/A"
                end = str(ds.dset_end)[:10] if pd.notna(ds.dset_end) else "N/A"
                
                print(f"{ds.loc_id:<12} {ds.param:<15} {ds.label:<25} {dtype:<10} {sensor:<8} {depth:<12} {start:<12} {end:<12}")
            
            print(f"\nTotal: {len(datasets)} datasets")
            print("\n💡 Next step: Run 'download --start-date YYYY-MM-DD --end-date YYYY-MM-DD' to download the data")
            return True
        
        # Store the datasets for download
        session.selected_datasets = datasets
        
        print(f"\n📊 Loaded {len(datasets)} datasets based on your selections:")
        print(f"   Parameters: {session.selected_params}")
        print(f"   Stations: {session.selected_stations}")
        
        if session.selected_sensors:
            print(f"   Sensors: {session.selected_sensors}")
        if session.selected_depths:
            print(f"   Depths: {session.selected_depths}")
        
        print("-" * 130)
        print(f"{'Station':<12} {'Parameter':<15} {'Label':<25} {'Type':<10} {'Sensor':<8} {'Depth':<12} {'Start':<12} {'End':<12}")
        print("-" * 130)
        
        for _, ds in datasets.iterrows():
            sensor = getattr(ds, 'sensor', 'N/A')
            depth = getattr(ds, 'depth', 'N/A')
            dtype = getattr(ds, 'type', 'N/A')
            start = str(ds.dset_start)[:10] if pd.notna(ds.dset_start) else "N/A"
            end = str(ds.dset_end)[:10] if pd.notna(ds.dset_end) else "N/A"
            
            print(f"{ds.loc_id:<12} {ds.param:<15} {ds.label:<25} {dtype:<10} {sensor:<8} {depth:<12} {start:<12} {end:<12}")
        
        print(f"\nTotal: {len(datasets)} datasets ready for download")
        print("\n💡 Next step: Run 'download' to download the data")
        print("   Optional: Add date range with --start-date YYYY-MM-DD --end-date YYYY-MM-DD")
        
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
        
        # Default to last 7 days if no dates specified
        start_date = args.start_date
        end_date = args.end_date
        
        if not start_date and not end_date:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            print(f"📅 Using last 7 days: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
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
            output_file = os.path.join(out_dir, f"{station_id}.csv")
            
            try:
                data = session.portal.fetch_dataset(
                    dset_names=station_datasets.dset_name.tolist(),
                    start=start_date.strftime('%Y-%m-%d') if start_date else None,
                    end=end_date.strftime('%Y-%m-%d') if end_date else None,
                    extra_data_types=args.extra_data_types if args.extra_data_types else None
                )
                
                # Save to CSV
                data.to_csv(output_file, index=False)
                print(f"  ✅ {station_id}: {len(data)} records → {output_file}")
                
                success_count += 1
                
            except Exception as e:
                print(f"  ❌ {station_id}: Error - {e}")
        
        print(f"\n🎉 Download complete!")
        print(f"   Successfully downloaded: {success_count}/{len(grouped)} stations")
        print(f"   Files saved to: {out_dir}")
        
        # Show summary
        print(f"\n📊 Summary:")
        print(f"   Parameters: {session.selected_params}")
        print(f"   Stations: {session.selected_stations}")
        print(f"   Date range: {start_date.strftime('%Y-%m-%d') if start_date else 'N/A'} to {end_date.strftime('%Y-%m-%d') if end_date else 'N/A'}")
        
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


def handle_reset(session: RISMASession) -> bool:
    """Reset all selections"""
    session.reset_selections()
    print("🔄 All selections have been reset")
    print("💡 Next step: Run 'params' to start over")
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
    
    # Check if a command was provided
    if args.command:
        # Execute the specific command
        if args.command == 'params':
            handle_params_step(session, args)
        elif args.command == 'stations':
            handle_stations_step(session, args)
        elif args.command == 'datasets':
            handle_datasets_step(session, args)
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
        # Interactive mode
        run_interactive_mode(session, args)


if __name__ == '__main__':
    cli()