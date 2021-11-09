import os
import time
import glob
import datetime
import requests
from requests.structures import CaseInsensitiveDict
from dateutil.relativedelta import relativedelta


class RISMA:

    def __init__(self, project_name, station_name, data_type, start_date, end_date, units, interval, output):

        self.project_name = project_name
        self.station_name = station_name
        self.output = self.make_dir(output=output, dtype=data_type)
        self.data_type = self.switch_data_type(dtype=data_type)
        self.start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        self.units = units
        self.interval = interval
        self.count = self.count_interval()
        self.seq_dates = self.timestamp()
        self.headers = self.set_headers()
        self.stations = self.load_stations()

    def switch_data_type(self, dtype):

        switcher = {
            'daily': True,
            'hourly': False
        }

        return switcher.get(dtype, 'Expected data type are daily and hourly!')

    def timestamp(self):

        # Create a sequence of numbers, one for each time interval.
        sequence = range(0, self.count)

        grouped_date = list()
        for i in sequence:
            delta = i * self.interval
            if self.units == 'day':
                start_date = self.start_date + relativedelta(days=delta)
                end_date = self.start_date + relativedelta(days=delta + self.interval)
                grouped_date.append((int(time.mktime(start_date.timetuple())), int(time.mktime(end_date.timetuple()))))

            elif self.units == 'month':
                start_date = self.start_date + relativedelta(months=delta)
                end_date = self.start_date + relativedelta(months=delta + self.interval)
                grouped_date.append((int(time.mktime(start_date.timetuple())), int(time.mktime(end_date.timetuple()))))

            elif self.units == 'year':
                start_date = self.start_date + relativedelta(years=delta)
                end_date = self.start_date + relativedelta(years=delta + self.interval)
                grouped_date.append((int(time.mktime(start_date.timetuple())), int(time.mktime(end_date.timetuple()))))

            else:
                grouped_date = None

        return grouped_date

    def load_stations(self):

        url = 'https://aafc.fieldvision.ca/dashboard/ajax/loadStations?lang=en'
        resp = requests.post(url, headers=self.headers).json()

        return resp

    def get_encoded_url_params(self, d):

        def get_pairs(value, base):
            if isinstance(value, dict):
                return get_dict_pairs(value, base)
            elif isinstance(value, list):
                return get_list_pairs(value, base)
            else:
                return [base + '=' + str(value)]

        def get_list_pairs(li, base):
            pairs = []
            for idx, value in enumerate(li):
                new_base = base + '[' + str(idx) + ']'
                pairs += get_pairs(value, new_base)
            return pairs

        def get_dict_pairs(d, base=''):
            pairs = []
            for key, value in d.items():
                new_base = key if base == '' else base + '[' + key + ']'
                pairs += get_pairs(value, new_base)
            return pairs

        return '&'.join(get_dict_pairs(d))

    def request(self, data):

        url = 'https://aafc.fieldvision.ca/dashboard/ajax/downloadData?lang=en'
        resp = requests.post(url, data=self.get_encoded_url_params(data), headers=self.headers)

        return resp.json()

    def download(self, filename):

        url = 'https://aafc.fieldvision.ca/data_exports/' + filename
        r = requests.get(url, allow_redirects=True)

        with open(os.path.join(self.output, filename), 'wb') as fx:
            fx.write(r.content)

        fx.close()

        return None

    def make_dir(self, output, dtype):

        directory = os.path.join(output, self.project_name, dtype, self.station_name)
        if not os.path.exists(directory):
            os.makedirs(directory)

        return directory

    def set_headers(self):

        headers = CaseInsensitiveDict()
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=utf-8"
        headers["Accept"] = "application/json"

        return headers

    def count_interval(self):

        # Get the interval between two dates
        diff = relativedelta(self.end_date, self.start_date)
        diff_in_months = diff.months + diff.years * 12

        return int(diff_in_months / self.interval)

    def excutor(self):

        for station in self.stations:
            if self.project_name in station.values() and self.station_name in station.values():
                for date in tuple(self.seq_dates):

                    payload = {
                        'parameters': {
                            'IsDailyData': self.data_type,
                            'StationId': station['StationId'],
                            'StartDate': date[0],
                            'EndDate': date[1]
                        }
                    }

                    fname = self.request(data=payload)['Filename']

                    filename, file_extension = os.path.splitext(fname)
                    unique_fname = '_'.join(filename.split('_')[:5])

                    # Get all infiles that match tile and file pattern
                    infiles = glob.glob('%s/*.csv' % self.output)

                    selected_files = ['_'.join(os.path.splitext(file.split('\\')[-1])[0].split('_')[:5]) for file in infiles]

                    if not unique_fname in selected_files:
                        print('Downloading *** {fname}'.format(fname=fname))
                        self.download(filename=fname)

                    else:
                        print('This file already has been downloaded. *** {fname}'.format(fname=fname))

        return None
