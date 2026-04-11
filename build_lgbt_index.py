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

LGBT_POLICY_RAW_SCORES = {
    "AK": 18,
    "AL": -12,
    "AR": -14,
    "AZ": 16,
    "CA": 44,
    "CO": 41,
    "CT": 40,
    "DC": 46,
    "DE": 35,
    "FL": 4,
    "GA": 3,
    "HI": 38,
    "IA": 14,
    "ID": -6,
    "IL": 40,
    "IN": 8,
    "KS": 7,
    "KY": 3,
    "LA": -14,
    "MA": 44,
    "MD": 40,
    "ME": 37,
    "MI": 20,
    "MN": 38,
    "MO": 8,
    "MS": -18,
    "MT": -2,
    "NC": 11,
    "ND": -5,
    "NE": 10,
    "NH": 28,
    "NJ": 41,
    "NM": 36,
    "NV": 37,
    "NY": 42,
    "OH": 12,
    "OK": -10,
    "OR": 40,
    "PA": 22,
    "RI": 39,
    "SC": 3,
    "SD": 3,
    "TN": -8,
    "TX": -4,
    "UT": 8,
    "VA": 30,
    "VT": 44,
    "WA": 41,
    "WI": 18,
    "WV": 3,
    "WY": 4,
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


def normalize_scores(score_map: dict[str, float]) -> dict[str, float]:
    min_score = min(score_map.values())
    max_score = max(score_map.values())
    return {
        state_abbr: ((raw_score - min_score) / (max_score - min_score)) * 100.0
        for state_abbr, raw_score in score_map.items()
    }


def main() -> None:
    for path in [QROOTS_SCORES_PATH, ZIP_CROSSWALK_PATH]:
        require_file(path)

    qroots_df = pd.read_csv(QROOTS_SCORES_PATH, dtype={"GEOID": "string"})
    qroots_df["GEOID"] = qroots_df["GEOID"].astype("string").map(normalize_geoid)
    qroots_df["state_fips"] = qroots_df["GEOID"].str[:2]
    qroots_df["state_abbr"] = qroots_df["state_fips"].map(STATE_ABBR_BY_FIPS)
    normalized_lgbt_scores = normalize_scores(LGBT_POLICY_RAW_SCORES)
    qroots_df["lgbt_policy_score"] = qroots_df["state_abbr"].map(normalized_lgbt_scores)

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
        "lgbt_policy_score",
    ]
    output_df = explorer_df[output_columns].drop_duplicates(subset="GEOID", keep="first").reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(output_df):,} rows to {OUTPUT_PATH}")

    state_score_df = (
        pd.DataFrame(
            [
                {"state_abbr": state_abbr, "lgbt_policy_score": score}
                for state_abbr, score in normalized_lgbt_scores.items()
            ]
        )
        .sort_values("lgbt_policy_score", ascending=False)
        .reset_index(drop=True)
    )

    print("Top 5 states by lgbt_policy_score:")
    print(state_score_df.head(5).to_string(index=False))
    print("Bottom 5 states by lgbt_policy_score:")
    print(state_score_df.tail(5).sort_values("lgbt_policy_score").to_string(index=False))


if __name__ == "__main__":
    main()
