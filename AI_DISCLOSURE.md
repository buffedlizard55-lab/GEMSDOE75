# AI Assistance & Scientific Reproducibility Disclosure

## Competition
- **Challenge:** [DOE GEMS: Geothermal Exploration with Machine Learning for Subsurface Fault Discovery](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- **Repository:** `https://github.com/buffedlizard55-lab/GEMSDOE75`
- **Primary Submission Artifact:** `docs/downloads/gems75-trlt-radon-loco-ridge-20261021-zeros.tif` (`SHA-256: e04df46e8a0770b470bf8846ed2aff966fd192e7ff71fbc4d82724b28c0b1b71`)

## Scope of AI Tool Usage
Autonomous coding agent tooling on Arena.ai was used to:
1. Perform forensic code, physical-unit, and metric audits across the competition feature stack and sibling GEMSDOE repositories.
2. Implement modular, leak-free Python source code (`src/gems75/`), automated data integrity checks (`scripts/fetch_data.py`, `scripts/prepare_data.py`), single-feature holdout leakage canaries (`scripts/run_canaries.py`), pre-registered 3-experiment cross-partition training and evaluation (`scripts/run_experiments.py`), figure generation (`scripts/build_figures.py`), GitHub Pages portal synthesis (`scripts/build_site.py`), and preflight verification (`scripts/check_submission.py`).
3. Verify every numerical result directly from executed code receipts stored under `evidence/`.

## Scientific & Anti-Hallucination Safeguards
- **Zero fabricated metrics or projections:** Every number reported in `README.md`, `docs/*.html`, and `evidence/*.json` is generated programmatically from executed code on SHA-256-pinned data artifacts.
- **Zero test-set or hidden-segment leakage:** All 59 Stage-1 features passed single-feature ROC-AUC holdout canaries (`max(AUC, 1 - AUC) = 0.78383 <= 0.90`), and all Stage-1, `LOCO-Quat`, and Stage-2 models were trained strictly out-of-fold across spatially buffered partitions (`1.2 km` boundary erosion).
- **100% open-source scientific stack:** Built exclusively with open-source Python packages (`numpy`, `scipy`, `scikit-learn`, `rasterio`, `matplotlib`, `pytest`) and public-domain U.S. government datasets (DOE GEMS, USGS 3DEP, USGS GeoDAWN, USGS ScienceBase, DOE GDR #1391, U.S. Census TIGER/Line).
