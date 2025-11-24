import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import folium
from streamlit_folium import st_folium
import os

st.set_page_config(page_title="Strava Dashboard", layout="wide")

@st.cache_data
def load_data():
    return pd.read_parquet("data/runs.parquet")

df = load_data()

st.title("🏃 My Strava Dashboard")

# ---------------------
# FILTERS
# ---------------------
min_date = df["start_date"].min()
max_date = df["start_date"].max()

date_range = st.date_input("Filter by date range:", [min_date, max_date])

filtered = df[
    (df["start_date"].dt.date >= date_range[0]) &
    (df["start_date"].dt.date <= date_range[1])
]

# ---------------------
# WEEKLY MILEAGE
# ---------------------
st.subheader("📈 Mileage Over Time")

group_choice = st.radio(
    "Group mileage by:",
    ["Week", "Month", "Year"],
    horizontal=True,
    index=0,  # Default = Week
)

# Default date filter = past 12 weeks
default_start = df["start_date"].max() - pd.Timedelta(weeks=12)

start_date = st.date_input(
    "Start date",
    value=default_start.date(),
)

# Apply date filter
df["start_date_local"] = (
    pd.to_datetime(df["start_date_local"]).dt.tz_localize(None)
)

filtered = df[df["start_date_local"] >= pd.to_datetime(start_date)]

if group_choice == "Week":
    grouped = (
        filtered.groupby("week", as_index=False)
        .agg({"distance_miles": "sum"})
        .rename(columns={"week": "Period"})
    )

elif group_choice == "Month":
    grouped = (
        filtered.groupby("month", as_index=False)
        .agg({"distance_miles": "sum"})
        .rename(columns={"month": "Period"})
    )

elif group_choice == "Year":
    grouped = (
        filtered.groupby("year", as_index=False)
        .agg({"distance_miles": "sum"})
        .rename(columns={"year": "Period"})
    )


fig = px.bar(
    grouped,
    x="Period",
    y="distance_miles",
    text="miles",
    title=f"Total Mileage per {group_choice}",
)

fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
fig.update_layout(yaxis_title="Miles")

st.plotly_chart(fig, use_container_width=True)

# ---------------------
# PACE TREND
# ---------------------
st.subheader("⏱ Pace Trend")

pace_fig = px.scatter(
    filtered,
    x="start_date",
    y="pace_sec_per_km",
    hover_data=["name", "distance_km"],
    trendline="lowess",
    labels={"pace_sec_per_km": "Seconds per km"},
)
st.plotly_chart(pace_fig, use_container_width=True)

# ---------------------
# ROUTE MAP SELECTOR
# ---------------------
st.subheader("🗺 View Run Route (GPS Only)")

# select run by name
run_choice = st.selectbox("Choose a run:", filtered.sort_values("start_date")["name"].unique())

selected = filtered[filtered["name"] == run_choice].iloc[0]

st.write(f"**Selected Run:** {selected['name']}")
st.write(f"**Distance:** {selected['distance_km']:.2f} km")
st.write(f"**Date:** {selected['start_date'].date()}")

# Fetch GPS stream
def fetch_latlng_stream(activity_id, access_token):
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    params = {"keys": "latlng", "key_by_type": "true"}
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers, params=params)
    try:
        return r.json().get("latlng", {}).get("data")
    except:
        return None

# Get token stored from GitHub action? (Optional local)
token = os.getenv("STRAVA_ACCESS_TOKEN")  # or leave blank for local-only map features

coords = None
if token:
    coords = fetch_latlng_stream(selected["id"], token)

if coords:
    m = folium.Map(location=coords[0], zoom_start=13)
    folium.PolyLine(coords, weight=4).add_to(m)
    st_folium(m, width=700, height=500)
else:
    st.info("No GPS data available for this run.")
