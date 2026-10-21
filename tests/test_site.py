from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
PAGES=['index.html','executive-summary.html','research.html','evidence.html']


class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.urls=[];self.has_main=False;self.has_title=False
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='main' and d.get('id')=='main': self.has_main=True
        if tag=='title': self.has_title=True
        for name in ('href','src'):
            if name in d:self.urls.append(d[name])


def test_site_local_links_and_status():
    for page in PAGES:
        parser=Links();text=(ROOT/page).read_text();parser.feed(text)
        assert parser.has_main and parser.has_title
        assert 'lang="en"' in text
        assert 'viewport' in text
        for url in parser.urls:
            parts=urlsplit(url)
            if parts.scheme or parts.netloc or not parts.path: continue
            path=(ROOT/unquote(parts.path)).resolve()
            assert path.is_relative_to(ROOT),url
            assert path.exists(),f'{page}: {url}'
            # A format-demonstration TIF may be linked for review, but nothing may
            # be presented as an approved submission candidate.
            assert path.suffix.lower() not in {'.zip'},'No ZIP candidate is cleared'
    index_text=(ROOT/'index.html').read_text()
    exec_text=(ROOT/'executive-summary.html').read_text()
    # Status must be truthful: artifact exists but is not approved for submission.
    assert 'Generated, not approved' in index_text or 'DO NOT SUBMIT' in index_text
    assert 'DO NOT SUBMIT' in exec_text
    assert 'not holdout-validated' in exec_text or 'NOT MEASURED' in exec_text
    # The download link must point at the actual generated file.
    assert 'gems75-blind-upflow-radial-20261021T040220Z-43cdadda2c43.tif' in exec_text


def test_site_build_reproducible():
    before={p:(ROOT/p).read_bytes() for p in PAGES}
    subprocess.run([sys.executable,'scripts/build_site.py'],cwd=ROOT,check=True)
    assert before=={p:(ROOT/p).read_bytes() for p in PAGES}
