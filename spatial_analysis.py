
# setup
import geopandas as gpd
import matplotlib.pyplot as plt
import altair as alt
import warnings
import tempfile
from IPython.display import display, Image
import vl_convert as vlc
warnings.filterwarnings('ignore')
alt.renderers.enable('png')
data_path = 'data/external'

# improve graph resolution


def display_altair_png(chart, scale=2):
    """
    Render an Altair chart to a PNG and display it inline.

    Parameters
    ----------
    chart : altair.Chart
        Altair chart object to render.
    scale : int, optional
        Resolution scaling factor for the PNG (default = 2). Use scale=2 for standard slides. Use scale = 3–4 for dense figures or PDF exports.
    """
    png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=scale)

    # Write to a temporary PNG file and display
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        tmp.write(png_bytes)
        tmp.flush()
        display(Image(filename=tmp.name))


tract_usage2 = gpd.read_file('data/derived-data/tract_usage2.geojson')

fig, ax = plt.subplots(figsize=(8,10))

plot = tract_usage2.plot(
    column='n_bikes',
    cmap='viridis',
    linewidth=0.1,
    edgecolor='white',
    legend=True,
    legend_kwds={
        "shrink": 0.6,   
        "aspect": 30     
    },
    missing_kwds={
        "color": "lightgrey",
        "label": "No data"
    },
    ax=ax
)

cbar = plot.get_figure().axes[1]

cbar.set_ylabel("")

cbar.set_title("Total Bikes (Dock Capacity)", fontsize=10, pad=10)

ax.set_title("Chicago Divvy Bike Amount by Census Tract", fontsize=14)
ax.axis('off')

plt.savefig("spatial_analysis/n_bikes_map.png",
            dpi=300,
            bbox_inches='tight')

plt.show()


fig, ax = plt.subplots(figsize=(8,10))

plot = tract_usage2.plot(
    column='bike_utilization',
    cmap='viridis',
    linewidth=0.1,
    edgecolor='white',
    legend=True,
    legend_kwds={
        "shrink": 0.6,
        "aspect": 30
    },
    missing_kwds={
        "color": "lightgrey",
        "label": "No data"
    },
    ax=ax
)

cbar = plot.get_figure().axes[1]

cbar.set_ylabel("")

cbar.set_title("Trips per Bike (Utilization)", fontsize=10, pad=10)

ax.set_title("Chicago Divvy Bike Utilization by Census Tract", fontsize=14)
ax.axis('off')

plt.savefig("spatial_analysis/bike_utilization_map.png",
            dpi=300,
            bbox_inches='tight')

plt.show()

base = alt.Chart(tract_usage2).encode(
    x=alt.X('median_income:Q',
            title='Median Income ($)',
            scale=alt.Scale(zero=False)),
    y=alt.Y('bike_utilization:Q',
            title='Bike Utilization (Trips per Bike)',
            scale=alt.Scale(zero=False))
)

points = base.mark_circle(
    size=40,
    opacity=0.35,
    color="#1f77b4"
)

trend = base.transform_regression(
    'median_income',
    'bike_utilization'
).mark_line(color='red')

chart = (points + trend).properties(
    title='Income vs Bike Utilization (Census Tract)',
    width=600,
    height=400
)

chart.save("spatial_analysis/income_vs_utilization.png")

chart

base = alt.Chart(tract_usage2).encode(
    x=alt.X('median_income:Q',
            title='Median Income ($)',
            scale=alt.Scale(zero=False)),
    y=alt.Y('n_bikes:Q',
            title='Total Bikes (Dock Capacity)',
            scale=alt.Scale(zero=False))
)

points = base.mark_circle(
    size=40,
    opacity=0.35,
    color="#2ca02c"
)

trend = base.transform_regression(
    'median_income',
    'n_bikes'
).mark_line(color='red')

chart1 = (points + trend).properties(
    title='Income vs Bike Amount (Census Tract)',
    width=600,
    height=400
)

chart1.save("spatial_analysis/income_vs_bikes.png")

chart1

