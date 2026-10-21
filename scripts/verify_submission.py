#!/usr/bin/env python3
"""Stand-alone validator for any GeoTIFF you are about to submit.

This directly answers "will the DrivenData form reject this file?" by
reproducing every check the organizer's format spec implies, including the
exact two mechanisms that produce "Predicted values must be in range
[0, 1]" (see src/gems_doe/submission_io.py docstring for the full
diagnosis).

Usage:
    python scripts/verify_submission.py path/to/candidate.tif
    python scripts/verify_submission.py path/to/candidate.tif --template data/raw/training_features.tif
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems_doe.submission_io import SubmissionTemplate, validate_submission  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tif_path")
    ap.add_argument("--template", default=None, help="optional reference raster (e.g. training_features.tif) to check shape/transform against")
    args = ap.parse_args()

    template = SubmissionTemplate.from_raster(args.template) if args.template else None
    report = validate_submission(args.tif_path, template=template)
    print(report.to_json())

    if report.ok:
        print("\nRESULT: PASS -- this file satisfies every format rule this project can check.", file=sys.stderr)
        print("It is still your responsibility to confirm shape/CRS/transform against the", file=sys.stderr)
        print("real training_features.tif with --template before submitting.", file=sys.stderr)
    else:
        print("\nRESULT: FAIL -- do not submit this file. See errors above.", file=sys.stderr)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
