#!/usr/bin/env python3
"""
ORCA - scripts/ingest_marine_regions_eez_v12.py
Role 4 (Geospatial & Localization Engineer)

Converts the downloaded Marine Regions World EEZ v12 shapefile into a clean,
India-filtered GeoJSON at orchestration/data/india_imbl_eez.geojson --
the exact path geospatial_agent.py expects (see BOUNDARY_GEOJSON_PATH there).

Usage:
    python scripts/ingest_marine_regions_eez_v12.py [path_to_shapefile.shp]

If no path is given, this script auto-detects the shapefile in the current
directory or any subfolder.
"""

import os
import sys
import glob

try:
    import geopandas as gpd
except ImportError:
    print("geopandas is not installed. Run: pip install geopandas shapely fiona pyogrio")
    sys.exit(1)

# Real filenames used in the World EEZ v12 archive (confirmed against the
# actual Marine Regions download: World_EEZ_v12_20231025.zip)
CANDIDATE_FILENAMES = [
    "eez_v12.shp",
    "World_EEZ_v12.shp",
    "eez_boundaries_v12.shp",
    "eez_v12_20231025.shp",
]

# Real MRGIDs for India's EEZ zones (mainland, Andaman & Nicobar, Lakshadweep)
INDIA_MRGIDS = [8480, 8481, 8482]

OUTPUT_PATH = os.path.join("orchestration", "data", "india_imbl_eez.geojson")


def find_shapefile(search_dir="."):
    for name in CANDIDATE_FILENAMES:
        path = os.path.join(search_dir, name)
        if os.path.exists(path):
            return path
    matches = glob.glob(os.path.join(search_dir, "**", "*eez*.shp"), recursive=True)
    return matches[0] if matches else None


def main(input_path=None):
    if not input_path:
        input_path = find_shapefile()

    if not input_path or not os.path.exists(input_path):
        print("[!] Shapefile not found.")
        print("    1. Go to https://www.marineregions.org/downloads.php")
        print("    2. Find the category 'Exclusive Economic Zones (EEZ)' (NOT 'Maritime Boundaries')")
        print("    3. Download 'World EEZ v12' (.zip)")
        print("    4. Unzip it -- keep all files (.shp, .shx, .dbf, .prj) together in one folder")
        print("    5. Re-run this script, or pass the .shp path directly as an argument")
        print(f"    Looked for: {CANDIDATE_FILENAMES}")
        return False

    print(f"[+] Loading: {input_path}")
    gdf = gpd.read_file(input_path)
    print(f"[+] Total features in dataset: {len(gdf)}")
    print(f"[+] Columns available: {gdf.columns.tolist()}")

    # Column names vary slightly by Marine Regions release -- check both common variants
    sovereign_col = next((c for c in ["SOVEREIGN1", "Sovereign1", "SOVEREIGN"] if c in gdf.columns), None)
    mrgid_col = next((c for c in ["MRGID", "mrgid", "MRGID_EEZ"] if c in gdf.columns), None)

    if not sovereign_col or not mrgid_col:
        print(f"[!] Could not find expected columns. Available columns: {gdf.columns.tolist()}")
        print("    Update sovereign_col / mrgid_col in this script to match, then re-run.")
        return False

    india_filter = (
        gdf[sovereign_col].astype(str).str.contains("India", case=False, na=False)
        | gdf[mrgid_col].isin(INDIA_MRGIDS)
    )
    india_gdf = gdf[india_filter].copy()

    if len(india_gdf) == 0:
        print("[!] No India features matched. Inspect gdf[sovereign_col].unique() and adjust the filter.")
        return False

    print(f"[+] Matched {len(india_gdf)} India EEZ feature(s):")
    for _, row in india_gdf.iterrows():
        name = row.get("GEONAME", row.get("TERRITORY1", "Unnamed"))
        print(f"    - {name}")

    india_gdf = india_gdf.to_crs(epsg=4326)  # standard lat/long

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    india_gdf.to_file(OUTPUT_PATH, driver="GeoJSON")
    print(f"[\u2713] Saved to: {OUTPUT_PATH}")
    print("[\u2713] geospatial_agent.py will read this file automatically -- no code changes needed.")
    return True


if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(path_arg)
