#!/usr/bin/env python3
"""Generate a GEMS Prize submission GeoTIFF.

Two modes, selected automatically by whether data/raw/training_features.tif
exists:

  REAL MODE (data present): builds the template from the real organizer
  raster, runs the selected rule, validates, and writes a submit-ready file
  to docs/downloads/.

  SCHEMA-DEMO MODE (data absent, the current state of this checkout): builds
  a small synthetic template so the code path is exercised end-to-end and
  produces a file that LOOKS like a submission but is explicitly named and
  stamped "SCHEMA-DEMO" / "DO-NOT-SUBMIT" everywhere (filename, GeoTIFF tag,
  and an accompanying .json receipt) so nobody mistakes it for a real,
  scientifically-grounded entry. See LIMITATIONS.md.

Usage:
    python scripts/make_submission.py --rule zeros
    python scripts/make_submission.py --rule zeros --out docs/downloads/my-submission.tif
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems_doe.submission_io import SubmissionTemplate, validate_submission, write_submission  # noqa: E402

RAW_FEATURES = ROOT / "data" / "raw" / "training_features.tif"
DOWNLOADS_DIR = ROOT / "docs" / "downloads"


def build_schema_demo_template() -> tuple[SubmissionTemplate, bool]:
    """Build a small synthetic stand-in template with the shape/CRS/transform
    that several independent sibling repositories *claim* (unverified by us)
    for the real training_features.tif: EPSG:32611, 100 m, 3730 rows x 3292
    cols. We cannot confirm this ourselves (no network path to the real
    file from this sandbox), so this template is clearly flagged
    `verified=False` and the resulting GeoTIFF is clearly flagged as a
    schema demo, not a submission.
    """
    import rasterio
    from rasterio.transform import Affine

    h, w = 3730, 3292
    # Arbitrary origin -- the real organizer origin is unknown to us; only
    # the pixel size (100 m) and axis orientation match the documented spec.
    transform = Affine(100.0, 0.0, 0.0, 0.0, -100.0, 0.0)
    tmp_path = ROOT / "data" / "processed" / "_schema_demo_template.tif"
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        tmp_path, "w", driver="GTiff", height=h, width=w, count=1, dtype="float32",
        crs="EPSG:32611", transform=transform,
    ) as dst:
        dst.write(np.zeros((h, w), dtype=np.float32), 1)
    return SubmissionTemplate.from_raster(str(tmp_path)), False


def build_real_template() -> tuple[SubmissionTemplate, bool]:
    return SubmissionTemplate.from_raster(str(RAW_FEATURES)), True


def rule_zeros(template: SubmissionTemplate) -> np.ndarray:
    """The organizer-sanctioned reference baseline: predicts total fault
    absence everywhere. Guaranteed to pass format validation; DTI = 0 by
    construction (TP_w = 0) -- a safety fallback, not a competitive entry.
    """
    return np.zeros((template.height, template.width), dtype=np.float32)


RULES = {
    "zeros": rule_zeros,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rule", choices=sorted(RULES), default="zeros")
    ap.add_argument("--out", default=None, help="output .tif path")
    args = ap.parse_args()

    is_real = RAW_FEATURES.exists()
    if is_real:
        template, verified = build_real_template()
        mode = "REAL"
    else:
        template, verified = build_schema_demo_template()
        mode = "SCHEMA-DEMO"

    array = RULES[args.rule](template)

    if args.out:
        out_path = Path(args.out)
    else:
        suffix = "" if is_real else "-SCHEMA-DEMO-DO-NOT-SUBMIT"
        out_path = DOWNLOADS_DIR / f"gemsdoe75-{args.rule}{suffix}.tif"

    report = write_submission(array, str(out_path), template)
    report2 = validate_submission(str(out_path), template=template)

    receipt = {
        "mode": mode,
        "template_verified_from_real_organizer_file": verified,
        "rule": args.rule,
        "output_file": str(out_path),
        "validation": json.loads(report2.to_json()),
        "ready_to_submit": bool(is_real and report2.ok),
        "note": (
            "This is a real-geometry submission ready for the DrivenData form."
            if (is_real and report2.ok)
            else "DO NOT SUBMIT: geometry is an unverified placeholder because this "
            "sandbox cannot reach the login-walled DrivenData data page. Run "
            "scripts/download_competition_data.sh on an unrestricted machine, place "
            "training_features.tif in data/raw/, then re-run this script."
        ),
    }
    receipt_path = out_path.with_suffix(".json")
    with open(receipt_path, "w") as f:
        json.dump(receipt, f, indent=2)

    print(json.dumps(receipt, indent=2))
    return 0 if report2.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
