"""H75-3: 1D Ridge-Skeleton Topological Concentration + Exact 300 m Submodular Tversky Packing.

THEOREM (Elimination of 3.13x 2D-Blob Submodular Bias — IR-75-BLOB-BIAS):
  Under the competition's 300 m triangular kernel K(dy, dx) = max(0, 1 - hypot(dy, dx)/3):
    - Sum of K over a 2D 5x5 uniform blob (25 cells)      = 9.380298
    - Sum of K over a 1D 1-px fault trace (5 cells along y) = 3.000000
  Therefore, running 2D submodular coverage directly on un-thinned posterior probability
  rasters awards a 9.380298 / 3.000000 = 3.1268x spurious gain multiplier to wide diffuse
  hillslopes over razor-sharp 1-pixel piedmont fault scarps!

  Concentrating posterior mass onto the local multi-azimuth transverse ridge crest
  (directional non-maximum emphasis along normal vector n_perp across +/- 1..2 px)
  restores exact 1D line geometry matching ground-truth rasterized faults while preserving
  calibrated multi-physics ranking across the entire fault network.
"""
from __future__ import annotations

import heapq
import numpy as np
from scipy import ndimage as ndi
from scipy.stats import rankdata

from .constants import KERNEL_300M


def rank01(values: np.ndarray) -> np.ndarray:
    v = np.asarray(values, dtype=np.float64)
    if v.size == 0:
        return np.empty(0, dtype=np.float32)
    if np.ptp(v) == 0.0:
        return np.full(v.size, 0.5, dtype=np.float32)
    return (rankdata(v, method="average") / float(v.size)).astype(np.float32)


def exp_tail(values: np.ndarray) -> np.ndarray:
    """Exact Gumbel/Exponential survival transform `-log(1 - rank01(v))` ~ Exp(1) on (0, 15.5).

    Simultaneously provides:
      1. Exact marginal scale equalization across classifiers trained under different class
         imbalance priors (`p_phys54` vs `p_s2_phys` vs `p_loco59`), AND
      2. Constant unit derivative per upper-tail decade (`99% -> 4.61`, `99.9% -> 6.91`,
         `99.99% -> 9.21`), preserving full transverse ridge second-differences in the top 1%!
    """
    r = rank01(values).astype(np.float64)
    return (-np.log(np.maximum(1.0 - r, 0.5 / max(r.size, 1)))).astype(np.float32)


def directional_ridge_concentration(surface_2d: np.ndarray, valid_2d: np.ndarray) -> np.ndarray:
    """Concentrate exponential-tail surface (`Exp(1)`) onto 1D fault centerlines across 8 normals."""
    u = np.where(valid_2d & np.isfinite(surface_2d), surface_2d, 0.0).astype(np.float32)
    sm = ndi.gaussian_filter(u, sigma=0.75)
    h, w = sm.shape
    pad = 3
    p = np.pad(sm, pad, mode="edge")

    normals_d2 = [
        (0, 2),
        (1, 2),
        (2, 2),
        (2, 1),
        (2, 0),
        (2, -1),
        (2, -2),
        (1, -2),
    ]
    max_prom = np.zeros((h, w), dtype=np.float32)
    is_local_crest = np.zeros((h, w), dtype=bool)
    center = p[pad : pad + h, pad : pad + w]

    for dy, dx in normals_d2:
        plus2 = p[pad + dy : pad + dy + h, pad + dx : pad + dx + w]
        minus2 = p[pad - dy : pad - dy + h, pad - dx : pad - dx + w]
        prom = center - 0.5 * (plus2 + minus2)
        max_prom = np.maximum(max_prom, prom)

        dy1 = int(np.sign(dy)) if abs(dy) >= abs(dx) else int(np.rint(dy / 2.0))
        dx1 = int(np.sign(dx)) if abs(dx) >= abs(dy) else int(np.rint(dx / 2.0))
        if dy1 != 0 or dx1 != 0:
            p1 = p[pad + dy1 : pad + dy1 + h, pad + dx1 : pad + dx1 + w]
            m1 = p[pad - dy1 : pad - dy1 + h, pad - dx1 : pad - dx1 + w]
            is_local_crest |= (center >= p1 - 1e-6) & (center >= m1 - 1e-6) & (prom > 0.0)

    prom_pos = np.clip(max_prom, 0.0, None)
    p99 = float(np.percentile(prom_pos[valid_2d], 99.5)) + 1e-6
    prom_norm = np.clip(prom_pos / p99, 0.0, 1.5)
    crest_factor = np.where(is_local_crest, 1.0, 0.40).astype(np.float32)
    concentrated = sm * crest_factor * (0.55 + 0.45 * prom_norm)
    return np.where(valid_2d, concentrated, 0.0).astype(np.float32)


def submodular_pack_300m(
    surface_2d: np.ndarray,
    allowed_2d: np.ndarray,
    target_n: int,
    support_quantile: float = 0.90,
    gamma: float = 2.0,
    min_spacing_px: float = 0.0,
    max_candidates: int = 450000,
) -> tuple[np.ndarray, int]:
    """Exact 300 m triangular-kernel lazy-greedy submodular coverage packer (Minoux 1978),
    with optional hard minimum inter-dot spacing `min_spacing_px` to eliminate redundant clustering.
    """
    h, w = surface_2d.shape
    allow = np.asarray(allowed_2d, dtype=bool)
    vals = surface_2d[allow]
    if vals.size < target_n:
        raise ValueError(f"Allowed support ({vals.size}) < target_n ({target_n})")

    ranks = rank01(vals)
    pos = np.clip((ranks - support_quantile) / max(1.0 - support_quantile, 1e-6), 0.0, 1.0)
    weights_allow = (pos ** gamma + 1e-5 * ranks).astype(np.float32)

    pad = 3
    hp, wp = h + 2 * pad, w + 2 * pad
    w_pad = np.zeros((hp, wp), dtype=np.float32)
    ay, ax = np.nonzero(allow)
    w_pad[ay + pad, ax + pad] = weights_allow

    g0 = np.zeros((h, w), dtype=np.float32)
    for dy, dx, k in KERNEL_300M:
        g0 += k * w_pad[pad + dy : pad + dy + h, pad + dx : pad + dx + w]

    cand_scores = g0[allow]
    if cand_scores.size > max_candidates:
        part = np.argpartition(cand_scores, -max_candidates)[-max_candidates:]
        part = part[np.argsort(cand_scores[part], kind="mergesort")[::-1]]
    else:
        part = np.argsort(cand_scores, kind="mergesort")[::-1]

    cy = (ay[part] + pad).astype(np.int32)
    cx = (ax[part] + pad).astype(np.int32)
    flat_idx = cy * wp + cx
    init_gains = cand_scores[part]

    heap = [(-float(init_gains[i]), int(flat_idx[i])) for i in range(flat_idx.size)]
    heapq.heapify(heap)

    w_list = w_pad.ravel().tolist()
    cov_list = [0.0] * (hp * wp)
    blocked = bytearray(hp * wp)
    off_k = tuple((dy * wp + dx, k) for dy, dx, k in KERNEL_300M)

    block_offs: tuple[int, ...] = ()
    if min_spacing_px > 0.0:
        r_b = int(np.floor(min_spacing_px))
        block_offs = tuple(
            dy * wp + dx
            for dy in range(-r_b, r_b + 1)
            for dx in range(-r_b, r_b + 1)
            if np.hypot(dy, dx) < min_spacing_px - 1e-6
        )

    dots = np.zeros((h, w), dtype=bool)
    picked = 0
    pop = heapq.heappop
    push = heapq.heappush

    while picked < target_n and heap:
        neg_ub, idx = pop(heap)
        if blocked[idx]:
            continue
        gain = 0.0
        for off, k in off_k:
            j = idx + off
            wj = w_list[j]
            if wj > 0.0:
                rem = k - cov_list[j]
                if rem > 0.0:
                    gain += wj * rem
        if not heap or gain >= -heap[0][0] - 1e-12:
            y = idx // wp - pad
            x = idx % wp - pad
            if not dots[y, x]:
                dots[y, x] = True
                for off, k in off_k:
                    j = idx + off
                    if k > cov_list[j]:
                        cov_list[j] = k
                for boff in block_offs:
                    blocked[idx + boff] = 1
                picked += 1
        elif gain > 0.0:
            push(heap, (-gain, idx))

    return dots, picked
