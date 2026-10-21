#!/usr/bin/env python3
"""Step 1 (Rule 4): Build the 54-channel physical stack, add fold-proper LOCO-Quat
network features per held-out fold, verify zero NaN/Inf explosions, cache `.cache/gems75_static54.f32.npy`,
and run single-feature ROC-AUC leakage canaries across ALL 59 features BEFORE fitting any model!
"""
from __future__ import annotations

import json
import resource
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw

from gems75.network import compute_network_features_2d
from gems75.physics import ALL_STAGE1_FEATURES, build_static_feature_stack
from gems75.protocol import run_feature_leakage_canaries


def peak_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def main() -> int:
    t0 = time.time()
    data_dir = ROOT / ".cache" / "data"
    ext_root = ROOT / ".cache" / "gems_data"
    cache_path = ROOT / ".cache" / "gems75_static54.f32.npy"
    strike_path = ROOT / ".cache" / "gems75_strike.f32.npy"

    grid = load_grid(data_dir)
    valid = grid.footprint
    cat = grid.catalogue
    print(f"[canary] Loaded Grid {grid.shape}, valid={int(valid.sum()):,}, cat={int(cat.sum()):,} (RSS={peak_rss_mb():.0f} MB)")

    X_stat, surf_strike = build_static_feature_stack(data_dir, ext_root, valid)
    np.save(cache_path, X_stat)
    np.save(strike_path, surf_strike)
    print(f"[canary] Built & cached X_stat {X_stat.shape} in {time.time() - t0:.1f}s (RSS={peak_rss_mb():.0f} MB)")

    folds, _ = buffered_component_draw(grid, seed=20, buffer_px=3, boundary_px=12)

    # Compute network features strictly from globally buffered `folds[0]['visible']`
    dc, ta, rs, hl, mb = compute_network_features_2d(folds[0]["visible"])
    X_net = np.column_stack([
        dc[valid],
        ta[valid],
        rs[valid],
        hl[valid],
        mb[valid],
    ]).astype(np.float32)

    X_all = np.hstack([X_stat, X_net])
    del X_net

    canaries = run_feature_leakage_canaries(X_all, ALL_STAGE1_FEATURES, valid, folds)
    max_sym = max(c["sym_auc"] for c in canaries)
    top12 = sorted(canaries, key=lambda r: -r["sym_auc"])[:12]
    all_pass = all(c["pass"] for c in canaries)

    out = {
        "protocol_rule": "Rule 4: Single-feature holdout ROC-AUC canary (max(AUC, 1-AUC) <= 0.90)",
        "evaluator_folds": "gems57 buffered_component_draw(seed=20, buffer_px=3, boundary_px=12)",
        "n_features_tested": len(canaries),
        "max_symmetric_auc": round(max_sym, 5),
        "threshold": 0.90,
        "all_pass": all_pass,
        "elapsed_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(peak_rss_mb(), 1),
        "canaries": canaries,
    }
    ev_path = ROOT / "evidence" / "leakage_canaries.json"
    ev_path.write_text(json.dumps(out, indent=2) + "\n")

    print(f"[canary] Tested {len(canaries)} features | max(AUC, 1-AUC) = {max_sym:.5f} | ALL_PASS = {all_pass}")
    print("[canary] Top 12 strongest single physical/network features on held-out faults:")
    for r in top12:
        print(f"  [{r['col']:02d}] {r['name']:32s} AUC={r['auc']:.5f}  sym={r['sym_auc']:.5f}  PASS={r['pass']}")

    if not all_pass:
        raise SystemExit("LEAKAGE CANARY FAILED (> 0.90)!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
