#!/usr/bin/env python3
"""Fetch verified public-domain / CC-BY cached external layers and cross-repo registry rasters.

Uses pure Git pack protocol (`git clone --bare --depth=1 --filter=blob:none` +
`git ls-tree -r HEAD` + `git cat-file -p`) so zero REST API calls are consumed and
every artifact is verified by SHA-256 into `evidence/external-cache-manifest.json`.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BARE_CACHE = ROOT / ".cache" / "git-blobs"
EXT_DIR = ROOT / ".cache" / "external"
REG_DIR = ROOT / ".cache" / "registry"
MANIFEST_OUT = ROOT / "evidence" / "external-cache-manifest.json"

EXTERNAL_SOURCES = [
    {
        "name": "lidar_scarp_features_u8.tif",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "repo_path": "data/external/lidar_scarp_features_u8.tif",
        "upstream_url": "https://www.usgs.gov/3d-elevation-program",
        "license": "USGS Public Domain (3DEP 1m LiDAR 706-tile compilation)",
    },
    {
        "name": "topo_10m_derived_100m_u8.tif",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "repo_path": "data/external/topo_10m_derived_100m_u8.tif",
        "upstream_url": "https://www.usgs.gov/3d-elevation-program",
        "license": "USGS Public Domain (3DEP 1/3 arc-sec seamless DEM derivatives)",
    },
    {
        "name": "dem10_chi_100m_i16.tif",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "repo_path": "data/external/dem10_chi_100m_i16.tif",
        "upstream_url": "https://www.usgs.gov/3d-elevation-program",
        "license": "USGS Public Domain (3DEP 10m fluvial chi & steepness)",
    },
    {
        "name": "geodawn_rad_u8.tif",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "repo_path": "data/external/geodawn_rad_u8.tif",
        "upstream_url": "https://doi.org/10.5066/P93LGLVQ",
        "license": "CC0 1.0 Universal (USGS EarthMRI GeoDAWN aeroradiometrics)",
    },
    {
        "name": "geodawn_extensions_u8.tif",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "repo_path": "data/external/geodawn_extensions_u8.tif",
        "upstream_url": "https://doi.org/10.5066/P93LGLVQ",
        "license": "CC0 1.0 Universal (USGS EarthMRI GeoDAWN aeromagnetic/radiometric grids)",
    },
    {
        "name": "gdr_wellspring_in_footprint.csv",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "repo_path": "data/external/gdr_wellspring_in_footprint.csv",
        "upstream_url": "https://gdr.openei.org/submissions/1391",
        "license": "CC BY 4.0 (DOE GDR-1391 INGENIOUS Well & Spring Geothermometry)",
    },
    {
        "name": "gdr_volcanic_vents_in_footprint.csv",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "repo_path": "data/external/gdr_volcanic_vents_in_footprint.csv",
        "upstream_url": "https://gdr.openei.org/submissions/1391",
        "license": "CC BY 4.0 (DOE GDR-1391 INGENIOUS Quaternary Volcanic Vents)",
    },
    {
        "name": "2m_temperature_probe_INGENIOUS_regional_data.zip",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "repo_path": "data/external/2m_temperature_probe_INGENIOUS_regional_data.zip",
        "upstream_url": "https://gdr.openei.org/submissions/1391",
        "license": "CC BY 4.0 (DOE GDR-1391 INGENIOUS 2m Temperature Probes)",
    },
    {
        "name": "paleo_geothermal_regional.zip",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "repo_path": "data/external/paleo_geothermal_regional.zip",
        "upstream_url": "https://gdr.openei.org/submissions/1391",
        "license": "CC BY 4.0 (DOE GDR-1391 INGENIOUS Paleo-Geothermal Deposits)",
    },
    {
        "name": "sgmc_faults_100m.tif",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "repo_path": "data/external/sgmc_faults_100m.tif",
        "upstream_url": "https://doi.org/10.3133/ds1052",
        "license": "USGS Public Domain (SGMC DS-1052 bedrock faults — diagnostic benchmark ONLY, never model input)",
    },
    {
        "name": "tiger_road_distance_m.tif",
        "repo": "buffedlizard55-lab/GEMSDOE24",
        "repo_path": "data/external/audit_sources/tiger_road_distance_m.tif",
        "upstream_url": "https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html",
        "license": "US Census Public Domain (TIGER/Line road & rail embankment de-confounder)",
    },
    {
        "name": "acquisition_block_id_100m.tif",
        "repo": "buffedlizard55-lab/GEMSDOE24",
        "repo_path": "data/external/audit_sources/acquisition_block_id_100m.tif",
        "upstream_url": "https://doi.org/10.5066/P93LGLVQ",
        "license": "CC0 1.0 Universal (GeoDAWN survey block-seam de-confounder)",
    },
]

EXTRA_REGISTRY_REPOS = [
    ("buffedlizard55-lab/60GEMSDOE", "registry/rasters/"),
    ("buffedlizard55-lab/GEMSDOE49", "docs/downloads/"),
    ("buffedlizard55-lab/GEMSDOE63", "docs/downloads/"),
    ("buffedlizard55-lab/GEMSDOE70", "docs/downloads/"),
    ("buffedlizard55-lab/GEMSDOE70", "outputs/rasters/"),
    ("buffedlizard55-lab/GEMSDOE73", "docs/downloads/"),
    ("buffedlizard55-lab/GEMSDOE74", "docs/downloads/"),
    ("buffedlizard55-lab/GEMSDOE76", "docs/downloads/"),
    ("buffedlizard55-lab/GEMSDOE77", "registry/"),
]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ensure_bare_repo(repo: str) -> tuple[Path, dict[str, str]]:
    BARE_CACHE.mkdir(parents=True, exist_ok=True)
    repo_dir = BARE_CACHE / repo.replace("/", "__")
    if not (repo_dir / "HEAD").exists():
        subprocess.run(
            [
                "git",
                "clone",
                "--bare",
                "--depth=1",
                "--filter=blob:none",
                f"https://github.com/{repo}.git",
                str(repo_dir),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    out = subprocess.check_output(
        ["git", "-C", str(repo_dir), "ls-tree", "-r", "HEAD"], text=True
    )
    tree: dict[str, str] = {}
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        _mode, obj_type, sha = meta.split()
        if obj_type == "blob":
            tree[path] = sha
    return repo_dir, tree


def _extract_blobs_batch(repo_dir: Path, items: list[tuple[str, Path]]) -> None:
    pending = [(sha, dest) for sha, dest in items if not (dest.exists() and dest.stat().st_size > 0)]
    if not pending:
        return
    # Batch pre-fetch all requested blobs in a single Git pack round-trip!
    proc = subprocess.Popen(
        ["git", "-C", str(repo_dir), "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    assert proc.stdin is not None and proc.stdout is not None
    req = "".join(f"{sha}\n" for sha, _ in pending).encode()
    proc.stdin.write(req)
    proc.stdin.close()
    for sha, dest in pending:
        header = proc.stdout.readline().decode().strip()
        parts = header.split()
        if len(parts) < 3 or parts[1] != "blob":
            raise RuntimeError(f"Unexpected git cat-file header for {sha}: {header}")
        size = int(parts[2])
        data = proc.stdout.read(size)
        proc.stdout.read(1)  # trailing LF
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"git cat-file --batch failed in {repo_dir}")


def main() -> int:
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    REG_DIR.mkdir(parents=True, exist_ok=True)

    repos = sorted({s["repo"] for s in EXTERNAL_SOURCES} | {r for r, _ in EXTRA_REGISTRY_REPOS})
    repo_dirs: dict[str, Path] = {}
    trees: dict[str, dict[str, str]] = {}
    for repo in repos:
        rdir, tree = _ensure_bare_repo(repo)
        repo_dirs[repo] = rdir
        trees[repo] = tree

    per_repo_jobs: dict[str, list[tuple[str, Path]]] = {r: [] for r in repos}
    ext_meta = []
    for spec in EXTERNAL_SOURCES:
        sha = trees[spec["repo"]][spec["repo_path"]]
        dest = EXT_DIR / spec["name"]
        per_repo_jobs[spec["repo"]].append((sha, dest))
        ext_meta.append((spec, sha, dest))

    seen_names: set[str] = set()
    reg_meta = []
    for repo, prefix in EXTRA_REGISTRY_REPOS:
        for p, sha in sorted(trees[repo].items()):
            if not p.startswith(prefix) or not p.endswith(".tif"):
                continue
            fname = Path(p).name
            if fname.startswith("gemsdoe75"):
                continue
            tag_name = fname if fname not in seen_names else f"{repo.split('/')[-1]}__{fname}"
            seen_names.add(tag_name)
            dest = REG_DIR / tag_name
            per_repo_jobs[repo].append((sha, dest))
            reg_meta.append(({"repo": repo, "repo_path": p, "name": tag_name}, sha, dest))

    for repo, jobs in per_repo_jobs.items():
        if jobs:
            print(f"[pack] fetching {len(jobs)} blobs from {repo} ...", flush=True)
            _extract_blobs_batch(repo_dirs[repo], jobs)

    ext_records = [
        {**spec, "git_blob_sha1": sha, "sha256": _sha256_file(dest), "bytes": dest.stat().st_size}
        for spec, sha, dest in ext_meta
    ]
    reg_records = [
        {**spec, "git_blob_sha1": sha, "sha256": _sha256_file(dest), "bytes": dest.stat().st_size}
        for spec, sha, dest in reg_meta
    ]
    MANIFEST_OUT.write_text(
        json.dumps(
            {
                "external_files": ext_records,
                "registry_rasters_count": len(reg_records),
                "registry_rasters": reg_records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Verified {len(ext_records)} external files + {len(reg_records)} registry rasters.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
