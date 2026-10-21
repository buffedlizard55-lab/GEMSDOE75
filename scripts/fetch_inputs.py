"""Restore educational audit inputs from immutable GitHub mirrors, never predictions."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _fetch_from_codeload(record, temporary: Path) -> None:
    url = f"https://codeload.github.com/{record['repo']}/tar.gz/{record['commit']}"
    target_suffix = "/" + record["path"].lstrip("/")
    with urllib.request.urlopen(url, timeout=60) as resp:
        with tarfile.open(fileobj=resp, mode="r|gz") as tf:
            for member in tf:
                if member.isfile() and member.name.endswith(target_suffix):
                    fobj = tf.extractfile(member)
                    if fobj is None:
                        break
                    temporary.write_bytes(fobj.read())
                    return
    raise RuntimeError(f"Could not locate {record['path']} in {url}")


def fetch(record, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / record['name']
    if dest.exists() and sha256(dest) == record['sha256']:
        return dest
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=folder, delete=False) as out:
            temporary = Path(out.name)
            try:
                subprocess.run(['gh', 'api',
                    f"repos/{record['repo']}/git/blobs/{record['git_blob']}",
                    '--jq', '.content'], stdout=out, stderr=subprocess.PIPE, check=True)
                encoded = b''.join(temporary.read_bytes().split())
                temporary.write_bytes(base64.b64decode(encoded, validate=True))
            except subprocess.CalledProcessError:
                _fetch_from_codeload(record, temporary)
        if sha256(temporary) != record['sha256']:
            raise ValueError(f"SHA-256 mismatch: {record['name']}; expected {record['sha256']}, got {sha256(temporary)}")
        temporary.replace(dest)
        return dest
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    for row in json.loads((ROOT / 'evidence/input-manifest.json').read_text())['files']:
        try:
            print(fetch(row, ROOT / '.cache/inputs').relative_to(ROOT))
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or b'').decode(errors='replace').strip()
            print(f"::error::Mirror retrieval failed for {row['name']}: {detail}")
            raise
        except ValueError as exc:
            print(f'::error::{exc}')
            raise
