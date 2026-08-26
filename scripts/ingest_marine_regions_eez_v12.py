#!/usr/bin/env python3
"""
ORCA - scripts/ingest_marine_regions_eez_v12.py
Role 4 (Geospatial & Localization Engineer)

Converts the downloaded Marine Regions World EEZ v12 shapefile into a clean,
India-only GeoJSON at orchestration/data/india_imbl_eez.geojson.

FIX: the previous version filtered on a guessed MRGID list ([8480, 8481, 8482])
that was wrong -- 8481 is Bangladesh and 8482 is Myanmar, not India's
Andaman/Lakshadweep zones as originally assumed. This caused non-India EEZs
to leak into the output file. This version filters on SOVEREIGN1 == "India"
only, which is reliable and doesn't depend on knowing exact MRGID numbers.

Usage:
    python scripts/ingest_marine_regions_eez_v12.py [path_to_shapefile.shp]
"""

import os
import sys
import glob

try:
    import geopandas as gpd
except ImportError:
    print("geopandas is not installed. Run: pip install geopandas shapely fiona pyogrio")
    sys.exit(1)

CANDIDATE_FILENAMES = [
    "eez_v12.shp",
    "World_EEZ_v12.shp",
    "eez_boundaries_v12.shp",
    "eez_v12_20231025.shp",
]

OUTPUT_PATH = os.path.join("orchestration", "data", "india_imbl_eez.geojson")


def find_shapefile(search_dir="."):
    for name in CANDIDATE_FILENAMES:
        path = os.path.join(search_dir, name)
        if os.path.exists(path):
            return path
    matches = glob.glob(os.path.join(search_dir, "**", "eez_v12.shp"), recursive=True)
    return matches[0] if matches else None


def main(input_path=None):
    if not input_path:
        input_path = find_shapefile()

    if not input_path or not os.path.exists(input_path):
        print("[!] Shapefile not found. Pass the .shp path as an argument.")
        return False

    print(f"[+] Loading: {input_path}")
    gdf = gpd.read_file(input_path)
    print(f"[+] Total features in dataset: {len(gdf)}")

    sovereign_col = next((c for c in ["SOVEREIGN1", "Sovereign1", "SOVEREIGN"] if c in gdf.columns), None)
    if not sovereign_col:
        print(f"[!] Could not find a sovereign column. Available: {gdf.columns.tolist()}")
        return False

    india_gdf = gdf[gdf[sovereign_col].astype(str).str.strip() == "India"].copy()

    if len(india_gdf) == 0:
        print(f"[!] No India features matched on column '{sovereign_col}'.")
        print(f"    Unique values sample: {gdf[sovereign_col].unique()[:10]}")
        return False

    print(f"[+] Matched {len(india_gdf)} India EEZ feature(s) (SOVEREIGN1 == 'India' only):")
    for _, row in india_gdf.iterrows():
        name = row.get("GEONAME", "Unnamed")
        mrgid = row.get("MRGID", "?")
        print(f"    - {name} (MRGID: {mrgid})")

    india_gdf = india_gdf.to_crs(epsg=4326)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    india_gdf.to_file(OUTPUT_PATH, driver="GeoJSON")
    print(f"[\u2713] Saved to: {OUTPUT_PATH}")
    return True


if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(path_arg)