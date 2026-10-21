# Next-Session Handoff · GEMSDOE75 (2026-10-21)

## 1. Completed in This Session (`arena/e44a1ed5-gemsdoe75`)

1. **Restored & Sanitized Full Competition + External Feature Stack (`.cache/gems_data/`, `.cache/bands/`):**
   - Restored SHA-256-verified competition rasters (`training_features.tif`, `labels.tif`, `existing_faults.tif`, `sample_submission.tif`), 12 external layers (`lidar_scarp_features_u8.tif`, `topo_10m_derived_100m_u8.tif`, `dem10_chi_100m_i16.tif`, `geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`, `derived_sgmc_faults_100m_u8.tif`, `gdr_wellspring_in_footprint.csv`, `gdr_qfaults_traces.csv`, `gdr_volcanic_vents_in_footprint.csv`, `trace_segments_utm11.csv`), and 62 canonical registry rasters from `buffedlizard55-lab/60GEMSDOE` (`scripts/download_competition_data.sh`, `evidence/data_restore_receipt.json`).
   - Scrubbed all `58,171` unflagged `-3.4028235e+38` (`-FLT_MAX`) sentinel values across `3,073` active-footprint pixels in `training_features.tif` (`scripts/prepare_data.py`, `evidence/prepared_manifest.json`).
2. **Live External Verification & Irregularity Discovery (`evidence/comcat_verification.json`):**
   - Verified live DrivenData public leaderboard (`#1 xiaofanhu` `0.4413`, `#2 cfld__` `0.3904`, `#3 Batik Shirt Brothers` `0.3894`, `#47 extradr19` `0.2778`).
   - Queried live USGS ANSS ComCat FDSN event API (`95,541` $M \ge 1.5$ and `317` $M \ge 4.2$ epicentres in footprint) and proved **`IR-75-BAND10-DEQ-SIGN`**: Official Band 10 (`10_deq_n100a15`, tagged `"Distance to earthquake"`) correlates negatively with true epicentre distance (`Spearman = -0.83271`) and positively with Band 16 earthquake intensity (`Spearman = +0.84048`), proving Band 10 is **Earthquake Density ($D_{\text{eq}}$)**, not distance.
3. **47-Feature Single-Feature Leakage Canary (`Rule 4`, `evidence/leakage_canary.json`):**
   - All 47 sanitized features tested alone on `buffered_component_draw` (`22,893` withheld positive pixels) passed (`max_discriminative_auc = 0.59003 <= 0.90` on `lidar_lappos_max`, `0` features flagged).
4. **Executed 3 Preregistered `GEMSDOE75` (`H75-1`) Experiments (`src/gems_doe/h75_lane.py`, `evidence/h75_experiments.json`):**
   - **`E1` (Label-Free 4-Domain Surface + Lahontan Mimic Filter + Sign-Corrected $D_{\text{eq}}$):** `HOLDOUT-DTI = 0.0582 [0.0474, 0.0699]`, `SGMC-off-DTI = 0.1110`.
   - **`E2` (4-Quadrant LOQO `HistGradientBoosting` + 4-Domain Corroboration):** `HOLDOUT-DTI = 0.0656 [0.0539, 0.0773]`, `SGMC-off-DTI = 0.1226`.
   - **`E3` (12-Azimuth Strike-Projected Tip & Relay-Bridge Continuation with $B=2.0\text{ px}$ Kernel-Spill Ramp + 4-Domain LOQO Ridge Crests, decoded via $d_{\min}=2.85\text{ px}$ Poisson Disk, `38,200` dots):**
     - Fold-Blind `HOLDOUT-DTI` = **`0.1121 [0.0980, 0.1256]`** (`gems57-pooled-hide-v2`, `22,893` withheld positives)
     - Static Full-Catalogue `HOLDOUT-DTI` = **`0.0079 [0.0068, 0.0090]`** (**2.03x** `H33-2-B2` `0.0039` and **3.08x** `GEMS70-P5` `0.0026`)
     - Off-Catalogue `SGMC` Bedrock Fault Discovery DTI = **`0.1018`** (vs `H33-2-B2` `0.0954`, `GEMS36-PINN` `0.0968`, `D2.8` `0.0954`)
5. **Packaged & Verified Unique GeoTIFF Deliverable (`submissions/gemsdoe75-h75-strike-corrob-b2-d285-k38200-20261021-zero.tif`):**
   - Packaged via `vendor/gems57/submission_writer.py` (`sha256: 9156bf61b5a17ba11695731620f93b2ad2f5ed9835c2bc01834deecedc11f6af`, `141,260 bytes`, `min = 0.0`, `max = 1.0`, `n_nan = 0`, `n_inf = 0`, `0` dots within `2 px` of mapped catalogue).
   - Passed canonical registry uniqueness (`max 3-px dot overlap = 55.87% <= 70%`, `28.30%` vs `H33-2-B2`, `max |Spearman| = 0.1051 <= 0.90`).

## 2. Recommended Next Steps for Future Sessions

1. **Record `ORGANIZER-CONFIRMED` Live Score Receipt:** Once `submissions/gemsdoe75-h75-strike-corrob-b2-d285-k38200-20261021-zero.tif` is uploaded to DrivenData by the selector, log the live portal score and timestamp in `evidence/run-card.json` as an `ORGANIZER-CONFIRMED` anchor.
2. **Test Hypothesis `H75-5` (Anisotropic Eikonal Geodesic Minimum-Action Path Linking Across Relay Gaps):** Solve a strike-anisotropic Eikonal minimum-cost path $\int (1 - S_{E2}(s) + \lambda \sin^2\Delta\theta)\,ds$ between degree-1 morphological fault tips within $5\text{ km}$ to test whether explicit geodesic bridge trajectories improve off-catalogue relay recovery beyond the 12-azimuth ray projection in `H75-E3`.
3. **Upstream Patch for `IR-75-BAND10-DEQ-SIGN` and `IR-75-DENSE-COMPARATOR-SATURATION`:** Propagate the Band 10 (`deq_n100a15`) earthquake-density sign documentation and the `two_phase_summary` dot-field vs continuous-surface comparator separation to the central template repository (`buffedlizard55-lab/60GEMSDOE`).
