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