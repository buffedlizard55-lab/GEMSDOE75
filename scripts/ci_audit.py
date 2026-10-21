"""Repeat the audit and expose actionable CI failures through check annotations."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def annotate(message):
    # GitHub workflow-command escaping; never include environment/credentials.
    message = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::error::' + message, flush=True)


if __name__ == '__main__':
    run = subprocess.run([sys.executable, 'scripts/audit.py'], cwd=ROOT,
                         capture_output=True, text=True)
    if run.returncode:
        annotate('Audit failed: ' + run.stdout[-1500:] + run.stderr[-5000:])
        sys.exit(1)
    print(run.stdout)
    diff = subprocess.run(['git', 'diff', '--exit-code', '--', 'evidence/audit.json',
                           'evidence/run-card.json'], cwd=ROOT, capture_output=True, text=True)
    if diff.returncode:
        annotate('Audit reproducibility diff: ' + diff.stdout[:6500] + diff.stderr[:1000])
        sys.exit(1)
