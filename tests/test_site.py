from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["index.html", "executive-summary.html", "research.html", "evidence.html"]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.has_main = False
        self.has_title = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "main" and d.get("id") == "main":
            self.has_main = True
        if tag == "title":
            self.has_title = True
        for name in ("href", "src"):
            if name in d:
                self.urls.append(d[name])


def test_site_local_links_and_download_readiness():
    card = json.loads((ROOT / "evidence/run-card.json").read_text())
    sub = card["submission"]
    tif_sha = hashlib.sha256((ROOT / sub["tif_path"]).read_bytes()).hexdigest()
    zip_sha = hashlib.sha256((ROOT / sub["zip_path"]).read_bytes()).hexdigest()
    assert tif_sha == sub["tif_sha256"]
    assert zip_sha == sub["zip_sha256"]

    for base_dir in (ROOT, ROOT / "docs"):
        for page in PAGES:
            pfile = base_dir / page
            assert pfile.exists(), f"Missing {pfile}"
            parser = Links()
            text = pfile.read_text()
            parser.feed(text)
            assert parser.has_main and parser.has_title
            assert 'lang="en"' in text
            assert "viewport" in text
            assert "OK TO DOWNLOAD: YES" in text
            assert sub["submission_name"] in text
            resolved_names = set()
            for url in parser.urls:
                parts = urlsplit(url)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                path = (base_dir / unquote(parts.path)).resolve()
                assert path.is_relative_to(ROOT), f"{pfile}: {url} escapes repo root"
                assert path.exists(), f"{pfile}: broken local path {url} -> {path}"
                resolved_names.add(path.name)
            assert Path(sub["tif_path"]).name in resolved_names
            assert Path(sub["zip_path"]).name in resolved_names


def test_site_build_reproducible():
    targets = [*(ROOT / p for p in PAGES), *(ROOT / "docs" / p for p in PAGES)]
    before = {p: p.read_bytes() for p in targets}
    subprocess.run([sys.executable, "scripts/build_site.py"], cwd=ROOT, check=True)
    assert before == {p: p.read_bytes() for p in targets}
