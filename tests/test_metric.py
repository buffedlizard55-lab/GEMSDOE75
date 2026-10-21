"""Line-by-line verification of the DTI implementation.

Every assertion here is either:
  (a) a direct reproduction of the organizer-published worked example, or
  (b) a hand-derivable synthetic case whose correct answer can be checked
      with pencil and paper (documented inline), independent of any
      competition data we do not have access to.
"""

import numpy as np
import pytest

from gems_doe.metric import (
    ALPHA,
    BETA,
    KERNEL_RANGE_M,
    distance_weighted_tversky,
    organizer_worked_example_dti,
    triangular_kernel,
)


def test_organizer_worked_example_rounds_to_published_value():
    # ORGANIZER-CONFIRMED: page 967 states DTI(0.2, 0.8) = 0.60 for
    # TP_w=3.00, FP_w=1.89, FN_w=2.00. 3.00 / (3.00 + 0.2*1.89 + 0.8*2.00)
    # = 3.00 / 4.978 = 0.602652...  rounds to 0.60 as published.
    value = organizer_worked_example_dti()
    assert round(value, 2) == 0.60
    assert value == pytest.approx(3.00 / 4.978, rel=1e-9)


def test_triangular_kernel_endpoints():
    # k(0) = 1, k(R) = 0, k(R/2) = 0.5, k(>R) = 0 (clipped, not negative)
    d = np.array([0.0, 150.0, 300.0, 450.0])
    k = triangular_kernel(d, kernel_range_m=300.0)
    np.testing.assert_allclose(k, [1.0, 0.5, 0.0, 0.0])


def test_perfect_prediction_gives_dti_one():
    # If p == g exactly (binary), every ground-truth pixel is covered with
    # kernel weight 1 (d=0) and there are no off-target predictions, so
    # TP_w = n, FP_w = 0, FN_w = 0  =>  DTI = n / n = 1 regardless of alpha/beta.
    g = np.zeros((20, 20))
    g[10, 2:18] = 1  # a line of faults, like the organizer's example
    p = g.copy().astype(np.float64)
    result = distance_weighted_tversky(p, g, pixel_size_m=100.0)
    assert result["FP_w"] == pytest.approx(0.0, abs=1e-9)
    assert result["FN_w"] == pytest.approx(0.0, abs=1e-9)
    assert result["DTI"] == pytest.approx(1.0, abs=1e-6)


def test_all_zero_prediction_gives_dti_zero():
    # The organizer's own reference baseline ("predicts total fault
    # absence"): p is identically 0 everywhere. TP_w = 0, FP_w = 0,
    # FN_w = sum(g) (no coverage at all) => DTI = 0 / (0+0+beta*FN_w) = 0.
    g = np.zeros((20, 20))
    g[5, 5] = 1
    g[12, 3] = 1
    p = np.zeros_like(g)
    result = distance_weighted_tversky(p, g, pixel_size_m=100.0)
    assert result["TP_w"] == pytest.approx(0.0, abs=1e-9)
    assert result["DTI"] == pytest.approx(0.0, abs=1e-6)


def test_no_ground_truth_pixels_predicted_anywhere_is_pure_false_positive():
    # No ground truth at all; any predicted mass is 100% false positive
    # (K(x) = 0 everywhere since there is no positive pixel to be near).
    # TP_w = 0, FN_w = 0, FP_w = sum(p). DTI = 0/(0 + alpha*FP_w + 0) = 0.
    g = np.zeros((10, 10))
    p = np.zeros((10, 10))
    p[3, 3] = 0.7
    result = distance_weighted_tversky(p, g, pixel_size_m=100.0)
    assert result["FP_w"] == pytest.approx(0.7, abs=1e-9)
    assert result["TP_w"] == pytest.approx(0.0, abs=1e-9)
    assert result["DTI"] == pytest.approx(0.0, abs=1e-6)


def test_one_pixel_offset_by_exactly_one_pixel_is_half_credit():
    # Single ground-truth pixel at (5,5); prediction of confidence 1.0 placed
    # exactly 1 pixel (100 m) away. k(100/300) = 1 - 1/3 = 2/3.
    # V(g) = 1.0 * 2/3 = 2/3 (that's the only predicted pixel within range).
    # TP_w = 2/3, FN_w = 1/3.
    # For FP: the predicted pixel is itself at distance 100 m from the one
    # ground-truth pixel, so K(x) = 2/3, FP_w = p*(1-2/3) = 1 * 1/3 = 1/3.
    g = np.zeros((20, 20))
    g[5, 5] = 1
    p = np.zeros((20, 20))
    p[5, 6] = 1.0
    result = distance_weighted_tversky(p, g, pixel_size_m=100.0)
    assert result["TP_w"] == pytest.approx(2 / 3, abs=1e-6)
    assert result["FN_w"] == pytest.approx(1 / 3, abs=1e-6)
    assert result["FP_w"] == pytest.approx(1 / 3, abs=1e-6)
    expected_dti = (2 / 3) / (2 / 3 + ALPHA * (1 / 3) + BETA * (1 / 3))
    assert result["DTI"] == pytest.approx(expected_dti, rel=1e-6)


def test_rejects_values_outside_unit_interval():
    g = np.zeros((5, 5))
    p = np.zeros((5, 5))
    p[0, 0] = 1.5
    with pytest.raises(ValueError):
        distance_weighted_tversky(p, g, pixel_size_m=100.0)


def test_rejects_nan_inside_scoring_domain():
    g = np.zeros((5, 5))
    p = np.zeros((5, 5))
    p[0, 0] = np.nan
    with pytest.raises(ValueError):
        distance_weighted_tversky(p, g, pixel_size_m=100.0)


def test_competition_constants_match_published_values():
    # ORGANIZER-CONFIRMED (page 967): "we set alpha=0.2 and beta=0.8";
    # "the range R is 300 meters (i.e., 3 pixels at 100m resolution)"
    assert ALPHA == 0.2
    assert BETA == 0.8
    assert KERNEL_RANGE_M == 300.0
