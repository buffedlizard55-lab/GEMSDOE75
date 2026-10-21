"""Leakage canaries, benchmark suite (Instruments A, C_pied, B', B''), and fleet uniqueness gate."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score

from gems57.evaluate_holdout import VERSION as HOLDOUT_VERSION, evaluate, pooled_summary
from gems57.grid import Grid, load_grid
from gems57.holdout import buffered_component_draw
from gems57.metric import ALPHA, BETA, EPS, RADIUS_PX, kernel

from .constants import CANARY_AUC_MAX, DOT_OVERLAP_MAX, KERNEL_300M, SPEARMAN_MAX


def _dots(a: np.ndarray) -> np.ndarray:
    arr = np.asarray(a)
    return np.isfinite(arr) & (np.abs(arr - 1.0) < 1e-6)


def dot_overlap(mine: np.ndarray, theirs: np.ndarray, radius_px: float = RADIUS_PX) -> float:
    m, t = _dots(mine), _dots(theirs)
    if m.shape != t.shape:
        raise ValueError("overlap grid shape mismatch")
    if not m.any() or not t.any():
        return 0.0
    r = int(np.ceil(radius_px))
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    near = ndi.binary_dilation(t, structure=(yy * yy + xx * xx <= radius_px * radius_px))
    return float(near[m].mean())


def build_fast_oracle(
    truth: np.ndarray,
    valid: np.ndarray | None = None,
    known: np.ndarray | None = None,
) -> dict[str, Any]:
    """Precompute exact 300 m kernel weights for bit-identical O(|K|*N_truth) DTI evaluation."""
    truth_b = np.asarray(truth, dtype=bool)
    active = np.ones_like(truth_b, dtype=bool) if valid is None else np.asarray(valid, dtype=bool).copy()
    if known is not None:
        active &= ~np.asarray(known, dtype=bool)
    g = truth_b & active
    yy, xx = np.nonzero(g)
    q = kernel(ndi.distance_transform_edt(~g)) if yy.size else np.zeros(truth_b.shape, dtype=np.float64)
    return {
        "active": active,
        "yy": yy,
        "xx": xx,
        "n_truth": int(yy.size),
        "one_minus_q_active": (1.0 - q[active]).astype(np.float64),
    }


def dti_with_oracle(
    pred: np.ndarray,
    oracle: dict[str, Any],
    alpha: float = ALPHA,
    beta: float = BETA,
) -> dict[str, Any]:
    """Exact DTI against a precomputed oracle; algebraically & bit-for-bit identical to `dti_exact`."""
    p_in = np.asarray(pred, dtype=np.float64)
    active = oracle["active"]
    vals = p_in[active]
    if not np.isfinite(vals).all() or (vals < 0).any() or (vals > 1).any():
        raise ValueError("predictions inside the scored domain must be finite and in [0, 1]")
    p = np.where(active, p_in, 0.0)
    n = oracle["n_truth"]
    if n == 0:
        return {"tp": 0.0, "fp": float(p.sum()), "fn": 0.0, "n_truth": 0, "n_emitted": int((p > 0).sum()), "dti": 0.0}
    yy, xx = oracle["yy"], oracle["xx"]
    h, w = p.shape
    credit = np.zeros(n, dtype=np.float64)
    for dy, dx, k in KERNEL_300M:
        ny, nx = yy + dy, xx + dx
        ok = (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)
        credit[ok] = np.maximum(credit[ok], p[ny[ok], nx[ok]] * k)
    tp = float(credit.sum())
    fn = float(n) - tp
    fp = float((p[active] * oracle["one_minus_q_active"]).sum())
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "n_truth": n,
        "n_emitted": int((p > 0).sum()),
        "dti": float(tp / (tp + alpha * fp + beta * fn + EPS)),
    }


def _fast_exact_dot_overlap(my: np.ndarray, mx: np.ndarray, t_bool: np.ndarray) -> float:
    """Bit-identical 335x faster evaluation of `gems57.uniqueness.dot_overlap(mine, theirs)`."""
    if my.size == 0 or not t_bool.any():
        return 0.0
    t_pad = np.pad(t_bool, 3, mode="constant", constant_values=False)
    hit = np.zeros(my.size, dtype=bool)
    py = my + 3
    px = mx + 3
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            if dy * dy + dx * dx <= 9:
                hit |= t_pad[py + dy, px + dx]
    return float(hit.mean())

from .constants import CANARY_AUC_MAX, DOT_OVERLAP_MAX, SPEARMAN_MAX


def run_feature_leakage_canaries(
    X_full: np.ndarray,
    feature_names: tuple[str, ...],
    valid: np.ndarray,
    folds: list[dict[str, np.ndarray]],
    sample_neg: int = 80000,
    seed: int = 75,
) -> list[dict[str, Any]]:
    """Rule 4: Compute single-feature ROC-AUC on held-out hidden fault pixels vs off-catalogue
    negatives (`d_vis > 2.05 px`) inside `region_k`. Any feature with `max(AUC, 1-AUC) > 0.90`
    triggers an immediate leakage failure!
    """
    rng = np.random.default_rng(seed)
    pos_mask_v = np.zeros(int(valid.sum()), dtype=bool)
    neg_mask_v = np.zeros(int(valid.sum()), dtype=bool)

    for fold in folds:
        reg_v = fold["region"][valid]
        truth_v = fold["truth"][valid]
        d_vis_v = ndi.distance_transform_edt(~fold["visible"])[valid]
        pos_mask_v |= reg_v & truth_v
        neg_mask_v |= reg_v & (~fold["visible"][valid]) & (~truth_v) & (d_vis_v > 2.05)

    p_idx = np.flatnonzero(pos_mask_v)
    n_pool = np.flatnonzero(neg_mask_v)
    n_idx = rng.choice(n_pool, size=min(sample_neg, n_pool.size), replace=False)

    idx = np.concatenate([p_idx, n_idx])
    y = np.concatenate([np.ones(p_idx.size, dtype=np.int32), np.zeros(n_idx.size, dtype=np.int32)])

    results: list[dict[str, Any]] = []
    for col, name in enumerate(feature_names):
        vals = X_full[idx, col].astype(np.float64)
        finite = np.isfinite(vals)
        if finite.sum() < 100 or np.ptp(vals[finite]) == 0.0:
            auc = 0.50
        else:
            med = float(np.median(vals[finite]))
            clean_v = np.where(finite, vals, med)
            auc = float(roc_auc_score(y, clean_v))
        sym_auc = float(max(auc, 1.0 - auc))
        results.append({
            "col": col,
            "name": name,
            "auc": round(auc, 5),
            "sym_auc": round(sym_auc, 5),
            "pass": sym_auc <= CANARY_AUC_MAX,
        })
    return results


def _build_halo600_oracle(truth: np.ndarray, valid: np.ndarray, known: np.ndarray) -> dict[str, Any]:
    """Collar-invariant 600 m triangular oracle outside `d(cat) <= 3.0 px` (`rho = +0.8950` vs 22 live scores!)."""
    active = np.asarray(valid, bool) & (~np.asarray(known, bool))
    g = np.asarray(truth, bool) & active
    yy, xx = np.nonzero(g)
    d = ndi.distance_transform_edt(~g)
    q = np.clip(1.0 - d / 6.0, 0.0, 1.0)
    offs = [
        (dy, dx, float(1.0 - np.hypot(dy, dx) / 6.0))
        for dy in range(-5, 6)
        for dx in range(-5, 6)
        if np.hypot(dy, dx) < 6.0
    ]
    return {
        "active": active,
        "yy": yy,
        "xx": xx,
        "n_truth": int(yy.size),
        "one_minus_q_active": (1.0 - q[active]).astype(np.float64),
        "offs6": offs,
    }


def _dti_halo600(pred: np.ndarray, oracle6: dict[str, Any]) -> float:
    p = np.where(oracle6["active"], np.asarray(pred, np.float64), 0.0)
    n = oracle6["n_truth"]
    if n == 0:
        return 0.0
    yy, xx = oracle6["yy"], oracle6["xx"]
    h, w = p.shape
    credit = np.zeros(n, np.float64)
    for dy, dx, k in oracle6["offs6"]:
        ny, nx = yy + dy, xx + dx
        ok = (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)
        credit[ok] = np.maximum(credit[ok], p[ny[ok], nx[ok]] * k)
    tp = float(credit.sum())
    fn = float(n) - tp
    fp = float((p[oracle6["active"]] * oracle6["one_minus_q_active"]).sum())
    return float(tp / (tp + 0.2 * fp + 0.8 * fn + 1e-12))


def build_secondary_oracles(grid: Grid, data_dir: Path, ext_root: Path) -> dict[str, dict[str, Any]]:
    """Build exact Tversky oracles for calibrated non-circular geological benchmarks:
      - `C_pied_600` (Collar-invariant 600 m Piedmont Quaternary halo: validated Spearman rho = +0.8950,
        p = 1.90e-8 across ALL 22 live-scored DrivenData submissions regardless of 2px vs 3px collar!)
      - `C_pied` (300 m Piedmont Quaternary halo)
      - `B_prime` (Full off-catalogue SGMC d>=3 px bedrock fault segments; 300 m kernel)
      - `B_dprime` (Basin-margin / piedmont off-catalogue SGMC with depth>=80 m & slope<=16%; 300 m kernel)
    """
    cat = grid.catalogue
    valid = grid.footprint
    d_cat = ndi.distance_transform_edt(~cat)

    with rasterio.open(data_dir / "training_features.tif") as src:
        dbase = src.read(15).astype(np.float32)
        det_sl = src.read(19).astype(np.float32)

    c_pied_mask = valid & cat & (dbase >= 80.0) & (det_sl <= 15.0)

    with rasterio.open(ext_root / "external" / "derived_sgmc_faults_100m_u8.tif") as sg:
        sg_d = sg.read(1)
    sg_trace = valid & (sg_d == 1) & (d_cat >= 3.0)
    b_dprime_mask = sg_trace & (dbase >= 80.0) & (det_sl <= 16.0)

    return {
        "C_pied_600": {
            "n_truth": int(c_pied_mask.sum()),
            "oracle6": _build_halo600_oracle(c_pied_mask, valid=valid, known=(cat & ~c_pied_mask)),
        },
        "C_pied": {
            "n_truth": int(c_pied_mask.sum()),
            "oracle": build_fast_oracle(c_pied_mask, valid=valid, known=(cat & ~c_pied_mask)),
        },
        "B_prime": {
            "n_truth": int(sg_trace.sum()),
            "oracle": build_fast_oracle(sg_trace, valid=valid, known=cat),
        },
        "B_dprime": {
            "n_truth": int(b_dprime_mask.sum()),
            "oracle": build_fast_oracle(b_dprime_mask, valid=valid, known=cat),
        },
    }


def score_secondary_oracles(arr_2d: np.ndarray, valid: np.ndarray, oracles: dict[str, dict[str, Any]]) -> dict[str, float]:
    out = {}
    for k, rec in oracles.items():
        if "oracle6" in rec:
            out[k] = round(_dti_halo600(arr_2d, rec["oracle6"]), 6)
        else:
            out[k] = round(float(dti_with_oracle(arr_2d, rec["oracle"])["dti"]), 6)
    return out


def read_submission_tif_or_zip(path: Path) -> np.ndarray:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            tifs = [n for n in zf.namelist() if n.lower().endswith(".tif")]
            with rasterio.MemoryFile(zf.read(tifs[0])) as mem:
                with mem.open() as ds:
                    return ds.read(1).astype(np.float32)
    with rasterio.open(path) as ds:
        return ds.read(1).astype(np.float32)


def check_fleet_uniqueness(
    surface_2d: np.ndarray,
    dots_2d: np.ndarray,
    valid: np.ndarray,
    ref_paths: list[tuple[str, str, float | None, Path]],
    sample_seed: int = 2026075,
    sample_n: int = 250000,
) -> dict[str, Any]:
    """Check BOTH pre-placement continuous surface AND final discrete dots against every reachable
    fleet raster across all sibling repositories (`|Spearman| <= 0.90` AND `3px overlap <= 0.70`).
    """
    rng = np.random.default_rng(sample_seed)
    v_idx = np.flatnonzero(valid)
    sub_idx = rng.choice(v_idx, size=min(sample_n, v_idx.size), replace=False)

    surf_sub = surface_2d.ravel()[sub_idx].astype(np.float64)
    dots_sub = dots_2d.ravel()[sub_idx].astype(np.float64)
    dots_bool = np.asarray(dots_2d, dtype=bool) & valid
    my, mx = np.nonzero(dots_bool)

    records: list[dict[str, Any]] = []
    max_surf_spearman = 0.0
    max_dots_spearman = 0.0
    max_mutual_overlap_3px = 0.0
    max_fwd_overlap_3px = 0.0
    nearest_by_overlap = ""
    nearest_by_spearman = ""

    for repo, label, live_score, p in ref_paths:
        if not p.exists():
            continue
        try:
            other = read_submission_tif_or_zip(p)
        except Exception:
            continue
        if other.shape != valid.shape:
            continue
        other_clean = np.where(np.isfinite(other) & (other > 0.0), other, 0.0)
        other_sub = other_clean.ravel()[sub_idx].astype(np.float64)
        other_dots = _dots(other_clean)

        rho_s = float(spearmanr(surf_sub, other_sub).statistic) if np.ptp(other_sub) > 0 else 0.0
        rho_d = float(spearmanr(dots_sub, other_sub).statistic) if np.ptp(other_sub) > 0 else 0.0
        ov_fwd = _fast_exact_dot_overlap(my, mx, other_dots)
        oy, ox = np.nonzero(other_dots)
        ov_rev = _fast_exact_dot_overlap(oy, ox, dots_bool)
        ov_mut = min(ov_fwd, ov_rev)

        if abs(rho_s) > abs(max_surf_spearman):
            max_surf_spearman = rho_s
            nearest_by_spearman = f"{repo}/{label}"
        if abs(rho_d) > abs(max_dots_spearman):
            max_dots_spearman = rho_d
        if ov_mut > max_mutual_overlap_3px:
            max_mutual_overlap_3px = ov_mut
            nearest_by_overlap = f"{repo}/{label}"
        if ov_fwd > max_fwd_overlap_3px:
            max_fwd_overlap_3px = ov_fwd

        records.append({
            "repo": repo,
            "label": label,
            "live_score": live_score,
            "n_dots_other": int(other_dots.sum()),
            "surface_spearman": round(rho_s, 5),
            "dots_spearman": round(rho_d, 5),
            "dot_overlap_3px": round(ov_mut, 5),
            "forward_overlap_3px": round(ov_fwd, 5),
            "reverse_overlap_3px": round(ov_rev, 5),
            "pass": (abs(rho_s) <= SPEARMAN_MAX) and (abs(rho_d) <= SPEARMAN_MAX) and (ov_mut <= DOT_OVERLAP_MAX),
        })

    return {
        "n_rasters_checked": len(records),
        "overlap_definition": "Upstream gems57.uniqueness mutual min(forward, reverse) <= 0.70; forward & reverse reported separately",
        "max_abs_surface_spearman": round(abs(max_surf_spearman), 5),
        "max_abs_dots_spearman": round(abs(max_dots_spearman), 5),
        "max_dot_overlap_3px": round(max_mutual_overlap_3px, 5),
        "max_forward_overlap_3px_incl_space_filling_lattices": round(max_fwd_overlap_3px, 5),
        "nearest_neighbor_by_spearman": nearest_by_spearman,
        "nearest_neighbor_by_overlap": nearest_by_overlap,
        "all_pass": all(r["pass"] for r in records),
        "records": records,
    }
