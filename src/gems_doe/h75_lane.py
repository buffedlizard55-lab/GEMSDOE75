"""GEMSDOE75 (Lane H75-1): Strike-Projected Fault-Tip & Relay-Bridge Kinematic
Transfer + 4-Domain Multi-Physics LOQO Corroboration with Lahontan Mimic Gate.

All operations stream sanitized per-band arrays from ``.cache/bands/`` so peak
RSS remains below 800 MB on 3.8 GiB sandboxes.  Catalogue-derived features are
computed strictly from the fold-visible fault mask ``visible_faults`` on holdout
folds and from ``existing_faults.tif`` only for the final full-grid prediction.
"""
from __future__ import annotations

import csv
import gc
import types
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[2]
BANDS_DIR = ROOT / ".cache" / "bands"
EXT_DIR = ROOT / ".cache" / "gems_data" / "external"

SUBMISSION_STEM = "gemsdoe75-h75-strike-corrob-b2-d285-k38200-20261021-zero"
SUBMISSION_FILENAME = f"{SUBMISSION_STEM}.tif"
SUBMISSION_NOTE = (
    "GEMSDOE75 H75-1 E3: 4-dom LOQO + 12-az strike tip/relay transfer, "
    "Lahontan mimic gate, B=2px collar, d=2.85 Poisson 38200 dots [0,1]."
)


def load_z(name: str, foot: np.ndarray, bands_dir: Path = BANDS_DIR, log_transform: bool = False) -> np.ndarray:
    """Load one sanitized band, median-impute inside footprint, and standardize."""
    arr = np.load(bands_dir / f"{name}.npy").astype(np.float32)
    if log_transform:
        arr = np.where(
            np.isfinite(arr) & (arr > 0),
            np.log1p(arr),
            np.where(np.isfinite(arr), 0.0, np.nan),
        )
    valid = foot & np.isfinite(arr)
    med = float(np.median(arr[valid])) if valid.any() else 0.0
    out = np.where(valid, arr, med)
    mu = float(out[foot].mean())
    sd = float(out[foot].std()) + 1e-6
    z = np.clip((out - mu) / sd, -8.0, 8.0).astype(np.float32)
    z[~foot] = 0.0
    return z


def robust_01(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Map an array to [0, 1] inside the study footprint using [p10, p99.2] scaling."""
    v = arr[foot]
    p10, p99 = np.percentile(v, [10, 99.2])
    out = np.clip((arr - p10) / (p99 - p10 + 1e-6), 0.0, 1.0).astype(np.float32)
    out[~foot] = 0.0
    return out


def grad_mag(arr: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Compute Gaussian-smoothed gradient magnitude."""
    s = ndi.gaussian_filter(arr, sigma=sigma) if sigma > 0 else arr
    gy, gx = np.gradient(s)
    return np.hypot(gy, gx).astype(np.float32)


def ridge_crest(arr: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Positive local ridge-crest prominence above a 7x7 neighborhood mean."""
    s = ndi.gaussian_filter(arr, sigma=sigma)
    loc_mean = ndi.uniform_filter(s, size=7)
    return np.maximum(0.0, s - loc_mean).astype(np.float32)


def compute_strike_kinematics(
    vis_mask: np.ndarray,
    foot_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute 12-azimuth (15 deg) strike-projected tip, relay-bridge, and ramp corridor.

    Derived strictly from ``vis_mask`` so holdout evaluation has zero access to
    withheld fault segments or their 3-pixel buffers.
    """
    v_f = vis_mask.astype(np.float32)
    g_s = ndi.gaussian_filter(v_f, sigma=1.5)
    gy, gx = np.gradient(g_s)
    jxx = ndi.gaussian_filter(gx * gx, sigma=2.5)
    jyy = ndi.gaussian_filter(gy * gy, sigma=2.5)
    jxy = ndi.gaussian_filter(gx * gy, sigma=2.5)
    theta_grad = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    theta_strike = (theta_grad + 0.5 * np.pi) % np.pi
    del g_s, gy, gx, jxx, jyy, jxy

    n_bins = 12
    bin_idx = np.floor(theta_strike / np.pi * n_bins).astype(np.int32) % n_bins
    del theta_grad, theta_strike
    tip_acc = np.zeros_like(v_f, dtype=np.float32)
    bridge_acc = np.zeros_like(v_f, dtype=np.float32)
    radii = [3, 4, 5, 7, 9, 12, 16, 21, 27]
    weights = [1.0, 0.96, 0.90, 0.80, 0.68, 0.55, 0.42, 0.30, 0.20]

    for b in range(n_bins):
        ang = (b + 0.5) * (np.pi / n_bins)
        dy_u, dx_u = np.sin(ang), np.cos(ang)
        vb = ndi.gaussian_filter((vis_mask & (bin_idx == b)).astype(np.float32), sigma=1.1)
        if vb.max() < 1e-4:
            continue
        f_plus = np.zeros_like(v_f)
        f_minus = np.zeros_like(v_f)
        for r, w_r in zip(radii, weights):
            sy, sx = int(round(r * dy_u)), int(round(r * dx_u))
            f_plus += w_r * np.roll(vb, shift=(sy, sx), axis=(0, 1))
            f_minus += w_r * np.roll(vb, shift=(-sy, -sx), axis=(0, 1))
        tip_acc = np.maximum(tip_acc, f_plus + f_minus)
        bridge_acc = np.maximum(bridge_acc, np.sqrt(f_plus * f_minus))
        del f_plus, f_minus, vb

    d_vis = ndi.distance_transform_edt(~vis_mask).astype(np.float32)
    ramp = 1.0 - np.exp(-np.maximum(0.0, d_vis - 2.0) / 1.8)
    decay = (
        0.68 * np.exp(-np.maximum(0.0, d_vis - 3.5) / 6.5)
        + 0.32 * np.exp(-np.maximum(0.0, d_vis - 3.5) / 18.0)
    )
    corridor = (ramp * decay) * foot_mask
    return (
        robust_01(tip_acc * ramp, foot_mask),
        robust_01(bridge_acc * ramp, foot_mask),
        robust_01(corridor, foot_mask),
    )


def poisson_disk_pack(
    score: np.ndarray,
    valid_mask: np.ndarray,
    min_dist_px: float = 2.85,
    max_dots: int = 38200,
) -> np.ndarray:
    """Priority-ordered Poisson-disk point-process decoder."""
    h, w = score.shape
    cand_yx = np.argwhere(valid_mask & (score > 0))
    if cand_yx.shape[0] == 0:
        return np.zeros((h, w), dtype=bool)
    vals = score[cand_yx[:, 0], cand_yx[:, 1]]
    if vals.size > max_dots * 14:
        thresh = np.partition(vals, -max_dots * 14)[-max_dots * 14]
        keep = vals >= thresh
        cand_yx = cand_yx[keep]
        vals = vals[keep]
    order = np.argsort(-vals, kind="mergesort")
    cand_yx = cand_yx[order]

    r_int = int(np.ceil(min_dist_px))
    dy, dx = np.mgrid[-r_int : r_int + 1, -r_int : r_int + 1]
    disk_offsets = np.argwhere((dy * dy + dx * dx) < (min_dist_px * min_dist_px)) - r_int
    ody = disk_offsets[:, 0]
    odx = disk_offsets[:, 1]

    blocked = np.zeros((h + 2 * r_int, w + 2 * r_int), dtype=bool)
    out = np.zeros((h, w), dtype=bool)
    count = 0
    for idx in range(cand_yx.shape[0]):
        ry = int(cand_yx[idx, 0])
        cx = int(cand_yx[idx, 1])
        pry = ry + r_int
        pcx = cx + r_int
        if not blocked[pry, pcx]:
            out[ry, cx] = True
            blocked[pry + ody, pcx + odx] = True
            count += 1
            if count >= max_dots:
                break
    return out


def build_e3_surface(vis_mask: np.ndarray, bands_dir: Path = BANDS_DIR) -> np.ndarray:
    """Build the H75-E3 surface strictly from ``vis_mask`` and cached E1/E2 fields."""
    foot = np.load(bands_dir / "_footprint.npy")
    s_e1 = np.load(bands_dir / "surf_E1.npy")
    s_e2 = np.load(bands_dir / "surf_E2.npy")
    g_corrob = np.load(bands_dir / "dom_G_corrob.npy")
    phys_combo = robust_01(0.75 * s_e2 + 0.25 * s_e1, foot)
    phys_crest = robust_01(ridge_crest(phys_combo, sigma=1.0), foot)
    far_score = robust_01(
        (0.56 * s_e2 + 0.20 * s_e1 + 0.24 * phys_crest) * (0.48 + 0.52 * g_corrob),
        foot,
    )
    tip, br, corr = compute_strike_kinematics(vis_mask, foot)
    kin = robust_01(0.46 * tip + 0.36 * br + 0.18 * corr, foot)
    near = robust_01(
        kin * (0.28 + 0.44 * phys_combo + 0.28 * phys_crest) * (0.50 + 0.50 * g_corrob),
        foot,
    )
    return robust_01(
        0.34 * near + 0.58 * far_score + 0.08 * np.sqrt(near * far_score),
        foot,
    )
