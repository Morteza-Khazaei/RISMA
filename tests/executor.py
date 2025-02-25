from src.risma import RISMA


# Example usage
if __name__ == "__main__":
    # Test 1: Soil Moisture at 5 cm and 20 cm, average only
    downloader_avg = RISMA(
        date_range="Custom",
        start_time="2023-01-01 00:00",
        end_time="2023-12-31 00:00",
        time_zone=-6,
        calendar="CALENDARYEAR",
        interval="PointsAsRecorded",
        step=1,
        export_format="csv",
        time_aligned="True",
        round_data="False",
        include_grade_codes="False",
        include_approval_levels="False",
        include_qualifiers="undefined",
        include_interpolation_types="False",
        calculation="Instantaneous",
        unit_id=147,
        station_id="RISMA_MB5",
        dataset_names=["Soil Moisture"],
        depths=["5 cm", "20 cm"],
        sensor_numbers=None,  # Downloads average data
        output_dir="./soil_moisture_data"
    )
    downloader_avg.execute(filename="soil_moisture_5cm_20cm_avg_2023.csv")

    # Test 2: Soil Moisture at 5 cm and 20 cm, sensors 1 and 2 only
    downloader_sensors = RISMA(
        date_range="Custom",
        start_time="2023-01-01 00:00",
        end_time="2023-12-31 00:00",
        time_zone=-6,
        calendar="CALENDARYEAR",
        interval="PointsAsRecorded",
        step=1,
        export_format="csv",
        time_aligned="True",
        round_data="False",
        include_grade_codes="False",
        include_approval_levels="False",
        include_qualifiers="undefined",
        include_interpolation_types="False",
        calculation="Instantaneous",
        unit_id=None,
        station_id="RISMA_MB5",
        dataset_names=["Soil Moisture", "Soil temperature"],
        depths=["5 cm", "20 cm"],
        sensor_numbers=None,  # Downloads only sensor 1 and 2 data
        output_dir="./soil_moisture_data"
    )
    downloader_sensors.execute(filename="RISMA_MB5_avg_sensors12_2023.csv")