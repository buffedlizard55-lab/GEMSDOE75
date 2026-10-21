#!/usr/bin/env python3
"""Fetch the pinned input stack into .cache/inputs and verify SHA-256.

Uses pure Git pack transport (`git clone --bare --filter=blob:none --depth=1`
plus `git cat-file -p <blob_sha>`) with multi-part blob assembly (`parts` list
in `evidence/template-data-manifest.json`) and atomic temp-file replacement so
existing verified files are never overwritten on corrupt/mismatched transfers.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence/template-data-manifest.json"
FALLBACK_MANIFEST = ROOT / "evidence/input-manifest.json"
BARE_CACHE = ROOT / ".cache/git-blobs"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_repo(repo: str) -> Path:
    BARE_CACHE.mkdir(parents=True, exist_ok=True)
    slug = repo.replace("/", "__")
    repo_dir = BARE_CACHE / slug
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
    return repo_dir


def _stream_single_blob(repo: str, blob_sha: str, out_handle) -> None:
    try:
        repo_dir = ensure_repo(repo)
        subprocess.run(
            ["git", "-C", str(repo_dir), "cat-file", "-p", blob_sha],
            check=True,
            stdout=out_handle,
            stderr=subprocess.PIPE,
        )
    except Exception:
        tmp_b64 = out_handle.name + ".b64"
        try:
            with open(tmp_b64, "wb") as b64_file:
                subprocess.run(
                    [
                        "gh",
                        "api",
                        f"repos/{repo}/git/blobs/{blob_sha}",
                        "--jq",
                        ".content",
                    ],
                    check=True,
                    stdout=b64_file,
                    stderr=subprocess.PIPE,
                )
            with open(tmp_b64, "rb") as b64_file:
                out_handle.write(base64.b64decode(b64_file.read()))
        finally:
            Path(tmp_b64).unlink(missing_ok=True)


def fetch(row: dict, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / row["name"]
    if out.exists() and sha256(out) == row["sha256"]:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / f".{out.name}.tmp.{hashlib.md5(row['name'].encode()).hexdigest()[:8]}"
    try:
        with tmp.open("wb") as handle:
            if row.get("parts"):
                for part in row["parts"]:
                    _stream_single_blob(row["repo"], part["git_blob"], handle)
            else:
                _stream_single_blob(row["repo"], row["git_blob"], handle)
        got = sha256(tmp)
        if got != row["sha256"]:
            raise ValueError(
                f"{row['name']}: SHA-256 mismatch (got {got}, expected {row['sha256']})"
            )
        tmp.replace(out)
    finally:
        tmp.unlink(missing_ok=True)
    return out


def main() -> int:
    use_full = "--full" in sys.argv
    manifest_path = MANIFEST if (use_full and MANIFEST.exists()) else FALLBACK_MANIFEST
    rows = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
    row = {"name": "<none>"}
    try:
        for row in rows:
            print(fetch(row, ROOT / ".cache/inputs").relative_to(ROOT), flush=True)
    except (subprocess.CalledProcessError, ValueError) as exc:
        print(
            f"::error::Input retrieval failed for {row['name']}: {exc}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
