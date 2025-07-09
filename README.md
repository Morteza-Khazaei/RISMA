# Real‐Time In‐Situ Soil Monitoring for Agriculture (RISMA) network

## Overview

The Real-time In-Situ Soil Monitoring for Agriculture (RISMA) network provides accurate, near real-time soil and weather data from various agricultural regions across Canada. Established in 2010, RISMA is a collaborative effort between Agriculture and Agri-Food Canada (AAFC) and its partners, including Environment Canada, the Global Institute for Water Security (University of Saskatchewan), and the University of Guelph.

The network captures a wide range of data points every 15 minutes, including:
*   **Soil Conditions:** Soil moisture and temperature at multiple depths (0-5cm, 5cm, 20cm, 50cm, 100cm, and 150cm).
*   **Meteorological Data:** Precipitation, air temperature, relative humidity, wind speed, and wind direction.

As of 2015, the network consists of 22 stations located in Manitoba, Saskatchewan, and Ontario. The data from these stations is crucial for applications such as flood and yield forecasting, as well as for validating satellite-based environmental products.

Please see our quick user guide for more information on how to use this Portal by [clicking here](https://agrifood.aquaticinformatics.net/AQWebPortal/Data/GetFile/GettingStartedGuide)

## Getting Started

To get started with RISMA, follow the steps below.

### Prerequisites

*   Python 3.8 or higher
*   Jupyter Notebook or JupyterLab
*   Git

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/morteza-khazaei/RISMA.git
    cd RISMA
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: `venv\Scripts\activate`
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Install RISMA:**

    ```bash
    pip install .
    ```

### Running the Tutorial

The `tutorial.ipynb` notebook provides a comprehensive guide to using RISMA. To run it:

1.  **Start Jupyter:**

    ```bash
    jupyter notebook
    ```

2.  **Open the `tutorial.ipynb` notebook:**

## Usage

### Command-Line Interface (CLI)

The RISMA package includes a powerful command-line interface (CLI) for interacting with the data portal. After installation, you can use the `risma` command in your terminal.

**Global Options:**

*   `--server`: Specify the Aquarius server URL (defaults to `agrifood.aquaticinformatics.net`).
*   `--verbose` or `-v`: Enable detailed output.

You can get help on any command or subcommand by using the `--help` flag:

```bash
risma --help
risma locations --help
```

#### `params` - List Available Parameters

To see all parameters (e.g., "Air Temp", "Soil Moisture") available on the server:

```bash
risma params
```

#### `locations` - List Available Locations

To list all monitoring stations. This command supports filtering by one or more station IDs, which can be provided as a comma-separated list or by using the option multiple times.

```bash
# List all stations
risma locations

# Filter by specific stations (e.g., RISMA_MB1 and RISMA_MB2)
risma locations --stations RISMA_MB1,RISMA_MB2
```

#### `datasets` - List Available Datasets

To find datasets based on various criteria like station, parameter, sensor, and depth.

```bash
risma datasets --stations RISMA_MB1 --param-names "Soil temperature" --depths "5 cm"
```

#### `download` - Download Data

Download time-series data for one or more stations. The station ID (`--stations`) is required. If no date range is provided, it defaults to the last 7 days.

**Example:** Download soil moisture and temperature data for station `RISMA_MB1` and save it in the `./my_data` directory.

```bash
risma download --stations RISMA_MB1 --param-names "Soil temperature" --param-names "Soil Moisture" -o ./my_data
```

**Example:** Download data for multiple stations for a specific date range.

```bash
risma download --stations RISMA_MB1 --stations RISMA_MB2 --start-date 2024-01-01 --end-date 2024-01-31
```