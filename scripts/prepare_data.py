#!/usr/bin/env python3
"""Verify competition grid, feature bands, and external layers, writing evidence/prepared_manifest.json."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

import numpy as np
import rasterio
from scipy import ndimage as ndi
from gems57.grid import load_grid

DATA = Path(os.environ.get("GEMS_DATA", str(ROOT / ".cache" / "data")))
EXT = Path(os.environ.get("GEMS_EXT_ROOT", str(ROOT / ".cache" / "gems_data")))


def main() -> int:
    grid = load_grid(DATA)
    fp, cat = grid.footprint, grid.catalogue

    band_audit = []
    with rasterio.open(DATA / "training_features.tif") as src:
        for b in range(1, src.count + 1):
            arr = src.read(b).astype(np.float32)
            ok = np.isfinite(arr) & (arr > -1e30) & fp
            vals = arr[ok]
            band_audit.append(
                {
                    "band": b,
                    "description": src.descriptions[b - 1],
                    "valid_in_footprint": int(ok.sum()),
                    "missing_sentinel_in_footprint": int(fp.sum() - ok.sum()),
                    "p01": float(np.percentile(vals, 1)),
                    "p50": float(np.percentile(vals, 50)),
                    "p99": float(np.percentile(vals, 99)),
                }
            )
            if b == 2:
                eroded_valid = int(ndi.binary_erosion(ok, iterations=12).sum())

    manifest = {
        "evidence_class": "DATA-MEASUREMENT",
        "crs": str(grid.crs),
        "shape": list(grid.shape),
        "transform": list(grid.transform)[:6],
        "footprint_pixels": int(fp.sum()),
        "outside_footprint_pixels": int((~fp).sum()),
        "known_catalogue_pixels": int(cat.sum()),
        "active_off_catalogue_pixels": int((fp & (~cat)).sum()),
        "eroded_12px_valid_pixels": eroded_valid,
        "training_feature_bands": band_audit,
        "external_dir_present": (EXT / "external").is_dir(),
        "dem10_dir_present": (EXT / "dem10").is_dir(),
    }
    out = ROOT / "evidence" / "prepared_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"[ok] Prepared manifest verified: {fp.sum():,} footprint px, {cat.sum():,} known fault px -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
