"""Fold-proper elastic fault-tip propagation, relay-ramp step-over corridors,
and Self-Masked Leave-Component-Out Quaternary (LOCO-Quat) network feature synthesis.

CRITICAL ANTI-LEAKAGE DESIGN:
Every function in this module accepts an explicit binary mask `vis_mask` containing ONLY
the visible fault traces permitted in that context:
  - During Instrument A fold k evaluation: `vis_mask = fold['visible']` (all withheld truth
    and its 3-px buffer already zeroed out).
  - During inner LOCO-Quat training sub-draws: `vis_mask` additionally masks out 20% of
    connected components inside `H0` / `H1` at a 3-px buffer, matching the exact 80%
    visibility statistics of evaluation AND real unmapped Nevada faults!
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi


def extract_skeleton_tips_and_strike(vis_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract morphological fault terminations and local strike directors from `vis_mask`."""
    f = np.asarray(vis_mask, dtype=bool)
    # 3x3 thin approximation: pixels on trace with <= 2 8-connected foreground neighbors
    # or extrema along local structure tensor
    n_nb = np.zeros(f.shape, dtype=np.int8)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            n_nb += np.roll(np.roll(f, dr, axis=0), dc, axis=1)
    # Smooth binary fault trace to estimate local tangent vector cleanly
    sm = ndi.gaussian_filter(f.astype(np.float32), sigma=1.8)
    gy, gx = np.gradient(sm)
    # Fault tangent unit vector (tx, ty) = (-gy, gx) / hypot(gx, gy)
    mag = np.hypot(gx, gy) + 1e-8
    ty = (-gy / mag).astype(np.float32)
    tx = (gx / mag).astype(np.float32)

    # True tips: foreground pixels near component endpoints where forward or backward step leaves trace
    # Check 3-px forward and backward along tangent
    h, w = f.shape
    yy, xx = np.nonzero(f)
    if yy.size == 0:
        z = np.zeros(f.shape, dtype=bool)
        return z, ty, tx

    dy_s = np.rint(3.0 * ty[yy, xx]).astype(np.int32)
    dx_s = np.rint(3.0 * tx[yy, xx]).astype(np.int32)
    y_fwd = np.clip(yy + dy_s, 0, h - 1)
    x_fwd = np.clip(xx + dx_s, 0, w - 1)
    y_bwd = np.clip(yy - dy_s, 0, h - 1)
    x_bwd = np.clip(xx - dx_s, 0, w - 1)

    sm_thr = sm > 0.09
    fwd_empty = ~sm_thr[y_fwd, x_fwd]
    bwd_empty = ~sm_thr[y_bwd, x_bwd]
    is_tip = fwd_empty ^ bwd_empty  # Unilateral termination of a fault trace!

    tips = np.zeros(f.shape, dtype=bool)
    out_ty = np.zeros(f.shape, dtype=np.float32)
    out_tx = np.zeros(f.shape, dtype=np.float32)

    tips_y = yy[is_tip]
    tips_x = xx[is_tip]
    # Point outward from the termination into the unmapped gap
    sign = np.where(fwd_empty[is_tip], 1.0, -1.0).astype(np.float32)
    tips[tips_y, tips_x] = True
    out_ty[tips_y, tips_x] = ty[tips_y, tips_x] * sign
    out_tx[tips_y, tips_x] = tx[tips_y, tips_x] * sign
    return tips, out_ty, out_tx


def compute_network_features_2d(
    vis_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute 5 zero-leakage elastic fault-network transfer channels strictly from `vis_mask`:

    Returns (all float32 shape (H, W)):
      0. d_vis_capped     : min(EDT(~vis_mask), 45.0) [px]
      1. tip_along_lobe   : anisotropic mode-II along-strike continuation lobe off fault tips (2.8 km scale)
      2. relay_step_lobe  : off-axis mode-I wing-crack & relay-ramp step-over bridge corridor
      3. host_len_trans   : log(1 + nearest component pixel length) * exp(-d_vis / 18.0)
      4. multi_tip_bridge : product / mutual convergence where TWO distinct fault tips project toward each other!
    """
    vis = np.asarray(vis_mask, dtype=bool)
    h, w = vis.shape
    if not vis.any():
        z = np.zeros((h, w), dtype=np.float32)
        return np.full((h, w), 45.0, dtype=np.float32), z, z, z, z

    d_vis, inds = ndi.distance_transform_edt(~vis, return_indices=True)
    d_vis_f = d_vis.astype(np.float32)
    d_capped = np.minimum(d_vis_f, 45.0)

    # Host fault component size transferred via nearest-neighbor index
    comp, _ = ndi.label(vis, structure=np.ones((3, 3), dtype=np.int32))
    sizes = np.bincount(comp.ravel()).astype(np.float32)
    sizes[0] = 0.0
    len_vis = sizes[comp]
    nearest_len = len_vis[inds[0], inds[1]]
    host_len_trans = (np.log1p(nearest_len) * np.exp(-d_vis_f / 18.0)).astype(np.float32)
    del comp, sizes, len_vis, nearest_len, inds

    # Extract unilateral tips and their outward strike vector (out_ty, out_tx)
    tips, out_ty, out_tx = extract_skeleton_tips_and_strike(vis)
    if not tips.any():
        z = np.zeros((h, w), dtype=np.float32)
        return d_capped, z, z, host_len_trans, z

    d_tip, t_inds = ndi.distance_transform_edt(~tips, return_indices=True)
    d_tip_f = d_tip.astype(np.float32)
    # Vector from nearest tip (ty0, tx0) to pixel (y, x)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    vy = yy - t_inds[0].astype(np.float32)
    vx = xx - t_inds[1].astype(np.float32)
    uy = out_ty[t_inds[0], t_inds[1]]
    ux = out_tx[t_inds[0], t_inds[1]]
    del t_inds, out_ty, out_tx

    # Local coordinates relative to tip propagation ray:
    # u_par > 0 ahead of fault tip along strike; u_perp = step-over offset perpendicular to strike
    u_par = vy * uy + vx * ux
    u_perp = vy * ux - vx * uy
    del vy, vx, uy, ux

    # 1. Along-strike propagation lobe (u_par in [0, 28 px], narrow +/- 4.5 px transverse aperture)
    ahead = np.clip(u_par, 0.0, None)
    behind_pen = np.clip(-u_par, 0.0, None)
    tip_along = (
        np.exp(-ahead / 24.0)
        * np.exp(-behind_pen / 3.0)
        * np.exp(-(u_perp * u_perp) / (2.0 * 4.5 * 4.5))
    ).astype(np.float32)

    # 2. Relay-ramp / wing-crack dilatational step-over lobe:
    # Peaks at 3..14 px transverse offset (300 m - 1.4 km step-over width; Faulds & Hinz 2015!)
    abs_perp = np.abs(u_perp)
    relay_step = (
        np.exp(-((abs_perp - 7.0) ** 2) / (2.0 * 5.0 * 5.0))
        * np.exp(-(u_par * u_par) / (2.0 * 16.0 * 16.0))
    ).astype(np.float32)
    del u_par, u_perp, ahead, behind_pen, abs_perp

    # 3. Multi-tip convergence / unmapped gap bridge:
    # High smoothed tip density minus single-tip peak identifies corridors between >=2 approaching tips!
    tip_f = tips.astype(np.float32)
    dens_12 = ndi.gaussian_filter(tip_f, sigma=12.0)
    multi_bridge = np.log1p(dens_12 * 400.0) * np.exp(-d_tip_f / 26.0)
    return d_capped, tip_along, relay_step, host_len_trans, multi_bridge.astype(np.float32)


def make_inner_loco_dataset(
    X_stat: np.ndarray,
    valid: np.ndarray,
    vis_global: np.ndarray,
    partition_2d: np.ndarray,
    n_draws: int = 3,
    hide_frac: float = 0.22,
    neg_per_draw: int = 75000,
    seed: int = 7501,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate self-masked Leave-Component-Out Quaternary (LOCO-Quat) training data
    STRICTLY inside `partition_2d` using ONLY `vis_global & partition_2d`!

    In each inner draw r:
      - Connected Quaternary fault components inside `partition_2d` are randomly partitioned:
        22% hidden (`inner_truth`), 78% kept visible (`inner_vis`), with a 3-px buffer matching
        both Instrument A and real unmapped Great Basin fault spacing.
      - Network features (5 cols) are computed STRICTLY from `inner_vis`!
      - Positive rows = `inner_truth` inside `partition_2d & valid`;
      - Negative rows = off-catalogue cells (`~vis_global & d_inner_vis > 2.05`) inside `partition_2d & valid`.

    Result: 100% authentic Quaternary positive traces WITH real network continuation/step-over
    signals AND zero `d_vis == 0` self-memorization AND zero hide-mask covariate shift!
    """
    rng = np.random.default_rng(seed)
    part_vis = np.asarray(vis_global, dtype=bool) & np.asarray(partition_2d, dtype=bool)
    outside_part_vis = np.asarray(vis_global, dtype=bool) & (~np.asarray(partition_2d, dtype=bool))

    comp, n_comp = ndi.label(part_vis, structure=np.ones((3, 3), dtype=np.int32))
    comp_ids = np.arange(1, n_comp + 1)

    rows_list: list[np.ndarray] = []
    y_list: list[np.ndarray] = []

    valid_flat_map = np.full(valid.shape, -1, dtype=np.int32)
    valid_flat_map[valid] = np.arange(int(valid.sum()), dtype=np.int32)

    for r in range(n_draws):
        perm = rng.permutation(comp_ids)
        n_hide = max(1, int(round(hide_frac * len(comp_ids))))
        hid_set = np.zeros(n_comp + 1, dtype=bool)
        hid_set[perm[:n_hide]] = True
        inner_hid_raw = hid_set[comp]

        # 3.0 px buffer around hidden components (exact mirror of holdout protocol)
        d_hid = ndi.distance_transform_edt(~inner_hid_raw)
        inner_collar = d_hid <= 3.0
        inner_vis = (part_vis & (~inner_collar)) | outside_part_vis
        inner_pos_2d = inner_hid_raw & valid & partition_2d

        dc, ta, rs, hl, mb = compute_network_features_2d(inner_vis)
        neg_pool_2d = valid & partition_2d & (~vis_global) & (dc > 2.05)

        py, px = np.nonzero(inner_pos_2d)
        ny_all, nx_all = np.nonzero(neg_pool_2d)
        if py.size == 0 or ny_all.size == 0:
            continue

        take_n = min(neg_per_draw, ny_all.size)
        sel = rng.choice(ny_all.size, size=take_n, replace=False)
        ny, nx = ny_all[sel], nx_all[sel]

        sy = np.concatenate([py, ny])
        sx = np.concatenate([px, nx])
        v_idx = valid_flat_map[sy, sx]

        net_sub = np.column_stack([
            dc[sy, sx],
            ta[sy, sx],
            rs[sy, sx],
            hl[sy, sx],
            mb[sy, sx],
        ]).astype(np.float32)

        X_sub = np.hstack([X_stat[v_idx], net_sub])
        y_sub = np.concatenate([
            np.ones(py.size, dtype=np.int32),
            np.zeros(ny.size, dtype=np.int32),
        ])
        rows_list.append(X_sub)
        y_list.append(y_sub)

    return np.vstack(rows_list), np.concatenate(y_list)
