from src.risma import RISMA


# Example usage with the new URL parameters
if __name__ == "__main__":
    downloader = RISMA(
        date_range="Custom",
        start_time="2010-01-01 00:00",
        end_time="2024-12-31 00:00",
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
        station_ids=["RISMA_MB5"],
        sensor_ids=["1", "2", "3", None],
        depths=["0 to 5 cm", "5 cm"],
        output_dir="./soil_moisture_data"
    )
    downloader.execute(filename="soil_moisture_mb5_bulk_2010_2024_all_sensors.csv")
