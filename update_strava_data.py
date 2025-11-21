import os
import requests
import pandas as pd

STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

def refresh_access_token():
    url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": STRAVA_REFRESH_TOKEN,
    }
    res = requests.post(url, data=payload)
    res.raise_for_status()
    return res.json()["access_token"]

def get_all_activities(access_token, per_page=200):
    activities = []
    page = 1

    while True:
        url = "https://www.strava.com/api/v3/athlete/activities"
        params = {"page": page, "per_page": per_page}
        headers = {"Authorization": f"Bearer {access_token}"}

        r = requests.get(url, headers=headers, params=params)
        data = r.json()

        if not data:
            break

        activities.extend(data)
        page += 1

    return activities

def clean_activities(raw):
    df = pd.DataFrame(raw)
    if df.empty:
        return df

    # Normalize fields you tend to use
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["distance_km"] = df["distance"] / 1000
    df["pace_sec_per_km"] = df["moving_time"] / df["distance_km"]
    df["week"] = df["start_date"].dt.isocalendar().week
    df["year"] = df["start_date"].dt.year

    return df

def main():
    token = refresh_access_token()
    raw = get_all_activities(token)
    df = clean_activities(raw)

    os.makedirs("data", exist_ok=True)
    df.to_parquet("data/runs.parquet")
    print("Saved updated runs.parquet")

if __name__ == "__main__":
    main()
