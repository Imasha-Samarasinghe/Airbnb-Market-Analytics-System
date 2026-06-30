# =============================================================================
# Airbnb Market Analytics System
# Milestone 2: Data Ingestion & Profiling
# City: Configurable via --city argument
# Usage: python pipeline/ingestion/ingest_and_profile.py --city bangkok
#        python pipeline/ingestion/ingest_and_profile.py --city lisbon
# =============================================================================

import pandas as pd
import json
import os
import argparse
from datetime import datetime


# =============================================================================
# CONFIGURATION
# =============================================================================

def get_config(city):
    raw_path = f"data/raw/{city}"
    return {
        "city": city,
        "raw_path": raw_path,
        "schemas_path": "data/schemas",
        "files": {
            "listings":      os.path.join(raw_path, "listings.csv"),
            "calendar":      os.path.join(raw_path, "calendar.csv"),
            "reviews":       os.path.join(raw_path, "reviews.csv"),
            "neighbourhoods": os.path.join(raw_path, "neighbourhoods.geojson"),
        }
    }


# =============================================================================
# LOADERS
# =============================================================================

def load_csv(name, path):
    print(f"\n{'='*60}")
    print(f"Loading {name}...")
    try:
        df = pd.read_csv(path, low_memory=False)
        print(
            f"Successfully loaded {name}: {df.shape[0]:,} rows x {df.shape[1]} columns")
        return df
    except Exception as e:
        print(f"ERROR loading {name}: {e}")
        return None


def load_geojson(path):
    print(f"\n{'='*60}")
    print(f"Loading neighbourhoods.geojson...")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        feature_count = len(data.get("features", []))
        print(
            f"Successfully loaded neighbourhoods.geojson: {feature_count} neighbourhoods found")
        return data
    except Exception as e:
        print(f"ERROR loading geojson: {e}")
        return None


# =============================================================================
# PROFILING
# =============================================================================

def check_duplicates(name, df, key_col):
    print(f"\n--- Duplicate Detection: {name} ---")
    total_dupes = df.duplicated().sum()
    print(f"Exact duplicate rows: {total_dupes}")
    if key_col in df.columns:
        key_dupes = df.duplicated(subset=[key_col]).sum()
        print(f"Duplicate {key_col}: {key_dupes}")
    else:
        print(
            f"Key column '{key_col}' not found — skipping key duplicate check")


def profile_dataframe(name, df):
    print(f"\n{'='*60}")
    print(f"PROFILING: {name.upper()}")
    print(f"{'='*60}")

    print(f"\nShape: {df.shape[0]:,} rows x {df.shape[1]} columns")

    print(f"\nColumn Data Types:")
    print(f"{'-'*40}")
    for col, dtype in df.dtypes.items():
        print(f"  {col:<45} {str(dtype)}")

    print(f"\nNull Value Analysis:")
    print(f"{'-'*40}")
    null_counts = df.isnull().sum()
    null_pct = (null_counts / len(df) * 100).round(2)
    null_df = pd.DataFrame({
        "column": null_counts.index,
        "null_count": null_counts.values,
        "null_percentage": null_pct.values
    })
    null_df = null_df[null_df["null_count"] > 0].sort_values(
        "null_percentage", ascending=False)

    if null_df.empty:
        print("  No null values found!")
    else:
        for _, row in null_df.iterrows():
            print(
                f"  {row['column']:<45} {row['null_count']:>8,} nulls ({row['null_percentage']}%)")

    print(f"\nSample Values (first 3 non-null per column):")
    print(f"{'-'*40}")
    for col in df.columns:
        samples = df[col].dropna().head(3).tolist()
        print(f"  {col:<45} {samples}")

    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 0:
        print(f"\nNumeric Column Statistics:")
        print(f"{'-'*40}")
        print(df[numeric_cols].describe().round(2).to_string())

    return null_df


def save_profile_report(name, df, city, schemas_path):
    os.makedirs(schemas_path, exist_ok=True)
    output_path = os.path.join(schemas_path, f"{city}_{name}_profile.csv")

    profile_data = []
    for col in df.columns:
        null_count = df[col].isnull().sum()
        null_pct = round(null_count / len(df) * 100, 2)
        sample_values = str(df[col].dropna().head(3).tolist())
        profile_data.append({
            "city": city,
            "file": name,
            "column": col,
            "dtype": str(df[col].dtype),
            "null_count": null_count,
            "null_percentage": null_pct,
            "sample_values": sample_values,
            "total_rows": len(df)
        })

    profile_df = pd.DataFrame(profile_data)
    profile_df.to_csv(output_path, index=False)
    print(f"\nProfile saved to: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main(city):
    config = get_config(city)

    print("=" * 60)
    print("AIRBNB MARKET ANALYTICS SYSTEM")
    print("Milestone 2: Data Ingestion & Profiling")
    print(f"City: {city.upper()}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    files = config["files"]

    listings_df = load_csv("listings",  files["listings"])
    calendar_df = load_csv("calendar",  files["calendar"])
    reviews_df = load_csv("reviews",   files["reviews"])
    neighbourhoods = load_geojson(files["neighbourhoods"])

    dataframes = {
        "listings":  listings_df,
        "calendar":  calendar_df,
        "reviews":   reviews_df,
    }

    key_cols = {
        "listings": "id",
        "calendar": "listing_id",
        "reviews":  "id",
    }

    for name, df in dataframes.items():
        if df is not None:
            check_duplicates(name, df, key_cols[name])
            null_df = profile_dataframe(name, df)
            save_profile_report(name, df, city, config["schemas_path"])

    # Summary
    print(f"\n{'='*60}")
    print("INGESTION SUMMARY")
    print(f"{'='*60}")
    if listings_df is not None:
        print(
            f"  Listings:       {listings_df.shape[0]:>10,} rows x {listings_df.shape[1]} columns")
    if calendar_df is not None:
        print(
            f"  Calendar:       {calendar_df.shape[0]:>10,} rows x {calendar_df.shape[1]} columns")
    if reviews_df is not None:
        print(
            f"  Reviews:        {reviews_df.shape[0]:>10,} rows x {reviews_df.shape[1]} columns")
    if neighbourhoods is not None:
        print(
            f"  Neighbourhoods: {len(neighbourhoods.get('features', [])):>10,} areas")

    print(f"\nProfile CSVs saved to: {config['schemas_path']}/")
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest and profile Inside Airbnb data for a given city."
    )
    parser.add_argument(
        "--city", type=str, default="bangkok",
        help="City name matching folder in data/raw/ (e.g. bangkok, lisbon)"
    )
    args = parser.parse_args()
    main(args.city)
