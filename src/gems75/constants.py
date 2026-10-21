"""Pre-registered physical, geometric, and protocol constants for GEMSDOE75."""
from __future__ import annotations

import numpy as np

# Competition EPSG:32611 grid parameters
GRID_SHAPE: tuple[int, int] = (3730, 3292)
GRID_CRS: str = "EPSG:32611"
GRID_TRANSFORM: tuple[float, ...] = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
PIXEL_SIZE_M: float = 100.0

# Official Distance-Weighted Tversky Index parameters
ALPHA: float = 0.2
BETA: float = 0.8
RADIUS_PX: float = 3.0
RADIUS_M: float = 300.0

# Exact 21 positive-weight cells inside the 300 m (3.0 px) triangular kernel on Z^2
KERNEL_300M: tuple[tuple[int, int, float], ...] = tuple(
    (dy, dx, float(1.0 - np.hypot(dy, dx) / 3.0))
    for dy in range(-2, 3)
    for dx in range(-2, 3)
    if np.hypot(dy, dx) < 3.0
)

# SI unit conversion factors empirically verified on training_features.tif
# Band 3 (tmi_hg) is in nT/km [p50=13.16, p99=189.2], whereas Band 9 (tmi_vg) is in nT/m [p99=0.794]
TMI_VG_TO_NT_PER_KM: float = 1000.0
# Band 5 (iso_grav_anom_slope) is in mGal/100m [p99=0.368], whereas Band 11 (iso_grav_anom_vg) is in mGal/km [p99=4.24]
GRAV_SLOPE_TO_MGAL_PER_KM: float = 10.0

# Pre-registered holdout & emission parameters (frozen prior to holdout evaluation)
EROSION_PX: int = 12
FLANK_COLLAR_PX: float = 2.05   # Excludes d(visible_faults) <= 2.0 px (min d = sqrt(5) = 2.2361 px on Z^2)
MATCHED_DOT_BUDGET: int = 37654  # Exact mass parity for Exp 1 & Exp 2 vs H33 / P8 / P9
CANDIDATE_DOT_BUDGET: int = 36800  # Pre-committed Exp 3 Tversky-pruned high-precision ridge budget

# Protocol hard gates
CANARY_AUC_MAX: float = 0.90
SPEARMAN_MAX: float = 0.90
DOT_OVERLAP_MAX: float = 0.70
