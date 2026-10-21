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

## Full project prompt (retained operating requirement)

The following is the complete user prompt for this project. It is retained in the README
and must be re-read at the start of every session to ensure the work remains aligned with
the goal: place top of the DOE GEMS Prize Challenge leaderboard with a unique, defensible
submission TIF.

---

**HIGHEST URGENCY.** MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY
A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE
TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF
SUBMISSION.

There should be an easy to download submission tif file as described by the prompt. Read the
entire prompt.

**PARALLEL-RUN PROTOCOL.**
1. LANE. Your lane is the single method paragraph below. Stay inside it. If your raster's
   rank-correlation with any registry raster exceeds [0.90], or more than [70%] of your dots
   fall within 3 px of one registry raster's dots, you have drifted into another lane: log it
   as a duplicate and stop. Check this on the surface before placement AND on the final dots.
2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_holdout.py and
   submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a
   buffer, derive every catalogue-based feature only from the visible faults, mask visible
   faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a
   shared tool is wrong, fix it once in the template and report it; never keep a private fork.
3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI)
   or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never
   written as a score.
4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC
   above [0.90] means leakage until proven otherwise.
5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault process that
   could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator
   output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission
   name + note of at most 140 characters; verdict promote / negative. Negative results are
   deliverables.
6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions: promotion to a
   real slot is a separate selector step, within the weekly cap shown on the submission page.

**Starting point:** https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html —
h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778. Why and how did this get the highest
score and are we able to generate a submission that scores higher than 0.2778? Answer with PhD
level experience, knowledge, and judgement. Then use the answer to generate a unique TIF
submission into the competition. Must be unique submission unlike any within the GEMSDOE sites.

**Current competition leaderboard GEMSDOE high score: 0.4413** (live public leaderboard
snapshot, 2026-10-21; see docs/data/sources.json). Later prompt reference to 0.3195 is a stale
reading and does not match today's snapshot.

**GEMSDOE sites and reported scores (owner self-reports, NOT organizer-confirmed):**
GEMSDOE32 h33-h33-2-b2: 0.2778 | GEMSDOE gems-submission-20260925: 0.1563 | 6GEMSDOE: 0.0286 |
GEMSDOE3 pindrop-v4-nodes: 0.1193 | GEMSDOE2 gemsdoe2-dual-family-union: 0.1560 | GEMSDOE4: 0.0343 |
5GEMSDOE: 0.1563 | 7GEMSDOE lidarscarp-ridge-top2pct: 0.1461 | 8GEMSDOE Hedge-v2_submission: 0.1563 |
GEMSDOE9 2314b599: 0.0107 | 11GEMSDOE gems-structural-area06-v1: 0.0202 | 12GEMSDOE r7-nms3-dem10-scarp: 0.1294 |
15GEMSDOE gems-tso1: 0.0782 | 14GEMSDOE GEMS_r5-geom-horse-ensemble: 0.0020 | 17GEMSDOE: 0.0187 |
18GEMSDOE H19-C: 0.0297 | 19GEMSDOE h19-4-multiline: 0.1894 | GEMSDOE10 h16-continuation: 0.0461 |
GEMSDOE10 h20-dem10-scarp-thin: 0.0921 | GEMSDOE10 H25-ctx-ridge: 0.1280 | GEMSDOE10 h28-dotted-ridge: 0.1839 |
13GEMSDOE 20261001_r13-lattice-s5_v2: 0.0904 | 16GEMSDOE h16-1-topo-geophys-baseline-ridges: 0.1855 |
GEMSDOE21 h19-4-reference: 0.1894 | GEMSDOE20 h20-1-sarnnpu: 0.1890 | GEMSDOE20 h20-5-continuous-pu: 0.1859 |
GEMSDOE22 h23-a-dti-optimal-emission-6pct: 0.1002 | GEMSDOE23 h30-arrangement-matched-habitat: 0.1352 |
GEMSDOE24 h25-1-dotted-h19-5-d1-5: 0.2477 | GEMSDOE25 dotted-h19-5-d2-8: 0.2600 | GEMSDOE26 dilcond-oof-v1: 0.1223 |
GEMSDOE27 topo-gap-closure-t-v2-on-d1-5: 0.2449 | GEMSDOE30 d28-poisson300m-offcat-44090: 0.2600 |
GEMSDOE31 h27-4-solo-d28: 0.2708 | GEMSDOE33 h33d-analog-tip-stepover-r30: 0.2632 | GEMSDOE34 h34-scatter-q50: 0.0778 |
GEMSDOE35 h35-06-aaa86efb25: 0.0418 | GEMSDOE36 anderson-geothermal-pinn-38854-zeros: 0.2750 |
GEMSDOE37 h6-physics-dotted-80k: 0.1193 | GEMSDOE38 D-step-3p0-07pct: 0.0763 | GEMSDOE42 xscale-worm-persistence: 0.0581 |
GEMSDOE43 sup01-hgb21-sep40-n40000: 0.0424 | GEMSDOE45 h51-km-faultzone-zeros: 0.0106 | GEMSDOE49 gate_ortho_w0.25-40k: 0.2376 |
GEMSDOE28 h27-4-r1-solo-d2-8: 0.2708 | GEMSDOE28 h32-1-prethin-tip-euler-d2-8: 0.2649 | GEMSDOE28 h36-1-rung30-blind-r1: 0.2710 |
GEMSDOE28 h38-1-hf-euler-r30-r1: 0.2707 | GEMSDOE29 efd28-repro: 0.2600 | GEMSDOE29 repo-c0-habitat-emission: 0.0041 |
GEMSDOE29 sgmc-off-catalogue-44k: 0.0512 | GEMSDOE29 wormrank-d28-zeros: 0.2560 | GEMSDOE29 wormsurv-filter-zeros: 0.0532 |
GEMSDOE29 xfit-c0-habitat-zeros: 0.0439 | GEMSDOE29 xfit-h41-union-qfaults-zeros: 0.0356 | GEMSDOE46 r11f-scarp-radiometric-fusion-zeros: 0.1589 |
GEMSDOE46 r12-scarp-rad-concordance-zeros: 0.0843 | GEMSDOE39 h40-e-disc-h40e-30k-zeros: 0.0339 | GEMSDOE40 h8-euler-lineament-depthcluster: 0.0355 |
GEMSDOE40 h45-eulerdepthreadcluster-zeros: 0.0984 | GEMSDOE41 h42-submission-primary: 0.0245 | GEMSDOE44 h46-twostageAB_zeros: 0.0715 |
GEMSDOE47 h60-lidarscarp-s2p0-nanoutside: 0.0430 | GEMSDOE48 h59-cover-ds-belief-b2xh33d: 0.2296 | GEMSDOE50 h59-sharpened-scarp-scatter-90k-allfinite: 0.0764 |
GEMSDOE51 h53-twostage: 0.1047 | GEMSDOE52 h97b-candidate: 0.0856 | GEMSDOE53 h8-tiprelay-ridgeconcord-pr2-n80000-zeros: 0.0159 |
GEMSDOE54 h54c-manifest-edge: 0.0449 | 55GEMSDOE tensor_full-n16000-sep3-nan: 0.0290 | 56GEMSDOE h56-final-dotted-ridge-d2p8: 0.0658 |
57GEMSDOE h57r-joint-strata-38000-zeros: 0.0254 | 58GEMSDOE ml-binary-ridge: 0.0180 | 59GEMSDOE h59j-coherence-consensus-dotted: 0.0499 |
60GEMSDOE h73-chi-coherent-corridor-12000-zeros: 0.0351 | 61GEMSDOE h61a-basement-step-20000dots-zeros: 0.0009 |
61GEMSDOE h61o-vardepth-none-40000dots-zeros-zeros: 0.0751 | 62GEMSDOE datum-lahontan-strain-gauge-defensible-440dots-zeros: 0.0000 |
GEMSDOE63 cvarlw-thin-s3p17-54864-zeros: 0.2303 | GEMSDOE64 h64-lidar-scarp-cv: 0.0383 | GEMSDOE65 sar-em-propensity-half-zeros: 0.0431 |
GEMSDOE66 gems66-lidar03-cvretrain-reliefdecile-37654dots-zeros: 0.1152 | GEMSDOE67 h67a-orientip-lane-29447dots-allfinite: 0.0356 |
GEMSDOE67 ovtr-ml-cover-tau3p0-nan: 0.1426 | GEMSDOE68 gems68-autoctx-s3-strands-35000dots-nan: 0.0437 |
GEMSDOE68 gems68-autoctx-s3-strands-35000dots-zeros: 0.0437 | GEMSDOE69 h69-joint-relayramp-pullapart-38669: 0.0053 |
GEMSDOE70 gems70-p5-dual-submod300-oof38k: 0.2478 | GEMSDOE71 gems71-hydro-conduit-38800-zeros: 0.0558 |
GEMSDOE72 gemsdoe72-h72-1-sgmc-offcatalogue-20261020T195456Z-6e6525e5-zeros: 0.0492

**Competition links:**
- Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/
- Problem: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- About: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- Data: https://www.drivendata.org/competitions/306/competition-doe-gems/data/ (login-walled)
- Leaderboard: https://www.drivendata.org/competitions/306/competitions/306/competition-doe-gems/leaderboard/
- Official reference: https://github.com/drivendataorg/gems-prize-reference-solution
- Rules PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- USGS GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- INGENIOUS: https://gbcge.org/current-projects/ingenious/
- GDR submission 1391: https://gdr.openei.org/submissions/1391
- CRS: https://epsg.io/32611

**Core values:** Maximize P(Win) — weigh tradeoffs and risk rationally. Own the Outcome — own
end-to-end results; treat success and failure as signals. Here that means preventing an invalid
or falsely cleared competition entry, not inventing a score.

**Delivery standard:** Implement, review/fix, and re-check in three passes. Create a PR and
merge to main. Leave a concrete next-session handoff. No hallucinations — verify line by line.

---

## Next session, in order

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
