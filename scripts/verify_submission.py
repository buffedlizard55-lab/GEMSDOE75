#!/usr/bin/env python3
"""Verify the GEMSDOE75 submission GeoTIFF, ZIP, and receipt against all competition & protocol gates."""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import gates
from gems57.validate import assert_submittable, validate
from gems_doe.h75_lane import SUBMISSION_FILENAME


def verify_submission_file(tif_path: Path, sample_path: Path, existing_path: Path) -> dict:
    if not tif_path.is_file():
        raise FileNotFoundError(f"Submission GeoTIFF not found: {tif_path}")
    if not sample_path.is_file() or not existing_path.is_file():
        raise FileNotFoundError("Missing .cache/inputs/sample_submission.tif or existing_faults.tif")

    with rasterio.open(sample_path) as src:
        foot = np.isfinite(src.read(1))
    with rasterio.open(existing_path) as src:
        cat = (src.read(1) > 0) & foot

    local_val = validate(tif_path, foot, cat)
    assert_submittable(local_val)
    fmt_rep = gates.format_report(tif_path, sample_path, footprint=foot)
    if not fmt_rep.get("ok"):
        raise AssertionError(f"gates.format_report failed: {fmt_rep.get('problems')}")

    with rasterio.open(tif_path) as src:
        arr = src.read(1)
    dots = arr > 0
    d_cat = ndi.distance_transform_edt(~cat)
    d_dots = d_cat[dots]
    d_le_1 = int((d_dots <= 1.0 + 1e-6).sum())
    d_le_2 = int((d_dots <= 2.0 + 1e-6).sum())
    if d_le_2 != 0:
        raise AssertionError(f"Expected 0 dots within 2 px of mapped catalogue, found {d_le_2}")

    zip_path = tif_path.with_suffix(".zip")
    if zip_path.is_file():
        with zipfile.ZipFile(zip_path) as zf:
            if zf.namelist() != [tif_path.name]:
                raise AssertionError(f"ZIP namelist mismatch: {zf.namelist()}")
            if zf.read(tif_path.name) != tif_path.read_bytes():
                raise AssertionError("ZIP payload does not match GeoTIFF bytes")

    return {
        "ok": True,
        "file": str(tif_path.relative_to(ROOT)) if tif_path.is_relative_to(ROOT) else str(tif_path),
        "sha256": local_val["sha256"],
        "bytes": local_val["bytes"],
        "emitted_positive_pixels": local_val["emitted_positive_pixels"],
        "on_catalogue_positive_pixels": local_val["on_catalogue_positive_pixels"],
        "d_le_1_count": d_le_1,
        "d_le_2_count": d_le_2,
        "min": local_val["min"],
        "max": local_val["max"],
        "n_nan": local_val["n_nan"],
        "n_infinite": local_val["n_infinite"],
        "checks": local_val["checks"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "tif",
        nargs="?",
        default=str(ROOT / "submissions" / SUBMISSION_FILENAME),
        help="Path to GeoTIFF submission to verify.",
    )
    args = parser.parse_args(argv)
    report = verify_submission_file(
        Path(args.tif).resolve(),
        ROOT / ".cache" / "inputs" / "sample_submission.tif",
        ROOT / ".cache" / "inputs" / "existing_faults.tif",
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
