# =============================================================================
# Airbnb Market Analytics System
# Milestone 3: Data Cleaning & Standardization — Listings
# City: Configurable via --city argument
# Usage: python pipeline/cleaning/clean_listings.py --city bangkok
#        python pipeline/cleaning/clean_listings.py --city lisbon
# =============================================================================

import pandas as pd
import numpy as np
import os
import argparse
from datetime import datetime

# =============================================================================
# CITY-SPECIFIC CONFIGURATION
# Add a new entry here whenever you add a new city.
# =============================================================================

CITY_CONFIG = {
    "bangkok": {
        "scrape_date":   pd.Timestamp("2025-09-27"),
        "currency":      "฿",
        "coord_bounds": {
            # Tight bounds — Bangkok metro area only
            "lat": (13.4,  14.1),
            "lon": (100.2, 101.0),
        },
    },
    "lisbon": {
        "scrape_date":   pd.Timestamp("2026-03-26"),
        "currency":      "€",
        "coord_bounds": {
            # Wider bounds — Lisbon dataset covers full Greater Lisbon metro
            # (Cascais, Sintra, Setubal coast, Almada, Azambuja etc.)
            "lat": (38.4,  39.4),
            "lon": (-9.6,  -8.8),
        },
    },
}

# =============================================================================
# PROPERTY TYPE NORMALIZATION
# Covers common types across Bangkok and Lisbon.
# When you see types in "Other" after running a new city, add them here.
# =============================================================================

PROPERTY_TYPE_MAPPING = {
    # Entire Apartments
    "Entire rental unit":                   "Entire Apartment",
    "Entire condo":                         "Entire Apartment",
    "Entire serviced apartment":            "Entire Apartment",
    "Entire loft":                          "Entire Apartment",
    "Entire guest suite":                   "Entire Apartment",
    # Private Rooms
    "Private room in rental unit":          "Private Room",
    "Private room in condo":                "Private Room",
    "Private room in home":                 "Private Room",
    "Private room in loft":                 "Private Room",
    "Private room in guest suite":          "Private Room",
    "Private room in villa":                "Private Room",
    "Private room in serviced apartment":   "Private Room",
    "Private room in guesthouse":           "Private Room",
    "Private room in bed and breakfast":    "Private Room",
    "Private room in hostel":               "Private Room",
    "Private room in casa particular":      "Private Room",
    "Private room in townhouse":            "Private Room",
    "Private room in farm stay":            "Private Room",
    "Private room in castle":               "Private Room",
    "Private room in nature lodge":         "Private Room",
    "Private room in cabin":                "Private Room",
    "Private room in chalet":               "Private Room",
    "Private room in tent":                 "Private Room",
    "Private room in cottage":              "Private Room",
    "Private room in boat":                 "Private Room",
    "Private room in dome":                 "Private Room",
    "Private room in earthen home":         "Private Room",
    "Private room in windmill":             "Private Room",
    "Private room in tiny home":            "Private Room",
    "Private room in camper/rv":            "Private Room",
    "Private room in vacation home":        "Private Room",
    "Private room in bungalow":             "Private Room",
    "Private room in minsu":                "Private Room",
    "Private room":                         "Private Room",
    # Entire Houses / Villas
    "Entire home":                          "Entire House",
    "Entire villa":                         "Entire House",
    "Entire townhouse":                     "Entire House",
    "Entire place":                         "Entire House",
    "Entire bungalow":                      "Entire House",
    "Entire cottage":                       "Entire House",
    "Entire vacation home":                 "Entire House",
    "Entire guesthouse":                    "Entire House",
    "Entire cabin":                         "Entire House",
    "Entire chalet":                        "Entire House",
    "Entire bed and breakfast":             "Entire House",
    "Casa particular":                      "Entire House",
    "Farm stay":                            "Entire House",
    "Entire home/apt":                      "Entire House",
    # Hotel / Boutique
    "Room in hotel":                        "Hotel Room",
    "Room in boutique hotel":               "Hotel Room",
    "Room in aparthotel":                   "Hotel Room",
    "Room in serviced apartment":           "Hotel Room",
    "Room in bed and breakfast":            "Hotel Room",
    "Room in hostel":                       "Hotel Room",
    "Room in nature lodge":                 "Hotel Room",
    # Shared Rooms
    "Shared room in rental unit":           "Shared Room",
    "Shared room in home":                  "Shared Room",
    "Shared room in hostel":                "Shared Room",
    "Shared room in guesthouse":            "Shared Room",
    "Shared room in bed and breakfast":     "Shared Room",
    "Shared room in hotel":                 "Shared Room",
    "Shared room in boutique hotel":        "Shared Room",
    "Shared room in townhouse":             "Shared Room",
    "Shared room in villa":                 "Shared Room",
    # Unique / Alternative Stays
    "Boat":                                 "Unique Stay",
    "Houseboat":                            "Unique Stay",
    "Camper/RV":                            "Unique Stay",
    "Tiny home":                            "Unique Stay",
    "Windmill":                             "Unique Stay",
    "Dome":                                 "Unique Stay",
    "Hut":                                  "Unique Stay",
    "Tent":                                 "Unique Stay",
    "Campsite":                             "Unique Stay",
    "Shipping container":                   "Unique Stay",
    "Earthen home":                         "Unique Stay",
    "Yurt":                                 "Unique Stay",
    "Cave":                                 "Unique Stay",
    "Castle":                               "Unique Stay",
    "Lighthouse":                           "Unique Stay",
    "Treehouse":                            "Unique Stay",
    "Tower":                                "Unique Stay",
    "Bus":                                  "Unique Stay",
    "Barn":                                 "Unique Stay",
    "Entire hostel":                        "Unique Stay",
    "Holiday park":                         "Unique Stay",
}


# =============================================================================
# CONFIGURATION
# =============================================================================

def get_config(city):
    city_cfg = CITY_CONFIG.get(city, {})
    return {
        "city":        city,
        "input_file":  f"data/raw/{city}/listings.csv",
        "output_file": f"data/processed/{city}/listings_clean.csv",
        "cols_to_drop": [
            "license",
            "calendar_updated",
            "neighbourhood_group_cleansed",
            "listing_url",
            "scrape_id",
            "picture_url",
            "host_url",
            "host_thumbnail_url",
            "host_picture_url",
        ],
        "date_cols": [
            "last_scraped",
            "host_since",
            "first_review",
            "last_review",
            "calendar_last_scraped",
        ],
        "bool_cols": [
            "host_is_superhost",
            "host_has_profile_pic",
            "host_identity_verified",
            "has_availability",
            "instant_bookable",
        ],
        "scrape_date":  city_cfg.get("scrape_date", pd.Timestamp("2025-01-01")),
        "currency":     city_cfg.get("currency", "$"),
        "coord_bounds": city_cfg.get("coord_bounds", None),
    }


# =============================================================================
# CLEANING FUNCTIONS
# =============================================================================

def load_data(path):
    print(f"Loading {path}...")
    df = pd.read_csv(path, low_memory=False)
    print(f"Loaded: {df.shape[0]:,} rows x {df.shape[1]} columns")
    return df


def drop_columns(df, cols_to_drop):
    print(f"\n--- Dropping useless columns ---")
    before = df.shape[1]
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    after = df.shape[1]
    print(f"Dropped {before - after} columns. Remaining: {after}")
    return df


def clean_price(df, currency):
    print(f"\n--- Cleaning price column ---")
    before_nulls = df["price"].isnull().sum()

    # Strip any currency symbol, commas, spaces — works for $, ฿, € etc.
    df["price"] = (
        df["price"]
        .astype(str)
        .str.replace(r'[^\d.]', '', regex=True)
        .str.strip()
        .replace('', np.nan)
    )
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    after_nulls = df["price"].isnull().sum()
    valid = df["price"].notna().sum()

    print(f"Price nulls before: {before_nulls:,} → after: {after_nulls:,}")
    print(f"Valid prices: {valid:,}")
    print(
        f"Price range: {currency}{df['price'].min():,.2f} — {currency}{df['price'].max():,.2f}")
    print(f"Median price: {currency}{df['price'].median():,.2f}")

    extreme = df[df["price"] > 100000]
    if len(extreme) > 0:
        print(f"Extreme prices (>100,000): {len(extreme)} listings — flagged")

    return df


def clean_percentage_columns(df):
    """
    Handle both formats:
      Bangkok: "95%"  (string with percent sign)
      Lisbon:  already NaN / already numeric (100% null in this dataset version)
    """
    print(f"\n--- Cleaning percentage columns ---")
    for col in ["host_response_rate", "host_acceptance_rate"]:
        if col not in df.columns:
            print(f"{col}: not found — skipping")
            continue

        if pd.api.types.is_numeric_dtype(df[col]):
            null_pct = df[col].isnull().mean() * 100
            mean_val = df[col].mean()
            print(
                f"{col}: already numeric. Mean: {mean_val:.1f}% | Null: {null_pct:.1f}%")
        else:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace('%', '', regex=False)
                .str.strip()
                .replace('nan', np.nan)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
            print(f"{col}: converted from string. Mean: {df[col].mean():.1f}%")

    return df


def parse_dates(df, date_cols):
    print(f"\n--- Parsing date columns ---")
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            nulls = df[col].isnull().sum()
            print(f"{col}: parsed. Nulls: {nulls:,}")
    return df


def convert_booleans(df, bool_cols):
    """
    Handle both formats:
      Bangkok/standard: 't' / 'f' strings
      Lisbon instant_bookable: 100% null float column
    """
    print(f"\n--- Converting boolean columns ---")
    for col in bool_cols:
        if col not in df.columns:
            print(f"{col}: not found — skipping")
            continue

        null_pct = df[col].isnull().mean() * 100
        if null_pct == 100.0:
            print(
                f"{col}: 100% null — leaving as-is (not available in this city's dataset)")
            continue

        # Check whether values are already boolean-like (numeric 0/1) vs t/f strings
        sample_non_null = df[col].dropna().head(10).tolist()
        already_bool = all(
            isinstance(v, (bool, np.bool_)) or v in (0, 1, 0.0, 1.0)
            for v in sample_non_null
        )

        if already_bool:
            df[col] = df[col].astype("boolean")
            print(f"{col}: already boolean-like — converted cleanly")
        else:
            df[col] = df[col].map({"t": True, "f": False})

        true_count = df[col].sum()
        false_count = (df[col] == False).sum()
        null_count = df[col].isnull().sum()
        print(
            f"{col}: True: {true_count:,} | False: {false_count:,} | Null: {null_count:,}")

    return df


def handle_missing_values(df):
    print(f"\n--- Handling missing values ---")

    before = df["bedrooms"].isnull().sum()
    df["bedrooms"] = df["bedrooms"].fillna(1)
    print(f"bedrooms: filled {before:,} nulls with 1 (mode imputation)")

    before = df["beds"].isnull().sum()
    df["beds"] = df["beds"].fillna(df["accommodates"] / 2).round(0)
    print(f"beds: filled {before:,} nulls with accommodates/2")

    before = df["bathrooms"].isnull().sum()
    df["bathrooms"] = df["bathrooms"].fillna(1)
    print(f"bathrooms: filled {before:,} nulls with 1")

    print(f"Review score columns: left as null (no reviews = legitimate missing)")
    print(f"Host fields with nulls: left as null (host didn't fill in)")

    return df


def normalize_property_types(df):
    print(f"\n--- Property Type Normalization ---")
    df["property_type_grouped"] = df["property_type"].map(
        PROPERTY_TYPE_MAPPING
    ).fillna("Other")

    counts = df["property_type_grouped"].value_counts()
    for ptype, count in counts.items():
        print(f"  {ptype}: {count:,}")

    other_raw = df[df["property_type_grouped"] ==
                   "Other"]["property_type"].value_counts()
    if not other_raw.empty:
        print(f"\n  Raw types still in 'Other' (add to PROPERTY_TYPE_MAPPING if needed):")
        for raw_type, cnt in other_raw.items():
            print(f"    '{raw_type}': {cnt:,}")

    return df


def derive_features(df, city, scrape_date, currency):
    print(f"\n--- Deriving calculated fields ---")

    # host_tenure_years: use host_since if available; otherwise fall back to
    # hosts_time_as_host_years which Lisbon provides pre-calculated
    if "host_since" in df.columns and df["host_since"].notna().sum() > 0:
        df["host_tenure_years"] = (
            (scrape_date - df["host_since"]).dt.days / 365.25
        ).round(2)
        source = "host_since"
    elif "hosts_time_as_host_years" in df.columns and df["hosts_time_as_host_years"].notna().sum() > 0:
        df["host_tenure_years"] = df["hosts_time_as_host_years"].round(2)
        source = "hosts_time_as_host_years (host_since not available in this dataset)"
    else:
        df["host_tenure_years"] = np.nan
        source = "unavailable — set to null"

    valid_tenure = df["host_tenure_years"].notna().sum()
    print(f"host_tenure_years: derived from {source}")
    print(f"  → {valid_tenure:,} listings with valid tenure")

    df["price_per_bedroom"] = np.where(
        df["bedrooms"] > 0,
        (df["price"] / df["bedrooms"]).round(2),
        np.nan
    )
    print(
        f"price_per_bedroom: median={currency}{df['price_per_bedroom'].median():,.2f}")

    df["is_commercial_host"] = df["calculated_host_listings_count"] > 1
    commercial_count = df["is_commercial_host"].sum()
    print(
        f"is_commercial_host: {commercial_count:,} listings ({commercial_count/len(df)*100:.1f}%)")

    df["city"] = city
    print(f"city column added: '{city}'")

    return df


def validate_data(df, city, coord_bounds):
    print(f"\n--- Validation checks ---")

    neg_price = (df["price"] < 0).sum()
    print(
        f"Negative prices: {neg_price} {'✓' if neg_price == 0 else '⚠ FLAGGED'}")

    zero_price = (df["price"] == 0).sum()
    print(f"Price = 0: {zero_price} {'✓' if zero_price == 0 else '⚠ FLAGGED'}")

    if coord_bounds:
        lat_ok = df["latitude"].between(*coord_bounds["lat"])
        lon_ok = df["longitude"].between(*coord_bounds["lon"])
        invalid_coords = (~lat_ok | ~lon_ok).sum()
        note = "✓" if invalid_coords == 0 else "⚠ (may be legitimate listings just outside metro bounds)"
        print(f"Coordinates outside {coord_bounds}: {invalid_coords} {note}")
    else:
        print(
            f"Coordinate validation: skipped (no bounds configured for '{city}')")

    invalid_acc = (df["accommodates"] < 1).sum()
    print(
        f"Invalid accommodates (<1): {invalid_acc} {'✓' if invalid_acc == 0 else '⚠ FLAGGED'}")

    extreme_min_nights = (df["minimum_nights"] > 365).sum()
    print(f"Listings with minimum_nights > 365: {extreme_min_nights}")

    return df


def save_clean_data(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    print(f"\nSaved cleaned listings to: {path}")
    print(f"Final shape: {df.shape[0]:,} rows x {df.shape[1]} columns")


# =============================================================================
# MAIN
# =============================================================================

def main(city):
    config = get_config(city)

    print("=" * 60)
    print("MILESTONE 3: DATA CLEANING — LISTINGS")
    print(f"City: {city.upper()}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    df = load_data(config["input_file"])
    df = drop_columns(df, config["cols_to_drop"])
    df = clean_price(df, config["currency"])
    df = clean_percentage_columns(df)
    df = parse_dates(df, config["date_cols"])
    df = convert_booleans(df, config["bool_cols"])
    df = handle_missing_values(df)
    df = normalize_property_types(df)
    df = derive_features(df, city, config["scrape_date"], config["currency"])
    df = validate_data(df, city, config["coord_bounds"])
    save_clean_data(df, config["output_file"])

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clean and standardize Airbnb listings data for a given city."
    )
    parser.add_argument(
        "--city", type=str, default="bangkok",
        help="City name matching folder in data/raw/ (e.g. bangkok, lisbon)"
    )
    args = parser.parse_args()
    main(args.city)
