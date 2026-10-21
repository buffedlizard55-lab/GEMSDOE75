from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'vendor'))
# Added alongside tests/test_metric.py, tests/test_submission_io.py and
# tests/test_holdout.py (a second, independently-built cross-check package,
# see the "Parallel session" section of README.md): make `gems_doe` importable
# without requiring an editable `pip install -e .`, so `pip install -r
# requirements.txt && pytest -q` keeps working unchanged in CI.
sys.path.insert(0, str(ROOT/'src'))
