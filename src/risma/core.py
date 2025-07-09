import io
import re
import urllib.parse

import requests
from lxml import html
import pandas as pd


class AquariusWebPortal:
    """Access data from a deployment of Aquarius Web Portal.

    Args:
        server (str): URL of the Web Portal deployment.
        session (optional): requests.Session object to use
        auto_accept_disclaimer (bool): Automatically accept disclaimers if found

    The main methods to use are:

    - :meth:`aquarius_webportal.AquariusWebPortal.fetch_locations`: fetch metadata for all locations
    - :meth:`aquarius_webportal.AquariusWebPortal.fetch_datasets`: fetch metadata for datasets measuring a queried parameter
    - :meth:`aquarius_webportal.AquariusWebPortal.fetch_dataset`: fetch data for a single timeseries

    Relevant attributes of the ``AquariusWebPortal`` object are:

    Attributes:
        server (str): as initialised
        params (pd.DataFrame): the available parameters. If the
            portal is disclaimer-blocked, this will be empty (see
            ReadTheDocs documentation for further details)
        session: reqeusts.Session object

    """

    def __init__(self, server="water.data.sa.gov.au", session=None, auto_accept_disclaimer=True, **kwargs):
        if not server.startswith("http"):
            server = "https://" + server
        if session:
            self.session = session
        else:
            self.session = requests.Session(**kwargs)
        self.server = server
        self.auto_accept_disclaimer = auto_accept_disclaimer
        self.disclaimer_accepted = False
        self.params = self.fetch_params()
        
    def _check_and_accept_disclaimer(self, response):
        """Check if the response contains a disclaimer and accept it if configured to do so.
        
        Args:
            response: requests.Response object
            
        Returns:
            bool: True if disclaimer was found and accepted, False otherwise
        """
        if 'AAFC Disclaimer' in response.text or 'AcceptDisclaimer' in response.text:
            if not self.auto_accept_disclaimer:
                raise Exception("Disclaimer found but auto_accept_disclaimer is False. "
                              "Please set auto_accept_disclaimer=True or manually accept the disclaimer.")
            
            # Parse the disclaimer form
            root = html.document_fromstring(response.text)
            
            # Find the form with AcceptDisclaimer action
            form = root.xpath('//form[@action="/AcceptDisclaimer"]')[0] if root.xpath('//form[@action="/AcceptDisclaimer"]') else None
            
            if form is not None:
                # Extract form data
                form_data = {}
                
                # Get all input fields
                for input_field in form.xpath('.//input'):
                    name = input_field.get('name')
                    value = input_field.get('value', '')
                    if name:
                        form_data[name] = value
                
                # Submit the disclaimer acceptance
                disclaimer_url = self.server + "/AcceptDisclaimer"
                disclaimer_response = self.session.post(disclaimer_url, data=form_data)
                
                if disclaimer_response.status_code == 200:
                    self.disclaimer_accepted = True
                    return True
                else:
                    raise Exception(f"Failed to accept disclaimer. Status code: {disclaimer_response.status_code}")
            else:
                # raise Exception("Disclaimer form not found in the expected format.")
                print("Disclaimer form not found in the expected format. Skipping disclaimer acceptance.")
                self.disclaimer_accepted = True
                return True
        
        return False

    def _make_request_with_disclaimer_handling(self, url, method='GET', **kwargs):
        """Make a request and handle disclaimer if present.
        
        Args:
            url (str): URL to request
            method (str): HTTP method ('GET' or 'POST')
            **kwargs: Additional arguments to pass to the request
            
        Returns:
            requests.Response: The response after handling any disclaimer
        """
        if method.upper() == 'GET':
            response = self.session.get(url, **kwargs)
        else:
            response = self.session.post(url, **kwargs)
        
        # Check if we hit a disclaimer
        if self._check_and_accept_disclaimer(response):
            # Retry the original request after accepting disclaimer
            if method.upper() == 'GET':
                response = self.session.get(url, **kwargs)
            else:
                response = self.session.post(url, **kwargs)
        
        return response

    def fetch_params(self, payload=None):
        """Fetch the list of available parameters.

        Returns:
            pd.DataFrame: a table of available parameters with these
            columns:

                - param_id (int)
                - param_name (str)
                - param_desc (str)

        """
        url = self.server + "/Data/List/"
        response = self._make_request_with_disclaimer_handling(url, method='POST', data=payload)
        return self.parse_params_from_html(response.text)

    def get_param(self, param_name=None, param_desc=None, param_id=None):
        """Fetch/identify a single parameter from the ``params`` attribute.

        Args:
            param_name (str): select a parameter with this name
            param_desc (str): select a parameter with the description (note
                that usually the description functions as a "long name")
            param_id (int): select the parameter with this ID number

        Returns:
            pd.Series: the relevant row from ``self.params`` with these
            fields:

                - param_id (int)
                - param_name (str)
                - param_desc (str)

        """
        if param_name:
            return self.params[self.params.param_name == param_name].iloc[0]
        elif param_desc:
            return self.params[self.params.param_desc == param_desc].iloc[0]
        elif param_id:
            return self.params[self.params.param_id == param_id].iloc[0]

    def fetch_locations(self, stations=None):
        """Fetch a list of all locations from the portal.

        Returns:
            pd.DataFrame: a table of location metadata. The available fields
            may vary between different portals, but these may be present:

                - wp_loc_id (called "LocationId" in the AQWP internal APIs)
                - lon (called "LocX" in the AQWP internal APIs)
                - lat (called "LocY" in the AQWP internal APIs)
                - loc_name (called "Location" in the AQWP internal APIs)
                - loc_id (called "LocationIdentifier" in the AQWP internal APIs)
                - loc_type (called "LocType" in the AQWP internal APIs)
                - loc_folder (called "LocationFolder" in the AQWP internal APIs)

        """
        return self.fetch_list(stations=stations)

    def fetch_datasets(self, param_names=[], param_descs=[], param_ids=[], stations=[], sensors=[], depths=[]):
        """Fetch a list of all datasets from the portal with a given parameter

        Args:
            param_name (str): select a parameter with this name
            param_desc (str): select a parameter with the description (note
                that usually the description functions as a "long name")
            param_id (int): select the parameter with this ID number

        Returns:
            pd.DataFrame: a table of dataset metadata. The available fields
            may vary between different portals, but these may be present:

                - wp_loc_id (called "LocationId" in the AQWP internal APIs)
                - wp_dset_id (called "DatasetId" in the AQWP internal APIs)
                - lon (called "LocX" in the AQWP internal APIs)
                - lat (called "LocY" in the AQWP internal APIs)
                - loc_name (called "Location" in the AQWP internal APIs)
                - loc_id (called "LocationIdentifier" in the AQWP internal APIs)
                - dset_name (called "DatasetIdentifier" in the AQWP internal APIs)
                - loc_type (called "LocType" in the AQWP internal APIs)
                - loc_folder (called "LocationFolder" in the AQWP internal APIs)
                - dset_start (called "StartOfRecord" in the AQWP internal APIs)
                - dset_end (called "EndOfRecord" in the AQWP internal APIs)
                - param (str) - derived from dset_name
                - label (str) - derived from dset_name

        """
        if not param_ids:
            params = self.fetch_params()
            if len(param_names) and set(param_names).issubset(set(params.param_name.unique())):
                param_ids = params[params.param_name.isin(param_names)].param_id.to_list()
            elif len(param_descs) and set(param_descs).issubset(set(params.param_desc.unique())):
                param_ids = params[params.param_desc.isin(param_descs)].param_id.to_list()
            else:
                # If no parameters are specified, return all datasets
                raise Exception("No parameters specified. Please provide at least one of param_names, param_descs, or param_ids.")
        if param_ids is None:
            raise Exception("failed to identify parameter")
        else:
            df = self.fetch_list(param_ids=param_ids, stations=stations)

            # Add new column for air and soil sensors based on label column
            df['type'] = df["label"].apply(lambda x: "soil" if "Soil" in x else "air")

            df_air = df[df.type.eq("air")].copy()
            df_soil = df[df.type.eq("soil")].copy()
            
            # Apply the function to create the 'depth' column
            df_soil['depth'] = df_soil['label'].apply(self.extract_depth)
            df_soil['sensor'] = df_soil['label'].apply(self.extract_sensor)
            
            # Filter df based on sensors
            if isinstance(sensors, list):
                df_soil = df_soil[df_soil.sensor.isin(sensors)]
            elif isinstance(sensors, str):
                df_soil = df_soil[df_soil.sensor == sensors]
            else:
                raise Exception('sensors must be a string or a list of strings.')
            
            # Filter df based on depths
            if isinstance(depths, list):
                df_soil = df_soil[df_soil.depth.isin(depths)]
            elif isinstance(depths, str):
                df_soil = df_soil[df.depth == depths]
            else:
                raise Exception('depths must be a string or a list of strings.')

            # Put together both dfs
            df = pd.concat([df_air, df_soil])
            
            return df


    def fetch_list(self, param_ids=None, stations=None):
        """Internal function that fetches list data from the /Data/Data_List
        endpoint.

        Args:
            param_id (int): if not supplied, the list is of Locations.
                If supplied, the list is of Datasets/Time series.

        Returns:
            pd.DataFrame: a table of results with some columns renamed for
            convenience:

                - wp_loc_id (called "LocationId" in the AQWP internal APIs)
                - wp_dset_id (called "DatasetId" in the AQWP internal APIs)
                - lon (called "LocX" in the AQWP internal APIs)
                - lat (called "LocY" in the AQWP internal APIs)
                - loc_name (called "Location" in the AQWP internal APIs)
                - loc_id (called "LocationIdentifier" in the AQWP internal APIs)
                - dset_name (called "DatasetIdentifier" in the AQWP internal APIs)
                - loc_type (called "LocType" in the AQWP internal APIs)
                - loc_folder (called "LocationFolder" in the AQWP internal APIs)
                - dset_start (called "StartOfRecord" in the AQWP internal APIs)
                - dset_end (called "EndOfRecord" in the AQWP internal APIs)
                - classification (called "Classification" in the AQWP internal APIs)
                - bgcolor (called "Background" in the AQWP internal APIs)
                - seq (called "Sequence" in the AQWP internal APIs)
                - param (str) - derived from dset_name if the latter exists
                - label (str) - derived from dset_name if the latter exists

            Any other columns will not be renamed.

        """
        page_size = 5000
        page_no = 1
        request_complete = False
        results = []
        total_results = None
        n = 0
        while (request_complete) is False and n < 15:
            query = {
                "page": page_no,
                "pageSize": page_size,
            }
            if isinstance(param_ids, list):
                for i, param_id in enumerate(param_ids):
                    query[f"parameters[{i}]"] = param_id
            else:
                query["parameters[0]"] = param_ids
            url = self.server + "/Data/Data_List?" + urllib.parse.urlencode(query)
            resp = self._make_request_with_disclaimer_handling(url, method='POST', data=query)
            data = resp.json()

            if n == 0:
                total_results = data["Total"]

            results += data["Data"]
            n += 1

            if len(results) < total_results:
                page_no += 1
            else:
                request_complete = True

        df = pd.DataFrame(results)
        df = df.rename(
            columns={
                "LocationId": "wp_loc_id",
                "DatasetId": "wp_dset_id",
                "LocX": "lon",
                "LocY": "lat",
                "Location": "loc_name",
                "LocationIdentifier": "loc_id",
                "DatasetIdentifier": "dset_name",
                "LocType": "loc_type",
                "LocationFolder": "loc_folder",
                "StartOfRecord": "dset_start",
                "EndOfRecord": "dset_end",
                "Classification": "classification",
                "Background": "bgcolor",
                "Sequence": "seq",
            }
        )
        if "dset_name" in df:
            df["param"] = df.dset_name.apply(lambda v: v.split("@")[0].split(".")[0])
            df["label"] = df.dset_name.apply(lambda v: v.split("@")[0].split(".")[1])
        
        # Filter df if stations is not None
        if stations is not None:
            if isinstance(stations, str):
                df = df[df.loc_id == stations]
            elif isinstance(stations, list):
                df = df[df.loc_id.isin(stations)]
            else:
                raise Exception('stations must be a string or a list of strings.')
        else:
            print("No stations provided! Skipping filtering by stations.")
        
        return df

    def fetch_dataset(
        self,
        dset_names,
        date_range=None,
        extra_data_types=None,
        start=None,
        end=None,
        session=None,
        **kwargs,
    ):
        """Fetch timeseries data for a single dataset."""
        query = {
            "Calendar": "CALENDARYEAR",
            "Interval": "PointsAsRecorded",
            "Step": 1,
            "ExportFormat": "csv",
            "TimeAligned": True,
            "RoundData": True,
            "calculation": "Instantaneous"
        }
        if isinstance(dset_names, str):
            query["Datasets[0].DatasetName"] = dset_names
        elif isinstance(dset_names, list):
            for i, dset_name in enumerate(dset_names):
                query[f"Datasets[{i}].DatasetName"] = dset_name
        else:
            raise ValueError("dset_names must be a string or a list of strings.")

        if date_range is None and start is None and end is None:
            query["DateRange"] = "EntirePeriodOfRecord"
        elif start and end:
            query["DateRange"] = "Custom"
            query["StartTime"] = pd.Timestamp(start).strftime("%Y-%m-%d %H:%M")
            query["EndTime"] = pd.Timestamp(end).strftime("%Y-%m-%d %H:%M")
        elif date_range == "Days7":
            query["DateRange"] = "Days7"

        if extra_data_types == "all":
            extra_data_types = ["grade", "approval", "qualifier", "interpolation_type"]
        elif not extra_data_types:
            extra_data_types = []

        query["IncludeGradeCodes"] = "grade" in extra_data_types
        query["IncludeApprovalLevels"] = "approval" in extra_data_types
        query["IncludeQualifiers"] = "qualifier" in extra_data_types
        query["IncludeInterpolationTypes"] = "interpolation_type" in extra_data_types

        url = self.server + "/Export/BulkExport"
        resp = self._make_request_with_disclaimer_handling(url, method="GET", data=query)

        # Find header line starting with "Timestamp"
        lines = resp.text.splitlines()
        header_line_index = next(
            (i for i, line in enumerate(lines) if line.startswith("Timestamp (")), None
        ) - 1  # Adjust index to get the header line

        if header_line_index is None:
            raise ValueError("Failed to locate CSV header in response.")

        # Read using correct skiprows
        with io.StringIO(resp.text) as f:
            df = pd.read_csv(f, header=None, sep=",")
        
        # # Rename columns based on the header line
        # header_line = lines[header_line_index].split(",")
        # header_line[0] = lines[header_line_index + 1].split(",")[0]
        # header_line[1] = lines[header_line_index + 1].split(",")[1].replace("Value", header_line[1].split(".")[1])
        # df.columns = header_line

        # # Determine the timestamp column and convert it to datetime
        # timestamp_col = df.columns[0]
        # df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce")
        # df = df.set_index(timestamp_col)

        return df


    def parse_params_from_html(self, source):
        """Obtain a list of parameter names, descriptions, and IDs
        from the HTML source of a Web Portal page (either the List
        or Map pages will work).

        Returns:
            pd.DataFrame: a table of available parameters with these
            columns:

                - param_id (int)
                - param_name (str)
                - param_desc (str)

        """
        root = html.document_fromstring(source)
        params = []
        for element in root.xpath("//option[@data-code]"):
            attrs = element.attrib
            params.append(
                {
                    "param_id": attrs["value"],
                    "param_name": attrs["data-code"],
                    "param_desc": element.text,
                }
            )
        pdf = pd.DataFrame(params, columns=["param_id", "param_name", "param_desc"])
        pdf = pdf[
            ~pd.isnull(pdf.param_id.apply(lambda v: pd.to_numeric(v, errors="coerce")))
        ]
        return pdf.drop_duplicates()

    # Define a function to extract depth from the label
    def extract_depth(self, label):
        range_match = re.search(r'(\d+)(?:\s+to\s+|--)(\d+)\s*cm', label)
        if range_match:
            return range_match.group(0)
        single_match = re.search(r'(\d+)\s*cm', label)
        if single_match:
            return single_match.group(0)
        return 'average'
    
    # Define a function to extract sensor from the label
    def extract_sensor(self, label):
        sensor_match = re.search(r'sensor\s*(\d+)', label, re.IGNORECASE)
        if sensor_match:
            return sensor_match.group(1)
        return 'average'


# Example usage:
if __name__ == "__main__":
    # Initialize with automatic disclaimer acceptance
    portal = AquariusWebPortal(
        server="https://agrifood.aquaticinformatics.net",
        auto_accept_disclaimer=True
    )
    
    # Now you can use the portal normally
    print(f"Found {len(portal.params)} parameters")
    print(portal.params)
    locations = portal.fetch_locations()
    print(f"Found {len(locations)} locations")