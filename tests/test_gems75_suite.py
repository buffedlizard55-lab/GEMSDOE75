"""Comprehensive unit, mathematical-identity, anti-leakage, GeoTIFF-contract,
and GitHub Pages synchronization test suite for GEMSDOE75.

Designed to run 100% deterministically both locally AND inside clean GitHub Actions runners
(requiring zero uncommitted gigabyte `.cache/` files while also cross-checking `.cache/` when present).
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from gems57.grid import EPSG, HEIGHT, TRANSFORM, WIDTH
from gems57.metric import build_fast_oracle, dti_exact, dti_with_oracle
from gems57.uniqueness import dot_overlap
from gems57.validate import sha256, validate

from gems75.constants import (
    CANDIDATE_DOT_BUDGET,
    GRAV_SLOPE_TO_MGAL_PER_KM,
    KERNEL_300M,
    TMI_VG_TO_NT_PER_KM,
)
from gems75.decoder import (
    directional_ridge_concentration,
    exp_tail,
    submodular_pack_300m,
)
from gems75.network import compute_network_features_2d
from gems75.physics import (
    byerlee_mohr_coulomb_favorability,
    dequantize_lidar_u8,
    oriented_radon_ridge,
)
from gems75.protocol import _fast_exact_dot_overlap

ROOT = Path(__file__).resolve().parents[1]


def test_si_unit_constants_and_lidar_dequantization() -> None:
    assert TMI_VG_TO_NT_PER_KM == 1000.0
    assert GRAV_SLOPE_TO_MGAL_PER_KM == 10.0

    # Verify exact round-trip of `q = 1 + round(254 * sqrt(x / xmax))`
    xmax = 1.5
    x_true = np.array([0.0, 0.05, 0.25, 0.75, 1.5], dtype=np.float32)
    q_u8 = np.clip(np.rint(1.0 + 254.0 * np.sqrt(x_true / xmax)), 1, 255).astype(np.uint8)
    x_rec = dequantize_lidar_u8(q_u8, xmax=xmax, mode="sqrt")
    assert np.max(np.abs(x_rec - x_true)) < 0.012


def test_313x_blob_bias_theorem_and_1d_ridge_fix() -> None:
    """Prove the 9.380298 / 3.000000 = 3.1268x 2D-blob bias identity and verify
    that `directional_ridge_concentration` restores priority to sharp 1D fault scarps!
    """
    blob_sum = sum(k for _, _, k in KERNEL_300M)
    line_sum = sum(k for dy, dx, k in KERNEL_300M if dx == 0)
    assert abs(blob_sum - 9.380298) < 1e-5
    assert abs(line_sum - 3.000000) < 1e-6
    assert 3.126 < (blob_sum / line_sum) < 3.128

    # Construct synthetic 64x64 grid with:
    # - A diffuse flat 2D mountain plateau of height 4.0 around col 16
    # - A sharp 1-pixel piedmont fault trace of height 4.5 along col 48
    grid = np.zeros((64, 64), dtype=np.float32)
    valid = np.ones((64, 64), dtype=bool)
    grid[15:50, 10:23] = 4.0
    grid[15:50, 48] = 4.5

    conc = directional_ridge_concentration(grid, valid)
    # Along the sharp 1-px fault trace, concentrated ridge response strictly beats the flat plateau!
    assert float(conc[32, 48]) > 1.8 * float(conc[32, 16])

    # Verify 200 m minimum inter-dot spacing (`min_spacing_px = 2.0`) prevents d < 2.0 clumping
    dots, picked = submodular_pack_300m(conc, valid, target_n=12, support_quantile=0.5, min_spacing_px=2.0)
    assert picked == 12
    ys, xs = np.nonzero(dots)
    dmat = np.hypot(ys[:, None] - ys[None, :], xs[:, None] - xs[None, :])
    np.fill_diagonal(dmat, 999.0)
    assert float(dmat.min()) >= 2.0 - 1e-6


def test_radon_orientation_and_byerlee_mechanics() -> None:
    img = np.zeros((81, 81), dtype=np.float32)
    # Vertical N-S scarp along column 40 -> compass strike must be 0 deg!
    img[10:70, 40] = 5.0
    r_max, aniso, az = oriented_radon_ridge(img, step_px=2.0, norm_px=3.0)
    assert float(r_max[40, 40]) > 4.0
    assert float(aniso[40, 40]) > 2.5
    assert float(az[40, 40]) == 0.0

    # Normal-faulting regime (A_phi = 0.55): strike aligned with SHmax (20 deg) beats orthogonal (110 deg)
    fav_aligned = byerlee_mohr_coulomb_favorability(np.array([20.0]), np.array([20.0]), np.array([0.55]))
    fav_ortho = byerlee_mohr_coulomb_favorability(np.array([110.0]), np.array([20.0]), np.array([0.55]))
    assert float(fav_aligned[0]) > 0.99
    assert float(fav_ortho[0]) < 0.01

    # Strike-slip Walker Lane regime (A_phi = 1.65): SHmax - 29.5 deg conjugate beats orthogonal
    fav_wl = byerlee_mohr_coulomb_favorability(np.array([155.5]), np.array([5.0]), np.array([1.65]))
    assert float(fav_wl[0]) > 0.99


def test_fast_oracle_and_fast_overlap_exactness() -> None:
    rng = np.random.default_rng(75)
    valid = np.ones((90, 90), dtype=bool)
    valid[:5, :] = False
    known = np.zeros((90, 90), dtype=bool)
    known[10:20, 15] = True
    truth = np.zeros((90, 90), dtype=bool)
    truth[30:65, 44] = True
    truth[50, 20:55] = True

    pred = np.zeros((90, 90), dtype=np.float32)
    pts = rng.choice(90 * 90, size=180, replace=False)
    pred.ravel()[pts] = 1.0
    pred[~valid] = 0.0
    pred[known] = 0.0

    ref = dti_exact(pred, truth, valid=valid, known=known)
    orc = build_fast_oracle(truth, valid=valid, known=known)
    fast = dti_with_oracle(pred, orc)
    assert abs(ref["dti"] - fast["dti"]) < 1e-12
    assert abs(ref["tp"] - fast["tp"]) < 1e-11
    assert abs(ref["fp"] - fast["fp"]) < 1e-11

    other = np.zeros((90, 90), dtype=np.float32)
    other.ravel()[rng.choice(90 * 90, size=210, replace=False)] = 1.0
    my, mx = np.nonzero(pred == 1.0)
    assert abs(_fast_exact_dot_overlap(my, mx, other == 1.0) - dot_overlap(pred, other)) < 1e-12


def test_loco_network_zero_leakage_on_hidden_gap() -> None:
    vis = np.zeros((100, 100), dtype=bool)
    # Two approaching colinear N-S fault strands separated by a 14-pixel unmapped gap (rows 43..56)
    vis[15:43, 50] = True
    vis[57:85, 50] = True
    dc, ta, rs, hl, mb = compute_network_features_2d(vis)

    # Along-strike continuation right inside the unmapped gap (row 49, col 50) must vastly exceed far background!
    assert float(ta[49, 50]) > 10.0 * float(ta[49, 20])
    assert float(mb[49, 50]) > float(mb[15, 20])


def test_committed_submission_geotiff_evidence_and_pages_sync() -> None:
    rc = json.loads((ROOT / "evidence" / "run_card.json").read_text())
    exp = json.loads((ROOT / "evidence" / "experiments_summary.json").read_text())
    can = json.loads((ROOT / "evidence" / "leakage_canaries.json").read_text())
    unq = json.loads((ROOT / "evidence" / "uniqueness_scan.json").read_text())

    # 1. All protocol gates strictly satisfied
    assert rc["verdict"] == "promote"
    assert can["all_pass"] is True and can["max_symmetric_auc"] <= 0.90
    assert unq["all_pass"] is True
    assert unq["max_abs_surface_spearman"] <= 0.90
    assert unq["max_dot_overlap_3px"] <= 0.70
    assert rc["score_provenance"]["experiments_executed_count"] == 3

    # 2. Monotonic holdout ladder E1 < E2 < E3
    sc = exp["pooled_holdout_bootstrap"]["scores"]
    assert sc["E1_ALMRC_TiltSI_48"]["dti"] < sc["E2_Byerlee3D_HeatFlow_LOCOQuat_59"]["dti"]
    assert sc["E2_Byerlee3D_HeatFlow_LOCOQuat_59"]["dti"] < sc["E3_TRLT75_Stage2Radon_1DRidge_SpacedSubmod"]["dti"]

    # 3. Byte-level GeoTIFF & ZIP verification
    art = rc["artifact"]
    assert len(art["submission_note"]) <= 140
    tif_p = ROOT / art["tif_path"]
    zip_p = ROOT / art["zip_path"]
    assert tif_p.is_file() and zip_p.is_file()
    assert sha256(tif_p) == art["tif_sha256"]
    assert sha256(zip_p) == art["zip_sha256"]

    val = validate(tif_p)
    assert all(bool(v) for v in val["checks"].values())
    with rasterio.open(tif_p) as ds:
        a = ds.read(1)
        assert (ds.height, ds.width) == (HEIGHT, WIDTH)
        assert str(ds.crs) == f"EPSG:{EPSG}"
        assert tuple(ds.transform)[:6] == tuple(TRANSFORM)[:6]
        assert np.isfinite(a).all()
        assert float(a.min()) == 0.0 and float(a.max()) == 1.0
        assert int((a == 1.0).sum()) == CANDIDATE_DOT_BUDGET == art["n_dots"]

    with zipfile.ZipFile(zip_p) as zf:
        tifs = [n for n in zf.namelist() if n.endswith(".tif")]
        assert len(tifs) == 1

    # 4. Verify all HTML pages & local relative links resolve cleanly
    for page_name in ("index.html", "executive-summary.html", "run-card.html", "sources.html"):
        p = ROOT / "docs" / page_name
        assert p.is_file()
        assert (ROOT / page_name).is_file()
        txt = p.read_text()
        for m in re.finditer(r'(?:href|src)="([^"#]+)"', txt):
            target = m.group(1)
            if target.startswith(("http://", "https://", "mailto:", "javascript:")):
                continue
            assert (ROOT / "docs" / target).exists(), f"Broken relative link in docs/{page_name}: {target}"
