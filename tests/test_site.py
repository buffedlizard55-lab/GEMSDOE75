from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGES = ['index.html', 'executive-summary.html', 'research.html', 'evidence.html']


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.has_main = False
        self.has_title = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'main' and d.get('id') == 'main':
            self.has_main = True
        if tag == 'title':
            self.has_title = True
        for name in ('href', 'src'):
            if name in d:
                self.urls.append(d[name])


def test_site_local_links_and_status():
    for page in PAGES:
        parser = Links()
        text = (ROOT / page).read_text()
        parser.feed(text)
        assert parser.has_main and parser.has_title
        assert 'lang="en"' in text
        assert 'viewport' in text
        has_tif_link = False
        has_zip_link = False
        for url in parser.urls:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            path = (ROOT / unquote(parts.path)).resolve()
            assert path.is_relative_to(ROOT), url
            assert path.exists(), f'{page}: {url}'
            if path.suffix.lower() == '.tif':
                has_tif_link = True
            if path.suffix.lower() == '.zip':
                has_zip_link = True
        assert has_tif_link, f'{page} must provide a direct .tif download link'
        assert has_zip_link, f'{page} must provide a direct .zip download link'
    assert 'Yes — OK to download and submit this unique GeoTIFF (.tif)' in (ROOT / 'index.html').read_text()
    assert 'READY TO DOWNLOAD &amp; SUBMIT' in (ROOT / 'executive-summary.html').read_text()


def test_site_build_reproducible():
    before = {p: (ROOT / p).read_bytes() for p in PAGES}
    subprocess.run([sys.executable, 'scripts/build_site.py'], cwd=ROOT, check=True)
    assert before == {p: (ROOT / p).read_bytes() for p in PAGES}
