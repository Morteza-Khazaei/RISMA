import os
import time
import datetime
import requests
import zipfile
import io
from urllib.parse import quote


class RISMA:
    def __init__(self, date_range, start_time, end_time, time_zone, calendar, interval, step, 
                 export_format, time_aligned, round_data, include_grade_codes, include_approval_levels, 
                 include_qualifiers, include_interpolation_types, calculation, unit_id, 
                 station_ids, sensor_ids, depths, output_dir):
        """
        Initialize the SoilMoistureDownloader with all adjustable URL parameters for BulkExport.
        
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
        :param station_ids: List of station identifiers (e.g., ["RISMA_MB5"])
        :param sensor_ids: List of sensor identifiers (e.g., ["1", "2", "3", None])
        :param depths: List of depth values (e.g., ["0 to 5 cm", "5 cm"])
        :param output_dir: Directory to save the downloaded CSV file
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
        self.station_ids = station_ids
        self.sensor_ids = sensor_ids
        self.depths = depths
        self.output_dir = self.make_dir(output_dir)

    def make_dir(self, output_dir):
        """Create output directory if it doesn't exist."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir

    def construct_dataset_names(self):
        """Generate dataset names from station_ids, sensor_ids, and depths."""
        dataset_names = []
        # Use nested loops to combine all possible station, sensor, and depth values
        for station_id in self.station_ids:
            for depth in self.depths:
                for sensor_id in self.sensor_ids:
                    if sensor_id is None:
                        # Case without sensor (e.g., "Soil Moisture.Soil water content 5 cm depth@RISMA_MB5")
                        dataset_name = f"Soil Moisture.Soil water content {depth}@{station_id}"
                    else:
                        # Case with sensor (e.g., "Soil Moisture.Soil water content 0 to 5 cm depth sensor 1@RISMA_MB5")
                        dataset_name = f"Soil Moisture.Soil water content {depth} sensor {sensor_id}@{station_id}"
                    dataset_names.append(dataset_name)
        return dataset_names

    def construct_url(self):
        """Construct the URL with all parameters, applying calculation and unit_id to all datasets."""
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
            "_": int(time.time() * 1000)  # Current timestamp in milliseconds
        }

        # Generate dataset names and add to params
        dataset_names = self.construct_dataset_names()
        for i, dataset_name in enumerate(dataset_names):
            params[f"Datasets[{i}].DatasetName"] = dataset_name
            params[f"Datasets[{i}].Calculation"] = self.calculation
            params[f"Datasets[{i}].UnitId"] = self.unit_id

        # Construct URL with URL-encoded parameters
        query_string = "&".join(f"{key}={quote(str(value))}" for key, value in params.items())
        return f"{self.base_url}?{query_string}"

    def download(self, filename="soil_moisture_data.csv"):
        """Download the data from the constructed URL and save as CSV."""
        url = self.construct_url()
        output_path = os.path.join(self.output_dir, filename)

        # Make the HTTP request
        response = requests.get(url)
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'zip' in content_type:
                # Handle compressed response
                zip_content = io.BytesIO(response.content)
                with zipfile.ZipFile(zip_content, 'r') as zip_file:
                    # Assume one CSV file in the zip
                    csv_file_name = zip_file.namelist()[0]
                    with zip_file.open(csv_file_name) as csv_file:
                        with open(output_path, "wb") as f:
                            f.write(csv_file.read())
                print(f"Data downloaded and extracted to {output_path}")
            
            elif 'csv' in content_type:
                # Handle uncompressed CSV response
                with open(output_path, "wb") as f:
                    f.write(response.content)
                print(f"Data downloaded to {output_path}")
            
            else:
                raise ValueError(f"Unexpected content type: {content_type}")
        
        else:
            raise Exception(f"Failed to download data: HTTP {response.status_code}")

    def execute(self, filename="soil_moisture_data.csv"):
        """Execute the download process."""
        try:
            self.download(filename)
        except Exception as e:
            print(f"Error during download: {str(e)}")