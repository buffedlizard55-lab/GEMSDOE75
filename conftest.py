"""Ensure src/ and vendor/ are importable in pytest without installing editable wheels."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for sub in ("src", "vendor"):
    p = str(ROOT / sub)
    if p not in sys.path:
        sys.path.insert(0, p)
