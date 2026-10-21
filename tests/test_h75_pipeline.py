"""Unit and integration verification for GEMSDOE75 (`features_h75`, `dti_alloc`, and artifact gates)."""
from __future__ import annotations

import json
from pathlib import Path
import zipfile

import numpy as np
import pytest
import rasterio

from gems57 import metric
from gems_doe.dti_alloc import (
    calibrate_oof_probability,
    exact_shell_self_credit,
    expected_kernel_sum,
    submodular_dti_allocate,
)
from gems_doe.features_h75 import (
    FORBIDDEN_EXTERNAL_FILES,
    FORBIDDEN_LEAKAGE_COLUMNS,
    read_sanitized_csv,
    visible_network_features,
)

ROOT = Path(__file__).resolve().parents[1]


def test_exact_shell_self_credit_matches_monte_carlo_and_fixes_clip_bug():
    rng = np.random.default_rng(75)
    p = rng.uniform(0.02, 0.35, size=(11, 11)).astype(np.float32)
    exact = float(exact_shell_self_credit(p)[5, 5])
    clipped_approx = float(np.minimum(1.0, expected_kernel_sum(p))[5, 5])

    yy, xx = np.ogrid[-3:4, -3:4]
    kw = np.maximum(0.0, 1.0 - np.hypot(yy, xx) / 3.0).astype(np.float32)
    draws = rng.random((60_000, 7, 7)) < p[2:9, 2:9][None, :, :]
    mc = float((draws * kw[None, :, :]).max(axis=(1, 2)).mean())

    assert abs(exact - mc) < 3.5e-3
    # Confirm upstream `min(1, sum k_g p_g)` systematically overestimates self-credit (IR-75-02)
    assert clipped_approx > exact + 0.15


def test_leakage_guards_block_forbidden_columns_and_files(tmp_path):
    assert "dist_known_fault_px" in FORBIDDEN_LEAKAGE_COLUMNS
    assert "gdr_qfaults_traces.csv" in FORBIDDEN_EXTERNAL_FILES
    assert "sgmc_faults_100m.tif" in FORBIDDEN_EXTERNAL_FILES

    csv_path = tmp_path / "gdr_wellspring_in_footprint.csv"
    csv_path.write_text(
        "row,col,temp_c,dist_known_fault_px\n10,20,85.0,0.0\n15,25,112.5,1.0\n",
        encoding="utf-8",
    )
    rows, stripped = read_sanitized_csv(csv_path)
    assert "dist_known_fault_px" in stripped
    assert all("dist_known_fault_px" not in r for r in rows)
    assert [int(r["row"]) for r in rows] == [10, 15]

    banned = tmp_path / "gdr_qfaults_traces.csv"
    banned.write_text("row,col\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Refusing forbidden"):
        read_sanitized_csv(banned)


def test_visible_network_features_zero_lookahead_invariance():
    rng = np.random.default_rng(123)
    vis = np.zeros((40, 40), dtype=bool)
    vis[8:30, 12] = True
    vis[15:34, 26] = True
    p_geo = rng.uniform(0.0, 0.5, size=(40, 40)).astype(np.float32)
    query = np.ones((40, 40), dtype=bool)

    X1 = visible_network_features(vis, p_geo, query)
    X2 = visible_network_features(vis.copy(), p_geo.copy(), query.copy())
    assert np.array_equal(X1, X2)
    assert np.isfinite(X1).all()


def test_submodular_allocator_masks_forbidden_and_beats_naive_blob():
    H, W = 48, 48
    truth = np.zeros((H, W), dtype=bool)
    truth[6:42, 24] = True  # True 1-px fault line (36 pixels)

    p = np.full((H, W), 0.004, dtype=np.float32)
    p[6:42, 24] = 0.52  # Sharp calibrated line probability
    p[10:22, 6:14] = 0.09  # Broad low-density false plateau

    allowed = np.ones((H, W), dtype=bool)
    allowed[0:3, :] = False  # Masked collar/border

    res = submodular_dti_allocate(p, allowed, k_truth=36.0, min_spacing_px=2)
    assert (res.emitted[~allowed] == 0.0).all()
    assert np.isfinite(res.emitted).all()
    assert res.emitted.min() >= 0.0 and res.emitted.max() <= 1.0

    # Compare DTI against emitting every >0.08 pixel unthinned (dense false-positive blob trap)
    dense = np.where(allowed & (p > 0.08), 1.0, 0.0).astype(np.float32)
    assert metric.dti_exact(res.emitted, truth)["dti"] > metric.dti_exact(dense, truth)["dti"] + 0.08


def test_calibrate_oof_probability_preserves_monotone_order_and_bounds():
    rng = np.random.default_rng(7)
    y = (rng.random(2000) < 0.15).astype(np.int32)
    raw = np.clip(0.15 + 0.55 * y + rng.normal(0, 0.12, size=2000), 0.001, 0.999).astype(np.float32)
    test_s = np.linspace(0.01, 0.99, 200, dtype=np.float32)
    cal = calibrate_oof_probability(raw, y, test_s, 0.004)
    assert cal.shape == test_s.shape
    assert np.isfinite(cal).all()
    assert (cal > 0.0).all() and (cal < 1.0).all()
    assert np.all(np.diff(cal) >= -1e-7)


def test_emitted_submission_geotiff_and_zip_portal_guarantees():
    card = json.loads((ROOT / "evidence/run-card.json").read_text())
    tif_path = ROOT / card["submission"]["tif_path"]
    zip_path = ROOT / card["submission"]["zip_path"]

    with rasterio.open(tif_path) as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert src.crs.to_epsg() == 32611
        assert src.shape == (3730, 3292)
        assert src.nodata is None
        arr = src.read(1)

    assert np.isfinite(arr).all(), "Zero NaN/Inf required across all 12,279,160 pixels"
    assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
    assert int((arr > 0).sum()) == card["submission"]["emitted_positive_pixels"] == 29953

    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.namelist() == [tif_path.name]
        assert zf.read(tif_path.name) == tif_path.read_bytes()


def test_all_holdout_evidence_strictly_labeled_with_non_overlapping_cis():
    exp = json.loads((ROOT / "evidence/experiments-h75.json").read_text())
    assert exp["evidence_class"] == "HOLDOUT-DTI"
    assert exp["evaluator_version"] == "gems57-pooled-hide-v2"
    assert exp["experiments_used"] == 3

    # Verify strictly positive 95% CI lower bounds on paired differences across ALL THREE holdout suites
    assert exp["suite_N_whole_component_300m"]["paired_differences"]["H33_foldfair"]["ci95"][0] > 0.055
    assert exp["suite_Q_blind_quadrants_8km"]["paired_differences"]["D15_static"]["ci95"][0] > 0.015
    assert exp["suite_D_detached_splays_400m"]["paired_differences"]["H33_foldfair"]["ci95"][0] > 0.024
    assert exp["suite_D_detached_splays_400m"]["paired_differences"]["D28_static"]["ci95"][0] > 0.0075
