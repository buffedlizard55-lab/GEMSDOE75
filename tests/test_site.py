from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
PAGES=['index.html','download.html','executive-summary.html','research.html','evidence.html']
# The download page is the one authorized location where a candidate .tif may
# be linked, because it carries the full submit-readiness status. Every other
# page must remain free of direct .tif/.zip links (fail-closed guard).
DOWNLOAD_PAGE = 'download.html'


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
            if page != DOWNLOAD_PAGE:
                assert path.suffix.lower() not in {'.tif','.tiff','.zip'},'No candidate is cleared outside the download page'
    # Status strings must reflect reality: a candidate exists but is not approved.
    assert 'NOT_APPROVED_TO_SUBMIT' in (ROOT/'index.html').read_text()
    assert 'format-validated, not score-validated' in (ROOT/'index.html').read_text()
    assert 'Go to download page' in (ROOT/'executive-summary.html').read_text()
    assert 'Download candidate' in (ROOT/'download.html').read_text()
    assert 'not</strong> OK to submit to the contest yet' in (ROOT/'download.html').read_text() or 'not OK to submit to the contest yet' in (ROOT/'download.html').read_text()


def test_site_build_reproducible():
    before={p:(ROOT/p).read_bytes() for p in PAGES}
    subprocess.run([sys.executable,'scripts/build_site.py'],cwd=ROOT,check=True)
    assert before=={p:(ROOT/p).read_bytes() for p in PAGES}