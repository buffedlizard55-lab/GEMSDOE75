#!/usr/bin/env python3
"""Restore and SHA-256 verify competition rasters into .cache/data."""
from __future__ import annotations

import hashlib
import json
import os
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("GEMS_DATA", str(ROOT / ".cache" / "data")))

FEAT_REF = "main"
AUX_REF = "main"

PINS: dict[str, str] = {
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_from_tarball(repo: str, ref: str, wanted: dict[str, Path]) -> None:
    url = f"https://codeload.github.com/buffedlizard55-lab/{repo}/tar.gz/{ref}"
    req = urllib.request.Request(url, headers={"User-Agent": "gemsdoe75-restore-data"})
    with urllib.request.urlopen(req, timeout=240) as resp:
        with tarfile.open(fileobj=resp, mode="r|gz") as tf:
            for member in tf:
                if not member.isfile():
                    continue
                parts = member.name.split("/", 1)
                rel = parts[1] if len(parts) > 1 else parts[0]
                if rel in wanted:
                    dest = wanted[rel]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    fh = tf.extractfile(member)
                    if fh is not None:
                        tmp = dest.with_suffix(dest.suffix + ".tmp")
                        with tmp.open("wb") as out:
                            for chunk in iter(lambda: fh.read(1 << 20), b""):
                                out.write(chunk)
                        tmp.replace(dest)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    if not ((DATA / "training_features.tif").exists() and sha(DATA / "training_features.tif") == PINS["training_features.tif"]):
        part_map = {
            f"data/bridge/gems-geodawn-numerical-features.tif.part-00{i}": DATA / f"part-00{i}"
            for i in range(5)
        }
        extract_from_tarball("GEMSDOE", FEAT_REF, part_map)
        with (DATA / "training_features.tif").open("wb") as out:
            for i in range(5):
                p = DATA / f"part-00{i}"
                with p.open("rb") as f:
                    for b in iter(lambda: f.read(1 << 20), b""):
                        out.write(b)
                p.unlink()

    need_aux: dict[str, Path] = {}
    if not ((DATA / "existing_faults.tif").exists() and sha(DATA / "existing_faults.tif") == PINS["existing_faults.tif"]):
        need_aux["data/bridge/existing_faults.tif"] = DATA / "existing_faults.tif"
    if not ((DATA / "sample_submission.tif").exists() and sha(DATA / "sample_submission.tif") == PINS["sample_submission.tif"]):
        need_aux["data/sample_submission.tif"] = DATA / "sample_submission.tif"
    if need_aux:
        extract_from_tarball("60GEMSDOE", AUX_REF, need_aux)

    rows = {
        n: {
            "bytes": (DATA / n).stat().st_size,
            "sha256": sha(DATA / n),
            "expected": v,
            "ok": sha(DATA / n) == v,
        }
        for n, v in PINS.items()
    }
    (ROOT / "evidence").mkdir(parents=True, exist_ok=True)
    (ROOT / "evidence" / "data_receipt.json").write_text(
        json.dumps(
            {
                "evidence_class": "DATA-MEASUREMENT",
                "provenance": (
                    "SHA-256-verified owner mirrors of DrivenData competition rasters; "
                    "official competition download page is login-gated at "
                    "https://www.drivendata.org/competitions/306/competition-doe-gems/data/"
                ),
                "feature_ref": FEAT_REF,
                "aux_ref": AUX_REF,
                "files": rows,
            },
            indent=2,
        )
        + "\n"
    )
    if not all(r["ok"] for r in rows.values()):
        raise ValueError("input SHA256 mismatch; remove corrupt cache and restore")
    print(json.dumps(rows, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
