from pathlib import Path

import pandas as pd


QROOTS_SCORES_PATH = Path("data/processed/qroots_scores.csv")
ZIP_CROSSWALK_PATH = Path("data/processed/zip_tract_crosswalk.csv")
OUTPUT_PATH = Path("data/processed/explorer_index.csv")

STATE_ABBR_BY_FIPS = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
}


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")


def normalize_geoid(value: object) -> str:
    digits = "".join(character for character in str(value) if character.isdigit())
    return digits.zfill(11)


def normalize_zip(value: object) -> str:
    digits = "".join(character for character in str(value) if character.isdigit())
    return digits.zfill(5)


def main() -> None:
    for path in [QROOTS_SCORES_PATH, ZIP_CROSSWALK_PATH]:
        require_file(path)

    qroots_df = pd.read_csv(QROOTS_SCORES_PATH, dtype={"GEOID": "string"})
    qroots_df["GEOID"] = qroots_df["GEOID"].astype("string").map(normalize_geoid)
    qroots_df["state_fips"] = qroots_df["GEOID"].str[:2]
    qroots_df["state_abbr"] = qroots_df["state_fips"].map(STATE_ABBR_BY_FIPS)

    zip_crosswalk_df = pd.read_csv(
        ZIP_CROSSWALK_PATH,
        dtype={"zip": "string", "tract_geoid": "string"},
    )
    zip_crosswalk_df["zip"] = zip_crosswalk_df["zip"].astype("string").map(normalize_zip)
    zip_crosswalk_df["tract_geoid"] = zip_crosswalk_df["tract_geoid"].astype("string").map(normalize_geoid)
    zip_crosswalk_df = zip_crosswalk_df.sort_values(["tract_geoid", "zip"]).drop_duplicates(
        subset="tract_geoid",
        keep="first",
    )

    explorer_df = qroots_df.merge(
        zip_crosswalk_df[["tract_geoid", "zip"]],
        left_on="GEOID",
        right_on="tract_geoid",
        how="left",
    )

    output_columns = [
        "GEOID",
        "zip",
        "state_fips",
        "state_abbr",
        "qroots_score",
        "housing_stability_score",
        "walk_score",
        "transit_score",
        "education_score",
        "affordability_score",
    ]
    output_df = explorer_df[output_columns].drop_duplicates(subset="GEOID", keep="first").reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(output_df):,} rows to {OUTPUT_PATH}")
    print("Sample rows:")
    print(output_df.head().to_string(index=False))


if __name__ == "__main__":
    main()
