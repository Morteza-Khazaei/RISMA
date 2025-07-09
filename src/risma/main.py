#!/usr/bin/env python3
"""
RISMA CLI - Command Line Interface for RISMA using Click
"""

import os
import sys
from datetime import datetime, timedelta

import click
import pandas as pd

from risma import AquariusWebPortal


@click.group()
@click.option('--server', '-s', default='agrifood.aquaticinformatics.net', 
              help='Aquarius Web Portal server URL')
@click.option('--no-disclaimer', is_flag=True, 
              help='Do not automatically accept disclaimers')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, server, no_disclaimer, verbose):
    """RISMA CLI - Real-time In-Situ Soil Monitoring for Agriculture"""
    ctx.ensure_object(dict)
    ctx.obj['server'] = server
    ctx.obj['accept_disclaimer'] = not no_disclaimer
    ctx.obj['verbose'] = verbose


@cli.command()
@click.pass_context
def params(ctx):
    """List available parameters"""
    try:
        portal = AquariusWebPortal(
            server=ctx.obj['server'], 
            auto_accept_disclaimer=ctx.obj['accept_disclaimer']
        )
        
        click.echo(f"\nAvailable parameters from {ctx.obj['server']}:")
        click.echo("-" * 60)
        click.echo(f"{'ID':<5} {'Name':<20} {'Description':<30}")
        click.echo("-" * 60)
        
        for _, param in portal.params.iterrows():
            click.echo(f"{param.param_id:<5} {param.param_name:<20} {param.param_desc:<30}")
        
        click.echo(f"\nTotal: {len(portal.params)} parameters")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
@click.option('--stations', multiple=True, help='Station IDs to filter by')
def locations(ctx, stations):
    """List available locations"""
    try:
        portal = AquariusWebPortal(
            server=ctx.obj['server'], 
            auto_accept_disclaimer=ctx.obj['accept_disclaimer']
        )
        locations = portal.fetch_locations(stations=list(stations) if stations else None)
        
        click.echo(f"\nAvailable locations from {ctx.obj['server']}:")
        click.echo("-" * 80)
        click.echo(f"{'ID':<15} {'Name':<25} {'Type':<15} {'Lat':<10} {'Lon':<10}")
        click.echo("-" * 80)
        
        for _, loc in locations.iterrows():
            lat = f"{loc.lat:.4f}" if pd.notna(loc.lat) else "N/A"
            lon = f"{loc.lon:.4f}" if pd.notna(loc.lon) else "N/A"
            click.echo(f"{loc.loc_id:<15} {loc.loc_name:<25} {loc.loc_type:<15} {lat:<10} {lon:<10}")
        
        click.echo(f"\nTotal: {len(locations)} locations")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--stations', multiple=True, help='Station IDs to filter by')
@click.option('--param-names', multiple=True, 
              help='Parameter names (default: Air Temp, Soil temperature, Soil Moisture)')
@click.option('--sensors', multiple=True, help='Sensor IDs to filter by')
@click.option('--depths', multiple=True, help='Depth ranges (e.g., "0 to 5 cm")')
@click.pass_context
def datasets(ctx, stations, param_names, sensors, depths):
    """List available datasets"""
    try:
        portal = AquariusWebPortal(
            server=ctx.obj['server'], 
            auto_accept_disclaimer=ctx.obj['accept_disclaimer']
        )
        
        datasets = portal.fetch_datasets(
            param_names=list(param_names) if param_names else ['Air Temp', 'Soil temperature', 'Soil Moisture'],
            stations=list(stations) if stations else ["RISMA_MB1", "RISMA_MB2", "RISMA_MB3"],
            sensors=list(sensors) if sensors else ['average'],
            depths=list(depths) if depths else ['0 to 5 cm', '5 cm']
        )
        
        click.echo(f"\nAvailable datasets:")
        click.echo("-" * 120)
        click.echo(f"{'Station':<15} {'Parameter':<15} {'Label':<25} {'Type':<10} {'Sensor':<8} {'Depth':<12} {'Start':<12} {'End':<12}")
        click.echo("-" * 120)
        
        for _, ds in datasets.iterrows():
            sensor = getattr(ds, 'sensor', 'N/A')
            depth = getattr(ds, 'depth', 'N/A')
            dtype = getattr(ds, 'type', 'N/A')
            start = str(ds.dset_start)[:10] if pd.notna(ds.dset_start) else "N/A"
            end = str(ds.dset_end)[:10] if pd.notna(ds.dset_end) else "N/A"
            
            click.echo(f"{ds.loc_id:<15} {ds.param:<15} {ds.label:<25} {dtype:<10} {sensor:<8} {depth:<12} {start:<12} {end:<12}")
        
        click.echo(f"\nTotal: {len(datasets)} datasets")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--stations', multiple=True, required=True, 
              help='Station IDs to download data from')
@click.option('--start-date', type=click.DateTime(['%Y-%m-%d']), 
              help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(['%Y-%m-%d']), 
              help='End date (YYYY-MM-DD)')
@click.option('--output', '-o', default='./data', 
              help='Output directory (default: ./data)')
@click.option('--param-names', multiple=True, 
              help='Parameter names (default: Air Temp, Soil temperature, Soil Moisture)')
@click.option('--sensors', multiple=True, help='Sensor IDs to filter by')
@click.option('--depths', multiple=True, help='Depth ranges (e.g., "0 to 5 cm")')
@click.option('--extra-data-types', multiple=True, 
              type=click.Choice(['grade', 'approval', 'qualifier', 'interpolation_type', 'all']),
              help='Additional data types to include')
@click.pass_context
def download(ctx, stations, start_date, end_date, output, param_names, sensors, depths, extra_data_types):
    """Download data from the portal"""
    try:
        portal = AquariusWebPortal(
            server=ctx.obj['server'], 
            auto_accept_disclaimer=ctx.obj['accept_disclaimer']
        )
        
        # Default to last 7 days if no dates specified
        if not start_date and not end_date:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            if ctx.obj['verbose']:
                click.echo(f"Using last 7 days: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Use defaults if no parameters specified
        if not param_names:
            param_names = ['Air Temp', 'Soil temperature', 'Soil Moisture']
            if ctx.obj['verbose']:
                click.echo(f"Using default parameters: {list(param_names)}")
        
        # Fetch datasets
        with click.progressbar(length=1, label='Fetching datasets') as bar:
            datasets = portal.fetch_datasets(
                param_names=list(param_names),
                stations=list(stations),
                sensors=list(sensors) if sensors else [],
                depths=list(depths) if depths else []
            )
            bar.update(1)
        
        if datasets.empty:
            click.echo("No datasets found matching the criteria.")
            return
        
        click.echo(f"Found {len(datasets)} datasets")
        
        # Create output directory
        os.makedirs(output, exist_ok=True)
        
        # Group by station and download
        grouped = datasets.groupby('loc_id')
        
        with click.progressbar(grouped, label='Downloading data') as bar:
            for station_id, station_datasets in bar:
                output_file = os.path.join(output, f"{station_id}.csv")
                
                try:
                    data = portal.fetch_dataset(
                        dset_names=station_datasets.dset_name.tolist(),
                        start=start_date.strftime('%Y-%m-%d') if start_date else None,
                        end=end_date.strftime('%Y-%m-%d') if end_date else None,
                        extra_data_types=list(extra_data_types) if extra_data_types else None
                    )
                    
                    # Save to CSV
                    data.to_csv(output_file, index=False)
                    if ctx.obj['verbose']:
                        click.echo(f"  ✓ Saved {len(data)} records to {output_file}")
                    
                except Exception as e:
                    click.echo(f"  ✗ Error downloading data for {station_id}: {e}", err=True)
        
        click.echo(f"\nDownload complete. Files saved to: {output}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()