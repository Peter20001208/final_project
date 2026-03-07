import json
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import pydeck as pdk
import altair as alt
from matplotlib import cm

# ============================================================
# App Config
# ============================================================
st.set_page_config(page_title="Chicago Divvy — Map + Charts", layout="wide")

# Use relative paths so Streamlit Cloud can find files in the repo
GEOJSON_PATH = Path("data/derived-data/tract_usage2.geojson")
BIKE_ROUTES_PATH = Path("data/raw-data/CTA_transportation/Bike_Routes.geojson")

# Map layer options (label -> property name)
LAYER_OPTIONS = {
    "Trips (n_trips)": "n_trips",
    "Bikes (n_bikes)": "n_bikes",
    "Utilization (bike_utilization)": "bike_utilization",
    "Median income (median_income)": "median_income",
    "Bike lanes (n_lanes)": "n_lanes",
}

# Scatter axis options
SCATTER_OPTIONS = {
    "Median income": "median_income",
    "Trips": "n_trips",
    "Bikes": "n_bikes",
    "Utilization": "bike_utilization",
    "Bike lanes": "n_lanes",
}

NUM_COLS = ["n_trips", "n_bikes", "bike_utilization", "median_income", "mean_income", "n_lanes"]

LABEL_MAP = {
    "n_trips": "Total Trips (June 2025)",
    "n_bikes": "Total Bikes (Dock Capacity)",
    "bike_utilization": "Trips per Bike (Utilization)",
    "median_income": "Median Income ($)",
    "mean_income": "Mean Income ($)",
    "n_lanes": "Bike Lanes (count of intersecting segments)",
}

# ============================================================
# Cached IO Helpers
# ============================================================
@st.cache_data(show_spinner=False)
def load_geojson(path_str: str) -> dict:
    """Load a GeoJSON file and cache it."""
    with open(path_str, "r") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def geojson_properties_to_df(geo: dict) -> pd.DataFrame:
    """Convert GeoJSON feature properties to a DataFrame and apply basic cleaning."""
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

# Ensure tract IDs are strings (avoid pyarrow conversion errors)
    for id_col in ["geoid10", "GEOID"]:
        if id_col in df.columns:
            df[id_col] = df[id_col].astype(str)

    return df


# ============================================================
# Core Computation Helpers
# ============================================================
def compute_value_range(values, clip: bool):
    """Compute color scale range with optional percentile clipping."""
    arr = np.array(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return 0.0, 1.0

    if clip:
        lo, hi = np.percentile(arr, [2, 98])
    else:
        lo, hi = float(np.nanmin(arr)), float(np.nanmax(arr))

    if lo == hi:
        hi = lo + 1e-9
    return float(lo), float(hi)


def make_fill_color_fn(lo: float, hi: float, cmap_name: str = "viridis"):
    """Return a function mapping numeric values -> RGBA for polygons."""
    cmap = cm.get_cmap(cmap_name)

    def to_rgba(v):
        # Light grey for missing
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


def get_tract_id_field(df: pd.DataFrame):
    """Pick a tract id field if present."""
    if "geoid10" in df.columns:
        return "geoid10"
    if "GEOID" in df.columns:
        return "GEOID"
    return None

def build_scatter_with_trend(df: pd.DataFrame, xcol: str, ycol: str):
    """Build an Altair scatter plot with a regression trend line."""

    tooltip_cols = [
        c
        for c in ["geoid10", "GEOID", xcol, ycol, "n_trips", "n_bikes", "n_lanes", "median_income"]
        if c in df.columns
    ]

    x_title = LABEL_MAP.get(xcol, xcol.replace("_", " ").title())
    y_title = LABEL_MAP.get(ycol, ycol.replace("_", " ").title())
    chart_title = f"{x_title} vs {y_title} (Census Tract)"

    base = (
        alt.Chart(df)
        .transform_filter(f"isValid(datum.{xcol}) && isValid(datum.{ycol})")
        .encode(
            x=alt.X(
                f"{xcol}:Q",
                title=x_title,
                scale=alt.Scale(zero=False),
            ),
            y=alt.Y(
                f"{ycol}:Q",
                title=y_title,
                scale=alt.Scale(zero=False),
            ),
            tooltip=tooltip_cols,
        )
    )

    points = base.mark_circle(size=45, opacity=0.35)
    trend = base.transform_regression(xcol, ycol).mark_line()

    return (points + trend).properties(title=chart_title, height=420)


def render_css_colorbar(lo: float, hi: float, label: str, clipped: bool):
    """
    Lightweight, responsive CSS gradient bar (no matplotlib figure).
    Uses a viridis-like gradient with a few color stops.
    """
    stops = [
        ("0%", "#440154"),
        ("20%", "#3b528b"),
        ("40%", "#21918c"),
        ("60%", "#5ec962"),
        ("80%", "#b8de29"),
        ("100%", "#fde725"),
    ]
    gradient = ", ".join([f"{c} {p}" for p, c in stops])

    mid = (lo + hi) / 2.0

    def fmt(x):
        if abs(x) >= 1000:
            return f"{x:,.0f}"
        if abs(x) >= 10:
            return f"{x:.1f}"
        return f"{x:.2f}"

    html = f"""
    <div style="width:100%; margin-top:8px;">
      <div style="text-align:center; font-size:18px; font-weight:600; margin-bottom:6px;">
        {label}
      </div>

      <div style="
        height:18px;
        width:100%;
        border-radius:8px;
        border:1px solid rgba(0,0,0,0.18);
        background: linear-gradient(90deg, {gradient});
      "></div>

      <div style="
        display:flex;
        justify-content:space-between;
        font-size:12px;
        color: rgba(0,0,0,0.70);
        margin-top:4px;
      ">
        <span>{fmt(lo)}</span>
        <span>{fmt(mid)}</span>
        <span>{fmt(hi)}</span>
      </div>

      <div style="text-align:center; font-size:12px; color: rgba(0,0,0,0.60); margin-top:4px;">
        Range used: {fmt(lo)} – {fmt(hi)} (clipped={clipped})
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# Cached GeoJSON Colorization (Big speedup)
# ============================================================
@st.cache_data(show_spinner=False)
def colorize_tract_geojson(geo: dict, value_col: str, use_clip: bool, opacity: int):
    """
    Create a colored copy of the tract GeoJSON based on the selected variable.
    Cached so UI changes don't repeatedly recolor everything.
    """
    # Deep copy to avoid mutating cached base GeoJSON
    geo_copy = json.loads(json.dumps(geo))

    values = []
    for feat in geo_copy.get("features", []):
        v = feat.get("properties", {}).get(value_col, None)
        try:
            v = float(v)
        except Exception:
            continue
        if np.isfinite(v):
            values.append(v)

    lo, hi = compute_value_range(values, clip=use_clip)
    to_rgba = make_fill_color_fn(lo, hi, cmap_name="viridis")

    for feat in geo_copy.get("features", []):
        v = feat.get("properties", {}).get(value_col, None)
        rgba = to_rgba(v)
        rgba[3] = int(opacity)
        feat["properties"]["fill_color"] = rgba

    return geo_copy, lo, hi


# ============================================================
# Cached Bike Routes Colorization
# ============================================================
@st.cache_data(show_spinner=False)
def colorize_routes(routes_geo: dict, route_opacity: int):
    """
    Apply a deterministic color mapping to bike routes based on facility type.
    Cached to avoid recomputing on every rerun.
    """
    routes_copy = json.loads(json.dumps(routes_geo))
    features = routes_copy.get("features", [])

    facility_types = sorted(
        set(f.get("properties", {}).get("displayrou", "Unknown") for f in features)
    )

    palette = [
        [31, 119, 180],
        [255, 127, 14],
        [44, 160, 44],
        [214, 39, 40],
        [148, 103, 189],
        [140, 86, 75],
        [227, 119, 194],
    ]

    color_map = {t: palette[i % len(palette)] for i, t in enumerate(facility_types)}

    for f in features:
        t = f.get("properties", {}).get("displayrou", "Unknown")
        base_color = color_map.get(t, [120, 120, 120])
        f["properties"]["route_color"] = base_color + [int(route_opacity)]

    return routes_copy, color_map


# ============================================================
# App
# ============================================================
st.title("Chicago Divvy — Choropleth + Relationship Charts")

# --------- File checks (helpful on Streamlit Cloud) ----------
if not GEOJSON_PATH.exists():
    st.error(f"Missing file: {GEOJSON_PATH}. Make sure it is committed to your GitHub repo.")
    st.stop()

if not BIKE_ROUTES_PATH.exists():
    st.error(f"Missing file: {BIKE_ROUTES_PATH}. Make sure it is committed to your GitHub repo.")
    st.stop()

# --------- Load data (cached) ----------
geo = load_geojson(str(GEOJSON_PATH))
df = geojson_properties_to_df(geo)

# ============================================================
# 1) Choropleth Map
# ============================================================
st.subheader("Interactive choropleth (PyDeck)")

c1, c2, c3 = st.columns([2.5, 1.2, 1.3])
with c1:
    selected_label = st.radio("Select layer", list(LAYER_OPTIONS.keys()), horizontal=True)
value_col = LAYER_OPTIONS[selected_label]

with c2:
    use_clip = st.checkbox("Clip extremes (2%–98%)", value=True)

with c3:
    opacity = st.slider("Polygon opacity", min_value=50, max_value=220, value=160, step=10)

# Colorize tracts (cached)
geo_colored, lo, hi = colorize_tract_geojson(
    geo,
    value_col=value_col,
    use_clip=use_clip,
    opacity=opacity,
)

# Tooltip fields
tract_id_field = get_tract_id_field(df)
tooltip_html = f"<b>{LABEL_MAP.get(value_col, value_col)}:</b> {{{value_col}}}"
if tract_id_field:
    tooltip_html = f"<b>Tract:</b> {{{tract_id_field}}}<br/>" + tooltip_html

tooltip = {"html": tooltip_html, "style": {"backgroundColor": "white", "color": "black"}}

view_state = pdk.ViewState(latitude=41.88, longitude=-87.63, zoom=10.2)

tract_layer = pdk.Layer(
    "GeoJsonLayer",
    data=geo_colored,
    pickable=True,
    stroked=True,
    filled=True,
    get_fill_color="properties.fill_color",
    get_line_color=[255, 255, 255, 90],
    line_width_min_pixels=1,
)

deck = pdk.Deck(
    layers=[tract_layer],
    initial_view_state=view_state,
    map_style="light",
    tooltip=tooltip,
)

st.pydeck_chart(deck, use_container_width=True)

# Responsive CSS colorbar (no matplotlib)
bar_label = LABEL_MAP.get(value_col, value_col)
render_css_colorbar(lo=lo, hi=hi, label=bar_label, clipped=use_clip)

# ============================================================
# 2) Altair Charts
# ============================================================
st.divider()
st.subheader("Relationship charts (Altair)")

s1, s2 = st.columns(2)

with s1:
    x_label = st.selectbox("Select x-axis", list(SCATTER_OPTIONS.keys()), index=0)

with s2:
    y_label = st.selectbox("Select y-axis", list(SCATTER_OPTIONS.keys()), index=2)

xcol = SCATTER_OPTIONS[x_label]
ycol = SCATTER_OPTIONS[y_label]

if xcol == ycol:
    st.warning("Please select two different variables for the x-axis and y-axis.")
else:
    chart = build_scatter_with_trend(df, xcol=xcol, ycol=ycol)
    st.altair_chart(chart, use_container_width=True)

with st.expander("Data quick check"):
    cols = [c for c in ["geoid10", "GEOID", "n_trips", "n_bikes", "bike_utilization", "median_income", "n_lanes"] if c in df.columns]
    st.write(df[cols].describe(include="all"))

# ============================================================
# 3) Bike Routes Map (separate, below dashboard)
# ============================================================
st.divider()
st.subheader("Bike Routes by Facility Type")

r1, r2 = st.columns([1.2, 1.2])
with r1:
    route_width = st.slider("Route width", 1, 12, 3)
with r2:
    route_opacity = st.slider("Route opacity", 50, 255, 170, step=10)

routes_raw = load_geojson(str(BIKE_ROUTES_PATH))
routes_colored, color_map = colorize_routes(routes_raw, route_opacity=route_opacity)

routes_layer = pdk.Layer(
    "GeoJsonLayer",
    data=routes_colored,
    pickable=True,
    stroked=True,
    filled=False,
    get_line_color="properties.route_color",
    line_width_min_pixels=route_width,
)

tooltip_routes = {
    "html": "<b>Facility:</b> {displayrou}<br/>Street: {street}",
    "style": {"backgroundColor": "white", "color": "black"},
}

deck_routes = pdk.Deck(
    layers=[routes_layer],
    initial_view_state=pdk.ViewState(latitude=41.88, longitude=-87.63, zoom=10.2),
    map_style="light",
    tooltip=tooltip_routes,
)

st.pydeck_chart(deck_routes, use_container_width=True)

# ---- No HTML legend by default (simple annotation under the map) ----
facility_list = ", ".join(color_map.keys()) if len(color_map) else "Unknown"
st.caption(f"Facility types in this dataset: {facility_list}")

# Optional: allow users to show a compact HTML legend if they want
with st.expander("Show legend (optional)", expanded=False):
    legend_html = "<div style='margin-top:6px;'>"
    for t, c in color_map.items():
        legend_html += (
            "<div style='display:flex;align-items:center;margin-bottom:4px;'>"
            f"<div style='width:14px;height:14px;border-radius:3px;background:rgb({c[0]},{c[1]},{c[2]});margin-right:8px;'></div>"
            f"<div style='font-size:13px;'>{t}</div>"
            "</div>"
        )
    legend_html += "</div>"
    st.markdown(legend_html, unsafe_allow_html=True)