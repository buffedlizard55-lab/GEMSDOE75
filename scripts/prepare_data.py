#!/usr/bin/env python3
"""Prepare, sanitize, and audit the competition rasters and cached feature stack for GEMSDOE75.

Reads from data/raw/ (or .cache/gems_data/ restored by scripts/download_competition_data.sh):
  * training_features.tif (19 float32 official bands)
  * labels.tif & existing_faults.tif
  * sample_submission.tif
  * external/lidar_scarp_features_u8.tif (12 uint8 bands from USGS 3DEP 1 m DEM)
  * external/topo_10m_derived_100m_u8.tif (8 uint8 bands from USGS 3DEP 10 m DEM)
  * external/geodawn_rad_u8.tif (4 uint8 bands: K, Th, U, TC from USGS GeoDAWN)
  * external/geodawn_extensions_u8.tif (4 uint8 bands: ThK, UK, UTh, TMI_up150)
  * external/derived_sgmc_faults_100m_u8.tif (USGS SGMC bedrock faults)
  * external/gdr_volcanic_vents_in_footprint.csv, gdr_wellspring_in_footprint.csv,
    trace_segments_utm11.csv, 2m_temperature_probe_INGENIOUS_regional_data.zip,
    paleo_geothermal_regional.zip (DOE GDR 1391 datasets)

Sanitizes nodata sentinels (-3.4028235e+38), writes fast per-band .npy arrays to .cache/bands/
(git-ignored and snapshot-excluded), and writes data/processed/meta.json and
evidence/prepared_manifest.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

RAW_DIR = ROOT / "data" / "raw"
CACHE_DATA_DIR = ROOT / ".cache" / "gems_data"
BANDS_DIR = ROOT / ".cache" / "bands"
PROCESSED_DIR = ROOT / "data" / "processed"

BASE_NAMES = [
    "mag_anom",
    "rtp",
    "tmi_hg",
    "geod_2ndinv",
    "iso_grav_anom_slope",
    "tc",
    "geod_shearrate",
    "geod_dilaterate",
    "tmi_vg",
    "deq_n100a15",
    "iso_grav_anom_vg",
    "det_elev",
    "iso_grav_anom",
    "tmi",
    "depth_to_base_surf",
    "ieq_n100a15",
    "cond_surf",
    "iso_grav_anom_hg",
    "det_elev_slope",
]

REQUIRED_FILES = {
    "training_features.tif": "19-band GeoDAWN/INGENIOUS numerical feature stack",
    "labels.tif": "USGS/INGENIOUS mapped fault catalogue labels",
    "existing_faults.tif": "USGS/INGENIOUS mapped fault catalogue (identical to labels.tif)",
    "sample_submission.tif": "Submission grid and footprint template",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_input(rel: str) -> Path | None:
    for base in (RAW_DIR, CACHE_DATA_DIR):
        p = base / rel
        if p.exists():
            return p
    return None


def main() -> int:
    missing = [f for f in REQUIRED_FILES if resolve_input(f) is None]
    if missing:
        print("BLOCKED: required input file(s) not found in data/raw/ or .cache/gems_data/:")
        for f in missing:
            print(f"  - {f}  ({REQUIRED_FILES[f]})")
        print("\nRun `bash scripts/download_competition_data.sh` first, then re-run this script.")
        return 1

    import rasterio
    from gems_doe.submission_io import EXPECTED_CRS_EPSG, EXPECTED_RESOLUTION_M

    BANDS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    feat_path = resolve_input("training_features.tif")
    lab_path = resolve_input("labels.tif")
    exist_path = resolve_input("existing_faults.tif")
    tmpl_path = resolve_input("sample_submission.tif")
    assert feat_path and lab_path and exist_path and tmpl_path

    with rasterio.open(tmpl_path) as tmpl:
        epsg = tmpl.crs.to_epsg() if tmpl.crs else None
        if epsg != EXPECTED_CRS_EPSG:
            raise ValueError(f"Expected EPSG:{EXPECTED_CRS_EPSG}, got {tmpl.crs}")
        if not np.isclose(tmpl.res[0], EXPECTED_RESOLUTION_M):
            raise ValueError(f"Expected resolution {EXPECTED_RESOLUTION_M} m, got {tmpl.res}")
        shape_hw = (tmpl.height, tmpl.width)
        if shape_hw != (3730, 3292):
            raise ValueError(f"Expected shape (3730, 3292), got {shape_hw}")
        transform_tuple = tuple(float(v) for v in tmpl.transform)[:6]
        foot_arr = tmpl.read(1)
        foot = np.isfinite(foot_arr)
        tmpl_ones_on_foot = int((foot_arr[foot] == 1.0).sum())

    with rasterio.open(lab_path) as lab_src:
        lab_raw = lab_src.read(1)
        lab = (lab_raw == 1) & foot

    np.save(BANDS_DIR / "_footprint.npy", foot)
    np.save(BANDS_DIR / "_labels.npy", lab)

    sgmc_path = resolve_input("external/derived_sgmc_faults_100m_u8.tif")
    sgmc_px = 0
    if sgmc_path is not None:
        with rasterio.open(sgmc_path) as sgmc_src:
            sgmc = (sgmc_src.read(1) > 0) & foot
        np.save(BANDS_DIR / "_sgmc.npy", sgmc)
        sgmc_px = int(sgmc.sum())

    band_stats = []
    total_sentinel_in_foot = 0
    any_sentinel_in_foot = np.zeros(shape_hw, dtype=bool)
    feature_tags = []

    with rasterio.open(feat_path) as feat_src:
        if (feat_src.height, feat_src.width) != shape_hw:
            raise ValueError("training_features.tif shape mismatch")
        feat_meta = {
            "height": feat_src.height,
            "width": feat_src.width,
            "count": feat_src.count,
            "transform": list(feat_src.transform)[:6],
            "crs_epsg": feat_src.crs.to_epsg() if feat_src.crs else None,
            "nodata": float(feat_src.nodata) if feat_src.nodata is not None else None,
        }
        for idx, bname in enumerate(BASE_NAMES, 1):
            arr = feat_src.read(idx).astype(np.float32)
            feature_tags.append(feat_src.tags(idx))
            is_sentinel = (~np.isfinite(arr)) | (arr < -1e38)
            sentinel_in_foot = int(np.sum(is_sentinel & foot))
            total_sentinel_in_foot += sentinel_in_foot
            any_sentinel_in_foot |= is_sentinel & foot

            arr[is_sentinel] = np.nan
            arr[~foot] = np.nan
            np.save(BANDS_DIR / f"{idx:02d}_{bname}.npy", arr)

            valid_vals = arr[foot & np.isfinite(arr)]
            band_stats.append(
                {
                    "index": idx,
                    "name": bname,
                    "source": "training_features.tif",
                    "description": feat_src.descriptions[idx - 1] or bname,
                    "finite_in_footprint": int(valid_vals.size),
                    "sentinel_in_footprint": sentinel_in_foot,
                    "min": float(np.min(valid_vals)),
                    "p05": float(np.percentile(valid_vals, 5)),
                    "median": float(np.median(valid_vals)),
                    "p95": float(np.percentile(valid_vals, 95)),
                    "max": float(np.max(valid_vals)),
                }
            )

    external_stats = []
    for rel_ext, prefix in (
        ("external/lidar_scarp_features_u8.tif", "lidar"),
        ("external/topo_10m_derived_100m_u8.tif", "topo10m"),
        ("external/geodawn_rad_u8.tif", "rad"),
        ("external/geodawn_extensions_u8.tif", "ext"),
    ):
        ext_file = resolve_input(rel_ext)
        if ext_file is None:
            continue
        with rasterio.open(ext_file) as src:
            for b_idx in range(1, src.count + 1):
                bdesc = src.descriptions[b_idx - 1] or f"b{b_idx}"
                raw_u8 = src.read(b_idx)
                if bdesc == "valid":
                    val = (raw_u8 > 0).astype(np.float32)
                    val[~foot] = np.nan
                else:
                    val = np.where(raw_u8 > 0, (raw_u8.astype(np.float32) - 1.0) / 254.0, np.nan)
                    val[~foot] = np.nan
                cname = f"{prefix}_{bdesc}"
                np.save(BANDS_DIR / f"{cname}.npy", val.astype(np.float32))
                v = val[foot & np.isfinite(val)]
                external_stats.append(
                    {
                        "name": cname,
                        "source": ext_file.name,
                        "band": b_idx,
                        "finite_in_footprint": int(v.size),
                        "median": float(np.median(v)) if v.size else 0.0,
                        "p95": float(np.percentile(v, 95)) if v.size else 0.0,
                    }
                )

    source_hashes = {
        "training_features.tif": sha256_file(feat_path),
        "labels.tif": sha256_file(lab_path),
        "existing_faults.tif": sha256_file(exist_path),
        "sample_submission.tif": sha256_file(tmpl_path),
    }
    for opt_rel in (
        "external/lidar_scarp_features_u8.tif",
        "external/topo_10m_derived_100m_u8.tif",
        "external/geodawn_rad_u8.tif",
        "external/geodawn_extensions_u8.tif",
        "external/derived_sgmc_faults_100m_u8.tif",
        "external/gdr_volcanic_vents_in_footprint.csv",
        "external/gdr_wellspring_in_footprint.csv",
        "external/gdr_qfaults_traces.csv",
        "external/trace_segments_utm11.csv",
    ):
        opt_p = resolve_input(opt_rel)
        if opt_p is not None:
            source_hashes[Path(opt_rel).name] = sha256_file(opt_p)

    manifest = {
        "schema_version": 1,
        "prepared_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evidence_class": "DATA-PREPARATION-RECEIPT",
        "provenance": (
            "Prepared from SHA-256-verified owner/template mirrors of the competition and "
            "public USGS/DOE GDR datasets (see evidence/data_restore_receipt.json)."
        ),
        "grid": {
            "epsg": epsg,
            "height": shape_hw[0],
            "width": shape_hw[1],
            "total_cells": int(shape_hw[0] * shape_hw[1]),
            "transform": list(transform_tuple),
            "pixel_size_m": [100.0, 100.0],
        },
        "counts": {
            "footprint_valid_pixels": int(foot.sum()),
            "outside_footprint_pixels": int((~foot).sum()),
            "positive_catalogue_label_pixels": int(lab.sum()),
            "sgmc_positive_in_footprint_pixels": sgmc_px,
            "sample_submission_ones_in_footprint": tmpl_ones_on_foot,
            "negative_in_footprint_pixels": int(foot.sum() - lab.sum()),
            "total_sentinel_band_pixels_inside_footprint": total_sentinel_in_foot,
            "unique_footprint_pixels_with_any_sentinel": int(any_sentinel_in_foot.sum()),
        },
        "source_hashes": source_hashes,
        "bands": band_stats,
        "external_channels": external_stats,
    }

    (PROCESSED_DIR / "meta.json").write_text(
        json.dumps(
            {
                "features": feat_meta,
                "labels": {
                    "height": shape_hw[0],
                    "width": shape_hw[1],
                    "transform": list(transform_tuple),
                    "crs_epsg": epsg,
                },
                "bands": feature_tags,
                "counts": manifest["counts"],
            },
            indent=2,
        )
        + "\n"
    )
    (ROOT / "evidence" / "prepared_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    print(
        f"[GEMSDOE75] Prepared {len(manifest['bands'])} official bands + "
        f"{len(manifest['external_channels'])} external channels | "
        f"Footprint={manifest['counts']['footprint_valid_pixels']:,} px | "
        f"Catalogue positives={manifest['counts']['positive_catalogue_label_pixels']:,} px | "
        f"Sanitized {manifest['counts']['total_sentinel_band_pixels_inside_footprint']:,} sentinel band-pixels."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
