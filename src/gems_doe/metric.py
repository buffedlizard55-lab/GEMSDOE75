"""Distance-weighted Tversky Index (DTI) -- the official GEMS Prize metric.

This is a from-scratch, line-by-line implementation of the metric exactly as
published by the organizer on the competition "Problem description" page:

    https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
    (section "Performance metric", fetched and verified 2026-10-21)

Published definitions (verbatim, alpha=0.2, beta=0.8 for this competition):

    TI(a,b) = sum p*g / ( sum p*g + a*sum p*(1-g) + b*sum (1-p)*g )

    k(d) = max(1 - d/R, 0)                      # triangular kernel, R = 300 m

    TP_w = sum_{g in G} max_{x: d(x,g)<=R} p(x) * k(d(x,g))
    FP_w = sum_{x: p(x)>0} p(x) * [1 - max_{g in G} k(d(x,g))]
    FN_w = sum_{g in G} [1 - max_{x: d(x,g)<=R} p(x) * k(d(x,g))]

    DTI(a,b) = TP_w / (TP_w + a*FP_w + b*FN_w + eps)

where G is the set of ground-truth positive (fault) pixels.

Worked example copied verbatim from the organizer's page (ORGANIZER-CONFIRMED,
not re-derived from the source image, since the example raster is a diagram,
not a downloadable array):

    TP_w = 3.00, FP_w = 1.89, FN_w = 2.00  =>  DTI(0.2, 0.8) = 0.60

This module is independently verified against that published arithmetic
identity (see tests/test_metric.py::test_worked_example_arithmetic) and
against hand-computed synthetic rasters (tests/test_metric.py) since the
organizer did not publish the raw pixel array behind the diagram.
"""

from __future__ import annotations

import numpy as np

# Competition-fixed parameters (page 967, "Performance metric")
ALPHA = 0.2
BETA = 0.8
KERNEL_RANGE_M = 300.0


def triangular_kernel(distance_m: np.ndarray, kernel_range_m: float = KERNEL_RANGE_M) -> np.ndarray:
    """k(d) = max(1 - d/R, 0), vectorized."""
    return np.clip(1.0 - distance_m / kernel_range_m, 0.0, None)


def _weighted_dilation(p: np.ndarray, pixel_size_m: float, kernel_range_m: float) -> np.ndarray:
    """Grayscale dilation of p(x) by the structuring function k(d(x,y)).

    Returns V(y) = max_{x: d(x,y)<=R} p(x) * k(d(x,y)) for every pixel y.
    Implemented as an explicit max-over-offsets scan because the kernel
    footprint at 100 m resolution / 300 m range is only a 7x7 disk (radius 3
    px) -- small enough to be exact and fast without approximation.
    """
    radius_px = int(np.ceil(kernel_range_m / pixel_size_m))
    h, w = p.shape
    v = np.zeros_like(p, dtype=np.float64)
    for dy in range(-radius_px, radius_px + 1):
        for dx in range(-radius_px, radius_px + 1):
            d = np.hypot(dy * pixel_size_m, dx * pixel_size_m)
            if d > kernel_range_m:
                continue
            k = triangular_kernel(np.array(d))
            if k <= 0:
                continue
            # shift p by (dy, dx): value contributed to pixel y from pixel x=y-(dy,dx)
            shifted = np.zeros_like(p, dtype=np.float64)
            src_y0, src_y1 = max(0, dy), h + min(0, dy)
            src_x0, src_x1 = max(0, dx), w + min(0, dx)
            dst_y0, dst_y1 = max(0, -dy), h + min(0, -dy)
            dst_x0, dst_x1 = max(0, -dx), w + min(0, -dx)
            shifted[dst_y0:dst_y1, dst_x0:dst_x1] = p[src_y0:src_y1, src_x0:src_x1]
            np.maximum(v, shifted * k, out=v)
    return v


def _nearest_positive_kernel(g: np.ndarray, pixel_size_m: float, kernel_range_m: float) -> np.ndarray:
    """K(x) = max_{g in G} k(d(x,g)) for every pixel x, via an exact distance transform."""
    from scipy.ndimage import distance_transform_edt

    if not g.any():
        return np.zeros_like(g, dtype=np.float64)
    inverted = g == 0
    dist_px = distance_transform_edt(inverted)
    dist_m = dist_px * pixel_size_m
    return triangular_kernel(dist_m, kernel_range_m)


def distance_weighted_tversky(
    p: np.ndarray,
    g: np.ndarray,
    pixel_size_m: float,
    alpha: float = ALPHA,
    beta: float = BETA,
    kernel_range_m: float = KERNEL_RANGE_M,
    eps: float = 1e-12,
    valid_mask: np.ndarray | None = None,
) -> dict:
    """Compute the distance-weighted Tversky Index exactly as published.

    Parameters
    ----------
    p : float array in [0, 1], predicted probability of fault presence.
    g : binary array, 1 where a ground-truth fault pixel exists.
    pixel_size_m : grid spacing in metres (100 m for the competition grid).
    valid_mask : optional boolean array; pixels outside are excluded from
        both p and g before scoring (e.g. to pool several holdout folds, or
        to score only inside the raster's footprint).

    Returns
    -------
    dict with TP_w, FP_w, FN_w, DTI (plus the inputs' shapes for an audit
    trail).
    """
    p = np.asarray(p, dtype=np.float64)
    g = np.asarray(g)
    if p.shape != g.shape:
        raise ValueError(f"p.shape {p.shape} != g.shape {g.shape}")
    if np.isnan(p).any():
        raise ValueError("p contains NaN inside the scoring domain; mask it out via valid_mask first")
    if (p < 0).any() or (p > 1).any():
        raise ValueError("p has values outside [0, 1]; metric is undefined there")

    if valid_mask is not None:
        p = np.where(valid_mask, p, 0.0)
        g = np.where(valid_mask, g, 0)

    g_bin = (g > 0).astype(np.float64)

    v = _weighted_dilation(p, pixel_size_m, kernel_range_m)
    tp_w = float(np.sum(v * g_bin))
    fn_w = float(np.sum((1.0 - v) * g_bin))

    k_nearest = _nearest_positive_kernel(g_bin, pixel_size_m, kernel_range_m)
    fp_w = float(np.sum(p * (1.0 - k_nearest)))

    dti = tp_w / (tp_w + alpha * fp_w + beta * fn_w + eps)

    return {
        "TP_w": tp_w,
        "FP_w": fp_w,
        "FN_w": fn_w,
        "DTI": dti,
        "alpha": alpha,
        "beta": beta,
        "kernel_range_m": kernel_range_m,
        "pixel_size_m": pixel_size_m,
        "n_ground_truth_px": int(g_bin.sum()),
        "n_predicted_px": int((p > 0).sum()),
    }


def organizer_worked_example_dti(alpha: float = ALPHA, beta: float = BETA, eps: float = 1e-12) -> float:
    """Reproduce the organizer's published worked-example arithmetic exactly.

    Source (ORGANIZER-CONFIRMED, page 967, "Scoring example"):
        TP_w = 3.00, FP_w = 1.89, FN_w = 2.00  ->  DTI(0.2, 0.8) = 0.60
    """
    tp_w, fp_w, fn_w = 3.00, 1.89, 2.00
    return tp_w / (tp_w + alpha * fp_w + beta * fn_w + eps)
