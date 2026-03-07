
# setup
import altair as alt
import pandas as pd
import warnings
import tempfile
from IPython.display import display, Image
import vl_convert as vlc
warnings.filterwarnings('ignore')
alt.renderers.enable('png')
data_path = 'data/external'


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

# Draw Maps

divvy_2506 = pd.read_parquet("data/derived-data/divvy_202506_cleaned.parquet")


# Build small aggregated tables (start-hour)
member_small = (
    divvy_2506.dropna(subset=['start_hour', 'week_part', 'member_casual'])
      .groupby(['week_part', 'start_hour', 'member_casual'], as_index=False)
      .size()
      .rename(columns={'size': 'count'})
)

# Normalize by exposure days
DAY_DIVISOR = {'Weekday': 21, 'Weekend': 9}
member_small['avg_per_day'] = member_small['count'] / member_small['week_part'].map(DAY_DIVISOR)

# Map membership labels
member_map = {'member': 'Member', 'casual': 'Casual'}
member_small['member_label'] = (
    member_small['member_casual']
    .map(member_map)
    .fillna(member_small['member_casual'])
)

# Convert 24-hour clock to standard AM/PM labels
def hour_to_ampm(h):
    h = int(h)
    if h == 0:
        return "12 AM"
    elif h < 12:
        return f"{h} AM"
    elif h == 12:
        return "12 PM"
    else:
        return f"{h - 12} PM"

member_small['hour_label'] = member_small['start_hour'].apply(hour_to_ampm)

# Create sparse labels so only every 2 hours is shown
member_small['hour_label_sparse'] = member_small['start_hour'].apply(
    lambda h: hour_to_ampm(h) if h % 2 == 0 else ""
)

# Keep the correct chronological order on the x-axis
hour_order = [hour_to_ampm(h) for h in range(24)]

# Membership color palette
member_colors = alt.Scale(
    domain=['Member', 'Casual'],
    range=['#4CAF50', '#E91E63']
)

# Membership start-time chart
chart_member = alt.Chart(member_small).mark_bar(
    opacity=0.88,
    size=16
).encode(
    column=alt.Column(
        'week_part:N',
        title=None,
        sort=['Weekday', 'Weekend'],
        header=alt.Header(
            labelFontSize=16,
            titleFontSize=14,
            labelOrient='top'
        )
    ),

    x=alt.X(
        'hour_label:O',
        title='Hour of Day',
        sort=hour_order,
        axis=alt.Axis(
            values=hour_order[::2],   # show every 2 hours
            labelAngle=0,
            labelFontSize=12,
            titleFontSize=14,
            tickSize=4
        )
    ),

    y=alt.Y(
        'avg_per_day:Q',
        title='Avg rides per day',
        axis=alt.Axis(
            labelFontSize=12,
            titleFontSize=14,
            grid=True
        )
    ),

    color=alt.Color(
        'member_label:N',
        title='Membership',
        scale=member_colors,
        legend=alt.Legend(
            labelFontSize=12,
            titleFontSize=14,
            orient='right'
        )
    ),

    tooltip=[
        alt.Tooltip('week_part:N', title='Week Part'),
        alt.Tooltip('hour_label:N', title='Hour'),
        alt.Tooltip('member_label:N', title='Membership'),
        alt.Tooltip('avg_per_day:Q', title='Avg/day', format=',.1f')
    ]
).properties(
    width=500,
    height=400,
    title='Start Time Distribution — Membership'
).configure_title(
    fontSize=18,
    anchor='start'
).configure_view(
    stroke=None
)

display_altair_png(chart_member, scale=4)

chart_member.save("time_member_analysis/time_member_analysis.png")


