from src.AAFC import RISMA


if __name__ == '__main__':

    # The RISMA network structures
    risma_networks = {
        'Central Experimental Farm': ['Station 1'],
        'Manitoba': ['Station 1', 'Station 2', 'Station 3', 'Station 4',
                     'Station 6', 'Station 7', 'Station 8', 'Station 9',
                     'Station 10', 'Station 11', 'Station 12', 'Station 13'],
        'Ontario': ['Station 1', 'Station 2', 'Station 3', 'Station 4',
                    'Station 6',],
        'Saskatchewan': ['Station 1', 'Station 2', 'Station 3', 'Station 4']
    }

    # Type of in-situ data.
    data_type = 'hourly'

    # Aggregation unit.
    units = 'month'

    # Aggregation time interval based on server restrictions.
    interval = 2

    # Start range of date.
    start_date = '2015-01-01'

    # End date range of date.
    end_date = '2021-11-05'

    # Export path to store csv files.
    output = 'F:\Canada Projects\In-situ data'

    # Loop through the list of stations object.
    for project_name,station_names in risma_networks.items():
        print(project_name)
        for station_name in station_names:
            print(station_name)
            risma = RISMA(project_name=project_name, station_name=station_name, data_type=data_type,
                          start_date=start_date, end_date=end_date, units=units, interval=interval, output=output)
            risma.excutor()
