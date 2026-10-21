#!/usr/bin/env python3
"""Compute non-tunable reference baseline HOLDOUT-DTI table using shared gems57 evaluator."""
from __future__ import annotations

import gc
import json
from pathlib import Path
import sys
import time

import lightgbm as lgb
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import evaluate_holdout, holdout, spatial
from gems57.network import STRUCT3


def build_holdout_suites(catalogue: np.ndarray, eligible: np.ndarray):
    y3, x3 = np.ogrid[-3:4, -3:4]
    disk3 = (y3 * y3 + x3 * x3) <= 9
    qfolds = list(spatial.folds(catalogue, eligible, buffer_px=80))

    comp, ncomp = ndi.label(catalogue & eligible, structure=STRUCT3)
    sizes = np.bincount(comp.ravel())
    sizes[0] = 0
    rng = np.random.default_rng(75)
    perm = rng.permutation(np.arange(1, ncomp + 1))
    bins = [[] for _ in range(4)]
    loads = [0] * 4
    for cid in perm[np.argsort(-sizes[perm], kind="mergesort")]:
        b = int(np.argmin(loads))
        bins[b].append(int(cid))
        loads[b] += int(sizes[cid])
    _, is_det = holdout.component_detached(catalogue & eligible, detach_px=4)
    det_mask_all = is_det[comp]

    net_folds, det_folds = [], []
    for k in range(4):
        hid = np.isin(comp, np.asarray(bins[k], dtype=comp.dtype))
        vis = (catalogue & eligible) & ~hid & ~ndi.binary_dilation(hid, structure=disk3)
        net_folds.append(dict(fold=k, truth=hid, visible=vis, region=eligible))
        det_folds.append(
            dict(
                fold=k,
                truth=hid & det_mask_all,
                visible=vis,
                region=eligible & ~(hid & ~det_mask_all),
            )
        )
    return qfolds, net_folds, det_folds


def eval_pred(a: np.ndarray, folds: list[dict], eligible: np.ndarray) -> np.ndarray:
    return np.concatenate(
        [evaluate_holdout.evaluate(a, f, eligible, block_side=200)[1] for f in folds],
        axis=0,
    )


def main() -> int:
    t0 = time.time()
    inp = ROOT / ".cache/inputs"
    with rasterio.open(inp / "sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(inp / "labels.tif") as src:
        lab = src.read(1)
    catalogue = np.isfinite(lab) & (lab > 0)
    eligible = footprint & np.isfinite(lab)
    del lab

    qfolds, net_folds, det_folds = build_holdout_suites(catalogue, eligible)
    scored_map = {
        "H33_static": inp / "h33.tif",
        "D28_static": inp / "scored/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
        "D15_static": inp / "scored/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
        "H19_5_static": inp / "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif",
        "R13_lattice_s5": inp / "scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
    }

    q_mats, n_mats, d_mats = {}, {}, {}
    for name, p in scored_map.items():
        with rasterio.open(p) as src:
            a = src.read(1).astype(np.float32)
        a = np.where(np.isfinite(a), np.clip(a, 0.0, 1.0), 0.0)
        q_mats[name] = eval_pred(a, qfolds, eligible)
        n_mats[name] = eval_pred(a, net_folds, eligible)
        d_mats[name] = eval_pred(a, det_folds, eligible)
        print(f"[{time.time()-t0:5.1f}s] {name:16s} | dots={int((a > 0).sum()):7d}", flush=True)
        del a

    rng_r = np.random.default_rng(75)
    rand_a = np.zeros(footprint.shape, np.float32)
    rand_a.ravel()[rng_r.choice(np.flatnonzero(eligible & ~catalogue), size=37654, replace=False)] = 1.0
    q_mats["Random_37654"] = eval_pred(rand_a, qfolds, eligible)
    n_mats["Random_37654"] = eval_pred(rand_a, net_folds, eligible)
    d_mats["Random_37654"] = eval_pred(rand_a, det_folds, eligible)
    del rand_a

    print(f"[{time.time()-t0:5.1f}s] Scored Random_37654", flush=True)

    # Single-feature det_elev_slope (Band 19) non-tunable 3-px skeleton top-37654 baseline
    with rasterio.open(inp / "training_features.tif") as src:
        el_r, el_c = np.nonzero(eligible)
        X_full = np.empty((el_r.size, src.count), np.float32)
        for b in range(1, src.count + 1):
            band = src.read(b)
            v = band[el_r, el_c].astype(np.float32)
            bad = ~np.isfinite(v) | (np.abs(v) > 1e18)
            v[bad] = np.nanmedian(v[~bad])
            X_full[:, b - 1] = v
            del band, v
    gc.collect()
    print(f"[{time.time()-t0:5.1f}s] Loaded X_full {X_full.shape}", flush=True)

    slope_grid = np.zeros(footprint.shape, np.float32)
    slope_grid[el_r, el_c] = X_full[:, 18]
    ys_s, xs_s = np.nonzero(eligible & ~catalogue)
    ord_s = np.argsort(-slope_grid[ys_s, xs_s], kind="stable")
    ys_s, xs_s = ys_s[ord_s], xs_s[ord_s]
    taken_s = np.zeros(footprint.shape, bool)
    slope_dots = np.zeros(footprint.shape, np.float32)
    cnt_s = 0
    for y, x in zip(ys_s, xs_s):
        if taken_s[y, x]:
            continue
        slope_dots[y, x] = 1.0
        cnt_s += 1
        if cnt_s >= 37654:
            break
        taken_s[max(0, y - 2):min(footprint.shape[0], y + 3), max(0, x - 2):min(footprint.shape[1], x + 3)] = True
    q_mats["det_elev_slope_top37654"] = eval_pred(slope_dots, qfolds, eligible)
    n_mats["det_elev_slope_top37654"] = eval_pred(slope_dots, net_folds, eligible)
    d_mats["det_elev_slope_top37654"] = eval_pred(slope_dots, det_folds, eligible)
    del slope_grid, slope_dots, taken_s

    idx_map = np.full(footprint.shape, -1, np.int32)
    idx_map[el_r, el_c] = np.arange(el_r.size, dtype=np.int32)

    for sname, folds, dfolds in [("Q", qfolds, None), ("N", net_folds, det_folds)]:
        boots, dboots = [], []
        for k, f in enumerate(folds):
            vis, reg = f["visible"], f["region"]
            has_outside = (~reg & eligible).any()
            pos_grid = vis & (eligible & ~reg if has_outside else eligible)
            neg_pool = idx_map[(eligible & ~reg if has_outside else eligible) & ~ndi.binary_dilation(vis, iterations=3)]
            p_idx = idx_map[pos_grid]
            rng_f = np.random.default_rng(100 + k)
            n_idx = rng_f.choice(neg_pool, size=min(neg_pool.size, max(4 * p_idx.size, 40000)), replace=False)
            clf = lgb.LGBMClassifier(
                n_estimators=200,
                learning_rate=0.06,
                num_leaves=63,
                min_child_samples=80,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42 + k,
                n_jobs=2,
                verbose=-1,
            )
            clf.fit(
                X_full[np.concatenate([p_idx, n_idx])],
                np.concatenate([np.ones(p_idx.size, np.int32), np.zeros(n_idx.size, np.int32)]),
            )
            d_vis = ndi.distance_transform_edt(~vis)
            env = reg & eligible & (d_vis > 2.0) & (d_vis <= 15.0)
            pred_f = np.zeros(footprint.shape, np.float32)
            if env.any():
                prob = np.zeros(footprint.shape, np.float32)
                prob[env] = clf.predict_proba(X_full[idx_map[env]])[:, 1].astype(np.float32)
                k_dots = int(round(37654 * float(reg[eligible].mean())))
                ys, xs = np.nonzero(env)
                order = np.argsort(-prob[ys, xs], kind="stable")
                ys, xs = ys[order], xs[order]
                taken = np.zeros(footprint.shape, bool)
                cnt = 0
                for y, x in zip(ys, xs):
                    if taken[y, x]:
                        continue
                    pred_f[y, x] = 1.0
                    cnt += 1
                    if cnt >= k_dots:
                        break
                    taken[max(0, y - 2):min(footprint.shape[0], y + 3), max(0, x - 2):min(footprint.shape[1], x + 3)] = True
            boots.append(evaluate_holdout.evaluate(pred_f, f, eligible, block_side=200)[1])
            if dfolds is not None:
                dboots.append(evaluate_holdout.evaluate(pred_f, dfolds[k], eligible, block_side=200)[1])
        if sname == "Q":
            q_mats["H33_foldfair"] = np.concatenate(boots, axis=0)
        else:
            n_mats["H33_foldfair"] = np.concatenate(boots, axis=0)
            d_mats["H33_foldfair"] = np.concatenate(dboots, axis=0)
        print(f"[{time.time()-t0:5.1f}s] Built & scored H33_foldfair on Suite {sname}", flush=True)

    qs = evaluate_holdout.pooled_summary(q_mats, candidate="H33_foldfair", seed=75)
    ns = evaluate_holdout.pooled_summary(n_mats, candidate="H33_foldfair", seed=75)
    ds = evaluate_holdout.pooled_summary(d_mats, candidate="H33_foldfair", seed=75)

    out = {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluate_holdout.VERSION,
        "generated_utc": "2026-10-21",
        "suite_Q_blind_quadrants_8km": qs,
        "suite_N_whole_component_300m": ns,
        "suite_D_detached_splays_400m": ds,
    }
    (ROOT / "evidence/baseline-holdout-table.json").write_text(json.dumps(out, indent=2) + "\n")

    for title, s in [
        ("SUITE Q: 8 KM BLIND QUADRANTS (gems57-pooled-hide-v2, withheld=60,988)", qs),
        ("SUITE N: 4-FOLD WHOLE-COMPONENT HIDE-AND-RECOVER (withheld=60,988)", ns),
        ("SUITE D: DETACHED SPLAYS >400M ONLY (withheld=17,556)", ds),
    ]:
        print(f"\n=== {title} ===")
        for k, v in s["scores"].items():
            print(f"  {k:24s} | DTI={v['dti']:.4f} | CI95=[{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}]")
    gc.collect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
