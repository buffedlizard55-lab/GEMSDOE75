# Limitations, Residual Risks, and Remaining High-Value Work

## 1. Strict Epistemic & Protocol Boundaries of This Run

1. **No live DrivenData weekly slot consumed (`live_weekly_slots_consumed = 0`):**
   - Per Parallel-Run Protocol Rule 6, this autonomous research session **never uploads to DrivenData or spends a team weekly submission slot** (`3 / week` cap under DOE/NLR Official Rules `96647.pdf`).
   - All performance numbers for `gemsdoe75-h75-1-cover-multiphysics-comcat3d-v1.tif` are strictly labeled **`HOLDOUT-DTI`** (`evaluator_version: "gems57-pooled-hide-v2"`, `1,000` paired spatial-cluster bootstrap draws). No leaderboard projection is ever stated as a score.
2. **Public repository registry completeness scope:**
   - Uniqueness was verified exhaustively across **all `102` readable GeoTIFFs (`103` total entries including `smoke.tif`)** across the indexed public `buffedlizard55-lab` repositories. Any private local files or unpushed branches held by external teammates outside GitHub cannot be inspected without their hashes.
3. **Literal vs halo-unsaturated registry overlap reading:**
   - Under `vendor/gems57/uniqueness.py`'s unmodified `literal_reading`, `4` space-filling calibration lattices (`calib_r13lattice_00904.tif` at `99.872%` 3-px halo coverage, `r13_lattice_s5_00904.tif` at `99.872%`, `r14_union_tips10_lat6.tif` at `76.211%`, `r11_greedy_mp.tif` at `73.662%`) cover $> 73\%$ of the entire study area, forcing any independent geological prediction to overlap $> 0.70$. Across all **`98 / 98` non-lattice geological rasters**, worst 3-px forward overlap is **`0.69489 <= 0.70000` (`0` firings)**, overlap with `H33` is **`0.41298`**, and max `|Spearman rho|` across all `102` rasters is **`0.04343`**. Both readings are preserved verbatim in `evidence/run-card.json` and on the site.
4. **3D ComCat earthquake spatial coverage unevenness:**
   - The official `2015–2026` USGS ANSS ComCat catalog (`1,401` events $M \ge 3.0$) illuminates seismically active Basin-and-Range structures dramatically (e.g., Silver Springs `M5.68`, Parker Butte `M5.71`, Monte Cristo Range `M6.5`), whereas aseismic / locked faults in northern Winnemucca with multi-millennial recurrence intervals must rely on upward-continued potential-field tilt worms, MT clay-cap edges, and visible tip/relay geometry.
5. **Single-stage GBDT spatial receptive field:**
   - While multi-scale Gaussian derivatives, upward-continued potential-field worms ($200\text{ m} \to 2\text{ km}$), and 1D Steger Hessian crest skeletonization capture long-wavelength structural continuity well, a genuine multi-resolution U-Net / ConvNeXt backbone trained with direct differentiable Tversky-kernel loss on `EPSG:32611` patches could capture curved listric fault geometry even more sharply.

## 2. Recommended Next Steps for Human Selector & Next Research Cycle

1. **Human Selector Weekly Slot Decision:** Compare `GEMSDOE75`'s `evidence/run-card.json` (`Suite N = 0.2067 [0.1984, 0.2140]`, `Suite Q = 0.2041 [0.1860, 0.2213]`, `Suite D = 0.0679 [0.0620, 0.0739]`) against sibling parallel lanes (`GEMSDOE73`–`GEMSDOE78`) and promote the highest-scoring, mutually non-overlapping lane within the weekly `3`-submission budget.
2. **Next Lane Candidate (`H75-2` + Differentiable 2D Polyline U-Net):** Train an orientation-equivariant 2D U-Net directly optimizing the differentiable exact 6-shell Tversky objective on multi-height potential-field worms (`100 m, 300 m, 800 m, 2000 m`) + `2015–2026` relocated waveform catalog (GrowClust / NSL).
3. **Upstream Shared-Template Patch PR (`60GEMSDOE`):** Upstream our three verified fixes (`IR-75-01` `B06` radiometric TC label fix, `IR-75-02` exact 6-shell Bernoulli tail `k_self`, and `IR-75-06` `halo_coverage_fraction > 0.70` lattice classification in `uniqueness.py`) cleanly into `buffedlizard55-lab/60GEMSDOE`.
