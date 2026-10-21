#!/usr/bin/env python3
"""Numeric demonstration of DTI mechanics using ONLY our own verified
metric implementation (src/gems_doe/metric.py) and synthetic rasters.

Purpose: ground the research write-up (docs/research.html) in actual
computed numbers instead of assertions borrowed from sibling repositories.
This never touches real competition data -- it is a controlled experiment
on a fully synthetic fault + prediction raster, used only to illustrate the
*shape* of the scoring function (how concentrating vs. spreading a fixed
amount of predicted probability mass changes DTI under alpha=0.2, beta=0.8).

Run: python scripts/demo_dti_mechanics.py
Output: docs/data/dti_mechanics_demo.json (committed, so the numbers on the
research page are reproducible and auditable from the repo itself).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems_doe.metric import ALPHA, BETA, distance_weighted_tversky  # noqa: E402

PIXEL_SIZE_M = 100.0


def make_truth(h=80, w=80) -> np.ndarray:
    g = np.zeros((h, w), dtype=np.uint8)
    g[40, 10:70] = 1  # one straight 60-pixel fault trace
    return g


def experiment_a_thin_vs_wide_corridor():
    """Fixed total predicted probability MASS (sum of p over the raster),
    delivered two ways:
      (a) THIN: full confidence (p=1) on the exact true pixels only.
      (b) WIDE: the same total mass spread uniformly over a 5-pixel-wide
          corridor straddling the true line (p=0.2 on 5x as many pixels).
    This isolates the "thin vs. spread" effect that sibling repositories
    report finding empirically (e.g. "thinning... raises the credit per
    emitted pixel"), independent of any detector quality question.
    """
    g = make_truth()
    h, w = g.shape
    true_rows, true_cols = np.where(g == 1)
    mass = float(len(true_rows))  # total predicted mass = 60.0 in both cases

    p_thin = g.astype(np.float64).copy()

    p_wide = np.zeros((h, w))
    for dr in (-2, -1, 0, 1, 2):
        p_wide[true_rows + dr, true_cols] = 0.2
    assert np.isclose(p_wide.sum(), mass)

    r_thin = distance_weighted_tversky(p_thin, g, pixel_size_m=PIXEL_SIZE_M)
    r_wide = distance_weighted_tversky(p_wide, g, pixel_size_m=PIXEL_SIZE_M)
    return {"thin": r_thin, "wide_same_total_mass": r_wide}


def experiment_b_credit_density_breakeven():
    """What is the marginal DTI cost of adding ONE extra low-value predicted
    pixel far from any ground truth (a pure false positive), as a function
    of how far "far" is? This reproduces, from first principles, the
    "break-even credit per dot" argument sibling repositories report using
    empirically: with alpha=0.2 and no nearby truth, k(d)=0 so each unit of
    false-positive mass costs exactly alpha=0.2 of pooled FP_w, i.e. adding
    probability p far from any truth pixel changes
        DTI_new = TP_w / (TP_w + alpha*(FP_w + p) + beta*FN_w)
    which is strictly decreasing in p for any TP_w, FN_w >= 0. There is no
    data-dependent "0.0548" or "0.0520" break-even constant in the published
    formula itself -- those numbers (quoted on sibling sites) are
    properties of a *specific* candidate raster's TP_w/FN_w, not of the
    metric. This experiment makes that transparent with one concrete case.
    """
    g = make_truth()
    base_p = g.astype(np.float64).copy()
    base = distance_weighted_tversky(base_p, g, pixel_size_m=PIXEL_SIZE_M)

    far_p = base_p.copy()
    far_p[5, 5] = 1.0  # a single far-away false positive, full confidence
    far = distance_weighted_tversky(far_p, g, pixel_size_m=PIXEL_SIZE_M)

    marginal_dti_cost = base["DTI"] - far["DTI"]
    # closed-form prediction for a single additional far FP unit of mass p=1:
    tp, fn = base["TP_w"], base["FN_w"]
    predicted_new_dti = tp / (tp + ALPHA * (base["FP_w"] + 1.0) + BETA * fn + 1e-12)
    return {
        "base": base,
        "with_one_far_false_positive": far,
        "marginal_dti_cost": marginal_dti_cost,
        "closed_form_predicted_new_dti": predicted_new_dti,
        "matches_closed_form": bool(np.isclose(far["DTI"], predicted_new_dti, rtol=1e-6)),
    }


def experiment_c_offset_calibration():
    """How much does a *systematic* 1-2 pixel misalignment (the organizer's
    documented "rasterization...can induce off-by-one errors near pixel
    boundaries") cost a detector that is otherwise geometrically perfect?
    """
    g = make_truth()
    results = {}
    for offset in (0, 1, 2, 3, 4):
        p = np.roll(g.astype(np.float64), shift=offset, axis=0)
        r = distance_weighted_tversky(p, g, pixel_size_m=PIXEL_SIZE_M)
        results[f"offset_{offset}px"] = r
    return results


def main() -> None:
    out = {
        "pixel_size_m": PIXEL_SIZE_M,
        "alpha": ALPHA,
        "beta": BETA,
        "experiment_a_thin_vs_wide_corridor": experiment_a_thin_vs_wide_corridor(),
        "experiment_b_credit_density_breakeven": experiment_b_credit_density_breakeven(),
        "experiment_c_offset_calibration": experiment_c_offset_calibration(),
    }
    out_path = ROOT / "docs" / "data" / "dti_mechanics_demo.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {out_path}")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
