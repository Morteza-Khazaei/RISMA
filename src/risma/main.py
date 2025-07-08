import os

from risma import AquariusWebPortal


def main(server, workspace, start_date, end_date, station, sensor, depth, disclaimer=True):

    aafc = AquariusWebPortal(server=server, auto_accept_disclaimer=disclaimer)

    params = aafc.fetch_params()

    stations = aafc.fetch_locations(stations=station)
    
    level_params = params[params.param_name.isin(['Air Temp', 'Soil temperature', 'Soil Moisture'])]

    datasets = aafc.fetch_datasets(param_names=level_params.param_name.tolist(), stations=stations.loc_id.tolist(), sensors=sensor, depths=depth)

    # groupby datasets based on loc_id
    gp_df = datasets.groupby('loc_id')
    for station, df in gp_df:

        # Make dir if not exits
        os.makedirs(workspace, exist_ok=True)

        fpath = os.path.join(workspace, f'{station}.csv')

        print(f'Downloading: {fpath} ...')

        st_df = aafc.fetch_dataset(dset_names=df.dset_name.to_list(), start=start_date, finish=end_date, extra_data_types=None)

        # Save the DataFrame to a CSV file named 'data.csv'
        st_df.to_csv(fpath, index=False)


if __name__ == '__main__':
    main(server='agrifood.aquaticinformatics.net', workspace='data', 
         start_date='2023-01-01', end_date='2023-01-02', 
         station=['RISMA_MB1', 'RISMA_MB2', 'RISMA_MB3'], 
         sensor='average', depth=['0 to 5 cm', '5 cm'], disclaimer=True)