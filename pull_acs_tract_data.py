import json
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests
import time


ACS_YEAR = 2022
ACS_DATASET = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
CONFIG_PATH = Path(__file__).with_name("census_config.json")
OUTPUT_PATH = Path(__file__).with_name("acs_tract_data.csv")

ACS_VARIABLES: Dict[str, str] = {
    "B19013_001E": "median_household_income",
    "B25070_010E": "rent_burden_35_plus_units",
    "B25003_003E": "renter_occupied_units",
    "B25001_001E": "total_housing_units",
    "B23025_005E": "unemployed",
    "B23025_003E": "labor_force",
    "B25064_001E": "median_gross_rent",
}


def load_api_key(config_path: Path) -> str:
    with config_path.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    candidate_keys = (
        "api_key",
        "API_KEY",
        "census_api_key",
        "CENSUS_API_KEY",
        "key",
    )

    for candidate in candidate_keys:
        value = config.get(candidate)
        if isinstance(value, str) and value.strip():
            return value.strip()

    raise KeyError(
        f"Could not find a Census API key in {config_path.name}. "
        f"Tried keys: {', '.join(candidate_keys)}."
    )


def fetch_json(params: Dict[str, str], max_retries: int = 5, backoff: int = 3) -> List[List[str]]:
    """
    Robust Census API fetch with retries and backoff.
    Handles dropped connections, timeouts, and rate limits.
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(ACS_DATASET, params=params, timeout=60)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            print(f"[Retry {attempt}/{max_retries}] Census API error: {e}")

            if attempt == max_retries:
                print("Max retries reached. Giving up on this request.")
                raise

            time.sleep(backoff * attempt)  # exponential backoff


def fetch_states(api_key: str) -> List[str]:
    rows = fetch_json(
        {
            "get": "NAME",
            "for": "state:*",
            "key": api_key,
        }
    )
    return [row[1] for row in rows[1:]]


def fetch_counties(state_fips: str, api_key: str) -> List[str]:
    rows = fetch_json(
        {
            "get": "NAME",
            "for": "county:*",
            "in": f"state:{state_fips}",
            "key": api_key,
        }
    )
    return [row[2] for row in rows[1:]]


def fetch_tract_rows(state_fips: str, county_fips: str, api_key: str) -> List[Dict[str, str]]:
    variables = ",".join(ACS_VARIABLES.keys())
    rows = fetch_json(
        {
            "get": variables,
            "for": "tract:*",
            "in": f"state:{state_fips} county:{county_fips}",
            "key": api_key,
        }
    )
    header = rows[0]
    return [dict(zip(header, row)) for row in rows[1:]]


def to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_dataframe(records: List[Dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame.from_records(records)

    rename_map = {**ACS_VARIABLES, "state": "state_fips", "county": "county_fips", "tract": "tract_code"}
    df = df.rename(columns=rename_map)

    numeric_columns = list(ACS_VARIABLES.values())
    for column in numeric_columns:
        df[column] = to_numeric(df[column])

    df["GEOID"] = (
        df["state_fips"].astype(str).str.zfill(2)
        + df["county_fips"].astype(str).str.zfill(3)
        + df["tract_code"].astype(str).str.zfill(6)
    )

    df["rent_burden_35_plus_share"] = (
        df["rent_burden_35_plus_units"] / df["renter_occupied_units"]
    ).where(df["renter_occupied_units"] > 0)

    df["unemployment_rate_proxy"] = (
        df["unemployed"] / df["labor_force"]
    ).where(df["labor_force"] > 0)

    ordered_columns = [
        "GEOID",
        "state_fips",
        "county_fips",
        "tract_code",
        "median_household_income",
        "rent_burden_35_plus_units",
        "rent_burden_35_plus_share",
        "renter_occupied_units",
        "total_housing_units",
        "unemployed",
        "labor_force",
        "unemployment_rate_proxy",
        "median_gross_rent",
    ]
    return df[ordered_columns].sort_values("GEOID").reset_index(drop=True)

def main() -> None:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Missing config file: {CONFIG_PATH}. Add census_config.json next to this script."
        )

    api_key = load_api_key(CONFIG_PATH)
    records: List[Dict[str, str]] = []

    states = fetch_states(api_key)
    print(f"🗺️ Found {len(states)} states to process...")

    for i, state_fips in enumerate(states, 1):
        counties = fetch_counties(state_fips, api_key)
        print(f"📍 [{i}/{len(states)}] State {state_fips} — {len(counties)} counties")
        for county_fips in counties:
            records.extend(fetch_tract_rows(state_fips, county_fips, api_key))

    print(f"🏗️ Building dataframe from {len(records):,} raw records...")
    tract_df = build_dataframe(records)
    tract_df.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Saved {len(tract_df):,} tract rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()


