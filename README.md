# Chicago Divvy Bike Usage Analysis

This project analyzes the spatial distribution and usage patterns of Chicago Divvy bike-share stations using Divvy trip data, bike infrastructure data, and census tract income data.

## Streamlit Dashboard

https://finalproject-uz92nuaxeyo8ci2uznhdir.streamlit.app/

## Setup

```{bash}
conda env create -f environment_local.yml
conda activate dap
```

```{bash}
data/
  raw-data/                     # Raw data files
    202506-divvy-tripdata.csv   # Divvy bike trip dataset (June 2025)
    Divvy_Bicycle_Stations_20260224.geojson   # Divvy station dataset
    Bike_Routes.geojson         # Chicago bike lane network
    CensusTractsTIGER2010_20260301.geojson        # Census tract boundaries
    illinois_tract_income/      # Census tract income data
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
requirements.txt                # Python dependencies
```
### Divvy Trip Dataset (June 2025)

## Data Download

Divvy trip dataset (June 2025)

Due to GitHub's 100MB file size limit, the raw Divvy trip dataset is hosted externally.

[Download from Google Drive](https://drive.google.com/file/d/18I41PrL8AqqsEZMeZe_Pg5X6_nRMB7Lr/view?usp=sharing)



