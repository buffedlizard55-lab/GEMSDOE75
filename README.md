# GEMSDOE75 · evidence before emission

## Submission status: **FORMAT-VALIDATED, NOT SCORE-VALIDATED — DO NOT SUBMIT yet**

A unique TIFF has been generated: `docs/downloads/gems75-fault-tip-halo-20261021-SCHEMA-DEMO-DO-NOT-SUBMIT.tif`
(SHA-256: `89d57a586634dafa256dc752a5d8a08815be23f26de4f651063378a198742098`).

It passes every local format check (single band, float32, EPSG:32611, 100 m, values in [0,1], no NaN,
exact placeholder-grid geometry), but it is **not OK to submit to the contest** because the geometry is
placeholder data (this sandbox cannot reach the login-walled DrivenData data page) and no holdout DTI,
leakage canary, or registry uniqueness check could be run.

[Project website](https://buffedlizard55-lab.github.io/GEMSDOE75/) ·
[Download candidate](https://buffedlizard55-lab.github.io/GEMSDOE75/download.html) ·
[Executive summary / submission instructions](https://buffedlizard55-lab.github.io/GEMSDOE75/executive-summary.html) ·
[Run card](evidence/run-card.json) · [Reproducible raster audit](evidence/audit.json)

**Read this README and [the retained operating brief](PROJECT_BRIEF.md) at the start of every session.**

---

# FULL PROJECT PROMPT (retained for session start)

This is the complete set of requirements carried into every session. Read it before doing work.

## Core directive

**MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.**

There should be an easy to download submission tif file as described by the prompt. Read the entire prompt.

## Parallel-run protocol

1. **LANE.** Stay inside the single assigned method paragraph. If your raster's rank-correlation with any registry raster exceeds 0.90, or more than 70% of your dots fall within 3 px of one registry raster's dots, you have drifted into another lane: log it as a duplicate and stop. Check on the surface before placement AND on the final dots.

2. **REUSE, DON'T REBUILD.** Use the template's cached feature stack, `evaluate_holdout.py` and `submission_writer.py`. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it once in the template and report it; never keep a private fork.

3. **LABEL EVERY NUMBER** as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score.

4. **LEAKAGE CANARY.** Test each feature alone on the holdout before trusting any result. AUC above 0.90 means leakage until proven otherwise.

5. **RUN CARD.** End with one JSON card: hypothesis; mechanism; the named non-fault process that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name + note of at most 140 characters; verdict promote / negative. Negative results are deliverables.

6. **BUDGET.** Stop after 3 experiments or 2 hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.

## The competition

**GEMS Prize Challenge (DrivenData #306):** Predict new geothermal faults missing from the USGS/INGENIOUS catalogue.

- **Metric:** Distance-weighted Tversky Index, DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w), triangular kernel k(d) = max(1 − d/300m, 0), alpha=0.2, beta=0.8.
- **Worked example (organizer):** TP_w=3.00, FP_w=1.89, FN_w=2.00 → DTI=0.60.
- **Submission format:** Single-band float32 GeoTIFF, EPSG:32611 (UTM 11N), 100 m resolution, same bounds as training data, values in [0,1], null/NaN outside bounds.
- **Known faults are MASKED from scoring** (organizer forum thread 11516), pixel-exact, not buffered. New-fault truth CAN be within 300 m of a known fault (splays, tip extensions are explicit targets).
- **Leaderboard:** Live public board shows rank 1 at 0.4413 (2026-10-21 snapshot). Owner-reported values (0.2778 H33, 0.4413, 0.3195) conflict and are NOT organizer-confirmed.

## Key scientific insight

Known-fault pixels are masked from scoring, so predicting ON them wastes mass. New-fault ground truth can exist within 300 m of known faults. With beta=0.8 > alpha=0.2, missing truth costs more than false positives. The optimal strategy places sparse dots in the 100–300 m halo around fault tips and step-overs — where new faults nucleate — rather than on masked catalogue traces or random off-catalogue pixels.

## Required submission experience

- A single-band GeoTIFF or ZIP containing exactly one GeoTIFF
- Finite probability values in [0,1], exact reference CRS/shape/transform
- Unique informative name, short note (at most 140 characters)
- At the top of the site, state separately whether downloading is safe, format validation passed, uniqueness passed, and selector approval

## Blocker (current)

No access to real competition data (`training_features.tif`, `labels.tif`, `sample_submission.tif`, `1m_DEM_links.csv`) — the DrivenData data page is login-walled and the sandbox network cannot reach it, Dropbox, USGS, GDR, or other external hosts. A human with a DrivenData account must download the files and place them in `data/raw/`, then run `scripts/prepare_data.py`.

Until real data is available, any claimed geological holdout score would be fabricated. The only artifact shipped is the schema-demo TIF above, explicitly marked DO-NOT-SUBMIT.

## Research hypotheses (ranked, untested)

See `docs/data/hypotheses.json` — H75-1 through H75-4: Quaternary volcanic vent alignment, seismicity hypocenter anisotropy, heat-flow × magnetic-depth conjunction, slip/dilation-tendency azimuth mismatch. Each names layers, signature, why it finds catalogue-missing faults, named non-fault mimic, contrast to prior work, expected value/cost, and data obtainability. None has been validated.

## Core values

**Maximize P(Win):** Weigh tradeoffs and risk rationally. Prevent invalid or falsely cleared entries.  
**Own the Outcome:** Own results end-to-end; treat success and failure as evidence.

## Next session, in order

1. Obtain real competition data from DrivenData (human with account).
2. Place files in `data/raw/`, run `scripts/prepare_data.py`.
3. Re-run `scripts/make_submission.py --rule fault_tip_halo` in REAL mode.
4. Run leakage canary + holdout for the rule.
5. Compare against registry rasters for uniqueness.
6. Only if authorized and gates pass: publish the unique TIFF/ZIP and receipt.

---

## Reproduce

Python 3.11 and authenticated `gh` are needed for public-mirror fetches. No DrivenData credentials are requested or stored. CPU suffices for this audit.

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/fetch_inputs.py
.venv/bin/python scripts/audit.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/inventory.py       # optional fresh repository metadata inventory
.venv/bin/python scripts/build_site.py
```

Mirrored rasters stay in ignored `.cache/inputs/`, not Git or public downloads. Fetches are commit-pinned and SHA-256-checked. `vendor/gems57/` is copied byte-for-byte from the pinned shared template; it contains the evaluator and submission writer. No private replacement metric or writer was introduced. Tests exercise shared code but do not constitute a holdout.

The larger cached feature stack is discoverable in `evidence/template-data-manifest.json`; it has not been restored or modeled after the stop. Its owner mirror is not organizer-authenticated. The original prompt's `scripts/download_competition_data.sh` and `scripts/prepare_data.py` exist in this checkout and are ready to run once data is placed in `data/raw/`.