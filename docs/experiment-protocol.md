> **Earlier concurrent-session snapshot (PRs #1–2).** Preserved for provenance. Repository-readiness statements here predate the restored audit tools and inputs. See [the current review](review.md) and [current submission status](../index.html). External-page verification reported below belongs to the earlier session, not an independent recheck by the raster-audit run.

# Experiment and submission protocol

This is the execution contract for the next data-enabled session. It is a specification, **not evidence that the experiment has run**. Reuse the shared template's cached stack, `evaluate_holdout.py`, and `submission_writer.py` when present; do not maintain a private fork. None is present in this checkout.

## 0. Freeze the baseline and artifacts

- Record exact source commit, environment lockfile, input filenames, sizes and SHA-256 hashes.
- Read the official sample submission and feature raster metadata; do not guess dimensions, bounds, nodata, band order or transform.
- Inventory candidate/registry rasters available to the shared experiment registry. If absent, mark the novelty gate unavailable.
- Freeze a current holdout-best candidate and preregister the candidate, features, transform, thresholds, folds, exclusions and promotion rule before evaluating it.

## 1. Spatial holdout construction

- Split **whole fault segments**, not random pixels, into spatially blocked folds; buffer held-out segments so nearby pixels/connected continuations cannot leak across the split.
- Recompute every catalogue-based feature using visible faults only. No distance transform, density, mask, target encoding, feature selection, normalization statistic, or topology derived from hidden segments may cross the split.
- Mask visible fault pixels exactly from the prediction domain as specified by the shared evaluator. Keep the held-out positive set separate for scoring.
- Score pooled distance-weighted Tversky using alpha=0.2, beta=0.8 and the official 300 m triangular kernel. Report evaluator version, number of withheld positives, and 95% confidence interval obtained by resampling independent withheld fault segments/blocks, not individual correlated pixels.
- Compare candidate against frozen holdout best with paired folds and matched emission budget where applicable. Promote only under a preregistered rule; the public leaderboard is not a substitute for this holdout.

## 2. Leakage canaries

For every input channel/derived feature alone, score the same blocked holdout. AUC >0.90 is an alarm, not a win: check label-derived processing, spatial proximity leakage, split buffers, duplicate tiles, interpolation, and feature availability. Document an explanation before retaining the feature. AUC is a diagnostic only; the target promotion metric remains DTI.

## 3. Novelty / lane checks

- Before dot placement, compare the candidate's continuous score surface against every available registry raster on the common valid footprint using rank correlation. Stop as duplicate if correlation >0.90.
- After placement, measure nearest-dot distances to each registry dot set. Stop as duplicate if >70% of candidate dots fall within 3 pixels of one registry raster's dots.
- Record raster/registry hashes, overlap counts and denominators. If a registry raster is unavailable, report `NOT RUN`; do not claim the candidate is unique.

## 4. Validator and artifact

Write only after holdout and lane gates. Reopen the written raster from disk and check: one band; float32; CRS, shape, transform and bounds exactly match the sample/training grid; no NaN or infinity within the footprint; in-footprint values in [0,1]; outside-footprint cells are the permitted null/NaN; and the file is readable. Record independent validator output and SHA-256. Avoid nodata sentinels outside [0,1] where the submission parser may treat them as prediction values. The exact acceptance behavior must be tested against the actual format and sample file, not guessed.

## 5. Submission page requirements

A release page must show at its very top:

1. A prominent `READY TO SUBMIT` or `NOT READY` label.
2. An actual `.tif` download only when validation passes (optionally a zip with exactly one TIFF).
3. Unique submission name and a short <=140-character comment, plus hash, size, grid metadata, validator receipt, holdout evidence and explicit evidence class.
4. Plain upload instructions: log in to DrivenData, open the competition submission form, choose the `.tif`, paste name/note as applicable, submit, then save the organizer receipt. Never label a proposed / local holdout result as an organizer score.

## 6. Budget and run card

Stop after 3 experiments or 2 hours. No slot spending before holdout clearance. End with exactly one JSON run card in the session report; fields with unavailable data are null plus an explicit reason. Negative results are valid deliverables.
