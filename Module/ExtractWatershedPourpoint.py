"""
Watershed Delineation — TDX-Hydro HFX dataset via pourpoint
============================================================
For each dam in the input CSV, delineates the upstream watershed with the
pourpoint engine against the remote TDX-Hydro HFX dataset on S3 (Hetzner
object storage). pourpoint snaps the outlet to the dataset's declared snap
features, traverses the upstream graph and returns the dissolved watershed.
The delineation runs through pourpoint's staged API (select_level →
resolve_outlet → traverse → pre_merge_units → refine → dissolve →
compose_result) so the whole sub-basins can be saved BEFORE they are merged.

This dataset has NO D8 raster auxiliary, so refinement is disabled: the
result is always the whole terminal drainage unit plus every upstream unit
(vector delineation only).

Outputs
-------
  1. Sub-basins per dam — the whole drainage-unit polygons from the staged
     pre-merge step, saved as GeoPackage before the merge. Columns: unit_id,
     area_km2, up_area_km2 (the unit's inclusive upstream area), is_terminal.
  2. Watershed polygon per dam, saved as GeoPackage (its outline is the
     watershed boundary line); the dissolve of the sub-basins.
  3. Upstream river network per dam — every TDX-Hydro stream reach in the
     watershed (outlet reach included), saved as GeoPackage. Taken from the
     dataset's native "stems" snap layer, filtered to the watershed's
     upstream unit IDs; 'drain_km2' is the reach's inclusive drainage area.
  4. Merged GeoPackages combining every per-dam file (rebuilt at the end of
     each run): <input_filename>_subbasins_merged.gpkg,
     <input_filename>_watershed_merged.gpkg and
     <input_filename>_river_network_merged.gpkg, with a Dam_ID column.
  5. Area_km2 in the output CSV — filled ONLY where currently empty/NaN.
     Existing values are left untouched so results from multiple datasets
     can be compared side by side in the same CSV.

Credentials
-----------
Read from the local AWS profile PROFILE_NAME (~/.aws/credentials). Nothing
secret lives in this file. pourpoint's S3 layer reads AWS_* environment
variables rather than ~/.aws files, so the profile is resolved with boto3
and exported into this process's environment only (never printed).

Inputs
------
CSV : selected via file picker (opens in Data/), or passed with --csv.
      Required columns: Dam ID, Dam name, Latitude, Longitude.
      Area_km2 optional. UTF-8 with or without BOM.
Snap radius : default 1000 m; asked in the dialog, or --radius. Outlets are
      snapped to the CLOSEST stream reach ("distance-first" strategy);
      dams with no reach within the radius are skipped (see diagnostics).

Usage (run from this project's folder)
--------------------------------------
uv run python Module/ExtractWatershedPourpoint.py                  # dialogs
uv run python Module/ExtractWatershedPourpoint.py --csv Data/file.csv [--radius M] [--overwrite]
uv run python Module/ExtractWatershedPourpoint.py --test LAT LON [--radius M]

Output
------
CSV         : Output/<input_filename>_Pourpoint.csv
Diagnostics : Output/<input_filename>_Pourpoint_diagnostics.csv
GPKG        : Plot/<input_filename>_subbasins_pourpoint/<Dam_ID>_SubBasins.gpkg
              Plot/<input_filename>_watershed_pourpoint/<Dam_ID>_Watershed.gpkg
              Plot/<input_filename>_river_network_pourpoint/<Dam_ID>_RiverNetwork.gpkg
              <same folders>/<input_filename>_subbasins_merged.gpkg,
              <input_filename>_watershed_merged.gpkg and
              <input_filename>_river_network_merged.gpkg

Re-running
----------
By default dams that already have results are skipped (and their Area_km2
is read back into the output CSV). --overwrite (or answering Yes to the
dialog prompt) recomputes every dam, replacing the output CSV, diagnostics,
per-dam GPKGs (sub-basins, watershed, river network) and merged GPKGs.
A dam that fails on an overwrite run has its old per-dam files removed so
stale results never reach the merged files.

Single-point test (--test, no CSV, no dialogs)
----------------------------------------------
Prints area, terminal unit and snap details, and saves
Plot/test_watershed_pourpoint.geojson, Plot/test_subbasins_pourpoint.geojson
and Plot/test_river_network_pourpoint.geojson. Also reports the (tiny)
difference between the sub-basin union and the dissolved watershed.
"""

import argparse
import os
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import boto3
import geopandas as gpd
import numpy as np
import pandas as pd
import pourpoint
import shapely
from botocore.exceptions import ProfileNotFound
from pyproj import Geod


# ── Configuration ──────────────────────────────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "Data"
OUTPUT_DIR = PROJECT_DIR / "Output"
PLOT_DIR = PROJECT_DIR / "Plot"

DATASET = (
    "s3://pourpoint-hfx/hfx/"
    "tdx-hydro-nga-20230126-global-62basin-corrected-hfx-0.3.0-d4d4c5e28df7/"
)
ENDPOINT = "https://fsn1.your-objectstorage.com"
REGION = "fsn1"
PROFILE_NAME = "pourpoint-hfx"

# Default snap search radius (m) — overridden interactively / via --radius
DEFAULT_SEARCH_RADIUS_M = 1000

# Progressive save interval (dams)
SAVE_EVERY = 10


# ── S3 configuration ───────────────────────────────────────────────────────────

def configure_s3():
    """Resolve the AWS profile and export it for pourpoint's object_store."""
    try:
        creds = boto3.Session(profile_name=PROFILE_NAME).get_credentials()
    except ProfileNotFound:
        raise SystemExit(
            f"AWS profile '{PROFILE_NAME}' not found in ~/.aws. "
            f"See README.md → 'S3 credentials' to create it."
        )
    if creds is None:
        raise SystemExit(f"AWS profile '{PROFILE_NAME}' has no credentials.")
    frozen = creds.get_frozen_credentials()
    os.environ.update(
        AWS_ACCESS_KEY_ID=frozen.access_key,
        AWS_SECRET_ACCESS_KEY=frozen.secret_key,
        AWS_ENDPOINT=ENDPOINT,
        AWS_ENDPOINT_URL=ENDPOINT,
        AWS_ENDPOINT_URL_S3=ENDPOINT,
        AWS_REGION=REGION,
        AWS_DEFAULT_REGION=REGION,
        AWS_VIRTUAL_HOSTED_STYLE_REQUEST="false",  # path-style addressing
    )
    os.environ.pop("AWS_SESSION_TOKEN", None)
    os.environ.setdefault("HFX_CACHE_DIR", str(PROJECT_DIR / "Resources" / "hfx-cache"))


def open_engine(radius_m):
    print(f"Opening pourpoint engine (closest-feature snap, radius = {radius_m} m, no D8 refinement) …")
    t0 = time.monotonic()
    engine = pourpoint.Engine(
        DATASET,
        snap_radius=float(radius_m),
        snap_strategy="distance-first",
        refine=False,
        parquet_cache=True,
    )
    print(f" → engine open in {time.monotonic() - t0:.1f} s\n")
    return engine


def _dam_id_safe(dam_id):
    return str(dam_id).replace("/", "_").replace("\\", "_").replace(":", "_")


def delineate_staged(engine, lat, lon):
    """Run the staged pipeline; return (result, sub-basins GeoDataFrame).

    The sub-basins are the whole pre-merge drainage units (staged step 4),
    captured before dissolve() merges them into the watershed.
    """
    level = engine.select_level(selection=pourpoint.LevelSelection.FINEST)
    outlet = engine.resolve_outlet(level, lat=lat, lon=lon)
    upstream = engine.traverse(outlet)
    units = engine.pre_merge_units(upstream)
    refinement = engine.refine(outlet, units)  # status 'disabled' (refine=False)
    dissolved = engine.dissolve(units, refinement)
    result = engine.compose_result(outlet, upstream, units, refinement, dissolved)
    subbasins = gpd.GeoDataFrame(
        {
            "unit_id": [u.id for u in units.units],
            "area_km2": [u.area_km2 for u in units.units],
            "up_area_km2": [u.up_area_km2 for u in units.units],
            "is_terminal": [u.id == units.terminal_unit_id for u in units.units],
        },
        geometry=[shapely.from_wkb(w) for w in units.unit_geometry_wkb],
        crs="EPSG:4326",
    )
    return result, subbasins


def upstream_river_network(engine, result):
    """Stream reaches of the result's watershed, from the dataset's snap layer."""
    targets = engine.snap_targets(bbox=result.geometry_bbox).to_geodataframe()
    reaches = targets[targets["unit_id"].isin(set(result.upstream_unit_ids))]
    return gpd.GeoDataFrame(
        {"unit_id": reaches["unit_id"].values, "drain_km2": reaches["weight"].values},
        geometry=reaches.geometry.values, crs="EPSG:4326",
    )


def merge_gpkgs(folder, pattern, layer, out_path):
    """Concatenate every per-dam GPKG matching pattern into one GPKG."""
    frames = []
    for f in sorted(folder.glob(pattern)):
        gdf = gpd.read_file(f, layer=layer)
        if "Dam_ID" not in gdf.columns:  # per-dam networks written before Dam_ID was added
            gdf.insert(0, "Dam_ID", f.stem.rsplit("_", 1)[0])
        frames.append(gdf)
    if not frames:
        print(f" ! nothing to merge in {folder}")
        return
    merged = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")
    merged.to_file(out_path, driver="GPKG", layer=layer)
    print(f"✓ Merged {len(frames)} file(s), {len(merged)} feature(s) → {out_path}")


# ── Single-point test mode ─────────────────────────────────────────────────────

def run_test(lat, lon, radius_m):
    configure_s3()
    engine = open_engine(radius_m)
    t0 = time.monotonic()
    result, subbasins = delineate_staged(engine, lat, lon)
    print(f"Delineated in {time.monotonic() - t0:.1f} s")
    print(f" area_km2          : {result.area_km2:.2f}")
    print(f" terminal_unit_id  : {result.terminal_unit_id}")
    print(f" upstream units    : {len(result.upstream_unit_ids)}")
    print(f" resolution_method : {result.resolution_method}")
    print(f" refinement seed   : {result.refinement_seed_kind}")
    print(f" input (lon, lat)  : {result.input_outlet}")
    print(f" snapped (lon, lat): {result.resolved_outlet}")
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    out = PLOT_DIR / "test_watershed_pourpoint.geojson"
    out.write_text(result.to_geojson(), encoding="utf-8")
    print(f" → saved {out}")
    out = PLOT_DIR / "test_subbasins_pourpoint.geojson"
    subbasins.to_file(out, driver="GeoJSON")
    print(f" → saved {out} ({len(subbasins)} sub-basins)")
    diff = subbasins.union_all().symmetric_difference(shapely.from_wkb(result.geometry_wkb))
    diff_km2 = abs(Geod(ellps="WGS84").geometry_area_perimeter(diff)[0]) / 1e6
    print(f" sub-basin union vs watershed: {diff_km2:.4f} km² difference "
          f"(dissolve fills sliver gaps between sub-basins)")
    network = upstream_river_network(engine, result)
    out = PLOT_DIR / "test_river_network_pourpoint.geojson"
    network.to_file(out, driver="GeoJSON")
    print(f" → saved {out} ({len(network)} reaches)")


# ── CSV batch mode ─────────────────────────────────────────────────────────────

def run_batch(csv_path=None, radius_m=None, overwrite=False):
    if csv_path is None:
        root = tk.Tk()
        root.withdraw()
        input_csv_str = filedialog.askopenfilename(
            title="Select dam coordinates CSV",
            initialdir=DATA_DIR,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not input_csv_str:
            root.destroy()
            raise SystemExit("No CSV file selected — exiting.")
        radius_m = simpledialog.askfloat(
            title="Search radius",
            prompt="Snap search radius, in meters (dams beyond this distance from\n"
                   "the nearest stream will be skipped):",
            initialvalue=DEFAULT_SEARCH_RADIUS_M,
            minvalue=1,
        )
        if radius_m is None:
            radius_m = DEFAULT_SEARCH_RADIUS_M
            print(f" (no value entered — using default {DEFAULT_SEARCH_RADIUS_M} m)\n")
        existing = PLOT_DIR / f"{Path(input_csv_str).stem}_watershed_pourpoint"
        if any(existing.glob("*_Watershed.gpkg")):
            overwrite = messagebox.askyesno(
                title="Existing results",
                message="Results already exist for this CSV.\n\n"
                        "Yes = overwrite them (recompute every dam)\n"
                        "No = keep them and only process missing dams",
            )
        root.destroy()
    else:
        input_csv_str = csv_path

    input_csv = Path(input_csv_str).expanduser().resolve()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    watershed_dir = PLOT_DIR / f"{input_csv.stem}_watershed_pourpoint"
    watershed_dir.mkdir(parents=True, exist_ok=True)
    subbasins_dir = PLOT_DIR / f"{input_csv.stem}_subbasins_pourpoint"
    subbasins_dir.mkdir(parents=True, exist_ok=True)
    river_network_dir = PLOT_DIR / f"{input_csv.stem}_river_network_pourpoint"
    river_network_dir.mkdir(parents=True, exist_ok=True)
    output_csv = OUTPUT_DIR / f"{input_csv.stem}_Pourpoint.csv"
    diag_csv = OUTPUT_DIR / f"{input_csv.stem}_Pourpoint_diagnostics.csv"

    print(f" → Input CSV       : {input_csv}")
    print(f" → Watershed GPKGs : {watershed_dir}")
    print(f" → Sub-basin GPKGs : {subbasins_dir}")
    print(f" → River net GPKGs : {river_network_dir}")
    print(f" → Output CSV      : {output_csv}\n")

    dams_df = pd.read_csv(input_csv, encoding="utf-8-sig")
    required_cols = {"Dam ID", "Dam name", "Latitude", "Longitude"}
    missing = required_cols - set(dams_df.columns)
    if missing:
        raise SystemExit(f"Input CSV is missing required column(s): {missing}")
    if "Area_km2" not in dams_df.columns:
        dams_df["Area_km2"] = np.nan
    for col in ("Latitude", "Longitude", "Area_km2"):
        dams_df[col] = pd.to_numeric(dams_df[col], errors="coerce")

    invalid = dams_df[dams_df["Latitude"].isna() | dams_df["Longitude"].isna()]
    if not invalid.empty:
        print(f" ! {len(invalid)} row(s) with invalid coordinates will be skipped:")
        print(invalid[["Dam name", "Latitude", "Longitude"]])
        dams_df = dams_df.dropna(subset=["Latitude", "Longitude"]).copy()
    print(f" → {len(dams_df)} dams loaded\n")

    configure_s3()
    engine = open_engine(radius_m)

    # Reruns keep earlier diagnostics (replaced per Dam ID as dams are retried)
    diag_by_dam = {}
    if overwrite:
        print(" → overwrite mode: recomputing every dam\n")
    elif diag_csv.exists():
        for rec in pd.read_csv(diag_csv).to_dict("records"):
            diag_by_dam[rec["Dam ID"]] = {k: v for k, v in rec.items() if pd.notna(v)}
    n_processed = n_skipped = 0

    for i, row in dams_df.iterrows():
        dam_id, dam_name = row["Dam ID"], row["Dam name"]
        watershed_path = watershed_dir / f"{_dam_id_safe(dam_id)}_Watershed.gpkg"

        subbasins_path = subbasins_dir / f"{_dam_id_safe(dam_id)}_SubBasins.gpkg"
        river_network_path = river_network_dir / f"{_dam_id_safe(dam_id)}_RiverNetwork.gpkg"

        if overwrite:
            watershed_path.unlink(missing_ok=True)
            subbasins_path.unlink(missing_ok=True)
            river_network_path.unlink(missing_ok=True)

        if watershed_path.exists():
            if pd.isna(dams_df.at[i, "Area_km2"]):
                prev = gpd.read_file(watershed_path, layer="Watershed")
                dams_df.at[i, "Area_km2"] = prev["Area_km2"].iloc[0]
            print(f" • {dam_id} ({dam_name}) — already processed, skipping")
            continue

        t0 = time.monotonic()
        try:
            result, subbasins = delineate_staged(engine, row["Latitude"], row["Longitude"])
            geom = shapely.from_wkb(result.geometry_wkb)
            watershed_gdf = gpd.GeoDataFrame(
                {"Dam_ID": [dam_id], "Dam_name": [dam_name],
                 "Area_km2": [round(result.area_km2, 2)]},
                geometry=[geom], crs="EPSG:4326",
            )
            network = upstream_river_network(engine, result)
            network.insert(0, "Dam_ID", dam_id)
            subbasins.insert(0, "Dam_ID", dam_id)
            # Sub-basins (pre-merge) first; the watershed is written last, so its
            # existence marks the dam as done.
            subbasins.to_file(subbasins_path, driver="GPKG", layer="SubBasins")
            network.to_file(river_network_path, driver="GPKG", layer="UpstreamRiverNetwork")
            watershed_gdf.to_file(watershed_path, driver="GPKG", layer="Watershed")

            if pd.isna(dams_df.at[i, "Area_km2"]):
                dams_df.at[i, "Area_km2"] = round(result.area_km2, 2)

            lon_s, lat_s = result.resolved_outlet
            print(f" ✓ {dam_id} ({dam_name}) — {len(result.upstream_unit_ids)} unit(s), "
                  f"{len(subbasins)} sub-basin(s), {len(network)} reach(es), area={result.area_km2:.2f} km²")
            n_processed += 1
            diag_by_dam[dam_id] = {
                "Dam ID": dam_id, "Dam name": dam_name, "status": "OK",
                "computed_area_km2": round(result.area_km2, 2),
                "terminal_unit_id": result.terminal_unit_id,
                "n_upstream_units": len(result.upstream_unit_ids),
                "n_river_reaches": len(network),
                "resolution_method": result.resolution_method,
                "snapped_lon": lon_s, "snapped_lat": lat_s,
                "duration_s": round(time.monotonic() - t0, 1),
            }
        except pourpoint.PourpointError as e:
            print(f" ✗ {dam_id} ({dam_name}) — {type(e).__name__}: {e}")
            n_skipped += 1
            diag_by_dam[dam_id] = {"Dam ID": dam_id, "Dam name": dam_name,
                                   "status": "FAILED", "reason": f"{type(e).__name__}: {e}"}

        if (n_processed + n_skipped) % SAVE_EVERY == 0:
            dams_df.to_csv(output_csv, index=False)
            pd.DataFrame(list(diag_by_dam.values())).to_csv(diag_csv, index=False)

    print(f"\nProcessing complete: {n_processed} processed, {n_skipped} skipped\n")
    dams_df.to_csv(output_csv, index=False)
    pd.DataFrame(list(diag_by_dam.values())).to_csv(diag_csv, index=False)
    print(f"✓ Saved CSV         : {output_csv}")
    print(f"✓ Saved diagnostics : {diag_csv}")
    print(f"✓ Watershed GPKGs in: {watershed_dir}")
    print(f"✓ Sub-basin GPKGs in: {subbasins_dir}")
    print(f"✓ River net GPKGs in: {river_network_dir}\n")

    merge_gpkgs(subbasins_dir, "*_SubBasins.gpkg", "SubBasins",
                subbasins_dir / f"{input_csv.stem}_subbasins_merged.gpkg")
    merge_gpkgs(watershed_dir, "*_Watershed.gpkg", "Watershed",
                watershed_dir / f"{input_csv.stem}_watershed_merged.gpkg")
    merge_gpkgs(river_network_dir, "*_RiverNetwork.gpkg", "UpstreamRiverNetwork",
                river_network_dir / f"{input_csv.stem}_river_network_merged.gpkg")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pourpoint watershed delineation (TDX HFX)")
    parser.add_argument("--test", nargs=2, type=float, metavar=("LAT", "LON"),
                        help="delineate one point and exit (no CSV / dialogs)")
    parser.add_argument("--csv", help="run the batch on this CSV, skipping the file/radius dialogs")
    parser.add_argument("--overwrite", action="store_true",
                        help="with --csv: recompute every dam, replacing existing results")
    parser.add_argument("--radius", type=float, default=DEFAULT_SEARCH_RADIUS_M,
                        help="snap radius in metres for --test/--csv (default %(default)s)")
    args = parser.parse_args()
    if args.test:
        run_test(args.test[0], args.test[1], args.radius)
    else:
        run_batch(args.csv, args.radius, args.overwrite)
