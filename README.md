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

3. **Install RISMA:**

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

The RISMA package includes a powerful command-line interface (CLI) for interacting with the data portal. It can be run as a step-by-step interactive session or by executing individual commands.

To start the interactive session, simply run:

```bash
risma
```

This will launch a stateful session that guides you through the data selection and download process. Inside the session, you can run commands like `params --list-only`, `status`, or `exit`.

Alternatively, you can run each command directly from your shell by prefixing it with `risma`, for example: `risma params --list-only`.

**Global Options:**

*   `--server`: Specify the Aquarius server URL (defaults to `agrifood.aquaticinformatics.net`).
*   `--verbose` or `-v`: Enable detailed output.

You can get help on any command or subcommand by using the `-h` or `--help` flag:

```bash
risma --help
risma params --help
```

#### Step-by-Step Workflow

The CLI is designed around a 4-step workflow.

**1. Parameters Step (`params`)**

Load and select the parameters you are interested in (e.g., "Air Temp", "Soil Moisture").

*   **Load:** `params --list-only` - Shows all available parameters
*   **Select:** `params --select "Air Temp" "Soil Moisture"` - Select specific parameters
*   **Interactive:** `params` - Shows parameters with current selections marked

**2. Stations Step (`stations`)**

Load and select the monitoring stations.

*   **Load:** `stations --list-only` - Shows all available stations
*   **Select:** `stations --select RISMA_MB1 RISMA_MB2` - Select specific stations
*   **Interactive:** `stations` - Shows stations with current selections marked

**3. Datasets Step (`datasets`)**

Find available datasets based on your selected parameters and stations. You can further filter by sensor and depth.

*   **Load:** `datasets --list-only` - Shows available datasets based on selections
*   **Filter:** `datasets --sensors average --depths "0 to 5 cm"` - Add filters
*   **Interactive:** `datasets` - Shows datasets ready for download

**4. Download Step (`download`)**

Download the time-series data for the selected datasets.

*   **Execute:** `download --start-date 2024-01-01 --end-date 2024-01-31`
*   **Default:** `download` - Downloads last 7 days

#### Utility Commands

The following commands are also available (primarily for interactive mode):

```bash
status  # Show your current selections (parameters, stations, etc.).
reset   # Clear all your selections and start over.
help    # Display help information.
exit    # Exit the interactive session.
```