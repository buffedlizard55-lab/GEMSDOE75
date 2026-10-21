# GEMSDOE75 — GEMS geothermal-fault prospectivity

> **Submission status: NOT READY.** This checkout contains no competition rasters, cached feature stack, evaluator, submission writer, website, or prior submission registry. No GeoTIFF was generated. Do not download or submit a purported prediction from this repository until the data, spatial holdout, validation, and format checks described below have actually passed.

## Project charter

Build an auditable, reproducible system to identify geothermal-fault targets that may be absent from the USGS/INGENIOUS catalogue, maximize the probability of a scientifically defensible competition result, and own the outcome end to end. Prefer measured spatially blocked holdout performance to leaderboard folklore. Use free, publicly available, official data where possible; keep a source ledger, methods, code, and validation evidence together. Do not claim a score without an evaluator version, withheld-positive count, and confidence interval. Do not treat a prediction or a submission-page receipt as interchangeable with a confirmed competition score.

### Operating protocol (read before every experiment)

1. **One declared hypothesis/lane per experiment.** Compare its surface to every available registry raster before placing dots and compare final dots afterward. If rank correlation with any registry raster exceeds 0.90, or more than 70% of the dots lie within 3 pixels of one registry raster's dots, record a duplicate and stop that experiment. The full registry rasters are currently absent, so this gate cannot yet be run.
2. **Reuse shared tools.** Use the template's cached feature stack, `evaluate_holdout.py`, and `submission_writer.py` where available. The evaluator must withhold whole fault segments with a buffer, derive catalogue features from visible faults only, mask visible faults pixel-exactly, and calculate pooled DTI with alpha 0.2, beta 0.8, and a 300 m triangular kernel. Fix shared-tool defects in the shared template rather than maintaining private forks. None of those tools is present in this checkout.
3. **Label every metric.** A score must be marked either **HOLDOUT-DTI** (evaluator version, withheld-positive count, 95% CI) or **ORGANIZER-CONFIRMED** (submission-page receipt). A projection is not a score.
4. **Leakage canary.** Test each feature alone on the spatial holdout before trusting a composite. AUC above 0.90 is a leakage alarm until investigated and explained.
5. **Run card.** End each experiment with JSON containing: hypothesis; mechanism; named non-fault mimic process; holdout DTI and CI; registry correlation/overlap; raster SHA-256; validator output (no NaN within footprint, values in [0,1], CRS/shape/transform match); submission name and <=140-character note; verdict `promote` or `negative`.
6. **Budget and selection.** Stop after three experiments or two hours, whichever comes first. Do not promote/select or spend a weekly submission slot unless the independent selector and holdout gate authorize it. Negative results are deliverables.
7. **Submission safety.** A downloadable TIFF may be called submission-ready only after checking one band, required CRS, shape, geotransform, footprint, finite values in [0,1], and valid file integrity against the official sample submission. Never normalize/clip silently to conceal invalid predictions.

## Current checkout audit (2026-10-21)

This repository is a clean, single-commit checkout with only this README. It has no scripts, tests, data directory, source catalogue, raster, web app, or competition artifacts. Consequently, there is no model or previous code to review line-by-line, no cached features or evaluator/writer to reuse, no spatial holdout to run, and no basis for a valid TIFF or performance claim. These are concrete blockers, not evidence that the requested method failed. The user's reported leaderboard/submission scores are not independently confirmed here. The public GEMSDOE32 page was fetched and visibly labels its 0.2747 value as a model projection, not an organizer score; its displayed artifact metadata and claims are not independently verified by this checkout. The submitted user claim that the historical `h33-h33-2...-zeros` artifact scored 0.2778 cannot be explained causally from that score alone: the precise reason requires the TIFF, its producer/configuration, and the leaderboard/receipt context. A score is a result, not a scientific mechanism. Do not conflate it with the current leaderboard value in the prompt.

The official DrivenData problem page was fetched during this review. It confirms the target is faults missing from the existing USGS catalogue, describes GeoDAWN magnetic/radiometric and other provided features, gives the distance-weighted Tversky metric (300 m triangular kernel, alpha 0.2, beta 0.8), and states the output requirements: one float32 band, EPSG:32611, 100 m, same bounds, values [0,1], null/NaN outside bounds. Those are source-verified requirements; see the linked official problem page below. The official rules PDF was also fetched and identifies itself as the GEMS Prize Official Rules, dated September 2026. The exact input raster dimensions/geotransform still must be checked from the competition sample, which is not present here.

### Candidate hypotheses for future blocked-holdout evaluation

These are **proposals, not tested results**. The repository is empty, so “difference from existing implementation” means no implementation exists here to compare against. Rank is a research-priority ranking, not an expected numerical score improvement.

| Rank | Hypothesis / layers | Physical signature | Why it might find an uncatalogued fault | Key non-fault mimic | Cost / validation |
|---|---|---|---|---|---|
| 1 | Multi-scale magnetic-gradient edge persistence using official GeoDawn magnetic channels (only if present in the cached stack) | Directional/analytic-signal gradient edges that persist across scales, with locally coherent strike | Buried or unmapped structures can produce linear magnetic contrasts even where surface mapping is incomplete; persistence/coherence is intended to reject isolated noise | Lithologic contacts, dikes, survey-line striping | Low–medium if channels and cached stack exist; feature-only leakage test and whole-segment spatial holdout required |
| 2 | Radiometric boundary concordance (K, eTh, eU channels if available) gated by magnetic edge orientation | Coincident but independently measured radiometric gradient and magnetic boundary, not raw anomaly magnitude | Alteration/weathering or structurally juxtaposed units may create boundaries that guide field mapping to previously unmapped structures | Soil/moisture variation, lithologic contact, cultural disturbance | Medium; requires confirmed channels and careful masking; spatial holdout plus single-feature leakage checks |
| 3 | DEM curvature / channel-network discontinuity at multiple scales (official 1 m DEM coverage if already available) | Profile/plan curvature and drainage deflection aligned along a persistent linear trace | Subtle scarps or drainage offsets may expose young or low-relief structures absent from the fault catalogue | Stream incision, road cuts, landslides, erosional contacts | High due to DEM coverage/processing; requires official DEM availability and holdout before proposing as viable |
| 4 | Geophysical lineament termination/stepover geometry, conditioned on independent terrain corroboration | Junctions, terminations, and stepovers among extracted geophysical edges; terrain used only as corroboration | Fault intersections/relay zones may be structurally meaningful even if no mapped segment is present | Survey artifacts, non-tectonic contacts, random edge intersections | Medium–high; requires robust edge extraction and spatial nulls; distinguish from dot/lineament strategies in the supplied historical results |

The magnetic and radiometric sources are suggested only where they are part of the provided competition feature stack; this repository does not establish channel availability. Do not fetch external data or treat these as viable until official source, license, coverage, and retrieval are verified. The official USGS GeoDawn dataset landing page is listed below for manual review.

### Next actions and blockers

1. Obtain the official competition data and place it in the project's documented `data/` location. DrivenData's data tab requires an authenticated account; this sandbox does not have that access. Do not invent or replace competition labels with public proxies.
2. Restore/add the shared template feature cache, `evaluate_holdout.py`, `submission_writer.py`, feature definitions, and registry rasters. Record versions and hashes.
3. Verify evaluator implementation against the protocol (segment-level buffered withholding, visible-only catalogue-derived features, exact visible-fault mask, pooled DTI parameters). Add leakage-canary tests and test the evaluator on a known synthetic fixture.
4. Run no more than three candidate experiments/two hours; record JSON run cards and registry duplication checks. Promote only if the top candidate beats the current holdout best with uncertainty reported.
5. Generate a uniquely named GeoTIFF only from a validated experiment, then run a strict format/range/footprint validator against the official sample submission. Provide it as a clearly labeled download; report an organizer score only from the submission receipt.
6. Add the requested executive-summary/submission guide and GitHub Pages site after a usable, auditable implementation exists. This checkout currently has no website to improve or publish.

## Authoritative references

Links below are starting points supplied for this project; they have not been fetched or independently checked in this checkout. Verify current details at the source before relying on them.

- [DrivenData competition overview and rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData about page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [DrivenData data tab (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DOE/NLR GEMS prize reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDawn airborne magnetic and radiometric surveys](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [GBCGE INGENIOUS current projects](https://gbcge.org/current-projects/ingenious/)
- [GEMS competition technical report PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [EPSG:32611 / WGS 84 UTM zone 11N](https://epsg.io/32611)
- [Tversky index overview](https://en.wikipedia.org/wiki/Tversky_index) (secondary source; prefer competition documentation for metric implementation)

## Run-card status for this review

No experiment ran; no raster exists. This is an explicit negative/readiness finding, **not a holdout score**.

```json
{
  "hypothesis": "No experiment: the checkout contains no data, feature stack, holdout evaluator, or writer",
  "mechanism": "Not tested",
  "named_non_fault_mimic": "Not applicable; no raster was produced",
  "holdout_dti": null,
  "holdout_evaluator_version": null,
  "withheld_positives": null,
  "holdout_95_ci": null,
  "registry_correlation_overlap": "Not computable: registry rasters absent",
  "raster_sha256": null,
  "validator_output": "NOT RUN: no raster; CRS/shape/transform/range/footprint checks unavailable",
  "submission_name": null,
  "submission_note": "No valid TIFF generated; do not download or submit",
  "verdict": "negative"
}
```
