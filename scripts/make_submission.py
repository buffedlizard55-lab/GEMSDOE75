#!/usr/bin/env python3
"""Package the validated GEMSDOE75 (H75-1 E3) GeoTIFF submission via vendor/gems57/submission_writer.py."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import submission_writer
from gems_doe.h75_lane import (
    BANDS_DIR,
    SUBMISSION_FILENAME,
    SUBMISSION_NOTE,
    SUBMISSION_STEM,
    build_e3_surface,
    poisson_disk_pack,
)


def main() -> int:
    sample_path = ROOT / ".cache" / "inputs" / "sample_submission.tif"
    existing_path = ROOT / ".cache" / "inputs" / "existing_faults.tif"
    if not sample_path.is_file() or not existing_path.is_file():
        raise FileNotFoundError(
            "Missing .cache/inputs/sample_submission.tif or existing_faults.tif; run scripts/fetch_inputs.py first."
        )

    out_dir = ROOT / "submissions"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_tif = out_dir / SUBMISSION_FILENAME

    # Load footprint and catalogue from pinned .cache/inputs/
    with rasterio.open(sample_path) as src:
        foot = np.isfinite(src.read(1))
    with rasterio.open(existing_path) as src:
        cat = (src.read(1) > 0) & foot

    cached_dots = BANDS_DIR / "dots_E3_full.npy"
    if cached_dots.is_file():
        pred = np.load(cached_dots).astype(np.float32)
    elif out_tif.is_file():
        with rasterio.open(out_tif) as src:
            pred = src.read(1).astype(np.float32)
    else:
        from scipy import ndimage as ndi

        surf = build_e3_surface(cat, BANDS_DIR)
        d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
        allow = foot & (d_cat > 2.0)
        pred = poisson_disk_pack(surf, allow, min_dist_px=2.85, max_dots=38200).astype(np.float32)

    for ext in (".tif", ".zip", ".json"):
        p = out_tif.with_suffix(ext)
        if p.exists():
            p.unlink()

    receipt = submission_writer.write_submission(
        out_tif,
        pred,
        sample_path,
        foot,
        note=SUBMISSION_NOTE,
        name=SUBMISSION_STEM,
        catalogue=cat,
        metadata={
            "lane": "GEMSDOE75-H75-1",
            "hypothesis_id": "H75-1",
            "experiment_id": "H75-E3",
            "outside_fill": "zero",
            "min_dist_px": 2.85,
            "collar_px": 2.0,
            "dot_count": 38200,
        },
    )

    docs_sub_dir = ROOT / "docs" / "submissions"
    docs_sub_dir.mkdir(parents=True, exist_ok=True)
    for ext in (".tif", ".zip", ".json"):
        src_file = out_tif.with_suffix(ext)
        shutil.copy2(src_file, docs_sub_dir / src_file.name)

    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
