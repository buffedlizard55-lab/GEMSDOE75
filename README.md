# GEMSDOE75 · evidence before emission

## Submission status: **BLOCKED — no new TIFF generated or approved**

[Project website](https://buffedlizard55-lab.github.io/GEMSDOE75/) ·
[Executive summary / submission instructions](https://buffedlizard55-lab.github.io/GEMSDOE75/executive-summary.html) ·
[Run card](evidence/run-card.json) · [Reproducible raster audit](evidence/audit.json)

**Read this README and [the retained operating brief](PROJECT_BRIEF.md) at the start of every session.**
The starting checkout contained only `# GEMSDOE75`, not the pipeline claimed in the supplied prompt.
This review does not claim that the requested submission has been delivered.

### Why no download button?

The prompt requires both a unique TIFF and an immediate stop on excessive registry overlap.
The pinned shared template defines dots as finite positive pixels. A registered continuous
probability raster is positive throughout the footprint. We verified its bytes: every eligible
cell is covered, so every nonempty candidate would fail the forward-overlap rule. Also, the
promised single-method lane was absent. We did not invent one, jitter a previous submission,
or spend a competition slot. A negative preflight is the honest deliverable.

This is a **conditional policy conflict**, not proof that all geological hypotheses are duplicates.
A future owner-approved protocol can distinguish continuous surfaces from discrete dots, but
this run does not introduce that exemption. See [research and irregularities](docs/review.md).

### Reproduce

Python 3.11 and authenticated `gh` are needed for the public-mirror fetches. No DrivenData
credentials are requested or stored. CPU suffices for this audit.

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/fetch_inputs.py
.venv/bin/python scripts/audit.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/inventory.py       # optional fresh repository metadata inventory
.venv/bin/python scripts/build_site.py
```

Mirrored rasters stay in ignored `.cache/inputs/`, not Git or public downloads. Fetches are
commit-pinned and SHA-256-checked. `vendor/gems57/` is copied byte-for-byte from the pinned
shared template; it contains the evaluator and submission writer. No private replacement
metric or writer was introduced. Tests exercise shared code but do not constitute a holdout.

The larger cached feature stack is discoverable in `evidence/template-data-manifest.json`;
it has not been restored or modeled after the stop. Its owner mirror is not organizer-authenticated.
The original prompt's `scripts/download_competition_data.sh` and `scripts/prepare_data.py`
did not exist here, and no ready train→inference pipeline or GPU requirement was verified.

## Retained project instructions (deduplicated operating form)

- **Urgency:** generate a genuinely unique single-band submission GeoTIFF, never recycle a prior
  except for education. Put a prominent one-click download and truthful submit-readiness status
  at the top of the site when an artifact passes the gates; never offer a placeholder as a submission.
- **Parallel run:** use only the assigned single-method lane. Stop and log a duplicate if surface
  rank-correlation exceeds 0.90 or more than 70% of candidate dots lie within 3 px of any one prior.
  Check before placement and on final dots. No lane was supplied in this prompt.
- **Reuse:** use the template cached features, `evaluate_holdout.py`, and `submission_writer.py`.
  Whole-segment buffered hide-and-recover; derive catalogue features from visible faults only;
  mask visible faults exactly; pooled DTI with alpha 0.2, beta 0.8, triangular 300 m kernel.
  Fix shared defects upstream, never in a private fork.
- **Evidence:** HOLDOUT-DTI must include evaluator version, withheld-positive count, and 95% CI.
  ORGANIZER-CONFIRMED requires a submission-page receipt. User score reports are unverified,
  not promoted into either class. Projections are not scores. Feature-alone AUC >0.90 is a
  leakage alarm pending explanation, not automatic evidence of predictive power.
- **Run card:** hypothesis; mechanism; named non-fault mimic; holdout and CI; surface/dot novelty;
  raster hash; finite/range/CRS/shape/transform validation; unique name and ≤140-character note;
  verdict promote/negative. Null means not measured, not zero performance.
- **Budget:** stop after three experiments or two hours. Promotion to a real slot is a separate
  selector decision within the authenticated weekly cap. Never spend a slot without beating the
  current comparable spatial holdout best.
- **Research:** review prior GEMSDOE results; explain H33 without invented causality; propose and
  rank three–five untried geological hypotheses with layers, transforms, missing-fault rationale,
  contrast to prior implementations, expected benefit and cost. Verify official sources and external
  data obtainability; preserve an auditable knowledge base. No promised leaderboard win.
- **Product:** clean GitHub Pages UI, executive-summary subpage, exact submission instructions,
  transparent limitations, automation where safe, official links for manual verification. Address
  the portal error “Predicted values must be in range [0, 1]”. Retain the project prompt in the
  README and re-read each session; prefer facts over unsupported completion claims.
- **Delivery:** implement, review/fix, and re-check in three passes; create a PR and merge to main;
  leave a concrete next-session handoff. Do not ask for manual intervention merely to avoid work.
- **Values supplied by the owner:** Maximize P(Win)—weigh tradeoffs and risk rationally; Own the
  Outcome—own end-to-end results and treat success and failure as evidence. Here that means
  preventing an invalid or falsely cleared competition entry, not inventing a score.

This is a **deduplicated brief, not a verbatim transcript** of the long user message. The source
message remains the authority for its complete wording. Source links, reported-score conflicts,
and the list of all named repositories are retained in the linked brief/inventory. Repeated
requests to “verify no hallucinations” are implemented as explicit evidence scopes, not a claim
that every external page or every historical file was verified.

## Next session, in order

1. Resolve missing lane and dot semantics in a shared protocol decision; no silent exemption.
2. Authenticate the official template, rules/eligibility, score receipts and weekly cap. Network
   here is limited to GitHub and package registries; external links are not proof of retrieval.
3. Restore the existing feature cache; inspect band descriptions, provenance, nodata and licenses.
4. Confirm whole-segment independence: shared holdout segments are capped at 12 px; that is
   not automatically equivalent to withholding a complete geological fault. Resolve upstream.
5. Run feature-alone leakage canaries and a fixed-budget, buffered spatial holdout against the
   current best on identical splits. Report pooled DTI and paired spatial-bootstrap CI.
6. Only if authorized and gates pass: scan all accessible registry rasters on the surface and
   final dots, use the shared writer, validate roundtrip, publish the unique TIFF/ZIP and receipt.
   The selector—not this runner—decides the slot. Current metadata inventory is not clearance.

## Concurrent-session work preserved

During this run, PRs #1–2 merged documentation into main. Their source register, hypotheses,
protocol and earlier site remain under `docs/`, with explicit snapshot banners; their README
is preserved at [docs/history/concurrent-readme.md](docs/history/concurrent-readme.md).
Their [source notes](docs/sources.md) report a dated public leaderboard observation and external
page checks. Those are inherited session reports, not independently re-fetched here and not
submission-page receipts. Earlier claims that the repository has no scripts, tests or evaluator
are superseded by this audit. Both sessions' contributions are retained rather than overwritten.

## Parallel session (arena/f5af665d), merged alongside this audit

A second concurrent run worked the same brief independently, before discovering this branch's
`vendor/gems57/` pinned template. It did **not** fork or replace that template. It built, as an
additive, separately-tested cross-check and a second set of pages, none of which overwrite the
files above:

- `src/gems_doe/metric.py`, `submission_io.py`, `holdout.py` — a from-scratch DTI/holdout/writer
  implementation, reproducing the organizer's published worked example (0.60) exactly and cross-
  checked against `vendor/gems57/metric.py`'s independently-derived, more complete treatment (its
  `T`/`M`/`S` algebra and the `IR-57-BAR-01` greedy-emission bug it documents are **not**
  reproduced here — read `vendor/gems57/metric.py`'s own docstring, it is the more carefully
  verified of the two for anything beyond the base DTI formula). 21 tests in `tests/`.
- `scripts/download_competition_data.sh`, `prepare_data.py`, `make_submission.py`,
  `verify_submission.py`, `demo_dti_mechanics.py` — a second, independent data/submission
  pipeline, reaching the same "login-walled, cannot fetch" conclusion as `scripts/fetch_inputs.py`
  above, by direct `curl` tests against each host rather than inference.
- `docs/research.html`, `hypotheses.html`, `sources.html`, `limitations.html`,
  `submission-guide.html`, and `docs/data/*.json` — a second hypotheses/sources/limitations
  write-up (hypotheses **H75-1..4**: Quaternary volcanic vent alignment, seismicity hypocenter
  anisotropy, heat-flow × magnetic-depth conjunction, slip-tendency azimuth mismatch), cross-checked
  against `docs/hypotheses.md` above to confirm no duplication, and a numeric DTI-mechanics
  demonstration (`docs/data/dti_mechanics_demo.json`) showing, on a synthetic case, that
  concentrating a fixed amount of predicted mass onto the true line scores DTI 1.000 versus 0.217
  for the same mass spread over a 5-px corridor — independent confirmation of the same
  "thinning helps" mechanism this repository's other research pages describe.
- `LIMITATIONS.md` / `docs/limitations.html` — flags that the brief's "0.3195 current highest" does
  not match the live public leaderboard fetched in that session (0.4413 / 0.3904), and that one
  DrivenData forum thread (11527) had reply bodies its fetch tool could not render — both left for
  manual review rather than guessed at.

**Recommendation for the next session:** treat `vendor/gems57/` as the one shared template per the
brief's own "never keep a private fork" rule; use `src/gems_doe/` only as an independent
cross-check or delete it once `vendor/gems57/` is confirmed to cover the same ground, rather than
maintaining two parallel implementations long-term.
