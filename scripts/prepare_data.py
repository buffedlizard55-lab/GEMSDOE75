#!/usr/bin/env python3
"""Prepare competition data for training/inference.

Reads data/raw/training_features.tif and data/raw/labels.tif (placed there
by scripts/download_competition_data.sh run on an unrestricted machine, or
by hand), validates them against the organizer's documented format, and
writes a compact processed bundle to data/processed/.

This script is intentionally defensive: if the raw files are not present it
prints exactly what is missing and exits non-zero rather than fabricating
placeholder numbers. See LIMITATIONS.md for why those files are not present
in this checkout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"

REQUIRED_FILES = {
    "training_features.tif": "feature stack (organizer calls it numeric_features.tif in the reference notebook)",
    "labels.tif": "USGS/INGENIOUS fault labels",
}


def main() -> int:
    missing = [f for f in REQUIRED_FILES if not (RAW_DIR / f).exists()]
    if missing:
        print("BLOCKED: required raw file(s) not found in data/raw/:")
        for f in missing:
            print(f"  - {f}  ({REQUIRED_FILES[f]})")
        print()
        print("Run scripts/download_competition_data.sh on a machine with normal")
        print("internet access and an authenticated DrivenData session, then re-run")
        print("this script. See LIMITATIONS.md for details on why this sandbox")
        print("cannot fetch these files itself.")
        return 1

    import rasterio

    from gems_doe.submission_io import EXPECTED_CRS_EPSG, EXPECTED_RESOLUTION_M

    feat_path = RAW_DIR / "training_features.tif"
    label_path = RAW_DIR / "labels.tif"

    with rasterio.open(feat_path) as src:
        epsg = src.crs.to_epsg() if src.crs else None
        assert epsg == EXPECTED_CRS_EPSG, f"training_features.tif CRS is {src.crs}, expected EPSG:{EXPECTED_CRS_EPSG}"
        assert np.isclose(src.res[0], EXPECTED_RESOLUTION_M), f"resolution {src.res} != 100 m"
        features = src.read().astype(np.float32)
        feature_tags = [src.tags(i) for i in range(1, src.count + 1)]
        feat_meta = {
            "height": src.height,
            "width": src.width,
            "count": src.count,
            "transform": list(src.transform)[:6],
            "crs_epsg": epsg,
            "nodata": src.nodata,
        }

    with rasterio.open(label_path) as src:
        labels = src.read(1).astype(np.float32)
        label_meta = {
            "height": src.height,
            "width": src.width,
            "transform": list(src.transform)[:6],
            "crs_epsg": src.crs.to_epsg() if src.crs else None,
        }

    assert (feat_meta["height"], feat_meta["width"]) == (label_meta["height"], label_meta["width"]), (
        "features and labels have different shapes; cannot proceed"
    )

    # Documented sentinel per the reference solution: values < -1e38 are nodata.
    features[features < -1e38] = np.nan

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        PROCESSED_DIR / "features_labels.npz",
        features=features,
        labels=labels,
    )
    with open(PROCESSED_DIR / "meta.json", "w") as f:
        json.dump({"features": feat_meta, "labels": label_meta, "bands": feature_tags}, f, indent=2)

    print(f"OK: wrote {PROCESSED_DIR / 'features_labels.npz'} and meta.json")
    print(f"  feature stack shape: {features.shape}")
    print(f"  labels shape: {labels.shape}, positive px: {int((labels > 0).sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
