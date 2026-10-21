"""Spatially-blocked "hide-and-recover" holdout, per the parallel-run protocol:

    Holdout = hide-and-recover: withhold whole fault segments with a buffer,
    derive every catalogue-based feature only from the visible faults, mask
    visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8,
    300 m triangular kernel).

This module implements the *mechanics* of that protocol in a way that is
fully testable today with synthetic fault rasters, and will run unchanged
once the real USGS/INGENIOUS catalogue raster (existing_faults.tif /
labels.tif) is placed in data/raw/ (see scripts/download_competition_data.sh
and LIMITATIONS.md for exactly why that file is not present yet).

Design:
  1. Label connected components of the binary fault raster -> "segments".
  2. Assign each segment to one of K spatial folds (round-robin over a
     deterministic ordering, NOT random masking of individual pixels --
     masking individual pixels would leak the segment's geometry into both
     "visible" and "withheld" sets through the fault's own spatial
     autocorrelation).
  3. For each fold: the withheld segments, dilated by `buffer_px`, are
     removed from the "visible" raster (this is what any catalogue-derived
     feature must be computed from); the un-dilated withheld pixels are the
     fold's ground truth for scoring.
  4. A caller-supplied `predict_fn(visible_fault_raster) -> p` is scored with
     `distance_weighted_tversky` against the withheld truth, pooled across
     folds (pooled TP_w/FP_w/FN_w, not an average of per-fold DTI -- pooling
     is what the protocol's "score pooled DTI" line specifies).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.ndimage import binary_dilation, label

from gems_doe.metric import ALPHA, BETA, KERNEL_RANGE_M, distance_weighted_tversky


@dataclass
class Fold:
    fold_id: int
    visible_fault_raster: np.ndarray  # catalogue with this fold's segments removed (+buffer)
    withheld_truth: np.ndarray  # binary raster of exactly the withheld segments (no buffer)
    withheld_segment_ids: list


def make_spatial_folds(
    fault_raster: np.ndarray,
    n_folds: int = 4,
    buffer_px: int = 3,
    seed: int = 0,
) -> list[Fold]:
    """Split a binary fault raster into `n_folds` spatially-blocked folds by
    whole connected segment, not by pixel.
    """
    fault_bin = (fault_raster > 0).astype(np.uint8)
    structure = np.ones((3, 3), dtype=np.uint8)  # 8-connectivity for segment identity
    labeled, n_segments = label(fault_bin, structure=structure)
    if n_segments == 0:
        raise ValueError("fault_raster has no positive pixels; cannot build holdout folds")

    rng = np.random.default_rng(seed)
    segment_ids = np.arange(1, n_segments + 1)
    rng.shuffle(segment_ids)
    fold_assignment = {seg_id: int(i % n_folds) for i, seg_id in enumerate(segment_ids)}

    dilation_structure = np.ones((2 * buffer_px + 1, 2 * buffer_px + 1), dtype=np.uint8)

    folds = []
    for fold_id in range(n_folds):
        withheld_ids = [s for s, f in fold_assignment.items() if f == fold_id]
        withheld_truth = np.isin(labeled, withheld_ids).astype(np.uint8)
        withheld_buffered = binary_dilation(withheld_truth, structure=dilation_structure)
        visible = fault_bin.copy()
        visible[withheld_buffered] = 0
        folds.append(
            Fold(
                fold_id=fold_id,
                visible_fault_raster=visible,
                withheld_truth=withheld_truth,
                withheld_segment_ids=withheld_ids,
            )
        )
    return folds


def run_holdout(
    fault_raster: np.ndarray,
    predict_fn: Callable[[np.ndarray], np.ndarray],
    pixel_size_m: float,
    n_folds: int = 4,
    buffer_px: int = 3,
    seed: int = 0,
    alpha: float = ALPHA,
    beta: float = BETA,
    kernel_range_m: float = KERNEL_RANGE_M,
) -> dict:
    """Run the full hide-and-recover protocol and return a pooled score.

    `predict_fn` receives ONLY the visible (fold-masked) fault raster for
    each fold -- never the full catalogue and never the withheld truth --
    so any feature it derives is, by construction, blind to the segments it
    will be scored against. This is the mechanical guarantee against the
    leakage canary described in the parallel-run protocol.
    """
    folds = make_spatial_folds(fault_raster, n_folds=n_folds, buffer_px=buffer_px, seed=seed)

    tp_total = fp_total = fn_total = 0.0
    per_fold = []
    for fold in folds:
        p = predict_fn(fold.visible_fault_raster)
        p = np.asarray(p, dtype=np.float64)
        if p.shape != fold.withheld_truth.shape:
            raise ValueError(
                f"predict_fn returned shape {p.shape}, expected {fold.withheld_truth.shape}"
            )
        result = distance_weighted_tversky(
            p, fold.withheld_truth, pixel_size_m=pixel_size_m,
            alpha=alpha, beta=beta, kernel_range_m=kernel_range_m,
        )
        per_fold.append({"fold_id": fold.fold_id, **result})
        tp_total += result["TP_w"]
        fp_total += result["FP_w"]
        fn_total += result["FN_w"]

    pooled_dti = tp_total / (tp_total + alpha * fp_total + beta * fn_total + 1e-12)
    n_withheld = sum(int(f.withheld_truth.sum()) for f in folds)

    return {
        "pooled_DTI": pooled_dti,
        "pooled_TP_w": tp_total,
        "pooled_FP_w": fp_total,
        "pooled_FN_w": fn_total,
        "n_folds": n_folds,
        "n_withheld_positive_px": n_withheld,
        "buffer_px": buffer_px,
        "seed": seed,
        "per_fold": per_fold,
    }


def leakage_canary(
    feature_raster: np.ndarray,
    fault_raster: np.ndarray,
    pixel_size_m: float,
    n_folds: int = 4,
    buffer_px: int = 3,
) -> dict:
    """Score a single feature alone on the holdout, per protocol item 4
    ("Test each feature alone on the holdout before trusting any result.
    AUC above 0.90 means leakage until proven otherwise.").

    Uses the feature's own min-max-normalized value as the prediction, with
    no detector logic at all -- if a single raw feature alone scores
    suspiciously high, it is almost certainly encoding the withheld fault
    geometry directly (leakage) rather than a genuine geophysical signal.
    """

    def normalize_as_prediction(visible_fault_raster: np.ndarray) -> np.ndarray:
        f = feature_raster.astype(np.float64)
        finite = np.isfinite(f)
        lo = np.nanmin(f[finite]) if finite.any() else 0.0
        hi = np.nanmax(f[finite]) if finite.any() else 1.0
        norm = np.zeros_like(f)
        if hi > lo:
            norm[finite] = (f[finite] - lo) / (hi - lo)
        return np.clip(norm, 0.0, 1.0)

    result = run_holdout(fault_raster, normalize_as_prediction, pixel_size_m, n_folds=n_folds, buffer_px=buffer_px)
    result["leakage_flag"] = result["pooled_DTI"] > 0.90
    return result
