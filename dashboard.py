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
st.subheader("📈 Weekly Mileage")

weekly = (
    filtered.groupby(["year", "week"])["distance_km"]
    .sum()
    .reset_index()
    .assign(week_str=lambda x: x["year"].astype(str) + "-W" + x["week"].astype(str))
)

fig = px.bar(weekly, x="week_str", y="distance_km", labels={"distance_km":"km"})
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
