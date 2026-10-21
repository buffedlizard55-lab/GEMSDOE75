"""Verifies the submission writer/validator against the exact failure modes
documented in src/gems_doe/submission_io.py, using a small synthetic
template raster (since we do not have network access to the organizer's
real training_features.tif in this environment -- see LIMITATIONS.md).
"""

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gems_doe.submission_io import (
    EXPECTED_CRS_EPSG,
    FLOAT32_NEG_SENTINEL,
    SubmissionTemplate,
    sanitize_prediction,
    validate_submission,
    write_submission,
)


@pytest.fixture()
def synthetic_template(tmp_path) -> SubmissionTemplate:
    """A small stand-in for training_features.tif: EPSG:32611, 100 m, with
    a correct affine transform, so every geometry rule can be exercised
    end-to-end without the real (login-walled) competition file.
    """
    h, w = 12, 9
    transform = Affine(100.0, 0.0, 500000.0, 0.0, -100.0, 4400000.0)
    path = tmp_path / "fake_training_features.tif"
    data = np.zeros((h, w), dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=1,
        dtype="float32",
        crs=f"EPSG:{EXPECTED_CRS_EPSG}",
        transform=transform,
    ) as dst:
        dst.write(data, 1)
    return SubmissionTemplate.from_raster(str(path))


def test_template_rejects_wrong_crs(tmp_path):
    path = tmp_path / "wrong_crs.tif"
    with rasterio.open(
        path, "w", driver="GTiff", height=5, width=5, count=1, dtype="float32",
        crs="EPSG:4326", transform=Affine(0.001, 0, -119, 0, -0.001, 40),
    ) as dst:
        dst.write(np.zeros((5, 5), dtype=np.float32), 1)
    with pytest.raises(ValueError):
        SubmissionTemplate.from_raster(str(path))


def test_sanitize_strips_reference_solution_sentinel():
    # This is the exact sentinel value the organizer's own reference
    # solution strips: `X_orig[X_orig < -1e38] = np.nan` in
    # unet-mc-cv-reference-solution.ipynb (cell 5).
    arr = np.array([[0.3, float(FLOAT32_NEG_SENTINEL)], [1.4, -0.2]])
    clean = sanitize_prediction(arr)
    assert np.isfinite(clean).all()
    assert clean.min() >= 0.0
    assert clean.max() <= 1.0
    assert clean[0, 0] == pytest.approx(0.3, abs=1e-6)
    assert clean[0, 1] == 0.0  # sentinel -> treated as missing -> 0.0
    assert clean[1, 0] == 1.0  # clipped down from 1.4
    assert clean[1, 1] == 0.0  # clipped up from -0.2


def test_write_submission_reproduces_the_user_reported_error_then_fixes_it(synthetic_template, tmp_path):
    h, w = synthetic_template.height, synthetic_template.width
    bad = np.zeros((h, w), dtype=np.float32)
    bad[0, 0] = float(FLOAT32_NEG_SENTINEL)  # the exact bug: an unmasked sentinel

    # Writing `bad` directly (bypassing sanitize_prediction) is exactly what
    # produces the reported "Predicted values must be in range [0, 1]" error.
    raw_path = tmp_path / "raw_bad.tif"
    from rasterio.transform import Affine as _Affine

    with rasterio.open(
        raw_path, "w", driver="GTiff", height=h, width=w, count=1, dtype="float32",
        crs=f"EPSG:{synthetic_template.crs_epsg}", transform=_Affine(*synthetic_template.transform),
    ) as dst:
        dst.write(bad, 1)
    report_bad = validate_submission(str(raw_path), template=synthetic_template)
    assert not report_bad.ok
    assert any("range [0, 1]" in e for e in report_bad.errors)

    # The fixed path: write_submission() sanitizes first, so the same array
    # now produces a fully compliant file.
    good_path = tmp_path / "fixed.tif"
    report_good = write_submission(bad, str(good_path), synthetic_template)
    assert report_good.ok, report_good.errors
    assert report_good.checks["min_finite"] == 0.0
    assert report_good.checks["n_below_zero"] == 0
    assert report_good.checks["n_above_one"] == 0


def test_write_submission_matches_template_geometry_exactly(synthetic_template, tmp_path):
    h, w = synthetic_template.height, synthetic_template.width
    rng = np.random.default_rng(0)
    arr = rng.random((h, w)).astype(np.float32)
    out_path = tmp_path / "ok.tif"
    report = write_submission(arr, str(out_path), synthetic_template)
    assert report.ok, report.errors
    assert report.checks["shape"] == [h, w]
    assert report.checks["transform"] == list(synthetic_template.transform)


def test_zeros_baseline_is_always_valid(synthetic_template, tmp_path):
    h, w = synthetic_template.height, synthetic_template.width
    zeros = np.zeros((h, w), dtype=np.float32)
    out_path = tmp_path / "zeros.tif"
    report = write_submission(zeros, str(out_path), synthetic_template)
    assert report.ok, report.errors
    assert report.checks["n_predicted_px_gt_0"] == 0
    assert report.checks["nodata_tag"] is None


def test_footprint_mask_outside_zero_vs_nan(synthetic_template, tmp_path):
    h, w = synthetic_template.height, synthetic_template.width
    arr = np.full((h, w), 0.5, dtype=np.float32)
    mask = np.zeros((h, w), dtype=bool)
    mask[2:5, 2:5] = True

    zero_path = tmp_path / "outside_zero.tif"
    r_zero = write_submission(arr, str(zero_path), synthetic_template, footprint_mask=mask, outside_footprint="zero")
    assert r_zero.ok, r_zero.errors
    assert r_zero.checks["n_nan"] == 0

    nan_path = tmp_path / "outside_nan.tif"
    r_nan = write_submission(arr, str(nan_path), synthetic_template, footprint_mask=mask, outside_footprint="nan")
    assert r_nan.ok, r_nan.errors
    assert r_nan.checks["n_nan"] == h * w - 9
    assert r_nan.checks["nodata_tag"] is not None and np.isnan(r_nan.checks["nodata_tag"])
