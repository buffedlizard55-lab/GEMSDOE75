"""Multi-physics & strict visible-network feature engineering for Lane H75-1.

All 34 physical features are computed strictly from competition-provided bands
(`training_features.tif`, fixing the upstream B06 radiometric Total Count tag)
and official public external layers in `.cache/external/`, with explicit compile-
time / load-time stripping of `FORBIDDEN_LEAKAGE_COLUMNS` (`dist_known_fault_px`)
and complete exclusion of external fault-trace compilations (`gdr_qfaults_traces.csv`,
`sgmc_faults_100m.tif`, `derived_sgmc_faults_100m_u8.tif`).

All catalogue-network features in `visible_network_features` are computed strictly
from a single fold's `visible` mask (never full `labels.tif` during holdout).
"""
from __future__ import annotations

import csv
import gc
import struct
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from pyproj import Transformer
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import rankdata

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57.network import STRUCT3, local_strike, nearest_frame, offset_components

FORBIDDEN_LEAKAGE_COLUMNS: frozenset[str] = frozenset(
    {
        "dist_known_fault_px",
        "dist_fault_px",
        "dist_fault_m",
        "fault_id",
        "qfault_id",
    }
)

FORBIDDEN_EXTERNAL_FILES: frozenset[str] = frozenset(
    {
        "gdr_qfaults_traces.csv",
        "sgmc_faults_100m.tif",
        "derived_sgmc_faults_100m_u8.tif",
    }
)

PHYSICAL_FEATURE_NAMES: tuple[str, ...] = (
    # Block P: Potential-field phase-tilt, strike worms, shallow demagnetization (10)
    "p_mag_tilt_abs",
    "p_mag_tilt_grad",
    "p_mag_asig_log",
    "p_mag_worm_1500m",
    "p_demag_shallow",
    "p_grav_tilt_abs",
    "p_grav_tilt_grad",
    "p_grav_worm_2km",
    "p_pot_strike_concord",
    "p_rtp_curv",
    # Block G: Cover-adaptive geomorphic scarps, openness, knickpoints (10)
    "g_cover_index",
    "g_det_elev",
    "g_det_slope",
    "g_piedmont_inflect",
    "g_lidar_valid",
    "g_lidar_dipole",
    "g_lidar_coh",
    "g_topo10_breakline",
    "g_scarp_worm_1km",
    "g_chi_knick",
    # Block H: Hydrothermal upflow, radiometric alteration ratios, MT clay-cap (8)
    "h_mt_clay_depth",
    "h_mt_clay_edge",
    "h_mt_cond",
    "h_rad_k_th",
    "h_rad_u_th",
    "h_thermal_upflow",
    "h_paleo_sinter_probe",
    "h_vent_control",
    # Block S: Active strain, seismic clustering & 2015-2026 3D ComCat ruptures (6)
    "s_geod_shear",
    "s_geod_transtens",
    "s_eq_indep_log",
    "s_eq_cluster_ratio",
    "s_eq_ridge_aniso",
    "s_comcat_3d_rupture",
)

NETWORK_FEATURE_NAMES: tuple[str, ...] = (
    "n_log_d_vis",
    "n_d_perp_log",
    "n_d_par_log",
    "n_tip_lobe",
    "n_relay_bridge",
    "n_host_log_len",
    "n_host_coh",
    "n_vis_density_1km",
    "n_pgeo_prior",
    "n_pgeo_x_tip",
    "n_pgeo_x_relay",
    "n_pgeo_x_near",
)


def clean_grid(a: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Replace NaN/Inf/sentinel values outside or inside footprint with clean float32."""
    v = np.asarray(a, dtype=np.float32).copy()
    bad = ~np.isfinite(v) | (np.abs(v) > 1e18)
    valid = footprint & ~bad
    fill = float(np.median(v[valid])) if valid.any() else 0.0
    v[bad] = fill
    v[~footprint] = fill
    return v


def robust_z_inplace(v: np.ndarray, footprint: np.ndarray, clip: float = 10.0) -> np.ndarray:
    """Robust median/MAD z-score inside footprint in float32."""
    sub = v[footprint]
    med = float(np.median(sub))
    mad = float(np.median(np.abs(sub - med))) * 1.4826
    if not np.isfinite(mad) or mad <= 1e-9:
        mad = max(float(np.std(sub)), 1e-6)
    out = (v - np.float32(med)) / np.float32(mad)
    np.clip(out, -clip, clip, out=out)
    out[~footprint] = 0.0
    return out.astype(np.float32, copy=False)


def strike_worm_response(field: np.ndarray, half_len_px: int = 7, n_angles: int = 8) -> np.ndarray:
    """Multi-azimuth linear ridge response minus local isotropic background.

    Amplifies elongated fault lineaments of length ~`2*half_len_px*100 m` while
    cancelling circular/isotropic bullseyes (volcanic plugs, mountain peaks).
    """
    iso = ndi.uniform_filter(field, size=2 * half_len_px + 1, mode="nearest")
    best = np.full(field.shape, -1e30, dtype=np.float32)
    t = np.arange(-half_len_px, half_len_px + 1, dtype=np.float32)
    for k in range(n_angles):
        ang = np.pi * k / n_angles
        dy = np.round(-np.cos(ang) * t).astype(np.int32)
        dx = np.round(np.sin(ang) * t).astype(np.int32)
        ker = np.zeros((2 * half_len_px + 1, 2 * half_len_px + 1), dtype=np.float32)
        for r, c in zip(dy + half_len_px, dx + half_len_px):
            ker[r, c] += 1.0
        ker /= ker.sum()
        resp = ndi.convolve(field, ker, mode="nearest")
        np.maximum(best, resp, out=best)
    return (best - iso).astype(np.float32)


def hessian_ridge_max(field: np.ndarray, sigmas: tuple[float, ...] = (1.2, 2.8)) -> np.ndarray:
    """Maximum multiscale crest curvature `-lambda_min(H)` across Gaussian scales."""
    best = np.zeros(field.shape, dtype=np.float32)
    for s in sigmas:
        g = ndi.gaussian_filter(field, sigma=s, mode="nearest")
        gyy = ndi.gaussian_filter(g, sigma=0.8, order=(2, 0), mode="nearest")
        gxx = ndi.gaussian_filter(g, sigma=0.8, order=(0, 2), mode="nearest")
        gxy = ndi.gaussian_filter(g, sigma=0.8, order=(1, 1), mode="nearest")
        tr = 0.5 * (gxx + gyy)
        rad = np.hypot(0.5 * (gxx - gyy), gxy)
        crest = np.maximum(-(tr - rad), 0.0) * np.float32(s)
        np.maximum(best, crest, out=best)
    return best


def read_sanitized_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Read an external CSV while unconditionally stripping `FORBIDDEN_LEAKAGE_COLUMNS`."""
    if path.name in FORBIDDEN_EXTERNAL_FILES:
        raise ValueError(f"Refusing forbidden fault-compilation external file: {path.name}")
    stripped: list[str] = []
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames is not None
        keep_cols = []
        for col in reader.fieldnames:
            if col in FORBIDDEN_LEAKAGE_COLUMNS or "fault" in col.lower():
                stripped.append(col)
            else:
                keep_cols.append(col)
        for raw in reader:
            rows.append({c: raw[c] for c in keep_cols})
    return rows, stripped


def _read_shapefile_points_in_zip(zip_path: Path) -> list[tuple[float, float]]:
    """Extract 2D point coordinates `(x, y)` directly from `.shp` inside a `.zip`."""
    pts: list[tuple[float, float]] = []
    with zipfile.ZipFile(zip_path) as zf:
        shp_names = [n for n in zf.namelist() if n.lower().endswith(".shp")]
        if not shp_names:
            return pts
        buf = zf.read(shp_names[0])
        prj_names = [n for n in zf.namelist() if n.lower().endswith(".prj")]
        prj_txt = zf.read(prj_names[0]).decode("utf-8", errors="ignore") if prj_names else ""
    off = 100
    n = len(buf)
    while off + 12 <= n:
        rec_len_words = struct.unpack(">i", buf[off + 4 : off + 8])[0]
        rec_bytes = rec_len_words * 2
        content = buf[off + 8 : off + 8 + rec_bytes]
        if len(content) >= 20:
            shape_type = struct.unpack("<i", content[:4])[0]
            if shape_type in (1, 11, 21):
                x, y = struct.unpack("<dd", content[4:20])
                pts.append((x, y))
        off += 8 + rec_bytes
    if pts and ("GEOGCS" in prj_txt or abs(pts[0][0]) <= 180.0):
        tr = Transformer.from_crs("EPSG:4269", "EPSG:32611", always_xy=True)
        xs, ys = tr.transform([p[0] for p in pts], [p[1] for p in pts])
        pts = list(zip(xs, ys))
    return pts


def parse_comcat_hypocenters(
    comcat_path: Path, shape: tuple[int, int], transform: Any
) -> dict[str, Any]:
    """Parse verbatim USGS ANSS ComCat pipe-delimited text into UTM grid hypocenters."""
    lines = comcat_path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("#EventID|"):
        raise ValueError(f"Invalid ComCat header in {comcat_path}")
    lats, lons, deps, mags = [], [], [], []
    for idx, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        fields = line.split("|")
        if len(fields) != 13:
            raise ValueError(f"Malformed ComCat line {idx}: expected 13 fields")
        lats.append(float(fields[2]))
        lons.append(float(fields[3]))
        deps.append(float(fields[4]))
        mags.append(float(fields[10]))
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    ux, uy = tr.transform(np.asarray(lons, float), np.asarray(lats, float))
    cols = (ux - transform.c) / transform.a
    rows = (uy - transform.f) / transform.e
    mags_arr = np.asarray(mags, np.float32)
    deps_arr = np.asarray(deps, np.float32)
    in_bounds = (
        (rows >= -25)
        & (rows < shape[0] + 25)
        & (cols >= -25)
        & (cols < shape[1] + 25)
    )
    return {
        "total_events": len(lats),
        "near_grid_events": int(in_bounds.sum()),
        "rows": rows[in_bounds].astype(np.float32),
        "cols": cols[in_bounds].astype(np.float32),
        "depths_km": deps_arr[in_bounds],
        "mags": mags_arr[in_bounds],
    }


def build_comcat_3d_rupture_surface(
    comcat: dict[str, Any], shape: tuple[int, int], footprint: np.ndarray
) -> np.ndarray:
    """Project 2015-2026 M>=3.0 hypocenters onto anisotropic PCA rupture planes.

    When >= 4 earthquakes cluster within 8 km (`80 px`), the 2D covariance of
    their hypocenters reveals the active fault plane's strike azimuth `theta_pca`.
    Each event is splatted with an anisotropic kernel elongated along `theta_pca`
    (`sigma_par` scaling with Wells & Coppersmith subsurface rupture length
    `L ~ 10^(0.45*(M - 4.0))` km, `sigma_perp = 2.5 px`), turning discrete
    earthquake swarms (Monte Cristo M6.5, Antelope Valley M6.0, Parker Butte M5.71,
    Silver Springs M5.68) into crisp fault-plane lineaments.
    """
    H, W = shape
    out = np.zeros(shape, dtype=np.float32)
    rs, cs, mags, deps = comcat["rows"], comcat["cols"], comcat["mags"], comcat["depths_km"]
    if rs.size == 0:
        return out
    pts = np.column_stack([rs, cs])
    tree = cKDTree(pts)
    weights = np.power(10.0, 0.42 * np.clip(mags - 3.0, 0.0, 3.8)).astype(np.float32)
    # Upweight brittle upper-crustal seismogenic depths (1-14 km)
    weights *= np.where((deps >= 0.5) & (deps <= 15.0), 1.15, 0.85).astype(np.float32)

    for i in range(rs.size):
        r0, c0, w0, m0 = float(rs[i]), float(cs[i]), float(weights[i]), float(mags[i])
        nbrs = tree.query_ball_point([r0, c0], r=75.0)
        aniso = False
        ur, uc = 0.0, 1.0
        if len(nbrs) >= 4:
            sub = pts[nbrs]
            w_sub = weights[nbrs]
            mean = np.average(sub, axis=0, weights=w_sub)
            d = sub - mean
            cov = (d * w_sub[:, None]).T @ d / max(float(w_sub.sum()), 1e-6)
            eigvals, eigvecs = np.linalg.eigh(cov)
            if eigvals[1] > 2.2 * max(eigvals[0], 0.5):
                ur, uc = float(eigvecs[0, 1]), float(eigvecs[1, 1])
                aniso = True
        sig_par = float(np.clip(8.0 * (10.0 ** (0.32 * max(m0 - 3.5, 0.0))), 6.0, 34.0))
        sig_perp = 2.6 if aniso else 4.5
        rad = int(np.ceil(2.5 * (sig_par if aniso else sig_perp)))
        y0, y1 = max(0, int(np.floor(r0)) - rad), min(H, int(np.ceil(r0)) + rad + 1)
        x0, x1 = max(0, int(np.floor(c0)) - rad), min(W, int(np.ceil(c0)) + rad + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        yy, xx = np.ogrid[y0:y1, x0:x1]
        dr = yy.astype(np.float32) - np.float32(r0)
        dc = xx.astype(np.float32) - np.float32(c0)
        if aniso:
            d_par = dr * np.float32(ur) + dc * np.float32(uc)
            d_perp = -dr * np.float32(uc) + dc * np.float32(ur)
            kval = np.exp(-0.5 * ((d_par / np.float32(sig_par)) ** 2 + (d_perp / np.float32(sig_perp)) ** 2))
        else:
            kval = np.exp(-0.5 * (dr * dr + dc * dc) / np.float32(sig_perp * sig_perp))
        out[y0:y1, x0:x1] += np.float32(w0) * kval.astype(np.float32)

    out = np.log1p(out).astype(np.float32)
    return robust_z_inplace(out, footprint)


def fast_rank_auc(scores_1d: np.ndarray, y_bool: np.ndarray) -> tuple[float, float]:
    """Exact Mann-Whitney U / ROC-AUC and symmetric canary metric `max(AUC, 1-AUC)`."""
    fin = np.isfinite(scores_1d)
    s = scores_1d[fin]
    y = y_bool[fin]
    n1 = int(y.sum())
    n0 = int(y.size - n1)
    if n1 == 0 or n0 == 0:
        return 0.5, 0.5
    r = rankdata(s)
    auc = float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))
    return auc, float(max(auc, 1.0 - auc))


def build_physical_feature_matrix(
    inputs_dir: Path, external_dir: Path, eligible: np.ndarray
) -> tuple[np.ndarray, dict[str, Any]]:
    """Build `(N_eligible, 34)` float32 matrix of label-blind physical features."""
    el_r, el_c = np.nonzero(eligible)
    n_el = el_r.size
    X = np.empty((n_el, len(PHYSICAL_FEATURE_NAMES)), dtype=np.float32)
    receipts: dict[str, Any] = {"stripped_leakage_columns": {}, "external_counts": {}}

    with rasterio.open(inputs_dir / "training_features.tif") as src:
        transform = src.transform
        shape = src.shape
        b02 = clean_grid(src.read(2), eligible)
        b03 = clean_grid(src.read(3), eligible)
        b04 = clean_grid(src.read(4), eligible)
        b05 = clean_grid(src.read(5), eligible)
        b07 = clean_grid(src.read(7), eligible)
        b08 = clean_grid(src.read(8), eligible)
        b09 = clean_grid(src.read(9), eligible)
        b10 = clean_grid(src.read(10), eligible)
        b11 = clean_grid(src.read(11), eligible)
        b12 = clean_grid(src.read(12), eligible)
        b13 = clean_grid(src.read(13), eligible)
        b14 = clean_grid(src.read(14), eligible)
        b15 = clean_grid(src.read(15), eligible)
        b16 = clean_grid(src.read(16), eligible)
        b17 = clean_grid(src.read(17), eligible)
        b18 = clean_grid(src.read(18), eligible)
        b19 = clean_grid(src.read(19), eligible)

    # --- Block P (0..9): Potential-field phase-tilt & shallow demagnetization ---
    mag_tilt = np.arctan2(b09, np.maximum(np.abs(b03), 1e-6)).astype(np.float32)
    gy_mt, gx_mt = np.gradient(mag_tilt)
    mag_tilt_grad = np.hypot(gy_mt, gx_mt).astype(np.float32)
    mag_asig = np.log1p(np.hypot(b03, b09)).astype(np.float32)

    X[:, 0] = robust_z_inplace(-np.abs(mag_tilt), eligible)[el_r, el_c]
    X[:, 1] = robust_z_inplace(mag_tilt_grad + 0.5 * hessian_ridge_max(mag_tilt_grad, (1.0, 2.2)), eligible)[el_r, el_c]
    X[:, 2] = robust_z_inplace(mag_asig, eligible)[el_r, el_c]
    X[:, 3] = robust_z_inplace(
        strike_worm_response(robust_z_inplace(mag_tilt_grad, eligible) + 0.6 * robust_z_inplace(b03, eligible), half_len_px=7),
        eligible,
    )[el_r, el_c]
    del mag_tilt, gy_mt, gx_mt, mag_tilt_grad, mag_asig

    with rasterio.open(external_dir / "geodawn_extensions_u8.tif") as src:
        k_th = clean_grid(src.read(1), eligible)
        u_th = clean_grid(src.read(3), eligible)
        tmi_up150 = clean_grid(src.read(4), eligible)

    demag = robust_z_inplace(b14, eligible) - robust_z_inplace(tmi_up150, eligible)
    X[:, 4] = robust_z_inplace(np.abs(demag), eligible)[el_r, el_c]
    del demag, tmi_up150, b03

    grav_tilt = np.arctan2(b11, np.maximum(np.abs(b18), 1e-6)).astype(np.float32)
    gy_gt, gx_gt = np.gradient(grav_tilt)
    grav_tilt_grad = np.hypot(gy_gt, gx_gt).astype(np.float32)
    X[:, 5] = robust_z_inplace(-np.abs(grav_tilt), eligible)[el_r, el_c]
    X[:, 6] = robust_z_inplace(grav_tilt_grad, eligible)[el_r, el_c]
    X[:, 7] = robust_z_inplace(
        strike_worm_response(robust_z_inplace(b18, eligible) + 0.5 * robust_z_inplace(b05, eligible), half_len_px=10),
        eligible,
    )[el_r, el_c]

    # Cross-potential strike concordance cos(2*(phi_mag - phi_grav))
    my_m, mx_m = np.gradient(ndi.gaussian_filter(b14, sigma=1.5, mode="nearest"))
    my_g, mx_g = np.gradient(ndi.gaussian_filter(b13, sigma=2.5, mode="nearest"))
    phi_m = np.arctan2(my_m, mx_m)
    phi_g = np.arctan2(my_g, mx_g)
    concord = (np.cos(2.0 * (phi_m - phi_g)) * np.tanh(0.35 * np.maximum(robust_z_inplace(b18, eligible), 0.0))).astype(np.float32)
    X[:, 8] = robust_z_inplace(concord, eligible)[el_r, el_c]
    X[:, 9] = robust_z_inplace(-ndi.laplace(ndi.gaussian_filter(b02, sigma=1.2, mode="nearest")), eligible)[el_r, el_c]
    del grav_tilt, gy_gt, gx_gt, grav_tilt_grad, my_m, mx_m, my_g, mx_g, phi_m, phi_g, concord, b02, b05, b09, b11, b13, b14, b18
    gc.collect()

    # --- Block G (10..19): Cover-adaptive geomorphic scarps & fluvial knickpoints ---
    with rasterio.open(external_dir / "topo_10m_derived_100m_u8.tif") as src:
        t10_smax = clean_grid(src.read(2), eligible)
        t10_sstd = clean_grid(src.read(4), eligible)
        t10_rel = clean_grid(src.read(5), eligible)
        t10_curv = clean_grid(src.read(6), eligible)
        t10_coh = clean_grid(src.read(7), eligible)
        t10_hs = clean_grid(src.read(8), eligible)

    z_rel = robust_z_inplace(t10_rel, eligible)
    z_slp = robust_z_inplace(b19, eligible)
    cover = (1.0 / (1.0 + np.exp(1.2 * z_rel)) * 1.0 / (1.0 + np.exp(1.2 * z_slp))).astype(np.float32)
    X[:, 10] = cover[el_r, el_c]
    X[:, 11] = robust_z_inplace(b12, eligible)[el_r, el_c]
    X[:, 12] = z_slp[el_r, el_c]

    # Piedmont range-base inflection: active normal faults cluster near det_elev ~ 0 with sharp slope gradient
    gy_s, gx_s = np.gradient(ndi.gaussian_filter(b19, sigma=1.0, mode="nearest"))
    pied = np.hypot(gy_s, gx_s) * np.exp(-0.25 * np.square(robust_z_inplace(b12, eligible)))
    X[:, 13] = robust_z_inplace(pied, eligible)[el_r, el_c]
    del gy_s, gx_s, pied, cover, z_rel, b19

    topo10_comp = (
        0.30 * robust_z_inplace(t10_smax, eligible)
        + 0.25 * robust_z_inplace(t10_sstd, eligible)
        + 0.25 * robust_z_inplace(t10_curv, eligible)
        + 0.20 * robust_z_inplace(t10_hs, eligible)
    ).astype(np.float32)
    topo10_comp += 0.25 * hessian_ridge_max(topo10_comp, (1.0, 2.0))
    del t10_smax, t10_sstd, t10_rel, t10_curv, t10_hs

    with rasterio.open(external_dir / "lidar_scarp_features_u8.tif") as src:
        lid_valid = (src.read(12) > 0) & eligible
        lid_step = clean_grid(src.read(3), eligible)
        lid_lapn = clean_grid(src.read(4), eligible)
        lid_lapp = clean_grid(src.read(5), eligible)
        lid_down = clean_grid(src.read(6), eligible)
        lid_up = clean_grid(src.read(7), eligible)
        lid_coh = clean_grid(src.read(10), eligible)

    lid_raw = (
        0.25 * robust_z_inplace(lid_step, lid_valid)
        + 0.20 * robust_z_inplace(lid_lapn, lid_valid)
        + 0.20 * robust_z_inplace(lid_lapp, lid_valid)
        + 0.20 * robust_z_inplace(lid_down, lid_valid)
        + 0.15 * robust_z_inplace(lid_up, lid_valid)
    ).astype(np.float32)
    # Seam-free quantile matching across the 24.6% non-LiDAR gap using 10 m breakline ranks
    gap = eligible & ~lid_valid
    q_grid = np.linspace(0.0, 1.0, 501)
    if lid_valid.any() and gap.any():
        lid_raw[gap] = np.interp(
            topo10_comp[gap],
            np.quantile(topo10_comp[gap], q_grid),
            np.quantile(lid_raw[lid_valid], q_grid),
        ).astype(np.float32)
    lid_raw += 0.30 * hessian_ridge_max(lid_raw, (1.0, 2.2))
    lid_coh_seamless = np.where(lid_valid, robust_z_inplace(lid_coh, lid_valid), robust_z_inplace(t10_coh, gap)).astype(np.float32)

    X[:, 14] = lid_valid[el_r, el_c].astype(np.float32)
    X[:, 15] = robust_z_inplace(lid_raw, eligible)[el_r, el_c]
    X[:, 16] = lid_coh_seamless[el_r, el_c]
    X[:, 17] = robust_z_inplace(topo10_comp, eligible)[el_r, el_c]
    scarp_fused = 0.60 * robust_z_inplace(lid_raw, eligible) + 0.40 * robust_z_inplace(topo10_comp, eligible)
    X[:, 18] = robust_z_inplace(strike_worm_response(scarp_fused, half_len_px=5), eligible)[el_r, el_c]
    del lid_valid, lid_step, lid_lapn, lid_lapp, lid_down, lid_up, lid_coh, lid_raw, lid_coh_seamless, topo10_comp, t10_coh, scarp_fused

    with rasterio.open(external_dir / "dem10_chi_100m_i16.tif") as src:
        chi_step = clean_grid(src.read(1), eligible)
        chi_ksn = clean_grid(src.read(3), eligible)
    X[:, 19] = robust_z_inplace(0.6 * robust_z_inplace(chi_ksn, eligible) + 0.4 * robust_z_inplace(chi_step, eligible), eligible)[el_r, el_c]
    del chi_step, chi_ksn, b12, z_slp
    gc.collect()

    # --- Block H (20..27): Hydrothermal upflow, alteration ratios, MT clay-cap ---
    gy_b15, gx_b15 = np.gradient(ndi.gaussian_filter(b15, sigma=1.5, mode="nearest"))
    X[:, 20] = robust_z_inplace(b15, eligible)[el_r, el_c]
    X[:, 21] = robust_z_inplace(np.hypot(gy_b15, gx_b15), eligible)[el_r, el_c]
    X[:, 22] = robust_z_inplace(b17, eligible)[el_r, el_c]
    X[:, 23] = robust_z_inplace(k_th, eligible)[el_r, el_c]
    X[:, 24] = robust_z_inplace(u_th, eligible)[el_r, el_c]
    del gy_b15, gx_b15, b15, b17, k_th, u_th

    ws_rows, ws_stripped = read_sanitized_csv(external_dir / "gdr_wellspring_in_footprint.csv")
    vv_rows, vv_stripped = read_sanitized_csv(external_dir / "gdr_volcanic_vents_in_footprint.csv")
    receipts["stripped_leakage_columns"]["gdr_wellspring_in_footprint.csv"] = ws_stripped
    receipts["stripped_leakage_columns"]["gdr_volcanic_vents_in_footprint.csv"] = vv_stripped

    therm_imp = np.zeros(shape, dtype=np.float32)
    n_therm = 0
    for row in ws_rows:
        assert "dist_known_fault_px" not in row
        r_i, c_i = int(float(row["row"])), int(float(row["col"]))
        if not (0 <= r_i < shape[0] and 0 <= c_i < shape[1]):
            continue
        tc = float(row["temp_c"]) if row.get("temp_c") else 0.0
        tq = float(row["geothermquartz_c"]) if row.get("geothermquartz_c") else 0.0
        tch = float(row["geothermchalc_c"]) if row.get("geothermchalc_c") else 0.0
        w = max(0.0, (tc - 22.0) / 25.0) + max(0.0, (max(tq, tch) - 75.0) / 55.0)
        if w > 0.05:
            therm_imp[r_i, c_i] += float(min(w, 6.0))
            n_therm += 1
    therm_field = np.log1p(
        8.0 * ndi.gaussian_filter(therm_imp, sigma=6.0, mode="constant")
        + 25.0 * ndi.gaussian_filter(therm_imp, sigma=18.0, mode="constant")
    ).astype(np.float32)
    X[:, 25] = robust_z_inplace(therm_field, eligible)[el_r, el_c]
    del therm_imp, therm_field

    sinter_pts = _read_shapefile_points_in_zip(external_dir / "paleo_geothermal_regional.zip")
    probe_pts = _read_shapefile_points_in_zip(external_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip")
    sp_imp = np.zeros(shape, dtype=np.float32)
    for ux, uy in sinter_pts:
        cc = int(round((ux - transform.c) / transform.a))
        rr = int(round((uy - transform.f) / transform.e))
        if 0 <= rr < shape[0] and 0 <= cc < shape[1]:
            sp_imp[rr, cc] += 2.0
    for ux, uy in probe_pts:
        cc = int(round((ux - transform.c) / transform.a))
        rr = int(round((uy - transform.f) / transform.e))
        if 0 <= rr < shape[0] and 0 <= cc < shape[1]:
            sp_imp[rr, cc] += 0.6
    sp_field = np.log1p(
        10.0 * ndi.gaussian_filter(sp_imp, sigma=7.0, mode="constant")
        + 30.0 * ndi.gaussian_filter(sp_imp, sigma=20.0, mode="constant")
    ).astype(np.float32)
    X[:, 26] = robust_z_inplace(sp_field, eligible)[el_r, el_c]
    del sp_imp, sp_field

    vent_mask = np.zeros(shape, dtype=bool)
    for row in vv_rows:
        assert "dist_known_fault_px" not in row
        r_i, c_i = int(float(row["row"])), int(float(row["col"]))
        if 0 <= r_i < shape[0] and 0 <= c_i < shape[1]:
            vent_mask[r_i, c_i] = True
    d_vent = ndi.distance_transform_edt(~vent_mask).astype(np.float32) if vent_mask.any() else np.full(shape, 500.0, np.float32)
    X[:, 27] = robust_z_inplace(-np.log1p(d_vent), eligible)[el_r, el_c]
    del vent_mask, d_vent

    # --- Block S (28..33): Active strain, declustered seismicity & 2015-2026 ComCat ---
    X[:, 28] = robust_z_inplace(b07, eligible)[el_r, el_c]
    transtens = b08 / np.sqrt(b07 * b07 + b08 * b08 + 1e-12)
    X[:, 29] = robust_z_inplace(0.6 * robust_z_inplace(transtens, eligible) + 0.4 * robust_z_inplace(b04, eligible), eligible)[el_r, el_c]
    log_ieq = np.log(np.maximum(b16, 0.0) + 1e-6).astype(np.float32)
    log_deq = np.log(np.maximum(b10, 0.0) + 1e-6).astype(np.float32)
    X[:, 30] = robust_z_inplace(log_ieq, eligible)[el_r, el_c]
    X[:, 31] = robust_z_inplace(log_deq - log_ieq, eligible)[el_r, el_c]
    X[:, 32] = robust_z_inplace(hessian_ridge_max(log_ieq, (2.5, 6.0)), eligible)[el_r, el_c]

    comcat = parse_comcat_hypocenters(external_dir / "usgs_comcat_2015_2026_m30.txt", shape, transform)
    comcat_surf = build_comcat_3d_rupture_surface(comcat, shape, eligible)
    X[:, 33] = comcat_surf[el_r, el_c]

    receipts["external_counts"] = {
        "thermal_anomalies_in_footprint": n_therm,
        "paleo_sinter_sites": len(sinter_pts),
        "shallow_2m_temp_probes": len(probe_pts),
        "volcanic_vents": len(vv_rows),
        "comcat_total_events": comcat["total_events"],
        "comcat_near_grid_events": comcat["near_grid_events"],
    }
    del b04, b07, b08, b10, b16, transtens, log_ieq, log_deq, comcat_surf
    gc.collect()
    return X, receipts


def visible_network_features(
    visible: np.ndarray,
    p_geo_grid: np.ndarray,
    query_mask: np.ndarray,
) -> np.ndarray:
    """Compute strict fold-visible structural kinematics interacted with blind `p_geo`."""
    vis = np.asarray(visible, dtype=bool)
    strike, coh = local_strike(vis, smooth_px=3.0)
    comp, ncomp = ndi.label(vis, structure=STRUCT3)
    comp_len = np.bincount(comp.ravel(), minlength=ncomp + 1).astype(np.float32)

    # Visible endpoint map (pixels with <= 1 neighbour in 8-connectivity)
    nb_count = ndi.convolve(vis.astype(np.int8), np.ones((3, 3), np.int8), mode="constant") - vis.astype(np.int8)
    tips = vis & (nb_count <= 1)
    d_tip = ndi.distance_transform_edt(~tips).astype(np.float32) if tips.any() else np.full(vis.shape, 999.0, np.float32)

    d_vis, iy, ix = nearest_frame(vis)
    c1 = comp[iy, ix]
    d2 = np.full(vis.shape, 999.0, dtype=np.float32)
    if ncomp >= 2:
        nbits = int(np.ceil(np.log2(ncomp + 1)))
        for b in range(nbits):
            bit_c1 = (c1 >> b) & 1
            for val in (0, 1):
                sub = vis & (((comp >> b) & 1) == val)
                if not sub.any():
                    continue
                db = ndi.distance_transform_edt(~sub).astype(np.float32)
                use = (bit_c1 != val) & (db < d2)
                d2[use] = db[use]
                del db, use

    yy, xx = np.nonzero(query_mask)
    ay, ax = iy[yy, xx], ix[yy, xx]
    s = np.where(np.isfinite(strike[ay, ax]), strike[ay, ax], 0.0).astype(np.float32)
    d_par, d_perp, _ = offset_components((yy - ay).astype(np.float32), (xx - ax).astype(np.float32), s)

    dv = np.minimum(d_vis[yy, xx].astype(np.float32), 45.0)
    dp_perp = np.minimum(d_perp.astype(np.float32), 45.0)
    dp_par = np.minimum(np.abs(d_par).astype(np.float32), 45.0)
    dt = np.minimum(d_tip[yy, xx], 50.0)
    d2v = np.minimum(d2[yy, xx], 50.0)
    pgeo = p_geo_grid[yy, xx].astype(np.float32)

    # Tip propagation lobe: close to a visible tip AND aligned along-strike (`d_perp` small relative to `dt`)
    tip_lobe = np.exp(-dt / 18.0) * np.exp(-dp_perp / (3.5 + 0.25 * dt)) * (dt < 45.0)
    # Two-strand relay / stepover bridge: sits between two distinct mapped components (`dv + d2v` small)
    relay_bridge = np.exp(-(dv + d2v) / 22.0) * ((dv + d2v) < 60.0)

    y10, x10 = np.ogrid[-10:11, -10:11]
    disk10 = ((y10 * y10 + x10 * x10) <= 100).astype(np.float32)
    vis_dens = ndi.convolve(vis.astype(np.float32), disk10, mode="constant")[yy, xx]

    X_net = np.empty((yy.size, len(NETWORK_FEATURE_NAMES)), dtype=np.float32)
    X_net[:, 0] = np.log1p(dv)
    X_net[:, 1] = np.log1p(dp_perp)
    X_net[:, 2] = np.log1p(dp_par)
    X_net[:, 3] = tip_lobe.astype(np.float32)
    X_net[:, 4] = relay_bridge.astype(np.float32)
    X_net[:, 5] = np.log1p(comp_len[comp[ay, ax]])
    X_net[:, 6] = coh[ay, ax].astype(np.float32)
    X_net[:, 7] = np.log1p(vis_dens)
    X_net[:, 8] = pgeo
    X_net[:, 9] = pgeo * tip_lobe.astype(np.float32)
    X_net[:, 10] = pgeo * relay_bridge.astype(np.float32)
    X_net[:, 11] = pgeo * np.exp(-dv / 20.0).astype(np.float32)
    return X_net
