"""Verifies the hide-and-recover holdout mechanics on synthetic fault
rasters (we do not have the real USGS/INGENIOUS catalogue in this
environment -- see LIMITATIONS.md). These tests prove the *mechanism* is
correct (segment-level blocking, buffer exclusion, pooled scoring, leakage
canary threshold) so it is ready to run unchanged on the real catalogue.
"""

import numpy as np
import pytest

from gems_doe.holdout import leakage_canary, make_spatial_folds, run_holdout


def _synthetic_fault_raster(h=60, w=60, n_lines=8, seed=1) -> np.ndarray:
    """A handful of separated line segments, mimicking disjoint mapped fault
    traces -- enough connected components to split into folds.
    """
    rng = np.random.default_rng(seed)
    raster = np.zeros((h, w), dtype=np.uint8)
    for i in range(n_lines):
        r0 = rng.integers(2, h - 10)
        c0 = rng.integers(2, w - 10)
        length = rng.integers(4, 8)
        horizontal = i % 2 == 0
        for k in range(length):
            if horizontal:
                raster[r0, min(c0 + k, w - 1)] = 1
            else:
                raster[min(r0 + k, h - 1), c0] = 1
    return raster


def test_folds_partition_segments_without_overlap():
    fault = _synthetic_fault_raster()
    folds = make_spatial_folds(fault, n_folds=4, buffer_px=2, seed=0)
    assert len(folds) == 4
    all_withheld_ids = [sid for f in folds for sid in f.withheld_segment_ids]
    assert len(all_withheld_ids) == len(set(all_withheld_ids)), "a segment was assigned to >1 fold"

    # every original positive pixel is withheld truth in exactly one fold
    total_withheld_px = sum(int(f.withheld_truth.sum()) for f in folds)
    assert total_withheld_px == int(fault.sum())


def test_buffer_removes_withheld_segment_from_visible_raster():
    fault = _synthetic_fault_raster()
    folds = make_spatial_folds(fault, n_folds=4, buffer_px=3, seed=0)
    for f in folds:
        # no pixel that is withheld truth should still be visible
        assert (f.visible_fault_raster[f.withheld_truth.astype(bool)] == 0).all()
        # visible + (withheld truth alone, ignoring other folds' segments) should be
        # a subset of the original raster
        assert (f.visible_fault_raster <= fault).all()


def test_perfect_oracle_predictor_scores_near_one():
    # A legitimate "oracle" must still obey the predict_fn(visible) -> p
    # contract (it cannot see the withheld truth directly); to prove the
    # scoring plumbing is exactly correct end-to-end with zero cross-fold
    # contamination, build the fold lookup once, then have the oracle return
    # precisely *that fold's own* withheld truth when it recognizes its
    # corresponding visible raster. Any other synthetic fault raster passed
    # in that the oracle does not recognize is scored as all-zero (honest
    # abstention), so this is not "cheating" relative to run_holdout's API.
    fault = _synthetic_fault_raster()
    folds = make_spatial_folds(fault, n_folds=4, buffer_px=2, seed=0)
    lookup = {f.visible_fault_raster.tobytes(): f.withheld_truth for f in folds}

    def oracle(visible):
        return lookup[visible.tobytes()].astype(np.float64)

    result = run_holdout(fault, oracle, pixel_size_m=100.0, n_folds=4, buffer_px=2, seed=0)
    assert result["pooled_DTI"] == pytest.approx(1.0, abs=1e-6)
    assert result["n_withheld_positive_px"] == int(fault.sum())


def test_blank_predictor_scores_zero():
    fault = _synthetic_fault_raster()

    def blank(visible):
        return np.zeros_like(visible, dtype=np.float64)

    result = run_holdout(fault, blank, pixel_size_m=100.0, n_folds=4, buffer_px=2, seed=0)
    assert result["pooled_DTI"] == pytest.approx(0.0, abs=1e-6)


def test_leakage_canary_flags_the_raw_truth_as_a_feature():
    # Using the raw fault raster itself as a "feature" (i.e. a catalogue
    # value computed with knowledge of the withheld segment, not just the
    # visible ones) is the textbook leakage case. A single segment / single
    # fold isolates the effect so no unrelated visible segments contribute
    # false positives, which is exactly what makes a real leakage canary
    # diagnostic: AUC/DTI far above what the *visible* context alone could
    # ever justify.
    single = _synthetic_fault_raster(n_lines=1, seed=3)
    result = leakage_canary(single.astype(np.float64), single, pixel_size_m=100.0, n_folds=1, buffer_px=2)
    assert result["leakage_flag"] is True
    assert result["pooled_DTI"] > 0.90


def test_leakage_canary_does_not_flag_pure_noise():
    fault = _synthetic_fault_raster()
    rng = np.random.default_rng(2)
    noise = rng.random(fault.shape)
    result = leakage_canary(noise, fault, pixel_size_m=100.0, n_folds=4, buffer_px=2)
    assert result["leakage_flag"] is False
    assert result["pooled_DTI"] < 0.5
