from pathlib import Path

import pandas as pd


INPUT_PATH = Path("data/raw/all-tracts.csv")
OUTPUT_PATH = Path("data/processed/evictionlab_tract_data.csv")

KEEP_COLUMNS = [
    'GEOID',
    'year',
    'eviction.filing.rate',
    'eviction.rate',
    'eviction.filings',
    'evictions',
    'renter.occupied.households',
    'poverty.rate',
]

def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH, usecols=KEEP_COLUMNS)
    df = df.replace(-1, pd.NA)

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    most_recent_year = int(df["year"].max())
    df = df.loc[df["year"] == most_recent_year].copy()

    df["GEOID"] = df["GEOID"].astype(str).str.extract(r"(\d+)", expand=False).str.zfill(11)

    numeric_columns = [column for column in KEEP_COLUMNS if column != "GEOID"]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.sort_values("GEOID").reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(df):,} rows to {OUTPUT_PATH}")
    print(f"Filtered to most recent year: {most_recent_year}")


if __name__ == "__main__":
    main()
