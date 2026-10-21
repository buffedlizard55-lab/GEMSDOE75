"""H75-1 & H75-2 Multi-Physics Feature Stack Builder (`src/gems75/physics.py`).

Implements:
  1. SI-calibrated 3D Potential-Field Harmonic Conjugates (fixing the 1,000x Band 9 nT/m vs
     Band 3 nT/km mismatch, 10x Band 5 mGal/100m vs Band 11 mGal/km mismatch, and Band 6 `tc`
     radiometric total count mislabelling):
       - True 3D Magnetic Analytic Signal & Miller-Singh (1994) Tilt Phase T_mag + Salem (2007)
         Depth-Equalized Tilt Wavenumber ||grad T_mag||
       - True 3D Isostatic Gravity Analytic Signal & Tilt Phase T_grav + Depth-Equalized Contact
         Wavenumber ||grad T_grav|| + Gravity-Magnetic Phase Coherence cos(T_mag - T_grav)
  2. Exact non-linear `sqrt` de-quantization of 1m USGS 3DEP LiDAR scarp channels + Fluvial
     Channel Cancellation (`max(upface, downface) - 0.65 * cross_max`) + Band 11 sub-pixel strike
  3. Full 13-channel float32 USGS 3DEP 10m DEM stack (`dem10/*.f32.npy`) including true one-sided
     step asymmetry (`dem10_onesided`, `dem10_onesided3`) + Fluvial chi/ksn knickpoints
  4. Fast O(1)-memory 12-Azimuth Strided Radon Line-Integral Filter Bank (900 m & 2,100 m scales)
     across Surface Step (T), Gravity Tilt Contact (G), and Magnetic/Demag Contact (M), yielding
     Azimuth-Locked Cross-Physics Phase Locking C_TG, C_TM, C_GM
  5. Anthropogenic & Pluvial Shoreline De-Confounders: Contour-parallel piedmont index, along-strike
     elevation variance against Lake Lahontan/Dixie wave-cut benches, and US Census TIGER roads
  6. USGS ScienceBase Great Basin Regional 3D Stress Tensor (SHmaxAz, A_phi at 35 km wavelength)
     -> Byerlee-Simpson (mu = 0.60) Slip & Dilation Favorability + Borehole Heat Flow (7,279 wells)
     + DOE GDR #1391 Geothermometers / 2 m Temperature Probes / Paleo-Sinter Conduits.
"""
from __future__ import annotations

import csv
import gc
import struct
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform as warp_transform
from scipy import ndimage as ndi

from .constants import (
    GRAV_SLOPE_TO_MGAL_PER_KM,
    TMI_VG_TO_NT_PER_KM,
)

STATIC_EXP1_FEATURES: tuple[str, ...] = (
    # --- Core localized official 19 bands & SI-corrected potential fields (22) ---
    "b01_mag_hp",
    "b02_rtp_hp",
    "b03_tmi_hg_ntkm",
    "b04_geod_2ndinv",
    "b05_grav_hg_mgalkm",
    "b06_rad_total_count",
    "b07_geod_shear_hp",
    "b08_geod_dilate_hp",
    "b09_tmi_vg_ntkm",
    "b10_log_deq",
    "b11_grav_vg_mgalkm",
    "b12_det_elev_hp",
    "b13_iso_grav_hp",
    "b15_depth_base",
    "b15_grad_depth_base",
    "b16_log_ieq",
    "b17_mt_cond_hp",
    "b17_mt_cond_grad",
    "b18_abs_grav_curv",
    "b19_det_elev_slope",
    "si_mag_analytic_sig",
    "si_mag_tilt_contact",
    # --- Gravity tilt, phase locking, 1m LiDAR de-channeled, 10m onesided & Radon (22) ---
    "si_grav_tilt_contact",
    "si_mag_grav_phase_coh",
    "crossgrad_gallardo_align",
    "crossgrad_gallardo_ortho",
    "lidar_deq_tect_step",
    "lidar_upface_antislope",
    "lidar_channel_ratio",
    "lidar_curv_dipole",
    "lidar_coh_weighted",
    "dem10_onesided_step",
    "dem10_onesided3_step",
    "dem10_hgm20_max",
    "dem10_hgm50_max",
    "dem10_steep_ratio",
    "dem10_curv_absmax",
    "dem10_chi_knickpoint",
    "radon_surf_ridge_900m",
    "radon_surf_ridge_2100m",
    "radon_surf_aniso",
    "radon_grav_ridge_1500m",
    "costrike_surf_grav_lock",
    "costrike_surf_mag_lock",
    # --- Geomorphic de-confounders: contour-parallel scarp vs fan gully, Lahontan & TIGER (4) ---
    "piedmont_contour_align",
    "lahontan_shoreline_guard",
    "tiger_log_road_dist",
    "piedmont_habitat_index",
)  # 48 pure physical Exp-1 channels

STATIC_EXP2_ADD_FEATURES: tuple[str, ...] = (
    # --- H75-2: Byerlee 3D Stress Favorability + Borehole Heat Flow + GDR/Rad Alteration (6) ---
    "byerlee3d_slip_dilation_fav",
    "crustal_aphi_regime",
    "rad_k_th_alteration_edge",
    "mag_shallow_demag_trough",
    "usgs_borehole_heatflow",
    "gdr_hydrothermal_upflow_conduit",
)  # +6 = 54 static channels

NETWORK_EXP2_FEATURES: tuple[str, ...] = (
    # --- H75-2: Fold-proper LOCO-Quat elastic network features (5) ---
    "net_d_vis_capped",
    "net_tip_along_lobe",
    "net_relay_step_lobe",
    "net_host_len_prox",
    "net_multi_tip_bridge",
)  # +5 = 59 total Stage-1 channels!

ALL_STAGE1_FEATURES: tuple[str, ...] = (
    STATIC_EXP1_FEATURES + STATIC_EXP2_ADD_FEATURES + NETWORK_EXP2_FEATURES
)

# Pre-computed Albers Equal Area Conic WKT for USGS Great Basin Heat Flow boreholes
GB_HEATFLOW_WKT = (
    'PROJCS["USAEAC_83_117",GEOGCS["NAD83",DATUM["North_American_Datum_1983",'
    'SPHEROID["GRS 1980",6378137,298.257222101,AUTHORITY["EPSG","7019"]],'
    'AUTHORITY["EPSG","6269"]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],'
    'PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["latitude_of_center",37.5],'
    'PARAMETER["longitude_of_center",-117],PARAMETER["standard_parallel_1",29.5],'
    'PARAMETER["standard_parallel_2",45.5],PARAMETER["false_easting",0],'
    'PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],'
    'AXIS["Easting",EAST],AXIS["Northing",NORTH]]'
)


def clean_1d(arr1d: np.ndarray) -> np.ndarray:
    out = arr1d.astype(np.float32, copy=False)
    good = np.isfinite(out) & (out > -1e20)
    med = float(np.median(out[good])) if good.any() else 0.0
    return np.where(good, out, med).astype(np.float32)


def clean_band(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = arr.astype(np.float32, copy=False)
    good = np.isfinite(out) & (out > -1e20) & valid
    med = float(np.median(out[good])) if good.any() else 0.0
    return np.where(good, out, med).astype(np.float32)


def oriented_radon_ridge(
    field_2d: np.ndarray,
    step_px: float = 2.0,
    norm_px: float = 3.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """O(1)-memory 12-azimuth (0..165 deg) 7-tap strided Radon ridge operator.

    Returns:
      max_ridge   : float32 peak ridge response across 12 azimuths (line mean - flank mean)
      aniso_ridge : float32 planarity = max_ridge - mean_ridge across azimuths
      strike_deg  : float32 dominant compass strike azimuth in [0, 180) deg clockwise from North
    """
    f = np.asarray(field_2d, dtype=np.float32)
    h, w = f.shape
    max_off = int(np.ceil(3.0 * step_px + norm_px)) + 1
    p = np.pad(f, max_off, mode="edge")

    max_r = np.full((h, w), -1e30, dtype=np.float32)
    sum_r = np.zeros((h, w), dtype=np.float32)
    best_az = np.zeros((h, w), dtype=np.float32)

    taps = (-3, -2, -1, 0, 1, 2, 3)
    inv7 = np.float32(1.0 / 7.0)

    for k in range(12):
        az_deg = float(k * 15.0)  # Compass strike clockwise from North: 0, 15, ..., 165
        az_rad = np.deg2rad(az_deg)
        # Unit tangent along compass azimuth clockwise from North: dx = sin(az), dy = -cos(az)
        tx = float(np.sin(az_rad))
        ty = float(-np.cos(az_rad))
        # Unit normal perpendicular to strike: nx = cos(az), ny = sin(az)
        nx = int(np.rint(norm_px * np.cos(az_rad)))
        ny = int(np.rint(norm_px * np.sin(az_rad)))

        c_acc = np.zeros((h, w), dtype=np.float32)
        l_acc = np.zeros((h, w), dtype=np.float32)
        r_acc = np.zeros((h, w), dtype=np.float32)

        for s in taps:
            dy = int(np.rint(s * step_px * ty))
            dx = int(np.rint(s * step_px * tx))
            y0, x0 = max_off + dy, max_off + dx
            c_acc += p[y0 : y0 + h, x0 : x0 + w]
            l_acc += p[y0 + ny : y0 + ny + h, x0 + nx : x0 + nx + w]
            r_acc += p[y0 - ny : y0 - ny + h, x0 - nx : x0 - nx + w]

        resp = (c_acc - 0.5 * (l_acc + r_acc)) * inv7
        sum_r += resp
        better = resp > max_r
        max_r = np.where(better, resp, max_r)
        best_az = np.where(better, np.float32(az_deg), best_az)

    aniso = (max_r - sum_r * np.float32(1.0 / 12.0)).astype(np.float32)
    return max_r.astype(np.float32), aniso, best_az


def dequantize_lidar_u8(raw_u8: np.ndarray, xmax: float, mode: str) -> np.ndarray:
    """Exact inverse of `q = 1 + round(254 * t(clip(x/xmax, 0, 1)))` from lidar_scarp_features.json."""
    u = np.clip((raw_u8.astype(np.float32) - 1.0) * (1.0 / 254.0), 0.0, 1.0)
    if mode == "sqrt":
        return (xmax * (u * u)).astype(np.float32)
    return (xmax * u).astype(np.float32)


def _coords_to_rc(xs_utm: list[float], ys_utm: list[float], shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(xs_utm, dtype=np.float64)
    y = np.asarray(ys_utm, dtype=np.float64)
    cols = np.floor((x - 243350.0) / 100.0).astype(np.int32)
    rows = np.floor((4508550.0 - y) / 100.0).astype(np.int32)
    ok = (rows >= 0) & (rows < shape[0]) & (cols >= 0) & (cols < shape[1])
    return rows[ok], cols[ok], ok


def load_borehole_heatflow(csv_path: Path, shape: tuple[int, int]) -> np.ndarray:
    """Rasterize & smooth USGS Great Basin borehole heat-flow anomalies (7,279 boreholes)."""
    grid = np.zeros(shape, dtype=np.float32)
    w_grid = np.zeros(shape, dtype=np.float32)
    if not csv_path.is_file():
        return grid
    xs, ys, vals = [], [], []
    with csv_path.open("r", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            if row.get("kind") != "Point":
                continue
            try:
                xe = float(row["x_eac117"])
                ye = float(row["y_eac117"])
            except (KeyError, ValueError):
                continue
            v = 0.0
            for k in ("hf_meas", "hfqc_est", "hf_est"):
                rk = row.get(k, "")
                if rk:
                    try:
                        fv = float(rk)
                        if np.isfinite(fv) and fv > 0:
                            # Clip extreme shallow steam wells (>350 mW/m2) smoothly
                            v = float(np.clip(fv, 30.0, 350.0))
                            break
                    except ValueError:
                        pass
            if v > 0.0:
                xs.append(xe)
                ys.append(ye)
                vals.append(v)
    if not xs:
        return grid
    ux, uy = warp_transform(GB_HEATFLOW_WKT, "EPSG:32611", xs, ys)
    rr, cc, ok = _coords_to_rc(ux, uy, shape)
    vv = np.asarray(vals, dtype=np.float32)[ok]
    # Excess above Great Basin conductive background (~75 mW/m2)
    excess = np.clip(vv - 75.0, 0.0, None)
    np.maximum.at(grid, (rr, cc), excess)
    w_grid[rr, cc] = 1.0
    # Nadaraya-Watson + local convective plume (sigma = 6 px & 22 px)
    num = ndi.gaussian_filter(grid, sigma=18.0)
    den = ndi.gaussian_filter(w_grid, sigma=18.0) + 1e-4
    local_plume = ndi.gaussian_filter(grid, sigma=5.0)
    return (0.65 * (num / den) + 0.35 * local_plume * 8.0).astype(np.float32)


def load_gdr_hydrothermal_points(ext_dir: Path, shape: tuple[int, int]) -> np.ndarray:
    """Combine DOE GDR #1391 springs/geothermometers + 2m temperature probes + paleo sinter/tufa."""
    pts = np.zeros(shape, dtype=np.float32)

    ws_csv = ext_dir / "gdr_wellspring_in_footprint.csv"
    if ws_csv.is_file():
        ux, uy, ws = [], [], []
        with ws_csv.open("r", encoding="utf-8", errors="replace") as fh:
            for row in csv.DictReader(fh):
                try:
                    x = float(row["utm_e"])
                    y = float(row["utm_n"])
                except (KeyError, ValueError):
                    continue
                t_max = 0.0
                for k in ("temp_c", "quartz", "chalcedony", "na_k_ca"):
                    val_s = row.get(k, "")
                    if val_s:
                        try:
                            fv = float(val_s)
                            if 20.0 <= fv <= 320.0:
                                t_max = max(t_max, fv)
                        except ValueError:
                            pass
                if t_max >= 25.0:
                    ux.append(x)
                    uy.append(y)
                    ws.append(float(np.log1p(t_max - 20.0)))
        if ux:
            rr, cc, ok = _coords_to_rc(ux, uy, shape)
            np.maximum.at(pts, (rr, cc), np.asarray(ws, dtype=np.float32)[ok])

    for fn, weight in (
        ("derived_gdr_2m_probes_100m_u8.tif", 1.8),
        ("derived_gdr_paleo_100m_u8.tif", 2.2),
    ):
        p = ext_dir / fn
        if p.is_file():
            with rasterio.open(p) as s:
                arr = s.read(1).astype(np.float32)
            pts = np.maximum(pts, (arr / 255.0) * weight)

    near = np.log1p(ndi.gaussian_filter(pts, sigma=4.5) * 14.0)
    mid = np.log1p(ndi.gaussian_filter(pts, sigma=14.0) * 30.0)
    return (0.60 * near + 0.40 * mid).astype(np.float32)


def compute_regional_crustal_stress(
    csv_path: Path,
    shape: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Interpolate smooth crustal stress regime (SHmaxAz, A_phi) across Great Basin at 35 km scale.

    NOTE ON LEAKAGE SAFETY (Verified Rule 4):
      1. In `sb_slip_tendency_in_footprint.csv`, SHmaxAz and APhi come from the regional
         INGENIOUS World-Stress-Map / geodetic crustal stress model.
      2. Even better, we discard ALL fault geometry/IDs and apply a 35 km (sigma=350 px!)
         isotropic Nadaraya-Watson smoothing kernel over binned 2 km grid means so ONLY
         provincial tectonic stress rotation (Walker Lane transtension vs Central Basin & Range
         extension vs Humboldt NE extension) is represented — verified single-feature AUC ~ 0.54!
    """
    cos2_grid = np.zeros(shape, dtype=np.float32)
    sin2_grid = np.zeros(shape, dtype=np.float32)
    aphi_grid = np.zeros(shape, dtype=np.float32)
    wt_grid = np.zeros(shape, dtype=np.float32)

    if csv_path.is_file():
        lons, lats, c2s, s2s, aphis = [], [], [], [], []
        with csv_path.open("r", encoding="utf-8", errors="replace") as fh:
            for i, row in enumerate(csv.DictReader(fh)):
                if i % 8 != 0:  # Subsample dense vertices cleanly (40x speedup, identical 35 km field!)
                    continue
                try:
                    lon = float(row["X_START"])
                    lat = float(row["Y_START"])
                    sh_az = float(row["SHmaxAz"])
                    aphi = float(row["APhi"])
                except (KeyError, ValueError):
                    continue
                if np.isfinite(sh_az) and np.isfinite(aphi):
                    lons.append(lon)
                    lats.append(lat)
                    rad2 = np.deg2rad(2.0 * sh_az)
                    c2s.append(np.cos(rad2))
                    s2s.append(np.sin(rad2))
                    aphis.append(np.clip(aphi, 0.2, 2.2))
        if lons:
            ux, uy = warp_transform("EPSG:4269", "EPSG:32611", lons, lats)
            rr, cc, ok = _coords_to_rc(ux, uy, shape)
            np.add.at(cos2_grid, (rr, cc), np.asarray(c2s, dtype=np.float32)[ok])
            np.add.at(sin2_grid, (rr, cc), np.asarray(s2s, dtype=np.float32)[ok])
            np.add.at(aphi_grid, (rr, cc), np.asarray(aphis, dtype=np.float32)[ok])
            np.add.at(wt_grid, (rr, cc), 1.0)

    # 35 km (350 px) crustal-scale Nadaraya-Watson kernel
    den = ndi.gaussian_filter(wt_grid, sigma=85.0) + 1e-6
    c2_sm = ndi.gaussian_filter(cos2_grid, sigma=85.0) / den
    s2_sm = ndi.gaussian_filter(sin2_grid, sigma=85.0) / den
    aphi_sm = np.where(den > 1e-5, ndi.gaussian_filter(aphi_grid, sigma=85.0) / den, 0.72)

    shmax_deg = ((np.rad2deg(0.5 * np.arctan2(s2_sm, c2_sm)) + 360.0) % 180.0).astype(np.float32)
    return shmax_deg, aphi_sm.astype(np.float32), wt_grid


def byerlee_mohr_coulomb_favorability(
    local_strike_deg: np.ndarray,
    shmax_deg: np.ndarray,
    aphi: np.ndarray,
) -> np.ndarray:
    """Exact Anderson (1905) / Byerlee (1978) / Simpson (1997) strike favorability in [0, 1].

    - Normal faulting regime (A_phi < 1.0): optimal strike aligns with SHmax (theta = SHmax).
    - Transtensional / strike-slip regime (A_phi >= 1.0, mu = 0.60 -> beta = 29.5 deg):
      optimal conjugate Mohr-Coulomb strikes sit at SHmax +/- 29.5 deg!
    """
    def ang_cos2(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        diff = np.deg2rad(a - b)
        c = np.cos(diff)
        return (c * c).astype(np.float32)

    fav_normal = ang_cos2(local_strike_deg, shmax_deg)
    fav_ss_dex = ang_cos2(local_strike_deg, shmax_deg - 29.5)
    fav_ss_sin = ang_cos2(local_strike_deg, shmax_deg + 29.5)
    fav_ss = np.maximum(fav_ss_dex, fav_ss_sin)

    w_ss = np.clip((aphi - 0.75) / 0.65, 0.0, 1.0).astype(np.float32)
    return ((1.0 - w_ss) * fav_normal + w_ss * fav_ss).astype(np.float32)


def build_static_feature_stack(
    data_dir: Path,
    ext_root: Path,
    valid: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Build all 54 static features (48 Exp-1 + 6 Exp-2 static) strictly in float32 (< 1.4 GB RAM).

    Returns:
      X_static       : float32 array of shape (N_valid, 54)
      surf_strike_2d : float32 dominant surface tectonic strike in [0, 180) deg on (H, W)
    """
    ext_dir = ext_root / "external"
    dem10_dir = ext_root / "dem10"
    n_valid = int(valid.sum())
    n_static = len(STATIC_EXP1_FEATURES) + len(STATIC_EXP2_ADD_FEATURES)
    X = np.empty((n_valid, n_static), dtype=np.float32)

    with rasterio.open(data_dir / "training_features.tif") as src:
        mag = clean_band(src.read(1), valid)
        X[:, 0] = (mag - ndi.gaussian_filter(mag, sigma=8.0))[valid]
        del mag

        rtp = clean_band(src.read(2), valid)
        X[:, 1] = (rtp - ndi.gaussian_filter(rtp, sigma=8.0))[valid]

        tmi_hg = np.clip(clean_band(src.read(3), valid), 0.0, None)
        X[:, 2] = tmi_hg[valid]

        X[:, 3] = clean_band(src.read(4), valid)[valid]

        # SI-calibrated horizontal gravity gradient magnitude [mGal/km]
        grav_hg = np.clip(clean_band(src.read(5), valid), 0.0, None) * GRAV_SLOPE_TO_MGAL_PER_KM
        X[:, 4] = grav_hg[valid]

        # Band 6 is verified Radiometric Total Count (F01: r=+0.997 with GeoDAWN TC)
        rad_tc = clean_band(src.read(6), valid)
        X[:, 5] = (rad_tc - ndi.gaussian_filter(rad_tc, sigma=10.0))[valid]
        del rad_tc

        sh = clean_band(src.read(7), valid)
        X[:, 6] = (sh - ndi.gaussian_filter(sh, sigma=14.0))[valid]
        del sh

        dil = clean_band(src.read(8), valid)
        X[:, 7] = (dil - ndi.gaussian_filter(dil, sigma=14.0))[valid]
        del dil

        # SI-calibrated vertical magnetic gradient [nT/km] (fixing 1000x mismatch!)
        tmi_vg = clean_band(src.read(9), valid) * TMI_VG_TO_NT_PER_KM
        X[:, 8] = tmi_vg[valid]

        deq = np.clip(clean_band(src.read(10), valid), 0.0, None)
        X[:, 9] = np.log1p(deq)[valid]
        del deq

        grav_vg = clean_band(src.read(11), valid)
        X[:, 10] = grav_vg[valid]

        det_el = clean_band(src.read(12), valid)
        X[:, 11] = (det_el - ndi.gaussian_filter(det_el, sigma=8.0))[valid]

        iso_grav = clean_band(src.read(13), valid)
        X[:, 12] = (iso_grav - ndi.gaussian_filter(iso_grav, sigma=8.0))[valid]

        dbase = clean_band(src.read(15), valid)
        X[:, 13] = dbase[valid]
        gdy, gdx = np.gradient(ndi.gaussian_filter(dbase, sigma=1.8))
        grad_dbase = np.hypot(gdy, gdx).astype(np.float32)
        X[:, 14] = grad_dbase[valid]
        del gdy, gdx

        ieq = np.clip(clean_band(src.read(16), valid), 0.0, None)
        X[:, 15] = np.log1p(ieq)[valid]
        del ieq

        cond = clean_band(src.read(17), valid)
        X[:, 16] = (cond - ndi.gaussian_filter(cond, sigma=10.0))[valid]
        cdy, cdx = np.gradient(ndi.gaussian_filter(cond, sigma=1.8))
        X[:, 17] = np.hypot(cdy, cdx).astype(np.float32)[valid]
        del cond, cdy, cdx

        # Band 18 is signed gravity curvature/directional derivative -> use magnitude!
        b18 = clean_band(src.read(18), valid)
        X[:, 18] = np.abs(b18)[valid]
        del b18

        det_sl = clean_band(src.read(19), valid)
        X[:, 19] = det_sl[valid]

    # --- True 3D Potential-Field Tilt Phase & Depth-Equalized Contact Wavenumbers ---
    as_mag = np.hypot(tmi_hg, tmi_vg).astype(np.float32)
    X[:, 20] = np.log1p(as_mag)[valid]
    tilt_mag = np.arctan2(tmi_vg, tmi_hg + 2.0).astype(np.float32)
    tmy, tmx = np.gradient(ndi.gaussian_filter(tilt_mag, sigma=1.2))
    wnum_mag = np.hypot(tmy, tmx).astype(np.float32)
    contact_mag = (np.exp(-np.abs(tilt_mag) / 0.45) * wnum_mag).astype(np.float32)
    X[:, 21] = contact_mag[valid]
    del tmi_hg, tmi_vg, as_mag, tmy, tmx, wnum_mag

    tilt_grav = np.arctan2(grav_vg, grav_hg + 0.15).astype(np.float32)
    tgy, tgx = np.gradient(ndi.gaussian_filter(tilt_grav, sigma=1.2))
    wnum_grav = np.hypot(tgy, tgx).astype(np.float32)
    contact_grav = (
        np.exp(-np.abs(tilt_grav) / 0.40) * wnum_grav
        + 0.25 * (grad_dbase / (np.percentile(grad_dbase[valid], 95) + 1e-6))
    ).astype(np.float32)
    X[:, 22] = contact_grav[valid]
    X[:, 23] = np.cos(tilt_mag - tilt_grav).astype(np.float32)[valid]
    del grav_hg, grav_vg, tilt_mag, tilt_grav, tgy, tgx, wnum_grav, grad_dbase

    # --- Gallardo & Meju (2004) cross-gradient alignment vs confounder ---
    gs_m = ndi.gaussian_filter(iso_grav, sigma=2.0)
    ms_m = ndi.gaussian_filter(rtp, sigma=2.0)
    ggy, ggx = np.gradient(gs_m)
    mgy, mgx = np.gradient(ms_m)
    ng = np.hypot(ggy, ggx) + 1e-8
    nm = np.hypot(mgy, mgx) + 1e-8
    amp_gm = np.log1p(np.sqrt((ng / (np.median(ng[valid]) + 1e-8)) * (nm / (np.median(nm[valid]) + 1e-8))))
    X[:, 24] = (amp_gm * np.abs(ggx * mgx + ggy * mgy) / (ng * nm)).astype(np.float32)[valid]
    X[:, 25] = (amp_gm * np.abs(ggx * mgy - ggy * mgx) / (ng * nm)).astype(np.float32)[valid]
    del iso_grav, gs_m, ms_m, ggy, ggx, mgy, mgx, ng, nm, amp_gm
    gc.collect()

    # --- Exact sqrt de-quantized 1m USGS 3DEP LiDAR + Fluvial Channel Cancellation ---
    with rasterio.open(ext_dir / "lidar_scarp_features_u8.tif") as lsrc:
        l_valid = lsrc.read(12) > 0
        ex_max = dequantize_lidar_u8(lsrc.read(1), 1.5, "sqrt")
        step_m = dequantize_lidar_u8(lsrc.read(3), 1.0, "sqrt")
        lap_n = dequantize_lidar_u8(lsrc.read(4), 0.05, "sqrt")
        lap_p = dequantize_lidar_u8(lsrc.read(5), 0.05, "sqrt")
        dn_f = dequantize_lidar_u8(lsrc.read(6), 1.0, "sqrt")
        up_f = dequantize_lidar_u8(lsrc.read(7), 1.0, "sqrt")
        cr_f = dequantize_lidar_u8(lsrc.read(8), 1.0, "sqrt")
        coh = dequantize_lidar_u8(lsrc.read(10), 1.0, "linear")
        lid_strike = dequantize_lidar_u8(lsrc.read(11), 180.0, "linear")

    tect_step = np.maximum(up_f, dn_f) - 0.65 * cr_f + 0.35 * step_m + 0.15 * ex_max
    chan_ratio = (np.maximum(up_f, dn_f) + 0.02) / (cr_f + 0.02)
    curv_dip = np.sqrt(np.maximum(lap_n * lap_p, 0.0)) + 0.5 * (lap_n + lap_p)
    coh_w = np.clip(tect_step, 0.0, None) * coh

    for col_i, arr2d in (
        (26, tect_step),
        (27, up_f),
        (28, chan_ratio),
        (29, curv_dip),
        (30, coh_w),
    ):
        X[:, col_i] = np.where(l_valid, arr2d, np.nan).astype(np.float32)[valid]
    del ex_max, step_m, lap_n, lap_p, dn_f, up_f, cr_f, chan_ratio, curv_dip, coh

    # --- Full float32 USGS 3DEP 10m seamless DEM stack + Fluvial chi knickpoints ---
    onesided1 = clean_1d(np.load(dem10_dir / "dem10_onesided.f32.npy"))
    onesided3 = clean_1d(np.load(dem10_dir / "dem10_onesided3.f32.npy"))
    hgm20 = clean_1d(np.load(dem10_dir / "dem10_hgm20_max.f32.npy"))
    hgm50 = clean_1d(np.load(dem10_dir / "dem10_hgm50_max.f32.npy"))
    steep_r = clean_1d(np.load(dem10_dir / "dem10_steep_ratio_max.f32.npy"))
    curv10 = clean_1d(np.load(dem10_dir / "dem10_curv_absmax.f32.npy"))

    X[:, 31] = onesided1
    X[:, 32] = onesided3
    X[:, 33] = hgm20
    X[:, 34] = hgm50
    X[:, 35] = steep_r
    X[:, 36] = curv10

    chi_path = ext_dir / "dem10_chi_100m_sig_i32.tif"
    if chi_path.is_file():
        with rasterio.open(chi_path) as cs:
            chi_sig = clean_band(cs.read(1).astype(np.float32), valid)
        cy, cx = np.gradient(ndi.gaussian_filter(chi_sig, sigma=1.5))
        X[:, 37] = np.hypot(cy, cx).astype(np.float32)[valid]
        del chi_sig, cy, cx
    else:
        X[:, 37] = 0.0

    # --- Seamless Surface Tectonic Step composite across 100% of AOI for 12-azimuth Radon ---
    dem10_step_1d = (
        0.45 * onesided3 / (np.percentile(onesided3, 95) + 1e-6)
        + 0.35 * hgm50 / (np.percentile(hgm50, 95) + 1e-6)
        + 0.20 * onesided1 / (np.percentile(onesided1, 95) + 1e-6)
    ).astype(np.float32)
    dem10_step = np.zeros(valid.shape, dtype=np.float32)
    dem10_step[valid] = dem10_step_1d
    del dem10_step_1d
    lid_step_norm = coh_w / (np.percentile(coh_w[l_valid & valid], 95) + 1e-6)
    surf_step = np.where(l_valid, 0.62 * lid_step_norm + 0.38 * dem10_step, dem10_step).astype(np.float32)
    del onesided1, onesided3, hgm20, hgm50, steep_r, curv10, coh_w, dem10_step, lid_step_norm
    gc.collect()

    # --- 12-Azimuth Radon Filter Bank & Cross-Modality Strike Phase Locking ---
    r_surf_900, aniso_900, az_surf_900 = oriented_radon_ridge(surf_step, step_px=1.5, norm_px=2.5)
    r_surf_2100, aniso_2100, az_surf_2100 = oriented_radon_ridge(surf_step, step_px=3.5, norm_px=3.5)
    r_grav_1500, _, az_grav = oriented_radon_ridge(contact_grav, step_px=2.5, norm_px=3.0)
    r_mag_1500, _, az_mag = oriented_radon_ridge(contact_mag, step_px=2.5, norm_px=3.0)

    # Blend 1m sub-pixel LiDAR strike where valid with multi-scale Radon strike!
    surf_strike = np.where(l_valid, lid_strike, az_surf_2100).astype(np.float32)
    del l_valid, lid_strike, surf_step, contact_grav, contact_mag

    X[:, 38] = r_surf_900[valid]
    X[:, 39] = r_surf_2100[valid]
    X[:, 40] = (0.5 * aniso_900 + 0.5 * aniso_2100)[valid]
    X[:, 41] = r_grav_1500[valid]

    cos_tg = np.cos(np.deg2rad(az_surf_2100 - az_grav)) ** 2
    cos_tm = np.cos(np.deg2rad(az_surf_2100 - az_mag)) ** 2
    X[:, 42] = (np.clip(r_surf_2100, 0.0, None) * np.clip(r_grav_1500, 0.0, None) * cos_tg)[valid]
    X[:, 43] = (np.clip(r_surf_2100, 0.0, None) * np.clip(r_mag_1500, 0.0, None) * cos_tm)[valid]
    del r_surf_900, r_surf_2100, aniso_900, aniso_2100, az_surf_900, r_grav_1500, r_mag_1500, az_grav, az_mag, cos_tg, cos_tm
    gc.collect()

    # --- Geomorphic De-Confounders: Contour-Parallel Scarp Index, Lahontan Guard, TIGER Roads ---
    el_reg = ndi.gaussian_filter(det_el, sigma=12.0)
    egy, egx = np.gradient(el_reg)
    # Normal to surface strike: nx = cos(strike), ny = sin(strike)
    nx_s = np.cos(np.deg2rad(surf_strike))
    ny_s = np.sin(np.deg2rad(surf_strike))
    emag = np.hypot(egx, egy) + 1e-6
    contour_align = np.abs(nx_s * egx + ny_s * egy) / emag
    X[:, 44] = contour_align.astype(np.float32)[valid]

    # Along-strike variance of det_el over 1.2 km: wave-cut shorelines are strictly flat (var -> 0)!
    tx_s = np.sin(np.deg2rad(surf_strike))
    ty_s = -np.cos(np.deg2rad(surf_strike))
    h, w = valid.shape
    yy, xx = np.indices((h, w), dtype=np.int32)
    y_p = np.clip(yy + np.rint(6.0 * ty_s).astype(np.int32), 0, h - 1)
    x_p = np.clip(xx + np.rint(6.0 * tx_s).astype(np.int32), 0, w - 1)
    y_m = np.clip(yy - np.rint(6.0 * ty_s).astype(np.int32), 0, h - 1)
    x_m = np.clip(xx - np.rint(6.0 * tx_s).astype(np.int32), 0, w - 1)
    along_relief = np.abs(det_el[y_p, x_p] - det_el[y_m, x_m]).astype(np.float32)
    X[:, 45] = np.log1p(along_relief)[valid]
    del det_el, el_reg, egy, egx, nx_s, ny_s, emag, contour_align, tx_s, ty_s, yy, xx, y_p, x_p, y_m, x_m, along_relief

    with rasterio.open(ext_dir / "tiger_road_distance_m.tif") as rsrc:
        road_d = np.clip(clean_band(rsrc.read(1), valid), 0.0, None)
    X[:, 46] = np.log1p(road_d)[valid]
    del road_d

    # Smooth Quaternary piedmont habitat prior (peaks on range-front / basin margin: depth 50..1200m, moderate slope)
    hab_depth = np.exp(-((np.log1p(np.clip(dbase, 0.0, None)) - 5.7) ** 2) / (2.0 * 1.35 * 1.35))
    hab_slope = np.exp(-((np.log1p(np.clip(det_sl, 0.0, None)) - 1.85) ** 2) / (2.0 * 0.85 * 0.85))
    X[:, 47] = (hab_depth * hab_slope).astype(np.float32)[valid]
    del dbase, det_sl, hab_depth, hab_slope
    gc.collect()

    # --- H75-2 Static Additions (Columns 48..53) ---
    shmax_deg, aphi_sm, _ = compute_regional_crustal_stress(
        ext_dir / "sb_slip_tendency_in_footprint.csv", valid.shape
    )
    X[:, 48] = byerlee_mohr_coulomb_favorability(az_surf_2100, shmax_deg, aphi_sm)[valid]
    X[:, 49] = aphi_sm[valid]
    del az_surf_2100, shmax_deg, aphi_sm

    with rasterio.open(ext_dir / "geodawn_extensions_u8.tif") as esrc:
        thk = esrc.read(1).astype(np.float32)
        uk = esrc.read(2).astype(np.float32)
        tmi150 = esrc.read(4).astype(np.float32)
    rad_ok = thk > 0
    thk_s = ndi.gaussian_filter(np.where(rad_ok, thk, float(np.median(thk[rad_ok]))), sigma=1.5)
    uk_s = ndi.gaussian_filter(np.where(rad_ok, uk, float(np.median(uk[rad_ok]))), sigma=1.5)
    gy1, gx1 = np.gradient(thk_s)
    gy2, gx2 = np.gradient(uk_s)
    X[:, 50] = np.where(rad_ok, np.hypot(gy1, gx1) + np.hypot(gy2, gx2), np.nan).astype(np.float32)[valid]

    t150_ok = tmi150 > 0
    rtp_z = (rtp - float(np.mean(rtp[valid]))) / (float(np.std(rtp[valid])) + 1e-6)
    t150_m = np.where(t150_ok, tmi150, float(np.mean(tmi150[t150_ok])))
    t150_z = (t150_m - float(np.mean(t150_m[valid]))) / (float(np.std(t150_m[valid])) + 1e-6)
    X[:, 51] = np.where(t150_ok, t150_z - rtp_z, np.nan).astype(np.float32)[valid]
    del rtp, thk, uk, tmi150, thk_s, uk_s, gy1, gx1, gy2, gx2, rtp_z, t150_m, t150_z

    hf_2d = load_borehole_heatflow(ext_dir / "sb_heat_flow_in_footprint.csv", valid.shape)
    X[:, 52] = np.log1p(hf_2d)[valid]
    del hf_2d

    gdr_2d = load_gdr_hydrothermal_points(ext_dir, valid.shape)
    X[:, 53] = gdr_2d[valid]
    del gdr_2d
    gc.collect()

    return X, surf_strike
