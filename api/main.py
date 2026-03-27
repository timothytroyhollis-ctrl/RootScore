from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


SHAP_PATH = Path("data/processed/shap_explanations.csv")
MODELING_PATH = Path("data/processed/modeling_dataset.csv")

RISK_LABELS = {
    "median_household_income": "Median household income",
    "rent_burden_35_plus_share": "Share of renters spending 35%+ on rent",
    "renter_occupied_units": "Renter-occupied homes",
    "total_housing_units": "Total housing units",
    "unemployment_rate_proxy": "Unemployment rate",
    "median_gross_rent": "Median gross rent",
    "poverty.rate": "Poverty rate",
    "poverty_rate": "Poverty rate",
    "depression_among_adults": "Depression among adults",
    "fair_poor_health_status": "Fair or poor health status",
    "frequent_mental_distress": "Frequent mental distress",
}

CITY_COLUMN_CANDIDATES = ["city", "city_name", "City", "CityName"]
STATE_COLUMN_CANDIDATES = ["state_abbr", "StateAbbr", "state", "state_code"]

app = FastAPI(title="RootScore API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def normalize_geoid(value: str) -> str:
    digits = "".join(character for character in str(value) if character.isdigit())
    return digits.zfill(11)


def feature_label(feature_name: str) -> str:
    return RISK_LABELS.get(feature_name, feature_name.replace("_", " ").replace(".", " ").title())


def resolve_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def risk_tier(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


@app.on_event("startup")
def load_data() -> None:
    if not SHAP_PATH.exists():
        raise FileNotFoundError(f"Missing SHAP explanations file: {SHAP_PATH}")
    if not MODELING_PATH.exists():
        raise FileNotFoundError(f"Missing modeling dataset file: {MODELING_PATH}")

    shap_df = pd.read_csv(SHAP_PATH, dtype={"GEOID": "string"})
    shap_df["GEOID"] = shap_df["GEOID"].astype("string").map(normalize_geoid)

    modeling_df = pd.read_csv(MODELING_PATH, dtype={"GEOID": "string"})
    modeling_df["GEOID"] = modeling_df["GEOID"].astype("string").map(normalize_geoid)

    app.state.shap_df = shap_df
    app.state.modeling_df = modeling_df
    app.state.tract_df = shap_df.merge(modeling_df, on="GEOID", how="left", suffixes=("", "_model"))
    app.state.city_column = resolve_column(app.state.tract_df, CITY_COLUMN_CANDIDATES)
    app.state.state_column = resolve_column(app.state.tract_df, STATE_COLUMN_CANDIDATES)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tract/{geoid}")
def get_tract(geoid: str) -> dict:
    normalized_geoid = normalize_geoid(geoid)
    if len(normalized_geoid) != 11:
        raise HTTPException(status_code=400, detail="GEOID must be an 11-digit census tract code.")

    tract_df = app.state.tract_df
    tract_rows = tract_df.loc[tract_df["GEOID"] == normalized_geoid]
    if tract_rows.empty:
        raise HTTPException(status_code=404, detail="Tract not found.")

    row = tract_rows.iloc[0]
    drivers = []
    for rank in range(1, 4):
        feature_key = row.get(f"top_feature_{rank}")
        feature_value = row.get(f"top_feature_{rank}_value")
        drivers.append(
            {
                "feature": feature_key,
                "label": feature_label(str(feature_key)),
                "shap_value": None if pd.isna(feature_value) else float(feature_value),
            }
        )

    score = float(row["predicted_risk_score"])
    return {
        "GEOID": normalized_geoid,
        "predicted_risk_score": score,
        "risk_tier": risk_tier(score),
        "top_driving_factors": drivers,
    }


@app.get("/city/{city_name}")
def get_city(city_name: str, state_abbr: str = Query(..., min_length=2, max_length=2)) -> dict:
    city_column = app.state.city_column
    state_column = app.state.state_column

    if city_column is None or state_column is None:
        raise HTTPException(
            status_code=500,
            detail="City lookup columns are missing from the in-memory dataset.",
        )

    tract_df = app.state.tract_df.copy()
    city_mask = tract_df[city_column].astype(str).str.casefold() == city_name.casefold()
    state_mask = tract_df[state_column].astype(str).str.upper() == state_abbr.upper()
    filtered_df = tract_df.loc[city_mask & state_mask].sort_values(
        "predicted_risk_score",
        ascending=False,
    )

    if filtered_df.empty:
        raise HTTPException(status_code=404, detail="No tracts found for that city and state.")

    tracts = []
    for _, row in filtered_df.iterrows():
        score = float(row["predicted_risk_score"])
        tracts.append(
            {
                "GEOID": row["GEOID"],
                "predicted_risk_score": score,
                "risk_tier": risk_tier(score),
            }
        )

    return {
        "city_name": city_name,
        "state_abbr": state_abbr.upper(),
        "tract_count": len(tracts),
        "tracts": tracts,
    }
