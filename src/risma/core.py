import os
import time
import datetime
import requests
import zipfile
import io
from urllib.parse import quote


class RISMA:
    # Dictionary of dataset names from your input
    CATEGORIZED_DATA = {
        'Air Temp': {'Air temperature': 'Air Temp.Air temperature'},
        'Precip Total': {'Precipitation totals': 'Precip Total.Precipitation totals'},
        'Rel Humidity': {'Relative humidity': 'Rel Humidity.Relative humidity'},
        'Soil Moisture': {
            '0 to 5 cm': {
                'average': 'Soil Moisture.Soil water content 0 to 5 cm depth',
                'sensor': {
                    '1': 'Soil Moisture.Soil water content 0 to 5 cm depth sensor 1',
                    '2': 'Soil Moisture.Soil water content 0 to 5 cm depth sensor 2',
                    '3': 'Soil Moisture.Soil water content 0 to 5 cm depth sensor 3'
                }
            },
            '5 cm': {
                'average': 'Soil Moisture.Soil water content 5 cm depth',
                'sensor': {
                    '1': 'Soil Moisture.Soil water content 5 cm depth sensor 1',
                    '2': 'Soil Moisture.Soil water content 5 cm depth sensor 2',
                    '3': 'Soil Moisture.Soil water content 5 cm depth sensor 3'
                }
            },
            '20 cm': {
                'average': 'Soil Moisture.Soil water content 20 cm depth',
                'sensor': {
                    '1': 'Soil Moisture.Soil water content 20 cm depth sensor 1',
                    '2': 'Soil Moisture.Soil water content 20 cm depth sensor 2',
                    '3': 'Soil Moisture.Soil water content 20 cm depth sensor 3'
                }
            },
            '50 cm': {
                'average': 'Soil Moisture.Soil water content 50 cm depth',
                'sensor': {
                    '1': 'Soil Moisture.Soil water content 50 cm depth sensor 1',
                    '2': 'Soil Moisture.Soil water content 50 cm depth sensor 2',
                    '3': 'Soil Moisture.Soil water content 50 cm depth sensor 3'
                }
            },
            '100 cm': {
                'average': 'Soil Moisture.Soil water content 100 cm depth',
                'sensor': {
                    '1': 'Soil Moisture.Soil water content 100 cm depth sensor 1',
                    '2': 'Soil Moisture.Soil water content 100 cm depth sensor 2',
                    '3': 'Soil Moisture.Soil water content 100 cm depth sensor 3'
                }
            }
        },
        'Soil temperature': {
            '0 to 5 cm': {
                'average': 'Soil temperature.Soil temperature 0 to 5 cm depth',
                'sensor': {
                    '1': 'Soil temperature.Soil temperature 0 to 5 cm depth sensor 1',
                    '2': 'Soil temperature.Soil temperature 0 to 5 cm depth sensor 2',
                    '3': 'Soil temperature.Soil temperature 0 to 5 cm depth sensor 3'
                }
            },
            '5 cm': {
                'average': 'Soil temperature.Soil temperature 5 cm depth',
                'sensor': {
                    '1': 'Soil temperature.Soil temperature 5 cm depth sensor 1',
                    '2': 'Soil temperature.Soil temperature 5 cm depth sensor 2',
                    '3': 'Soil temperature.Soil temperature 5 cm depth sensor 3'
                }
            },
            '20 cm': {
                'average': 'Soil temperature.Soil temperature 20 cm depth',
                'sensor': {
                    '1': 'Soil temperature.Soil temperature 20 cm depth sensor 1',
                    '2': 'Soil temperature.Soil temperature 20 cm depth sensor 2',
                    '3': 'Soil temperature.Soil temperature 20 cm depth sensor 3'
                }
            },
            '50 cm': {
                'average': 'Soil temperature.Soil temperature 50 cm depth',
                'sensor': {
                    '1': 'Soil temperature.Soil temperature 50 cm depth sensor 1',
                    '2': 'Soil temperature.Soil temperature 50 cm depth sensor 2',
                    '3': 'Soil temperature.Soil temperature 50 cm depth sensor 3'
                }
            },
            '100 cm': {
                'average': 'Soil temperature.Soil temperature 100 cm depth',
                'sensor': {
                    '1': 'Soil temperature.Soil temperature 100 cm depth sensor 1',
                    '2': 'Soil temperature.Soil temperature 100 cm depth sensor 2',
                    '3': 'Soil temperature.Soil temperature 100 cm depth sensor 3'
                }
            }
        },
        'Wind Dir': {'Wind direction': 'Wind Dir.Wind direction'},
        'Wind Vel': {
            'Wind speed (maximum)': 'Wind Vel.Wind speed (maximum)',
            'Wind speed (minimum)': 'Wind Vel.Wind speed (minimum)'
        },
        'Voltage': {'Battery charge': 'Voltage.Battery charge'}
    }

    def __init__(self, date_range, start_time, end_time, time_zone, calendar, interval, step, 
                 export_format, time_aligned, round_data, include_grade_codes, include_approval_levels, 
                 include_qualifiers, include_interpolation_types, calculation, unit_id, 
                 station_id, dataset_names, depths=None, sensor_numbers=None, output_dir="", headers=None):
        """
        Initialize the SoilMoistureDownloader with adjustable parameters for BulkExport.
        
        :param date_range: Date range type (e.g., "Custom")
        :param start_time: Start date and time in 'YYYY-MM-DD HH:MM' format (e.g., "2010-01-01 00:00")
        :param end_time: End date and time in 'YYYY-MM-DD HH:MM' format (e.g., "2024-12-31 00:00")
        :param time_zone: Timezone offset (e.g., -6)
        :param calendar: Calendar type (e.g., "CALENDARYEAR")
        :param interval: Interval setting (e.g., "PointsAsRecorded")
        :param step: Step size (e.g., 1)
        :param export_format: Export format (e.g., "csv")
        :param time_aligned: Whether data is time-aligned (e.g., "True")
        :param round_data: Whether to round data (e.g., "False")
        :param include_grade_codes: Include grade codes (e.g., "False")
        :param include_approval_levels: Include approval levels (e.g., "False")
        :param include_qualifiers: Include qualifiers (e.g., "undefined")
        :param include_interpolation_types: Include interpolation types (e.g., "False")
        :param calculation: Calculation type for all datasets (e.g., "Instantaneous")
        :param unit_id: Unit ID for all datasets (e.g., 147)
        :param station_id: Station identifier (e.g., "RISMA_MB5")
        :param dataset_names: List of dataset categories (e.g., ["Soil Moisture", "Air Temp"])
        :param depths: List of depth values (e.g., ["5 cm", "20 cm"]) or None for non-depth datasets
        :param sensor_numbers: List of sensor numbers (e.g., ["1", "2"]); if empty or None, downloads average
        :param output_dir: Directory to save the downloaded CSV file
        :param headers: Optional dictionary of HTTP headers (e.g., {"Authorization": "Bearer TOKEN"})
        """
        self.base_url = "https://agrifood.aquaticinformatics.net/Export/BulkExport"
        self.date_range = date_range
        self.start_time = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        self.end_time = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M')
        self.time_zone = time_zone
        self.calendar = calendar
        self.interval = interval
        self.step = step
        self.export_format = export_format
        self.time_aligned = time_aligned
        self.round_data = round_data
        self.include_grade_codes = include_grade_codes
        self.include_approval_levels = include_approval_levels
        self.include_qualifiers = include_qualifiers
        self.include_interpolation_types = include_interpolation_types
        self.calculation = calculation
        self.unit_id = unit_id
        self.station_id = station_id
        self.dataset_names = dataset_names
        self.depths = depths if depths is not None else []
        self.sensor_numbers = sensor_numbers if sensor_numbers is not None else []
        self.output_dir = self.make_dir(output_dir)
        self.headers = headers or {}

    def make_dir(self, output_dir):
        """Create output directory if it doesn't exist."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir

    def construct_dataset_names(self):
        """Construct dataset names using the dictionary and input parameters."""
        dataset_names = []

        for dataset_name in self.dataset_names:
            dataset_dict = self.CATEGORIZED_DATA.get(dataset_name)
            if not dataset_dict:
                print(f"Warning: Invalid dataset_name: {dataset_name}")
                continue

            # Non-soil datasets (no depth or sensor)
            if dataset_name not in ['Soil Moisture', 'Soil temperature']:
                for measurement in dataset_dict.values():
                    if isinstance(measurement, str):
                        dataset_names.append(f"{measurement}@{self.station_id}")
                    elif isinstance(measurement, dict):
                        for sub_value in measurement.values():
                            dataset_names.append(f"{sub_value}@{self.station_id}")
                continue

            # Soil-related datasets (require depth)
            if not self.depths:
                print(f"Warning: No depths specified for {dataset_name}; skipping")
                continue

            for depth in self.depths:
                depth_dict = dataset_dict.get(depth)
                if not depth_dict:
                    print(f"Warning: Invalid depth {depth} for {dataset_name}; skipping")
                    continue

                if not self.sensor_numbers:  # Empty or None means average
                    dataset_names.append(f"{depth_dict['average']}@{self.station_id}")
                else:  # Specific sensors
                    sensor_dict = depth_dict.get('sensor', {})
                    for sensor in self.sensor_numbers:
                        sensor_name = sensor_dict.get(sensor)
                        if sensor_name:
                            dataset_names.append(f"{sensor_name}@{self.station_id}")
                        else:
                            print(f"Warning: Invalid sensor_number {sensor} for {dataset_name} at {depth}")

        return dataset_names

    def construct_url(self):
        """Construct the URL with all parameters."""
        params = {
            "DateRange": self.date_range,
            "StartTime": self.start_time.strftime('%Y-%m-%d %H:%M'),
            "EndTime": self.end_time.strftime('%Y-%m-%d %H:%M'),
            "TimeZone": self.time_zone,
            "Calendar": self.calendar,
            "Interval": self.interval,
            "Step": self.step,
            "ExportFormat": self.export_format,
            "TimeAligned": self.time_aligned,
            "RoundData": self.round_data,
            "IncludeGradeCodes": self.include_grade_codes,
            "IncludeApprovalLevels": self.include_approval_levels,
            "IncludeQualifiers": self.include_qualifiers,
            "IncludeInterpolationTypes": self.include_interpolation_types,
            "_": int(time.time() * 1000)
        }

        dataset_names = self.construct_dataset_names()
        for i, dataset_name in enumerate(dataset_names):
            params[f"Datasets[{i}].DatasetName"] = dataset_name
            params[f"Datasets[{i}].Calculation"] = self.calculation
            params[f"Datasets[{i}].UnitId"] = self.unit_id

        query_string = "&".join(f"{key}={quote(str(value))}" for key, value in params.items())
        url = f"{self.base_url}?{query_string}"
        print(f"Generated URL: {url}")  # Debug print
        return url

    def download(self, filename="soil_moisture_data.csv"):
        """Download the data from the constructed URL and save as CSV."""
        url = self.construct_url()
        output_path = os.path.join(self.output_dir, filename)

        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '').lower()
            if 'zip' in content_type:
                zip_content = io.BytesIO(response.content)
                with zipfile.ZipFile(zip_content, 'r') as zip_file:
                    csv_file_name = zip_file.namelist()[0]
                    with zip_file.open(csv_file_name) as csv_file:
                        with open(output_path, "wb") as f:
                            f.write(csv_file.read())
                print(f"Data downloaded and extracted to {output_path}")
            elif 'csv' in content_type:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                print(f"Data downloaded to {output_path}")
            else:
                print(f"Error: Unexpected content type: {content_type}")
        else:
            print(f"Error: Failed to download data: HTTP {response.status_code}")
            print(f"Server response: {response.text}")

    def execute(self, filename="soil_moisture_data.csv"):
        """Execute the download process."""
        self.download(filename)