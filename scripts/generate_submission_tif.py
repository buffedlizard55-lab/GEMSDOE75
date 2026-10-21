#!/usr/bin/env python3
"""
Generate a UNIQUE, format-correct GEMS Prize submission GeoTIFF candidate.

This script produces a single-band float32 GeoTIFF on the pinned competition
grid geometry (claimed from vendor/gems57/grid.py, UNVERIFIED against the
real organizer training_features.tif -- see LIMITATIONS.md).

CONTENT: A radial Gaussian decay from an off-center point inside the study
area, representing the "BLIND UPFLOW" hypothesis -- a geothermal system with
no surface fault scarp (exactly the class the competition says the USGS
catalogue may be missing) but a subsurface thermal anomaly that decays with
distance from the upflow center. Values are finite and in [0, 1] everywhere;
cells outside a circular influence zone are exactly 0.0.

STATUS: NOT ORGANIZER-CONFIRMED. NO HOLDOUT-DTI MEASUREMENT. NO REAL DATA
VALIDATION. This is a format demonstration and scientific hypothesis probe,
NOT a cleared competition entry. Whether it is OK to download and submit is
stated explicitly below and on the site: it is NOT OK to submit without
first (a) placing real data in data/raw/, (b) beating the current holdout
best on identical folds, and (c) receiving selector approval.

Usage:
    python scripts/generate_submission_tif.py
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS_DIR = ROOT / "docs" / "downloads"

# --- Pinned grid geometry (UNVERIFIED against the real organizer file) ---
# Source: vendor/gems57/grid.py, which claims byte-identity with
# existing_faults.tif (sha256 7ba308cc...). This project cannot confirm that
# claim because data/ is empty and the sandbox cannot reach DrivenData.
GRID = dict(
    height=3730,
    width=3292,
    crs_epsg=32611,
    transform=Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
    pixel_size_m=100.0,
)

# --- Blind upflow hypothesis parameters ---
# Center (row, col) in pixel coordinates -- deliberately off-center so the
# anomaly is not a trivial bullseye and does not coincide with any known
# catalogue structure (catalogue data unavailable, so this cannot be checked).
CENTER_ROW = 0.42 * GRID["height"]   # ~1567 px south of north edge
CENTER_COL = 0.63 * GRID["width"]    # ~2074 px east of west edge
# Influence radius in pixels (30 km at 100 m resolution).
RADIUS_PX = 300
# Peak probability at the center.
PEAK = 0.65


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_blind_upflow_array(height: int, width: int) -> np.ndarray:
    """Radial Gaussian decay from (CENTER_ROW, CENTER_COL), zero outside radius."""
    yy, xx = np.indices((height, width), dtype=np.float64)
    dy = yy - CENTER_ROW
    dx = xx - CENTER_COL
    dist_px = np.hypot(dy, dx)
    # Gaussian with sigma = RADIUS_PX / 2 so the edge drops to ~e^-2 ~ 0.135.
    sigma = RADIUS_PX / 2.0
    vals = PEAK * np.exp(-0.5 * (dist_px / sigma) ** 2)
    vals = np.where(dist_px <= RADIUS_PX, vals, 0.0)
    # Hard zero outside a slightly larger safety mask to guarantee no leakage
    # beyond the nominal influence zone.
    vals = np.where(dist_px <= RADIUS_PX + 5, vals, 0.0)
    return np.clip(vals, 0.0, 1.0).astype(np.float32)


def main() -> int:
    arr = build_blind_upflow_array(GRID["height"], GRID["width"])

    # Sanity checks before writing.
    assert arr.shape == (GRID["height"], GRID["width"]), arr.shape
    assert np.isfinite(arr).all(), "non-finite values present"
    assert arr.min() >= 0.0 and arr.max() <= 1.0, f"out of range: {arr.min()} {arr.max()}"
    n_pos = int((arr > 0).sum())
    print(f"Array: shape={arr.shape}, dtype={arr.dtype}")
    print(f"  min={arr.min():.6f} max={arr.max():.6f} mean={arr.mean():.6f}")
    print(f"  positive pixels: {n_pos} ({100.0 * n_pos / arr.size:.4f}% of footprint)")

    # --- Write the GeoTIFF ---
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    content_hash = hashlib.sha256(arr.tobytes()).hexdigest()[:12]
    tif_name = f"gems75-blind-upflow-radial-{timestamp}-{content_hash}.tif"
    out_path = DOWNLOADS_DIR / tif_name
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    profile = dict(
        driver="GTiff",
        height=GRID["height"],
        width=GRID["width"],
        count=1,
        dtype="float32",
        crs=f"EPSG:{GRID['crs_epsg']}",
        transform=GRID["transform"],
        nodata=None,  # all-finite export: every pixel has a value in [0,1]
        compress="deflate",
        predictor=2,
    )
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(arr, 1)
        dst.set_band_description(1, "predicted_new_fault_probability_blind_upflow")

    # --- Re-read and validate from disk (never trust the in-memory array) ---
    with rasterio.open(out_path) as src:
        disk = src.read(1)
        disk_checks = dict(
            bands=src.count,
            dtype=src.dtypes[0],
            crs=str(src.crs),
            height=src.height,
            width=src.width,
            transform=[float(v) for v in tuple(src.transform)[:6]],
            nodata=src.nodata,
            min=float(np.nanmin(disk)),
            max=float(np.nanmax(disk)),
            n_nan=int(np.isnan(disk).sum()),
            n_positive=int((disk > 0).sum()),
            sha256=sha256_of_file(out_path),
        )

    problems: list[str] = []
    if disk_checks["bands"] != 1:
        problems.append(f"expected 1 band, found {disk_checks['bands']}")
    if disk_checks["dtype"] != "float32":
        problems.append(f"expected float32, found {disk_checks['dtype']}")
    if disk_checks["crs"] != "EPSG:32611":
        problems.append(f"expected EPSG:32611, found {disk_checks['crs']}")
    if (disk_checks["height"], disk_checks["width"]) != (GRID["height"], GRID["width"]):
        problems.append("shape mismatch vs pinned grid")
    if disk_checks["transform"] != [
        100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0
    ]:
        problems.append("transform mismatch vs pinned grid")
    if disk_checks["n_nan"] != 0:
        problems.append(f"{disk_checks['n_nan']} NaN pixels")
    if disk_checks["min"] < 0.0 or disk_checks["max"] > 1.0:
        problems.append("values outside [0, 1]")

    # --- Receipt ---
    receipt = dict(
        generated_utc=timestamp,
        file=out_path.name,
        path=str(out_path),
        sha256=disk_checks["sha256"],
        bytes=out_path.stat().st_size,
        hypothesis="Blind upflow (no surface scarp): radial Gaussian decay from a "
        "subsurface geothermal upflow center; values in [0,1] inside a 30 km radius, "
        "0.0 elsewhere. Targets the fault class the competition states may be missing "
        "from the USGS/INGENIOUS catalogue.",
        mechanism="Distance-decay probability from an inferred blind upflow point; "
        "no feature stack, no catalogue-derived predictors, no holdout fitting.",
        named_non_fault_mimic="A buried volcanic intrusion or sedimentary basin edge "
        "can produce a subsurface thermal anomaly with no associated slip-prone fault.",
        grid_geometry=dict(
            height=GRID["height"],
            width=GRID["width"],
            crs_epsg=GRID["crs_epsg"],
            transform=[float(v) for v in tuple(GRID["transform"])[:6]],
            pixel_size_m=GRID["pixel_size_m"],
        ),
        grid_verified_against_real_organizer_file=False,
        validator=dict(
            ok=(len(problems) == 0),
            checks=disk_checks,
            errors=problems,
        ),
        holdout_dti=None,
        holdout_dti_ci95=None,
        holdout_dti_label="NOT MEASURED: no real catalogue or feature stack available "
        "(see LIMITATIONS.md). This number must not be inferred or projected.",
        correlation_overlap_vs_registry=None,
        correlation_overlap_label="NOT MEASURED: requires the real existing_faults.tif "
        "and a full registry scan, neither available in this environment.",
        submission_name=None,
        submission_note=None,
        approved_for_submission=False,
        submission_status=(
            "DO NOT SUBMIT. This TIF is a format demonstration and scientific probe only. "
            "It has no holdout-DTI measurement, no organizer confirmation, and its grid "
            "geometry is unverified against the real organizer raster. Download is safe for "
            "review; uploading to DrivenData is not authorized until the blockers in "
            "LIMITATIONS.md are resolved and a holdout-DTI beats the current best."
        ),
    )
    receipt_path = out_path.with_suffix(".json")
    receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")

    print(f"\nWritten: {out_path}")
    print(f"SHA-256: {disk_checks['sha256']}")
    print(f"Receipt: {receipt_path}")
    print(f"Validator OK: {receipt['validator']['ok']}")
    if problems:
        print(f"Validator problems: {problems}")
    print(f"\n{receipt['submission_status']}")
    return 0 if receipt["validator"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
