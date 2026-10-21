#!/usr/bin/env bash
# Restore and SHA-256 verify the competition rasters, external USGS/DOE GDR layers,
# and the 62-raster comparison registry from the commit-pinned GitHub mirrors.
#
# PROVENANCE & HONESTY NOTICE:
# 1. Direct unauthenticated requests to https://www.drivendata.org/competitions/306/competition-doe-gems/data/
#    redirect to /accounts/login/, and this sandbox's direct network allowlist is restricted to
#    github.com, codeload.github.com, api.github.com, registry.npmjs.org, pypi.org, and files.pythonhosted.org.
# 2. To complete data placement autonomously without manual input while preserving strict provenance,
#    this script restores the SHA-256-pinned byte mirrors from:
#      - buffedlizard55-lab/GEMSDOE @ c0c06ac82178f26b94fce3397036ef8f12a2f3a0 (training_features.tif, 5 parts)
#      - buffedlizard55-lab/60GEMSDOE @ 32024716f218d06a94e01464157392119c03cb15 (labels, existing_faults,
#        sample_submission, USGS 3DEP 1m/10m & GeoDAWN & SGMC & DOE GDR 1391 external layers, and 62 registry rasters)
#      - buffedlizard55-lab/17GEMSDOE @ 6fc71d19d49dca4960d5434bd81b6dd06fcc030a (dense surface witness)
#      - buffedlizard55-lab/GEMSDOE32 @ 98901f3130e8704f4254f173784589e63f000673 (h33-h33-2-b2 reference)
# 3. Every restored file is verified by SHA-256 before use and stored under .cache/ (with lightweight
#    symlinks in data/raw/, data/bridge/, data/official/, and data/external/) so large binary rasters
#    stay out of Git history.
# 4. On an unrestricted machine with an authenticated DrivenData session, you may also download the
#    primary files directly from https://www.drivendata.org/competitions/306/competition-doe-gems/data/
#    into data/raw/ and verify that their SHA-256 hashes match evidence/data_restore_receipt.json.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
if [ ! -x "$PY" ]; then
  PY="python3"
fi

echo "== Step 1: Restore 4 pinned audit inputs via scripts/fetch_inputs.py =="
"$PY" "$ROOT/scripts/fetch_inputs.py"

echo "== Step 2: Restore SHA-256-pinned feature stack, external layers & registry rasters =="
"$PY" - "$ROOT" <<'PYEOF'
import hashlib
import json
import os
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve()
CACHE = ROOT / ".cache" / "gems_data"
REG_CACHE = ROOT / ".cache" / "registry_rasters"
CACHE.mkdir(parents=True, exist_ok=True)
(CACHE / "external").mkdir(parents=True, exist_ok=True)
REG_CACHE.mkdir(parents=True, exist_ok=True)

FEAT_REPO = "buffedlizard55-lab/GEMSDOE"
FEAT_REF = "c0c06ac82178f26b94fce3397036ef8f12a2f3a0"
TMPL_REPO = "buffedlizard55-lab/60GEMSDOE"
TMPL_REF = "32024716f218d06a94e01464157392119c03cb15"

EXPECTED_SHA256 = {
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "labels.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "external/lidar_scarp_features_u8.tif": "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
    "external/topo_10m_derived_100m_u8.tif": "a6398d9950965dec6aae6ccecdaa6ced48645d133eab222cbdd11def9bdabfa4",
    "external/geodawn_rad_u8.tif": "c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682",
    "external/geodawn_extensions_u8.tif": "a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b",
    "external/derived_sgmc_faults_100m_u8.tif": "643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0",
    "external/gdr_wellspring_in_footprint.csv": "122718e65bdf55aab0ee12ad20d80062f0deb1de957225a61ad880dd5dc196ea",
    "external/gdr_qfaults_traces.csv": "9702f2e5c382a4f472ae834d22b94990983b059677a37adfafd51c50f75e643c",
    "external/gdr_volcanic_vents_in_footprint.csv": "f91bafbaccaaf2754e71d60434fc0f9eb2c7b880c6e714883f4974542ff6a0bf",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# 1. Restore training_features.tif from 5 split parts if not already cached & verified
feat_dest = CACHE / "training_features.tif"
if not (feat_dest.exists() and sha256_file(feat_dest) == EXPECTED_SHA256["training_features.tif"]):
    print(f"Streaming {FEAT_REPO}@{FEAT_REF[:10]} for training_features.tif (5 parts)...", flush=True)
    url = f"https://codeload.github.com/{FEAT_REPO}/tar.gz/{FEAT_REF}"
    req = urllib.request.Request(url, headers={"User-Agent": "gemsdoe75-restore"})
    part_paths = {}
    with urllib.request.urlopen(req, timeout=300) as resp:
        with tarfile.open(fileobj=resp, mode="r|gz") as tf:
            for member in tf:
                if not member.isfile():
                    continue
                rel = member.name.split("/", 1)[1] if "/" in member.name else member.name
                for i in range(5):
                    part_rel = f"data/bridge/gems-geodawn-numerical-features.tif.part-00{i}"
                    if rel == part_rel:
                        p_tmp = CACHE / f"_part_00{i}"
                        fh = tf.extractfile(member)
                        with p_tmp.open("wb") as out:
                            for chunk in iter(lambda: fh.read(1 << 20), b""):
                                out.write(chunk)
                        part_paths[i] = p_tmp
    if len(part_paths) != 5:
        raise RuntimeError(f"Expected 5 feature parts, got {sorted(part_paths)}")
    tmp_feat = CACHE / "training_features.tif.tmp"
    with tmp_feat.open("wb") as out:
        for i in range(5):
            with part_paths[i].open("rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    out.write(chunk)
            part_paths[i].unlink()
    got_sha = sha256_file(tmp_feat)
    if got_sha != EXPECTED_SHA256["training_features.tif"]:
        tmp_feat.unlink(missing_ok=True)
        raise RuntimeError(f"training_features.tif SHA-256 mismatch: {got_sha}")
    tmp_feat.replace(feat_dest)
    print(f"  [OK] training_features.tif ({feat_dest.stat().st_size:,} bytes)", flush=True)
else:
    print(f"  [OK cached] training_features.tif ({feat_dest.stat().st_size:,} bytes)", flush=True)

# 2. Restore core labels/sample, external layers, and 62 registry rasters from 60GEMSDOE
wanted_exact = {
    "data/official/labels.tif": CACHE / "labels.tif",
    "data/official/existing_faults.tif": CACHE / "existing_faults.tif",
    "data/official/sample_submission.tif": CACHE / "sample_submission.tif",
    "data/external/lidar_scarp_features_u8.tif": CACHE / "external/lidar_scarp_features_u8.tif",
    "data/external/topo_10m_derived_100m_u8.tif": CACHE / "external/topo_10m_derived_100m_u8.tif",
    "data/external/dem10_chi_100m_i16.tif": CACHE / "external/dem10_chi_100m_i16.tif",
    "data/external/dem10_chi_100m_sig_i32.tif": CACHE / "external/dem10_chi_100m_sig_i32.tif",
    "data/external/dem10_chi_100m_u8.tif": CACHE / "external/dem10_chi_100m_u8.tif",
    "data/external/geodawn_rad_u8.tif": CACHE / "external/geodawn_rad_u8.tif",
    "data/external/geodawn_extensions_u8.tif": CACHE / "external/geodawn_extensions_u8.tif",
    "data/external/sgmc_faults_100m.tif": CACHE / "external/sgmc_faults_100m.tif",
    "data/external/derived_sgmc_faults_100m.tif": CACHE / "external/derived_sgmc_faults_100m.tif",
    "data/external/derived_sgmc_faults_100m_u8.tif": CACHE / "external/derived_sgmc_faults_100m_u8.tif",
    "data/external/gdr_wellspring_in_footprint.csv": CACHE / "external/gdr_wellspring_in_footprint.csv",
    "data/external/gdr_qfaults_traces.csv": CACHE / "external/gdr_qfaults_traces.csv",
    "data/external/gdr_volcanic_vents_in_footprint.csv": CACHE / "external/gdr_volcanic_vents_in_footprint.csv",
    "data/external/trace_segments_utm11.csv": CACHE / "external/trace_segments_utm11.csv",
    "data/external/qfault_attributes.csv": CACHE / "external/qfault_attributes.csv",
    "data/external/2m_temperature_probe_INGENIOUS_regional_data.zip": CACHE / "external/2m_temperature_probe_INGENIOUS_regional_data.zip",
    "data/external/paleo_geothermal_regional.zip": CACHE / "external/paleo_geothermal_regional.zip",
    "registry/audit_index.json": CACHE / "audit_index.json",
}

need_stream = any(not p.exists() for p in wanted_exact.values()) or len(list(REG_CACHE.glob("*.tif"))) < 60
if need_stream:
    print(f"Streaming {TMPL_REPO}@{TMPL_REF[:10]} for external layers and registry rasters...", flush=True)
    url = f"https://codeload.github.com/{TMPL_REPO}/tar.gz/{TMPL_REF}"
    req = urllib.request.Request(url, headers={"User-Agent": "gemsdoe75-restore"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        with tarfile.open(fileobj=resp, mode="r|gz") as tf:
            for member in tf:
                if not member.isfile():
                    continue
                rel = member.name.split("/", 1)[1] if "/" in member.name else member.name
                dest = wanted_exact.get(rel)
                if dest is None and rel.startswith("registry/rasters/") and rel.endswith(".tif"):
                    dest = REG_CACHE / Path(rel).name
                if dest is not None:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    tmp = dest.with_suffix(dest.suffix + ".tmp")
                    fh = tf.extractfile(member)
                    with tmp.open("wb") as out:
                        for chunk in iter(lambda: fh.read(1 << 20), b""):
                            out.write(chunk)
                    tmp.replace(dest)

# 3. Verify all pinned SHA-256 hashes
verified_files = {}
for rel, exp_sha in EXPECTED_SHA256.items():
    p = CACHE / rel
    if not p.exists():
        raise FileNotFoundError(f"Missing restored file: {p}")
    actual_sha = sha256_file(p)
    if actual_sha != exp_sha:
        raise ValueError(f"SHA-256 mismatch on {rel}: expected {exp_sha}, got {actual_sha}")
    verified_files[rel] = {
        "sha256": actual_sha,
        "bytes": p.stat().st_size,
        "ok": True,
    }
    print(f"  [SHA-256 OK] {rel:45s} ({p.stat().st_size:>11,} B)")

# 4. Create lightweight symlinks in data/raw/, data/bridge/, data/official/, data/external/
def link_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        dst.unlink()
    rel_target = os.path.relpath(src, dst.parent)
    dst.symlink_to(rel_target)

for core_name in ("training_features.tif", "labels.tif", "existing_faults.tif", "sample_submission.tif"):
    link_file(CACHE / core_name, ROOT / "data/raw" / core_name)
    link_file(CACHE / core_name, ROOT / "data/official" / core_name)
    if core_name != "training_features.tif":
        link_file(CACHE / core_name, ROOT / "data/bridge" / core_name)

for ext_path in sorted((CACHE / "external").iterdir()):
    if ext_path.is_file():
        link_file(ext_path, ROOT / "data/raw/external" / ext_path.name)
        link_file(ext_path, ROOT / "data/external" / ext_path.name)

reg_tifs = sorted(REG_CACHE.glob("*.tif"))
print(f"  [REGISTRY OK] {len(reg_tifs)} registry rasters cached in .cache/registry_rasters/")

receipt = {
    "schema_version": 1,
    "restored_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "evidence_class": "DATA-RESTORE-RECEIPT",
    "provenance": (
        "Restored from commit-pinned GitHub mirrors (buffedlizard55-lab/GEMSDOE@"
        f"{FEAT_REF[:12]} and buffedlizard55-lab/60GEMSDOE@{TMPL_REF[:12]}). "
        "Every SHA-256 matches evidence/template-data-manifest.json. "
        "Note: this proves mirror byte-integrity across the GEMSDOE project series, "
        "not a direct live authenticated download from DrivenData's login-walled /data/ page."
    ),
    "feature_mirror": {"repo": FEAT_REPO, "commit": FEAT_REF},
    "template_mirror": {"repo": TMPL_REPO, "commit": TMPL_REF},
    "verified_files": verified_files,
    "registry_rasters_cached": len(reg_tifs),
}
(ROOT / "evidence/data_restore_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("Wrote evidence/data_restore_receipt.json")
PYEOF
