"""Read-only metadata scan of the user-listed repositories; not a uniqueness pass."""
import concurrent.futures
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REVERSED = {5,6,7,8,11,12,13,14,15,16,17,18,19,20,55,56,57,58,59,60,61,62}
REPOS = ['GEMSDOE'] + [f'{n}GEMSDOE' if n in REVERSED else f'GEMSDOE{n}' for n in range(2,79)]


def inspect(repo):
    p = subprocess.run(['gh','api',f'repos/buffedlizard55-lab/{repo}/git/trees/main?recursive=1'],
                       capture_output=True, text=True)
    if p.returncode:
        return dict(repository=repo,status='unavailable',error=p.stderr.strip())
    tree = json.loads(p.stdout)
    rasters = [dict(path=x['path'],git_blob=x['sha'],bytes=x.get('size'))
               for x in tree['tree'] if x['path'].lower().endswith(('.tif','.tiff'))]
    return dict(repository=repo,status='metadata only',tree_sha=tree['sha'],truncated=tree.get('truncated',False),
                rasters=rasters,score_verification='No organizer receipt checked')


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        rows=list(pool.map(inspect, REPOS))
    result=dict(date_utc='2026-10-21',scope='GitHub main-tree TIFF metadata, not website content, not raster uniqueness clearance',
                repositories=rows)
    (ROOT/'evidence/repository-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(repositories=len(rows),unavailable=[x['repository'] for x in rows if x['status']=='unavailable'],
                         tif_paths=sum(len(x.get('rasters',[])) for x in rows)),indent=2))
