# =============================================================================
# Airbnb Market Analytics System
# Milestone 3: Data Cleaning — Neighbourhoods
# City: Configurable
# =============================================================================

import json
import pandas as pd
import os
import argparse
from datetime import datetime


def get_config(city):
    return {
        "city": city,
        "input_file": f"data/raw/{city}/neighbourhoods.geojson",
        "output_csv": f"data/processed/{city}/neighbourhoods_clean.csv",
        "output_geojson": f"data/processed/{city}/neighbourhoods_clean.geojson",
    }


def load_geojson(path):
    print(f"Loading {path}...")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Loaded: {len(data['features'])} neighbourhoods")
    return data


def extract_reference_table(data, city):
    print(f"\n--- Extracting neighbourhood reference table ---")

    records = []
    for feature in data["features"]:
        props = feature["properties"]
        records.append({
            "city": city,
            "neighbourhood": props.get("neighbourhood", "").strip(),
            "neighbourhood_group": props.get("neighbourhood_group", None),
            "geometry_type": feature["geometry"]["type"],
        })

    df = pd.DataFrame(records)

    # Standardize neighbourhood names — strip whitespace, title case
    df["neighbourhood"] = df["neighbourhood"].str.strip().str.title()

    # Drop neighbourhood_group if 100% null
    if df["neighbourhood_group"].isnull().all():
        print(f"neighbourhood_group: 100% null — dropping")
        df = df.drop(columns=["neighbourhood_group"])

    # Add a surrogate key for use as dimension table PK
    df = df.reset_index(drop=True)
    df.insert(0, "neighbourhood_id", df.index + 1)

    print(f"Neighbourhoods extracted: {len(df)}")
    print(f"Sample: {df['neighbourhood'].head(5).tolist()}")

    return df


def save_outputs(df, data, config):
    os.makedirs(os.path.dirname(config["output_csv"]), exist_ok=True)

    # Save reference CSV
    df.to_csv(config["output_csv"], index=False)
    print(f"\nSaved reference table to: {config['output_csv']}")

    # Save cleaned GeoJSON (same structure, just standardized names)
    for i, feature in enumerate(data["features"]):
        feature["properties"]["neighbourhood"] = df.loc[i, "neighbourhood"]
        feature["properties"]["city"] = config["city"]

    with open(config["output_geojson"], "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Saved cleaned GeoJSON to: {config['output_geojson']}")


def main(city):
    config = get_config(city)

    print("=" * 60)
    print("MILESTONE 3: DATA CLEANING — NEIGHBOURHOODS")
    print(f"City: {city.upper()}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    data = load_geojson(config["input_file"])
    df = extract_reference_table(data, city)
    save_outputs(df, data, config)

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", type=str, default="bangkok")
    args = parser.parse_args()
    main(args.city)
