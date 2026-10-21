# Limitations, Irregularities & Verification Scope · GEMSDOE75 (2026-10-21)

## 1. Flagged Irregularities & Resolutions

1. **`IR-75-BAND10-DEQ-SIGN` (`training_features.tif` Band 10 `10_deq_n100a15` Metadata vs Physical Values):**
   - **Finding:** Band 10's GeoTIFF band description reads `"deq_n100a15 - Distance to earthquake"`, but values range from `0.0` in aseismic northern Nevada to `4,962,515.0` directly on the Chalfant Valley, Mammoth Lakes, and Mina Deflection earthquake swarms. Against live USGS ANSS ComCat $M \ge 4.2$ epicentre distances (`evidence/comcat_verification.json`), `Spearman(d_ComCat, deq_n100a15) = -0.83271`, and `Spearman(deq_n100a15, Band 16 ieq_n100a15) = +0.84048`.
   - **Resolution:** Band 10 is **Earthquake Density ($D_{\text{eq}}$)** (`d` = density, `eq` = earthquake), not distance. `GEMSDOE75` uses `+log1p(deq_n100a15)` with positive polarity.
2. **`IR-75-SENTINEL-NODATA` (`58,171` Unflagged `-3.4028235e+38` Sentinels Inside Active Footprint):**
   - **Finding:** `training_features.tif` has `nodata = None` in its GeoTIFF profile while containing `58,171` `-3.4028235e+38` (`-FLT_MAX`) values across `3,073` active-footprint pixels (`3,061` boundary pixels across 18 bands + `12` interior pixels in Band 6 `tc`).
   - **Resolution:** Scrubbed to `NaN` in `scripts/prepare_data.py` (`evidence/prepared_manifest.json`) and median-imputed inside the footprint before spatial filtering; `0` `NaN`/`Inf` in emitted `.tif`.
3. **`IR-75-STATIC-MASK-HOLDOUT-BIAS` (Evaluating Pre-Masked Full-Catalogue Rasters on `buffered_component_draw`):**
   - **Finding:** Scoring a static raster that already zeroed $d(x, C) \le 2.0\text{ px}$ on the *full* catalogue $C$ (`H33-2-B2`, `GEMS36-PINN`, `GEMS70-P5`) directly on `buffered_component_draw` folds yields `0.0039`–`0.0040` because withheld positive segments `fold['truth']` are subsets of $C$.
   - **Resolution:** Both the **fold-blind procedure** (where the $B = 2.0\text{ px}$ collar and strike kinematics use only `fold['visible']`, yielding `0.1121 [0.0980, 0.1256]`) and the **static full-catalogue raster** (`0.0079 [0.0068, 0.0090]`, 2.03x `H33-2-B2`), plus off-catalogue `SGMC` bedrock fault discovery (`0.1018` vs `0.0954`), are reported side by side.
4. **`IR-75-DENSE-COMPARATOR-SATURATION` (5 Registry Comparators with `> 70%` Footprint 3-px Halo):**
   - **Finding:** Five historical registry rasters (`17GEMSDOE` `E-proba-multiscale` at `100.0%` footprint halo in `.cache/inputs/registry-witness.tif`, `calib_r13lattice_00904.tif` and `r13_lattice_s5_00904.tif` at `99.87%`, `r14_union_tips10_lat6.tif` at `76.20%`, and `r11_greedy_mp.tif` at `73.97%`) cover more than `70%` of the entire footprint with their 3-px halo, making `< 70%` literal 3-px overlap mathematically impossible for any non-empty candidate.
   - **Resolution:** Reported transparently via `vendor/gems57/uniqueness.py::two_phase_summary`: both the literal reading and the satisfiable dot-field reading (`58/58` canonical dot-field comparators `PASS`, max overlap `55.87% <= 70%`, max `|Spearman| = 0.1051 <= 0.90`) are published side by side.

## 2. Leaderboard Discrepancy in Original Prompt (`0.4413` vs `0.3195`)

- The project prompt mentions both `0.4413` ("Currently the highest score on the leaderboard is `0.4413`") and `0.3195` ("The current highest score on the leaderboard is `0.3195`").
- Live inspection of `https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/` on `2026-10-21` confirms that `#1 xiaofanhu` is at **`0.4413`**, `#2 cfld__` is at **`0.3904`**, `#3 Batik Shirt Brothers` is at **`0.3894`**, and `#47 extradr19` (`h33-h33-2-b2`) is at **`0.2778`**. `0.3195` was an earlier mid-competition milestone.

## 3. Holdout vs Hidden Test Set Generalization Caveat

- `HOLDOUT-DTI` (`0.1121 [0.0980, 0.1256]` on `buffered_component_draw` and `0.1018` on off-catalogue `SGMC` bedrock faults) measures recovery of withheld USGS/INGENIOUS Quaternary fault components and unmapped SGMC bedrock faults. The organizer's hidden test set $G_{\text{test}}$ may have a different spatial mix of near-network extensions vs concealed intrabasin faults; therefore, `HOLDOUT-DTI` is never reported as a projected leaderboard score.
