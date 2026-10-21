"""Restore educational audit inputs from immutable GitHub mirrors, never predictions."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


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
            subprocess.run(['gh', 'api',
                f"repos/{record['repo']}/contents/{record['path']}?ref={record['commit']}",
                '-H', 'Accept: application/vnd.github.raw+json'], stdout=out, stderr=subprocess.PIPE, check=True)
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
