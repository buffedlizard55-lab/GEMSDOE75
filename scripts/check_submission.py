#!/usr/bin/env python3
"""Independent fail-closed preflight verification of the generated competition GeoTIFF,
ZIP archive, SHA-256 digests, [0, 1] finite bounds, zero-NaN guarantee, uniqueness gates,
and HTML/JSON cross-file consistency (`scripts/check_submission.py`).
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57.grid import load_grid
from gems57.validate import assert_submittable, sha256, validate


def main() -> int:
    rc = json.loads((ROOT / "evidence" / "run_card.json").read_text())
    art = rc["artifact"]
    tif_path = ROOT / art["tif_path"]
    zip_path = ROOT / art["zip_path"]

    assert tif_path.is_file(), f"Missing GeoTIFF: {tif_path}"
    assert zip_path.is_file(), f"Missing ZIP: {zip_path}"

    fp = None
    cat = None
    if (ROOT / ".cache" / "data" / "sample_submission.tif").is_file():
        grid = load_grid(ROOT / ".cache" / "data")
        fp, cat = grid.footprint, grid.catalogue
        rep = validate(tif_path, fp, cat)
    elif (ROOT / ".cache" / "inputs" / "sample_submission.tif").is_file():
        with rasterio.open(ROOT / ".cache" / "inputs" / "sample_submission.tif") as src:
            fp = np.isfinite(src.read(1))
        with rasterio.open(ROOT / ".cache" / "inputs" / "existing_faults.tif") as src:
            cat = src.read(1) > 0
        rep = validate(tif_path, fp, cat)
    else:
        rep = validate(tif_path)
    assert_submittable(rep)

    actual_tif_sha = sha256(tif_path)
    actual_zip_sha = sha256(zip_path)
    assert actual_tif_sha == art["tif_sha256"], f"TIF SHA mismatch: {actual_tif_sha} != {art['tif_sha256']}"
    assert actual_zip_sha == art["zip_sha256"], f"ZIP SHA mismatch: {actual_zip_sha} != {art['zip_sha256']}"

    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert (ds.height, ds.width) == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611"
        assert np.isfinite(arr).all(), "Found NaN or Inf in GeoTIFF!"
        assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0, "Values outside [0, 1]!"
        if fp is not None:
            assert int((arr[~fp] != 0.0).sum()) == 0, "Non-zero predictions outside footprint!"
        if cat is not None:
            assert int((arr[cat] != 0.0).sum()) == 0, "Predictions overlap mapped catalogue!"
        assert int((arr == 1.0).sum()) == art["n_dots"]

    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".tif")]
        assert len(names) == 1, f"Expected exactly 1 .tif in ZIP, found {names}"
        with rasterio.MemoryFile(zf.read(names[0])) as mem, mem.open() as zds:
            zarr = zds.read(1)
            assert np.array_equal(arr, zarr), "ZIP GeoTIFF differs from standalone GeoTIFF!"

    # Verify HTML synchronization
    idx_html = (ROOT / "docs" / "index.html").read_text()
    assert actual_tif_sha in idx_html, "TIF SHA-256 missing from docs/index.html!"
    assert f"{rc['score_provenance']['holdout_dti']:.5f}" in idx_html, "Holdout DTI missing from docs/index.html!"
    assert rc["verdict"] == "promote", f"Unexpected verdict: {rc['verdict']}"

    print(
        f"[check_submission] ALL CHECKS PASSED! "
        f"TIF={tif_path.name} ({tif_path.stat().st_size:,} B) | "
        f"SHA256={actual_tif_sha[:16]}... | Dots={art['n_dots']:,} | Range=[0.0, 1.0] | NaN=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
