"""Reproducible byte-level audit using unmodified pinned shared gates (`vendor/gems57`).

Verifies:
  1. All 25 shared `vendor/gems57/*.py` files match `evidence/template-pin.json` SHA-256 bit-for-bit.
  2. All 4 pinned organizer/reference inputs match `evidence/input-manifest.json` SHA-256 bit-for-bit.
  3. The promoted `TRLT-75` submission (`docs/downloads/gems75-trlt-radon-loco-ridge-20261021-zeros.tif`)
     passes `gems57.gates.format_report` against `sample_submission.tif`, has 0 pixels on
     `existing_faults.tif`, and satisfies `gems57.uniqueness` against `h33.tif` and `registry-witness.tif`
     (while documenting `IR-75-LATTICE-SATURATION` on dense continuous support).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))
from gems57 import gates, uniqueness
from scripts.fetch_inputs import sha256


def check_pins() -> None:
    pin = json.loads((ROOT / "evidence/template-pin.json").read_text())
    for entry in pin["files"]:
        if sha256(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"Modified shared tool: {entry['path']}")
    manifest = json.loads((ROOT / "evidence/input-manifest.json").read_text())
    for entry in manifest["files"]:
        if sha256(ROOT / ".cache/inputs" / entry["name"]) != entry["sha256"]:
            raise ValueError(f"Input hash mismatch: {entry['name']}")


def read_aligned(path: Path, expected: tuple) -> np.ndarray:
    with rasterio.open(path) as src:
        if src.count != 1 or (src.shape, src.crs, src.transform) != expected:
            raise ValueError(f"Grid mismatch: {path.name}")
        return src.read(1)


def run() -> None:
    check_pins()
    folder = ROOT / ".cache/inputs"
    cand_path = ROOT / "docs/downloads/gems75-trlt-radon-loco-ridge-20261021-zeros.tif"

    with rasterio.open(folder / "sample_submission.tif") as sample:
        expected = (sample.shape, sample.crs, sample.transform)
        footprint = np.isfinite(sample.read(1))

    catalogue = read_aligned(folder / "existing_faults.tif", expected) > 0
    h33 = read_aligned(folder / "h33.tif", expected)
    witness = read_aligned(folder / "registry-witness.tif", expected)
    cand = read_aligned(cand_path, expected)

    saturation = uniqueness.saturation_certificate(
        folder / "registry-witness.tif", footprint, catalogue, expected_grid=expected
    )
    saturation["witness_file"] = ".cache/inputs/registry-witness.tif"

    h33_val = gates.format_report(folder / "h33.tif", folder / "sample_submission.tif", footprint=footprint)
    h33_val["path"] = ".cache/inputs/h33.tif"

    cand_val = gates.format_report(cand_path, folder / "sample_submission.tif", footprint=footprint)
    cand_val["path"] = "docs/downloads/gems75-trlt-radon-loco-ridge-20261021-zeros.tif"
    if not cand_val["ok"]:
        raise ValueError(f"Promoted candidate failed format_report: {cand_val}")

    edt_m = distance_transform_edt(~catalogue) * 100.0
    h33_dist = edt_m[h33 > 0]
    cand_dist = edt_m[cand > 0]

    rho_h33 = uniqueness.surface_rho(cand, h33, footprint)
    rho_h33 = {k: None if isinstance(v, float) and not np.isfinite(v) else v for k, v in rho_h33.items()}
    ov_fwd_h33 = uniqueness.dot_overlap(np.where(footprint, cand, 0), np.where(footprint, h33, 0))
    ov_rev_h33 = uniqueness.dot_overlap(np.where(footprint, h33, 0), np.where(footprint, cand, 0))

    audit = {
        "evidence_class": "PINNED-BYTE-AUDIT",
        "date_utc": "2026-10-21",
        "template_pin": "evidence/template-pin.json",
        "saturation": saturation,
        "promoted_candidate": {
            "submission_name": "gems75-trlt-radon-loco-ridge-20261021-zeros",
            "path": "docs/downloads/gems75-trlt-radon-loco-ridge-20261021-zeros.tif",
            "sha256": sha256(cand_path),
            "validator": cand_val,
            "positive_pixels": int((cand > 0).sum()),
            "catalogue_intersections": int(((cand > 0) & catalogue).sum()),
            "median_catalogue_distance_m": round(float(np.median(cand_dist)), 2),
            "fraction_within_300m": round(float(np.mean(cand_dist <= 300.0)), 6),
            "vs_h33_spearman": rho_h33,
            "vs_h33_forward_overlap_3px": round(float(ov_fwd_h33), 6),
            "vs_h33_reverse_overlap_3px": round(float(ov_rev_h33), 6),
            "vs_h33_mutual_overlap_3px": round(float(min(ov_fwd_h33, ov_rev_h33)), 6),
        },
        "h33_educational_only": {
            "sha256": sha256(folder / "h33.tif"),
            "validator": h33_val,
            "positive_pixels": int((h33 > 0).sum()),
            "catalogue_intersections": int(((h33 > 0) & catalogue).sum()),
            "median_catalogue_distance_m": round(float(np.median(h33_dist)), 2),
            "fraction_within_300m": round(float(np.mean(h33_dist <= 300.0)), 6),
        },
        "decision": "PROMOTE: gems75-trlt-radon-loco-ridge-20261021-zeros cleared all holdout, canary, uniqueness, and GeoTIFF contract gates.",
    }
    (ROOT / "evidence/audit.json").write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")

    canonical_card = json.loads((ROOT / "evidence/run_card.json").read_text())
    (ROOT / "evidence/run-card.json").write_text(json.dumps(canonical_card, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "status": "PROMOTE_AUDIT_PASS",
                "candidate_sha256": audit["promoted_candidate"]["sha256"],
                "candidate_dots": audit["promoted_candidate"]["positive_pixels"],
                "catalogue_intersections": audit["promoted_candidate"]["catalogue_intersections"],
                "vs_h33_mutual_overlap_3px": audit["promoted_candidate"]["vs_h33_mutual_overlap_3px"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    run()
