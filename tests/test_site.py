from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ROOT_PAGES = [
    "index.html",
    "download.html",
    "executive-summary.html",
    "research.html",
    "evidence.html",
    "run-card.html",
    "sources.html",
]
DOCS_PAGES = [f"docs/{p}" for p in ROOT_PAGES]
ALL_PAGES = ROOT_PAGES + DOCS_PAGES


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []
        self.has_main = False
        self.has_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        if tag == "main" and d.get("id") == "main":
            self.has_main = True
        if tag == "title":
            self.has_title = True
        for name in ("href", "src"):
            val = d.get(name)
            if val is not None:
                self.urls.append(val)


def test_site_local_links_and_status() -> None:
    for rel_page in ALL_PAGES:
        page_path = ROOT / rel_page
        parser = Links()
        text = page_path.read_text()
        parser.feed(text)
        assert parser.has_main and parser.has_title, f"{rel_page} missing <main id='main'> or <title>"
        assert 'lang="en"' in text
        assert "viewport" in text
        for url in parser.urls:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            target = (page_path.parent / unquote(parts.path)).resolve()
            assert target.is_relative_to(ROOT), f"{rel_page}: {url}"
            assert target.exists(), f"{rel_page}: broken link {url} -> {target}"

    docs_index = (ROOT / "docs/index.html").read_text()
    assert "PROMOTE — SAFE TO DOWNLOAD &amp; SUBMIT" in docs_index or "PROMOTE — SAFE TO DOWNLOAD & SUBMIT" in docs_index
    assert "gems75-trlt-radon-loco-ridge-20261021-zeros.tif" in docs_index
    assert "e04df46e8a0770b470bf8846ed2aff966fd192e7ff71fbc4d82724b28c0b1b71" in docs_index


def test_site_build_reproducible() -> None:
    before = {p: (ROOT / p).read_bytes() for p in ALL_PAGES}
    subprocess.run([sys.executable, "scripts/build_site.py"], cwd=ROOT, check=True)
    assert before == {p: (ROOT / p).read_bytes() for p in ALL_PAGES}
