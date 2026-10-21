# GEMSDOE75 — DOE GEMS Prize research workbench

> **Submission status: NOT READY — do not download or submit a TIFF from this checkout.** There is no competition data, cached feature stack, validator, holdout evaluator, submission writer, or GeoTIFF in this repository. A fabricated/placeholder raster would not be a valid competition prediction. The official competition data page redirects to login in this environment. This is an explicit blocker, not a claim that a submission was generated.

## Executive summary

This project is intended to support an auditable, scientifically grounded search for unmapped geological faults in the GeoDAWN region for DrivenData competition #306. The official task requires a single-band float32 GeoTIFF on the training grid, EPSG:32611, 100 m resolution, with prediction values in [0, 1] and null/NaN outside the stated bounds. The official metric is distance-weighted Tversky, using alpha=0.2, beta=0.8, and a 300 m triangular distance kernel. See the [official problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).

**Current verified public-board observation (2026-10-21):** the official leaderboard page displayed xiaofanhu at 0.4413. Evidence class: `PUBLIC-LEADERBOARD` (live public board, not a submission-page receipt, not a private-test or final-award score). The user's cited 0.3195 is therefore not the current public leader at the time checked. The provided H33 TIFF name / 0.2778 attribution was not independently established: a score match does not prove that a specific TIFF earned it. See [the evidence and caveats](docs/irregularities.md).

### One-click submission file

**Not available yet.** There is deliberately no download link until a unique candidate raster has been generated from the licensed competition inputs, passed the independent format validator, passed the prescribed holdout and duplicate-lane gates, and had its checksum/metadata recorded. The [submission guide](docs/executive-summary.html) explains the exact contest upload steps and what must be checked first.

## Session-start brief — read before every project session

1. **Mission.** Build a useful, auditable workflow to discover faults that are missing from the public USGS/INGENIOUS catalogue and may be relevant to geothermal systems. Aim to improve the chance of winning through sound experiments, not leaderboard speculation. Own results end-to-end; publish failures and blockers as well as wins.
2. **Do not fabricate evidence.** Every score claim must be one of: `HOLDOUT-DTI` (evaluator version, number of withheld positives, 95% CI), `ORGANIZER-CONFIRMED` (copied from a submission-page receipt), `PUBLIC-LEADERBOARD` (dated capture), or explicitly `USER-REPORTED`. A projection is never a score. Never infer which TIFF earned a leaderboard score from a similar name or score alone.
3. **Reuse the shared template.** If the shared template and cached features are present, use its feature stack, `evaluate_holdout.py`, and `submission_writer.py`; fix shared-tool defects in the template, not in a private fork. This checkout currently has none of those assets. Do not silently recreate or claim to have run them.
4. **Holdout before slot.** Hide whole fault segments with a spatial buffer. Derive every catalogue-based feature only from visible faults; mask visible fault pixels exactly. Evaluate pooled DTI at alpha=0.2, beta=0.8, with a 300 m triangular kernel. Report evaluator version, withheld positive count, and a segment-clustered 95% CI. Test each feature alone first; an AUC above 0.90 is a leakage alarm until explained. Do not promote an idea to a real submission slot unless it beats the frozen holdout best under the preregistered rule.
5. **Novelty / lane gate.** Before placement and again on final dots, compare candidate score surface/raster and placements against every available registry raster. Stop and mark duplicate if rank correlation exceeds 0.90 or more than 70% of candidate dots lie within 3 pixels of a registry dot set. If registry artifacts are unavailable, record the comparison as not run; do not claim uniqueness. Never copy an earlier TIFF except for explicitly labeled educational diagnostics.
6. **Slots and budget.** Maximum 3 experiments or 2 hours per session. Promotion to a weekly competition slot is a separate selector decision; do not spend a slot while the holdout gate is unmet.
7. **Submission validator.** Re-open the written bytes independently; check one band, float32, exact CRS/shape/transform/bounds, finite values inside the footprint in [0,1], and allowed null/NaN outside. Include a SHA-256. The download page must unmistakably say whether the artifact is ready to submit.
8. **Research discipline.** Use free official or otherwise challenge-permitted sources. Track DOI, license, spatial coverage, version, retrieval status, and a manual-review URL. Distinguish a source being publicly downloadable from proof that its coverage overlaps the competition footprint.
9. **End each experiment with one JSON run card** containing hypothesis, mechanism, a named non-fault mimic, `HOLDOUT-DTI` plus CI (or explicit not-run reason), correlation/overlap vs registry, raster SHA-256, validator output, submission name/note (or none), and verdict `promote` or `negative`.
10. **This prompt is the operating brief.** Review it and the [research register](docs/hypotheses.md) at the start of each session and update claims when evidence changes. Core values: **Maximize P(Win)** through disciplined evidence and **Own the Outcome** by surfacing defects and blockers.

## Current repo review

The starting checkout was inspected on 2026-10-21. It contained only a title-only README (plus Git metadata); the research/site files added in this review do not add input data or a model pipeline. There is still no `data/`, `scripts/`, test suite, cached feature stack, registry artifact, shared evaluator/writer, or TIFF. Consequently, no holdout, leakage canary, correlation/overlap screen, raster validation, or submission generation could be run. No weekly slot should be spent from this state.

The exact next prerequisite is to obtain the competition-provided files through the authorized DrivenData account (the data page currently redirects to login), place them in the expected `data/` directory, and provide this session with the actual shared-template repository/artifacts including the evaluator and writer. See [limitations and irregularities](docs/irregularities.md). Do not place credentials in the repository or chat.

## Research and site pages

- [Executive summary and contest submission walkthrough](docs/executive-summary.html)
- [Ranked candidate hypotheses and feasibility](docs/hypotheses.md)
- [Official sources and what was actually verified](docs/sources.md)
- [Holdout, leakage, novelty, and submission gates](docs/experiment-protocol.md)
- [Irregularities, data blockers, and evidence classes](docs/irregularities.md)

## Core official references

- [DrivenData problem description, metric, and output contract](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — login required in this environment
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release](https://doi.org/10.5066/P93LGLVQ)
- [DOE Geothermal Data Repository: INGENIOUS compilation](https://gdr.openei.org/submissions/1391)
- [USGS 3DEP products and services](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services)

See [sources.md](docs/sources.md) for evidence notes and additional links.
