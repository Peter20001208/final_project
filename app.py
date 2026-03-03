import json
import numpy as np
import pandas as pd
import streamlit as st
import pydeck as pdk
import altair as alt
from matplotlib import cm

# -------------------------
# Config
# -------------------------
st.set_page_config(page_title="Chicago Divvy Map + Charts", layout="wide")

GEOJSON_PATH = "data_final/derive_data/tract_usage2.geojson"

BIKE_ROUTES_PATH = "data_final/CTA_transportation/Bike_Routes.geojson"

# Map layer options (radio -> property name)
LAYER_OPTIONS = {
    "Trips (n_trips)": "n_trips",
    "Bikes (n_bikes)": "n_bikes",
    "Utilization (bike_utilization)": "bike_utilization",
    "Median income (median_income)": "median_income",
    "Bike lanes (n_lanes)": "n_lanes",
}

# Scatter chart options (radio -> (x, y, y_title, chart_title))
CHART_OPTIONS = {
    "Income vs Utilization": (
        "median_income",
        "bike_utilization",
        "Bike Utilization (Trips per Bike)",
        "Income vs Bike Utilization (Census Tract)",
    ),
    "Income vs Bikes": (
        "median_income",
        "n_bikes",
        "Total Bikes (Dock Capacity)",
        "Income vs Bike Amount (Census Tract)",
    ),
    "Income vs Trips": (
        "median_income",
        "n_trips",
        "Total Trips",
        "Income vs Trips Amount (Census Tract)",
    ),
    "Bikes vs Utilization": (
        "n_bikes",
        "bike_utilization",
        "Bike Utilization (Trips per Bike)",
        "Bikes Amount vs Bike Utilization (Census Tract)",
    ),
}

NUM_COLS = ["n_trips", "n_bikes", "bike_utilization", "median_income", "mean_income", "n_lanes"]

LABEL_MAP = {
    "n_trips": "Total Trips (June 2025)",
    "n_bikes": "Total Bikes (Dock Capacity)",
    "bike_utilization": "Trips per Bike (Utilization)",
    "median_income": "Median Income ($)",
    "n_lanes": "Bike Lanes (count of intersecting segments)",
}

# -------------------------
# Helpers
# -------------------------
@st.cache_data(show_spinner=False)
def load_geojson(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)

@st.cache_data(show_spinner=False)
def geojson_properties_to_df(geo: dict) -> pd.DataFrame:
    props = [feat.get("properties", {}) for feat in geo.get("features", [])]
    df = pd.DataFrame(props)

    # Coerce numeric columns
    for c in NUM_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Cleaning rules
    if "median_income" in df.columns:
        df.loc[df["median_income"] < 0, "median_income"] = np.nan
    if "mean_income" in df.columns:
        df.loc[df["mean_income"] < 0, "mean_income"] = np.nan
    if "n_bikes" in df.columns:
        df.loc[df["n_bikes"] <= 0, "n_bikes"] = np.nan

    return df

def compute_value_range(values: list[float], clip: bool) -> tuple[float, float]:
    arr = np.array(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return (0.0, 1.0)

    if clip:
        lo, hi = np.percentile(arr, [2, 98])
    else:
        lo, hi = float(np.nanmin(arr)), float(np.nanmax(arr))

    if lo == hi:
        hi = lo + 1e-9
    return float(lo), float(hi)

def make_fill_color_fn(lo: float, hi: float, cmap_name: str = "viridis"):
    cmap = cm.get_cmap(cmap_name)

    def to_rgba(v):
        # light grey for missing
        if v is None:
            return [200, 200, 200, 70]
        try:
            v = float(v)
        except Exception:
            return [200, 200, 200, 70]
        if not np.isfinite(v):
            return [200, 200, 200, 70]

        v = min(max(v, lo), hi)
        t = (v - lo) / (hi - lo)

        r, g, b, a = cmap(t)  # 0-1
        return [int(r * 255), int(g * 255), int(b * 255), 160]

    return to_rgba

def get_tract_id_field(df: pd.DataFrame) -> str | None:
    if "geoid10" in df.columns:
        return "geoid10"
    if "GEOID" in df.columns:
        return "GEOID"
    return None

def build_scatter_with_trend(df: pd.DataFrame, xcol: str, ycol: str, ytitle: str, title: str):
    tooltip_cols = [
        c
        for c in ["geoid10", "GEOID", xcol, ycol, "n_trips", "n_bikes", "n_lanes", "median_income"]
        if c in df.columns
    ]

    base = (
        alt.Chart(df)
        .transform_filter(f"isValid(datum.{xcol}) && isValid(datum.{ycol})")
        .encode(
            x=alt.X(f"{xcol}:Q", title=LABEL_MAP.get(xcol, xcol.replace("_", " ").title()), scale=alt.Scale(zero=False)),
            y=alt.Y(f"{ycol}:Q", title=ytitle, scale=alt.Scale(zero=False)),
            tooltip=tooltip_cols,
        )
    )

    points = base.mark_circle(size=45, opacity=0.35)
    trend = base.transform_regression(xcol, ycol).mark_line()

    return (points + trend).properties(title=title, height=420)


def render_css_colorbar(lo: float, hi: float, label: str, clipped: bool, value_col: str):
    """
    Lightweight, responsive CSS gradient bar (no matplotlib figure).
    Uses a viridis-like gradient with a few color stops.
    """
    # A simple viridis-like palette (stops)
    stops = [
        ("0%",   "#440154"),
        ("20%",  "#3b528b"),
        ("40%",  "#21918c"),
        ("60%",  "#5ec962"),
        ("80%",  "#b8de29"),
        ("100%", "#fde725"),
    ]
    gradient = ", ".join([f"{c} {p}" for p, c in stops])

    # Nice tick labels: min / mid / max
    mid = (lo + hi) / 2.0

    def fmt(x):
        # compact readable formatting
        if abs(x) >= 1000:
            return f"{x:,.0f}"
        if abs(x) >= 10:
            return f"{x:.1f}"
        return f"{x:.2f}"

    note = f"clipped={clipped}"
    html = f"""
    <div style="width: 100%; margin-top: 8px; margin-bottom: 2px;">
      <div style="text-align:center; font-size: 18px; font-weight: 600; margin-bottom: 6px;">
        {label}
      </div>

      <div style="
        height: 18px;
        width: 100%;
        border-radius: 8px;
        border: 1px solid rgba(0,0,0,0.18);
        background: linear-gradient(90deg, {gradient});
      "></div>

      <div style="
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        color: rgba(0,0,0,0.70);
        margin-top: 4px;
      ">
        <span>{fmt(lo)}</span>
        <span>{fmt(mid)}</span>
        <span>{fmt(hi)}</span>
      </div>

      <div style="
        text-align:center;
        font-size: 12px;
        color: rgba(0,0,0,0.60);
        margin-top: 4px;
      ">
        Range used: {fmt(lo)} – {fmt(hi)} ({note})
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# -------------------------
# App
# -------------------------
st.title("Chicago Divvy — Choropleth + Relationship Charts")

# Load geojson + df
geo = load_geojson(GEOJSON_PATH)
df = geojson_properties_to_df(geo)

# -------------------------
# Map (top)
# -------------------------
st.subheader("Interactive choropleth (PyDeck)")

# Controls row
c1, c2, c3 = st.columns([2.5, 1.2, 1.3])
with c1:
    selected_label = st.radio("Select layer", list(LAYER_OPTIONS.keys()), horizontal=True)
value_col = LAYER_OPTIONS[selected_label]

with c2:
    use_clip = st.checkbox("Clip extremes (2%–98%)", value=True)

with c3:
    opacity = st.slider("Polygon opacity", min_value=50, max_value=220, value=160, step=10)

# Extract numeric values for range computation
vals = []
for feat in geo.get("features", []):
    v = feat.get("properties", {}).get(value_col, None)
    try:
        v = float(v)
    except Exception:
        continue
    if np.isfinite(v):
        vals.append(v)

if len(vals) == 0:
    st.error(f"No valid numeric values found for {value_col}.")
    st.stop()

lo, hi = compute_value_range(vals, clip=use_clip)
to_rgba = make_fill_color_fn(lo, hi, cmap_name="viridis")

# Assign fill colors
for feat in geo.get("features", []):
    v = feat.get("properties", {}).get(value_col, None)
    rgba = to_rgba(v)
    rgba[3] = int(opacity)  # alpha
    feat["properties"]["fill_color"] = rgba

# Tooltip id field
tract_id_field = get_tract_id_field(df)
tooltip_html = f"<b>{LABEL_MAP.get(value_col, value_col)}:</b> {{{value_col}}}"
if tract_id_field:
    tooltip_html = f"<b>Tract:</b> {{{tract_id_field}}}<br/>" + tooltip_html

tooltip = {"html": tooltip_html, "style": {"backgroundColor": "white", "color": "black"}}

# View
view_state = pdk.ViewState(latitude=41.88, longitude=-87.63, zoom=10.2)

layer = pdk.Layer(
    "GeoJsonLayer",
    data=geo,
    pickable=True,
    stroked=True,
    filled=True,
    get_fill_color="properties.fill_color",
    get_line_color=[255, 255, 255, 90],
    line_width_min_pixels=1,
)

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    map_style="light",
    tooltip=tooltip,
)

st.pydeck_chart(deck, use_container_width=True)

# --- Responsive CSS colorbar (no matplotlib) ---
bar_label = LABEL_MAP.get(value_col, value_col)

render_css_colorbar(
    lo=lo,
    hi=hi,
    label=bar_label,
    clipped=use_clip,
    value_col=value_col
)

# -------------------------
# Charts (bottom)
# -------------------------
st.divider()
st.subheader("Relationship charts (Altair)")

chart_label = st.radio("Select relationship chart", list(CHART_OPTIONS.keys()), horizontal=True)
xcol, ycol, ytitle, chart_title = CHART_OPTIONS[chart_label]

chart = build_scatter_with_trend(df, xcol=xcol, ycol=ycol, ytitle=ytitle, title=chart_title)
st.altair_chart(chart, use_container_width=True)

with st.expander("Data quick check"):
    cols = [c for c in ["geoid10", "GEOID", "n_trips", "n_bikes", "bike_utilization", "median_income", "n_lanes"] if c in df.columns]
    st.write(df[cols].describe(include="all"))

st.divider()
st.subheader("Bike Routes by Facility Type")

# -------------------------
# Load routes
# -------------------------
with open(BIKE_ROUTES_PATH, "r") as f:
    bike_routes = json.load(f)

features = bike_routes.get("features", [])

# -------------------------
# Controls
# -------------------------
r1, r2 = st.columns([1.2, 1.2])
with r1:
    route_width = st.slider("Route width", 1, 12, 3)
with r2:
    route_opacity = st.slider("Route opacity", 50, 255, 170, step=10)

# -------------------------
# Extract facility types
# -------------------------
facility_types = list(set(
    f["properties"].get("displayrou", "Unknown")
    for f in features
))

# Professional color palette
palette = [
    [31, 119, 180],   # blue
    [255, 127, 14],   # orange
    [44, 160, 44],    # green
    [214, 39, 40],    # red
    [148, 103, 189],  # purple
    [140, 86, 75],    # brown
    [227, 119, 194],  # pink
]

color_map = {}
for i, t in enumerate(facility_types):
    color_map[t] = palette[i % len(palette)]

# Assign color to each feature
for f in features:
    t = f["properties"].get("displayrou", "Unknown")
    base_color = color_map[t]
    f["properties"]["route_color"] = base_color + [route_opacity]

# -------------------------
# Create layer
# -------------------------
routes_layer = pdk.Layer(
    "GeoJsonLayer",
    data=bike_routes,
    pickable=True,
    stroked=True,
    filled=False,
    get_line_color="properties.route_color",
    line_width_min_pixels=route_width,
)

view_state_routes = pdk.ViewState(
    latitude=41.88,
    longitude=-87.63,
    zoom=10.2,
)

tooltip_routes = {
    "html": "<b>Facility:</b> {displayrou}<br/>Street: {street}",
    "style": {"backgroundColor": "white", "color": "black"},
}

deck_routes = pdk.Deck(
    layers=[routes_layer],
    initial_view_state=view_state_routes,
    map_style="light",
    tooltip=tooltip_routes,
)

st.pydeck_chart(deck_routes, use_container_width=True)

# -------------------------
# Legend (clean CSS)
# -------------------------
legend_html = "<div style='margin-top:10px;'>"
for t, c in color_map.items():
    legend_html += (
        f"<div style='display:flex;align-items:center;margin-bottom:4px;'>"
        f"<div style='width:16px;height:16px;background:rgb({c[0]},{c[1]},{c[2]});margin-right:8px;'></div>"
        f"<div style='font-size:13px;'>{t}</div>"
        f"</div>"
    )
legend_html += "</div>"

st.markdown(legend_html, unsafe_allow_html=True)

