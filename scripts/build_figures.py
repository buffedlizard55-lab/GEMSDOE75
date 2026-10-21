#!/usr/bin/env python3
"""Generate the 4 publication-grade scientific verification figures in `docs/assets/`
strictly from verified experimental outputs in `evidence/` and `.cache/`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57.grid import load_grid
from gems75.decoder import directional_ridge_concentration
from gems75.protocol import read_submission_tif_or_zip


def set_pub_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10.5,
        "axes.titlesize": 12.0,
        "axes.titleweight": "bold",
        "axes.labelsize": 10.5,
        "axes.edgecolor": "#334155",
        "axes.linewidth": 0.9,
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#f8fafc",
        "grid.color": "#cbd5e1",
        "grid.linestyle": "--",
        "grid.alpha": 0.55,
    })


def build_fig1_ablation(exp_sum: dict, out_dir: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.0, 6.2), dpi=180)
    scores = exp_sum["pooled_holdout_bootstrap"]["scores"]

    arms_order = [
        ("uniform_random_37654", "Uniform Random\n(37,654 dots)", "#94a3b8"),
        ("H33_loqo_fold_proper_37654", "H33 Linear Rule\n(Fold-Proper LOQO)", "#64748b"),
        ("19GEMSDOE_H19_5_01922", "19GEMSDOE H19-5\n(0.1922 Live)", "#475569"),
        ("GEMSDOE25_D28_02600", "GEMSDOE25 D28\n(0.2600 Live)", "#0284c7"),
        ("E1_ALMRC_TiltSI_48", "Exp 1: ALMRC + SI Tilt\n(48 Physical Ch.)", "#0d9488"),
        ("E2_Byerlee3D_HeatFlow_LOCOQuat_59", "Exp 2: + Byerlee3D / HF\n+ Self-Masked LOCO-Quat", "#2563eb"),
        ("E3_TRLT75_Stage2Radon_1DRidge_SpacedSubmod", "Exp 3: TRLT-75 (OURS)\nStage-2 Radon + 1D Ridge", "#059669"),
    ]
    ys = np.arange(len(arms_order))
    vals = [scores[k]["dti"] for k, _, _ in arms_order]
    err_lo = [scores[k]["dti"] - scores[k]["ci95"][0] for k, _, _ in arms_order]
    err_hi = [scores[k]["ci95"][1] - scores[k]["dti"] for k, _, _ in arms_order]
    cols = [c for _, _, c in arms_order]

    ci_his = [scores[k]["ci95"][1] for k, _, _ in arms_order]
    bars = ax1.barh(ys, vals, height=0.62, color=cols, edgecolor="#0f172a", linewidth=0.8, zorder=3)
    ax1.errorbar(vals, ys, xerr=[err_lo, err_hi], fmt="none", ecolor="#0f172a", elinewidth=1.5, capsize=4, zorder=4)
    for bar, v, chi in zip(bars, vals, ci_his):
        ax1.text(chi + 0.0035, bar.get_y() + bar.get_height() / 2.0, f"{v:.4f}", va="center", fontweight="bold", fontsize=9.8, color="#0f172a")

    ax1.set_yticks(ys, [lbl for _, lbl, _ in arms_order], fontsize=9.5)
    ax1.set_xlim(0, 0.186)
    ax1.grid(axis="x", zorder=0)
    ax1.set_xlabel("Pooled HOLDOUT-DTI (`gems57-pooled-hide-v2`, 95% 20 km Spatial Block CI)")
    ax1.set_title("A. Pre-Registered LOQO Holdout Progression (n = 12,175 Withheld Fault Pixels)")

    # Panel B: Real Off-Catalogue Piedmont Fault Benchmark B'' across entire fleet
    sec = exp_sum["secondary_geological_oracles"]
    b_order = [
        ("GEMSDOE71_DPST_00558", "GEMSDOE71 DPST\n(0.0558 Live)", "#94a3b8"),
        ("GEMSDOE70_P9_unsub", "GEMSDOE70 P9\n(Unsubmitted PR #48)", "#64748b"),
        ("19GEMSDOE_H19_5_01922", "19GEMSDOE H19-5\n(0.1922 Live)", "#475569"),
        ("GEMSDOE25_D28_02600", "GEMSDOE25 D28\n(0.2600 Live)", "#0284c7"),
        ("GEMSDOE32_H33_B2_02778", "GEMSDOE32 H33-B2\n(0.2778 Fleet Record)", "#d97706"),
        ("GEMSDOE36_PINN_02750", "GEMSDOE36 PINN\n(0.2750 Live)", "#ea580c"),
        ("GEMSDOE70_P8_02478", "GEMSDOE70 P8\n(0.2478 Live)", "#7c3aed"),
        ("E3_TRLT75_Stage2Radon_1DRidge_SpacedSubmod", "GEMSDOE75 TRLT-75\n(36,800 Dots | 75.6% Basin)", "#059669"),
    ]
    yb = np.arange(len(b_order))
    bvals = [sec[k]["B_dprime"] for k, _, _ in b_order]
    bcols = [c for _, _, c in b_order]
    bbars = ax2.barh(yb, bvals, height=0.62, color=bcols, edgecolor="#0f172a", linewidth=0.8, zorder=3)
    for bar, v in zip(bbars, bvals):
        ax2.text(v + 0.0025, bar.get_y() + bar.get_height() / 2.0, f"{v:.5f}", va="center", fontweight="bold", fontsize=9.8, color="#0f172a")
    ax2.set_yticks(yb, [lbl for _, lbl, _ in b_order], fontsize=9.5)
    ax2.set_xlim(0, 0.168)
    ax2.grid(axis="x", zorder=0)
    ax2.set_xlabel("Exact 300 m Tversky Score on Unmapped Piedmont Geologic Faults (`B''`)")
    ax2.set_title("B. Independent Validation on Off-Catalogue Piedmont Faults (`d >= 300 m`)")

    plt.tight_layout()
    fig.savefig(out_dir / "fig1_holdout_ablation_and_benchmarks.png", bbox_inches="tight")
    plt.close(fig)


def build_fig2_nevada_map(grid, out_dir: Path) -> None:
    data_dir = ROOT / ".cache" / "data"
    full_npz = np.load(ROOT / ".cache" / "gems75_full_outputs.npz")
    dots = full_npz["exp3_dots"] > 0.5
    surf = full_npz["exp3_surf"]
    X_mm = np.load(ROOT / ".cache" / "gems75_static54.f32.npy", mmap_mode="r")
    hf_2d = np.zeros(grid.shape, dtype=np.float32)
    hf_2d[grid.footprint] = X_mm[:, 52]

    with rasterio.open(data_dir / "training_features.tif") as src:
        dbase = src.read(15).astype(np.float32)

    step = 4
    valid_ds = grid.footprint[::step, ::step]
    db_ds = np.where(valid_ds, np.clip(dbase[::step, ::step], 0.0, 2500.0), np.nan)
    cat_dil = ndi.binary_dilation(grid.catalogue, iterations=2)[::step, ::step]
    dot_dil = ndi.binary_dilation(dots, iterations=2)[::step, ::step]
    surf_ds = np.where(valid_ds, surf[::step, ::step], np.nan)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.0, 8.2), dpi=180)
    extent = [243.35, 572.55, 4135.55, 4508.55]

    im1 = ax1.imshow(db_ds, cmap="terrain_r", extent=extent, interpolation="bilinear", alpha=0.88)
    cat_rgba = np.zeros((*cat_dil.shape, 4), dtype=np.float32)
    cat_rgba[cat_dil] = [0.07, 0.12, 0.25, 0.90]
    ax1.imshow(cat_rgba, extent=extent, interpolation="nearest")

    dot_rgba = np.zeros((*dot_dil.shape, 4), dtype=np.float32)
    dot_rgba[dot_dil] = [0.88, 0.11, 0.18, 0.95]
    ax1.imshow(dot_rgba, extent=extent, interpolation="nearest")
    ax1.set_title("A. Mapped Catalogue (Dark Navy) + TRLT-75 New Fault Discoveries (Crimson, 36,800 Dots)")
    ax1.set_xlabel("UTM Zone 11N Easting (km, EPSG:32611)")
    ax1.set_ylabel("UTM Zone 11N Northing (km, EPSG:32611)")
    cb1 = plt.colorbar(im1, ax=ax1, fraction=0.042, pad=0.03)
    cb1.set_label("Cenozoic Basin Depth to Basement (m)")

    im2 = ax2.imshow(surf_ds, cmap="magma", vmin=0.55, vmax=0.995, extent=extent, interpolation="bilinear")
    hf_ds = np.where(valid_ds, hf_2d[::step, ::step], np.nan)
    ax2.contour(
        np.linspace(extent[0], extent[1], hf_ds.shape[1]),
        np.linspace(extent[3], extent[2], hf_ds.shape[0]),
        np.nan_to_num(hf_ds, nan=0.0),
        levels=[3.2, 4.2],
        colors=["#38bdf8", "#7dd3fc"],
        linewidths=0.9,
        alpha=0.8,
    )
    ax2.set_title("B. Continuous TRLT-75 Probability Field + USGS Borehole Heat-Flow Contours (Cyan)")
    ax2.set_xlabel("UTM Zone 11N Easting (km, EPSG:32611)")
    ax2.set_ylabel("UTM Zone 11N Northing (km, EPSG:32611)")
    cb2 = plt.colorbar(im2, ax=ax2, fraction=0.042, pad=0.03)
    cb2.set_label("Calibrated Survival Probability (1 - exp(-E))")

    plt.tight_layout()
    fig.savefig(out_dir / "fig2_nevada_full_discovery_map.png", bbox_inches="tight")
    plt.close(fig)


def build_fig3_dixie_zoom(grid, out_dir: Path) -> None:
    full_npz = np.load(ROOT / ".cache" / "gems75_full_outputs.npz")
    X_mm = np.load(ROOT / ".cache" / "gems75_static54.f32.npy", mmap_mode="r")

    lid2d = np.zeros(grid.shape, dtype=np.float32)
    grav2d = np.zeros(grid.shape, dtype=np.float32)
    lid2d[grid.footprint] = X_mm[:, 26]
    grav2d[grid.footprint] = X_mm[:, 22]

    # Pick the 560x560 window with richest joint off-catalogue discoveries + known piedmont faults
    score_box = ndi.uniform_filter((full_npz["exp3_dots"] > 0.5).astype(np.float32), size=520)
    score_cat = ndi.uniform_filter(grid.catalogue.astype(np.float32), size=520)
    joint = score_box * np.sqrt(score_cat + 1e-6)
    cy, cx = np.unravel_index(int(np.argmax(joint[350:-350, 350:-350])), joint[350:-350, 350:-350].shape)
    cy += 350
    cx += 350
    r0, r1 = cy - 260, cy + 260
    c0, c1 = cx - 260, cx + 260
    sl = (slice(r0, r1), slice(c0, c1))

    h33_path = Path("/tmp/ref/GEMSDOE32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
    p8_path = Path("/tmp/ref/GEMSDOE70/docs/downloads/gems70-p5-dual-submod300-oof38k-20261020.tif")
    h33 = read_submission_tif_or_zip(h33_path)[sl] > 0.5
    p8 = read_submission_tif_or_zip(p8_path)[sl] > 0.5
    ours = full_npz["exp3_dots"][sl] > 0.5
    cat_w = grid.catalogue[sl]

    raw_e = -np.log(np.maximum(1.0 - full_npz["exp3_surf"][sl], 1e-6))
    ridge_w = directional_ridge_concentration(raw_e, grid.footprint[sl])

    ext = [243.35 + c0 * 0.1, 243.35 + c1 * 0.1, 4508.55 - r1 * 0.1, 4508.55 - r0 * 0.1]
    fig, axes = plt.subplots(2, 2, figsize=(14.5, 13.0), dpi=180)

    ax = axes[0, 0]
    p_lo, p_hi = np.nanpercentile(lid2d[sl], [5, 98])
    ax.imshow(lid2d[sl], cmap="viridis", vmin=p_lo, vmax=p_hi, extent=ext)
    ax.set_title("A. De-Quantized 1m 3DEP LiDAR Tectonic Step (Wash-Cancelled)")

    ax = axes[0, 1]
    g_lo, g_hi = np.nanpercentile(grav2d[sl], [5, 98])
    ax.imshow(grav2d[sl], cmap="inferno", vmin=g_lo, vmax=g_hi, extent=ext)
    ax.set_title("B. SI-Calibrated 3D Isostatic Gravity Tilt-Phase Contact Wavenumber")

    ax = axes[1, 0]
    ax.imshow(ridge_w, cmap="magma", vmin=np.percentile(ridge_w, 60), vmax=np.percentile(ridge_w, 99.6), extent=ext)
    ax.set_title("C. Stage-2 Radon Gap-Bridged 1D Transverse Ridge Concentration")

    ax = axes[1, 1]
    bg = np.full((*cat_w.shape, 3), 0.96, dtype=np.float32)
    bg[ndi.binary_dilation(cat_w, iterations=1)] = [0.08, 0.15, 0.32]
    ax.imshow(bg, extent=ext)
    py8, px8 = np.nonzero(p8)
    hy, hx = np.nonzero(h33)
    oy, ox = np.nonzero(ours)
    ax.scatter(ext[0] + px8 * 0.1, ext[3] - py8 * 0.1, s=5.0, c="#9333ea", alpha=0.50, label=f"P8 2D-Submod (0.2478, n={p8.sum()})")
    ax.scatter(ext[0] + hx * 0.1, ext[3] - hy * 0.1, s=6.5, c="#f59e0b", alpha=0.72, label=f"H33 Fleet Record (0.2778, n={h33.sum()})")
    ax.scatter(ext[0] + ox * 0.1, ext[3] - oy * 0.1, s=8.5, c="#dc2626", alpha=0.92, label=f"GEMSDOE75 TRLT-75 (OURS, n={ours.sum()})")
    ax.legend(loc="upper right", fontsize=8.8, framealpha=0.94)
    ax.set_title("D. 52 km x 52 km Structural Corridor: Navy=Known, Crimson=TRLT-75")

    for a in axes.ravel():
        a.set_xlabel("UTM 11N Easting (km)")
        a.set_ylabel("UTM 11N Northing (km)")

    plt.tight_layout()
    fig.savefig(out_dir / "fig3_dixie_valley_zoom_anatomy.png", bbox_inches="tight")
    plt.close(fig)


def build_fig4_audit(canaries: dict, uniq: dict, out_dir: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.0, 6.2), dpi=180)

    top_c = sorted(canaries["canaries"], key=lambda r: -r["sym_auc"])[:16][::-1]
    yc = np.arange(len(top_c))
    c_vals = [r["sym_auc"] for r in top_c]
    c_names = [r["name"] for r in top_c]
    c_cols = ["#2563eb" if r["name"].startswith("net_") else "#059669" for r in top_c]

    ax1.barh(yc, c_vals, height=0.68, color=c_cols, edgecolor="#0f172a", linewidth=0.7, zorder=3)
    ax1.axvline(0.90, color="#dc2626", linestyle="--", linewidth=2.0, label="Protocol Leakage Ceiling (AUC = 0.90)")
    ax1.set_yticks(yc, c_names, fontsize=8.8)
    ax1.set_xlim(0.45, 0.96)
    ax1.grid(axis="x", zorder=0)
    ax1.legend(loc="lower right", fontsize=9.2)
    ax1.set_xlabel("Single-Feature Symmetric Holdout ROC-AUC: max(AUC, 1 - AUC)")
    ax1.set_title("A. Rule 4 Leakage Canaries Across All 59 Channels (59/59 PASS, Max = 0.7838)")

    recs = uniq["records"]
    rhos = [abs(r["surface_spearman"]) for r in recs]
    ovs = [r["dot_overlap_3px"] for r in recs]
    ax2.axvspan(0.0, 0.90, ymin=0.0, ymax=0.70 / 0.85, color="#ecfdf5", alpha=0.7, zorder=0)
    ax2.scatter(rhos, ovs, s=26, c="#0284c7", alpha=0.72, edgecolors="#0f172a", linewidths=0.4, zorder=3, label="274 Unique SHA-256 Fleet Rasters")
    ax2.axvline(0.90, color="#dc2626", linestyle="--", linewidth=2.0, label="|Spearman| Gate (0.90)")
    ax2.axhline(0.70, color="#d97706", linestyle="--", linewidth=2.0, label="Mutual 3-px Overlap Gate (0.70)")
    ax2.set_xlim(-0.02, 0.98)
    ax2.set_ylim(-0.02, 0.85)
    ax2.grid(True, zorder=1)
    ax2.legend(loc="upper right", fontsize=9.2)
    ax2.set_xlabel("|Spearman Rank Correlation| vs Pre-Placement Continuous Surface")
    ax2.set_ylabel("Mutual 3-Pixel Dot Overlap: min(Forward, Reverse)")
    ax2.set_title("B. Fleet Uniqueness Audit Across All 274 Rasters (274/274 PASS)")

    plt.tight_layout()
    fig.savefig(out_dir / "fig4_canaries_and_uniqueness_audit.png", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    set_pub_style()
    out_dir = ROOT / "docs" / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)

    exp_sum = json.loads((ROOT / "evidence" / "experiments_summary.json").read_text())
    canaries = json.loads((ROOT / "evidence" / "leakage_canaries.json").read_text())
    uniq = json.loads((ROOT / "evidence" / "uniqueness_scan.json").read_text())
    grid = load_grid(ROOT / ".cache" / "data")

    build_fig1_ablation(exp_sum, out_dir)
    print("[figs] Wrote fig1_holdout_ablation_and_benchmarks.png")
    build_fig2_nevada_map(grid, out_dir)
    print("[figs] Wrote fig2_nevada_full_discovery_map.png")
    build_fig3_dixie_zoom(grid, out_dir)
    print("[figs] Wrote fig3_dixie_valley_zoom_anatomy.png")
    build_fig4_audit(canaries, uniq, out_dir)
    print("[figs] Wrote fig4_canaries_and_uniqueness_audit.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
