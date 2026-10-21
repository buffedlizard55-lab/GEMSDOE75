> **Earlier concurrent-session snapshot (PRs #1–2).** Preserved for provenance. Repository-readiness statements here predate the restored audit tools and inputs. See [the current review](review.md) and [current submission status](../index.html). External-page verification reported below belongs to the earlier session, not an independent recheck by the raster-audit run.

# Irregularities, evidence limits, and current blockers

## IR-01 — Repository is an empty scaffold

At review, this checkout held only a title-only README and Git metadata. No data directory, scripts, tests, cached feature stack, template evaluator, writer, registry raster, site, or TIFF was present. Therefore holdout scoring, leakage canaries, candidate-to-registry correlation/overlap, format validation, and TIF generation were not run. This is the decisive blocker.

## IR-02 — Competition data requires authenticated access

The official DrivenData data URL was fetched and redirected to the login page. We do not have the competition training feature raster, labels, sample submission, or the provided DEM-link table in this checkout. No authentication secrets were requested or stored. The research page explains this limitation rather than pretending that external public imagery substitutes for the competition grid.

## IR-03 — Score/time mismatch and evidence classes

The prompt includes several different values: it cites 0.3195 as the current top score, elsewhere cites 0.4413, and gives a named H33 file score of 0.2778. The official public leaderboard fetched on 2026-10-21 displayed xiaofanhu at 0.4413 (`PUBLIC-LEADERBOARD`). Thus 0.3195 is stale relative to this dated read. Public scores are dynamic and are not private-test/final-award scores.

The specific attribution of `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` to 0.2778 was not verified from an organizer submission receipt. The GEMSDOE32 site is a team-authored research page, not the competition receipt; it explicitly distinguishes candidate/projection/local claims from organizer-confirmed scores. A leaderboard row matching a score is not proof of which TIFF earned it. Treat 0.2778 and filename attribution as `USER-REPORTED` unless an organizer receipt is produced.

## IR-04 — H33 explanation cannot be asserted from the filename

The metric itself creates a plausible strategy: it has asymmetric costs (alpha=0.2 for false-positive mass, beta=0.8 for missed truth) and distance credit within 300 m, so a localized, carefully budgeted prediction can trade precision for recall and tolerate nearby offsets. But the score and TIFF name alone do not reveal its pixels, calibration, holdout behavior, training data, or cause of score. It would be speculation to claim the particular H33 artifact achieved its score because of a particular thinning, zero-fill, or geological transform. The official metric supports the general rationale; the specific attribution is not established.

## IR-05 — No unique submission artifact can be produced safely

There is no input grid to match and no verified candidate raster. Generating an arbitrary zeros TIFF or copying an older output would not satisfy the scientific uniqueness and evidence requirements, and could fail format or range checks. No TIF was created; no download is offered. This is intentional and prevents a misleading file being submitted.

## IR-06 — Candidate novelty is not global

The ranked hypotheses are new relative to the empty codebase only. The large sibling-site list is a result index, not a source-code corpus, and was not exhaustively audited. Some historical pages mention related DEM, geophysics, thermal, earthquake, and edge-style studies. The candidates are proposals and not claimed globally unique. Before any future implementation, check the candidate against actual registry rasters and historical artifact methods.

## Required next action

Use authorized access to retrieve the competition data and shared template/evaluator/writer into the expected workspace; verify licenses and input hashes. Then run Rank 1's feature-level canaries and the specified buffered whole-segment holdout. If it fails to beat frozen holdout best, record a negative run card and do not spend a submission slot. If inputs remain unavailable, stop: do not manufacture a score or a TIFF.
