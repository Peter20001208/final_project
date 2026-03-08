# Chicago Divvy Bike Usage Analysis

This project analyzes the spatial distribution and usage patterns of Chicago Divvy bike-share stations using Divvy trip data, bike infrastructure data, and census tract income data.

## Streamlit Dashboard

https://finalproject-uz92nuaxeyo8ci2uznhdir.streamlit.app/

## Setup

```{bash}
conda env create -f environment_local.yml
conda activate dap
```
## Project Structure

```bash
data/
  raw-data/                     # Raw data files
    202506-divvy-tripdata.csv   # Divvy bike trip dataset (June 2025)
    Divvy_Bicycle_Stations_20260224.geojson   # Divvy station dataset
    Bike_Routes.geojson         # Chicago bike lane network
    CensusTractsTIGER2010_20260301.geojson    # Chicago census tract boundaries
    illinois_tract_income/      # Illinois census tract median and mean income data
  derived-data/                 # Processed datasets
    divvy_202506_cleaned.parquet  # Cleaned Divvy trip data
    tract_usage2.geojson          # Aggregated tract-level usage data

spatial_analysis/               # Spatial analysis output figures
  bike_utilization_map.png
  income_vs_bikes.png
  income_vs_utilization.png
  n_bikes_map.png

time_member_analysis/           # Time and membership analysis output
  time_member_analysis.png

app.py                          # Streamlit dashboard
preprocessing.py                # Cleans and aggregates raw data
spatial_analysis.py             # Generates spatial analysis figures
time_member_analysis.py         # Generates temporal usage figures

final_project.qmd               # Quarto source file
final_project.pdf               # Final writeup
requirements.txt                # Streamlit app dependencies
environment_local.yml           # Python dependencies
```

## Data Download

Divvy trip dataset (June 2025)

Due to GitHub's 100MB file size limit, the dataset is hosted on Google Drive. 
You should download from the link below and and place it in: `data/raw-data/`

[Download from Google Drive](https://drive.google.com/file/d/18I41PrL8AqqsEZMeZe_Pg5X6_nRMB7Lr/view?usp=sharing)

Median household income by census tract from the 2023 5-year ACS estimate.  
The dataset originates from NHGIS and was provided in the course materials for Problem Set 5, which is the version used in this project.

[Illinois tract income (UChicago Box)](https://uchicago.app.box.com/s/hqcohbiu3jbgacsprwkncied2axqkazz/folder/364804110080)

## Data Process

The script `preprocessing.py` processes the raw datasets and produces the cleaned datasets used in the analysis.

The workflow includes the following steps:

1. **Clean Divvy trip data**

The raw Divvy trip dataset (`202506-divvy-tripdata.csv`) is loaded and the start and end timestamps are converted to datetime format.  

Additional variables are created including:

- trip start hour
- trip end hour
- day of week
- weekday vs weekend indicator

The cleaned dataset is saved as: `data/derived-data/divvy_202506_cleaned.parquet`

2. **Spatially join trips to census tracts**

Trip start locations are converted into geographic points and spatially joined with Chicago census tract boundaries.  
The number of trips originating from each tract is then aggregated.

3. **Aggregate bike station capacity**

Divvy station data are spatially joined to census tracts and the total dock capacity is aggregated for each tract to obtain the number of available bikes.

4. **Merge census income data**

Census tract median and mean household income data (from NHGIS / ACS) are merged with the tract-level trip and bike availability data.

5. **Construct bike utilization measure**

Bike utilization is calculated as: `number of trips / number of bikes`

Extreme outliers are trimmed at the 99th percentile.

6. **Compute bike infrastructure availability**

Chicago bike route data are spatially joined with census tracts to count the number of bike lane segments intersecting each tract.

7. **Generate final analysis dataset**

The final tract-level dataset includes:

- trip counts (`n_trips`)
- number of bikes (`n_bikes`)
- bike utilization
- median income
- mean income
- number of bike lanes (`n_lanes`)

The processed dataset is saved as: `data/derived-data/tract_usage2.geojson`

## Usage

1. Run preprocessing to clean and aggregate Divvy trip data:

```bash
python preprocessing.py
```

2. Generate spatial analysis figures:

```bash
python spatial_analysis.py
```

3. Generate time and membership analysis figures:

```bash
python time_member_analysis.py
```
4. Launch the interactive Streamlit dashboard:

```bash
streamlit run app.py
```
5. Generate the final report:

```bash
quarto render final_project.qmd
```

