# GEMSDOE75 — DOE GEMS Prize fault-discovery project

**Live site:** https://buffedlizard55-lab.github.io/GEMSDOE75/ (executive summary, submission guide,
research, hypotheses, sources, limitations — all generated from this repo, see `docs/`)

**Competition:** [DOE GEMS Prize, DrivenData #306](https://www.drivendata.org/competitions/306/competition-doe-gems/)
— find geological faults in the GeoDAWN region (NW Nevada / E California) not already in the
USGS/INGENIOUS catalogue. $300,000 total prize pool across two phases. Official rules:
[docs.nlr.gov/docs/fy26osti/96647.pdf](https://docs.nlr.gov/docs/fy26osti/96647.pdf).

## Core Values (read before every work session)

**Maximize P(Win)** — "Maximize the Probability of Winning" is the decision framework. Every design
choice here is weighed against whether it raises the probability of a real, defensible, high-scoring
submission — not against what looks impressive, and not against what a sibling repository merely
*claims* to have scored.

**Own the Outcome** — this project owns results end to end, not just its own slice. When a problem is
found (a format bug, a stale number, an unverifiable claim), it is fixed or flagged in the same
session, not left for someone else. Failure and success are both signals, used to improve the next
pass. Nothing is reported as true without a named evidence class and a link a human can click to check
it themselves.

## Current status (verified 2026-10-21 — see `docs/data/run_card.json` for the formal record)

| Question | Answer |
|---|---|
| Does a correct, tested implementation of the official metric (DTI) exist here? | **Yes** — `src/gems_doe/metric.py`, reproduces the organizer's published worked example (0.60) exactly |
| Does a submission writer that avoids the `[0,1]` rejection exist? | **Yes** — `src/gems_doe/submission_io.py`, two documented failure mechanisms fixed by construction |
| Does a spatially-blocked hide-and-recover holdout evaluator exist? | **Yes** — `src/gems_doe/holdout.py`, with a built-in leakage canary |
| Do we have the real competition data (features, labels)? | **No** — the data page is login-walled; see `LIMITATIONS.md` |
| Has any hypothesis beaten a real holdout score? | **No** — none has been run on real data yet; nothing here reports a fabricated score |
| Is there a downloadable file on the site? | **Yes, a format/schema demo only**, explicitly marked **DO NOT SUBMIT** — see `docs/index.html` |

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests -q                       # 21 tests, all pass on synthetic data today

# Once you have a DrivenData login (see docs/submission-guide.html):
bash scripts/download_competition_data.sh   # run on a machine with normal internet access
python scripts/prepare_data.py
python scripts/make_submission.py --rule zeros
python scripts/verify_submission.py <your_file>.tif --template data/raw/training_features.tif
```

## Repository layout

```
src/gems_doe/metric.py          DTI implementation (organizer formula, verified)
src/gems_doe/submission_io.py   GeoTIFF writer/validator (fixes the [0,1] error)
src/gems_doe/holdout.py         spatially-blocked hide-and-recover holdout + leakage canary
scripts/download_competition_data.sh   data fetch (documents the login-wall + free external sources)
scripts/prepare_data.py         builds data/processed/ from data/raw/
scripts/make_submission.py      generates a submission GeoTIFF (real or schema-demo mode)
scripts/verify_submission.py    stand-alone format validator for any .tif
scripts/demo_dti_mechanics.py   reproducible numeric demo behind docs/research.html
tests/                          21 unit tests, all against synthetic/hand-derivable data
docs/                           the GitHub Pages site (index, submission guide, research, hypotheses, sources, limitations)
docs/data/*.json                machine-readable sources, hypotheses, run card, mechanics demo output
LIMITATIONS.md                  every blocker, with the exact unblock steps
```

## Why there is no high-scoring submission in this repository yet

This project has **no access to the real `training_features.tif` / `labels.tif`** (the data page
requires a DrivenData login) and this sandbox's network is firewalled to six code-hosting domains — it
cannot reach `drivendata.org`, `gdr.openei.org`, `usgs.gov`, or `dropbox.com` directly. Every official
source cited in this repository was still read live, through a separate research tool, and is linked
for manual verification in `docs/data/sources.json` — but that tool cannot download binary GeoTIFFs or
shapefiles either. Fabricating a "detection" raster without any real signal to detect would be exactly
the kind of hallucination this project is built to refuse. See `LIMITATIONS.md` for the precise,
actionable unblock steps (they take a human about five minutes).

What exists instead is a complete, tested, ready-to-run pipeline, four new ranked hypotheses grounded
in free official data this project could not fetch itself, and one honestly-labeled schema-demo file
proving the writer code is correct — so that the moment real data lands in `data/raw/`, there is zero
engineering distance between "we have the data" and "we have a validated, submittable file."

## Suggested next steps / open work for the next session

1. **Unblock data access** (human, ~5 minutes): download the 4 competition files from DrivenData and
   place them in `data/raw/`; run `python scripts/prepare_data.py`.
2. **Test H75-2's data reachability** (agent, cheap): try fetching the USGS ComCat FDSN event API —
   it's a small JSON endpoint and may be reachable even though `earthquake.usgs.gov` failed a raw
   `curl` test; if the page-fetch research tool can reach it, H75-2 becomes immediately buildable
   without needing an external machine.
3. **Build and holdout-score H75-1..4** in rank order once data exists; do not spend a weekly
   submission slot on any of them until each beats the current holdout best.
4. **Re-verify the live leaderboard and any sibling-repo claim before quoting it** — this session
   already found one stale number ("0.3195") and one partially-unretrievable forum thread; both are
   logged in `LIMITATIONS.md` and `docs/limitations.html`.
5. **GitHub Pages**: confirm the repository's Pages source is set to deploy `docs/` from `main` (Settings
   → Pages) if the live site linked at the top of this file is not yet serving.

---

<details>
<summary><strong>Standing brief — the original, full working prompt for this project (click to expand; re-read at the start of every session, per explicit project instruction)</strong></summary>

> THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!
>
> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS
> IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS
> WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.
>
> There should be an easy to download submission tif file as described by the prompt. Read the entire
> prompt.
>
> **PARALLEL-RUN PROTOCOL** — read first. This session is one of several running from this same
> prompt.
>
> 1. LANE. Your lane is the single method paragraph below. Stay inside it. If your raster's
>    rank-correlation with any registry raster exceeds 0.90, or more than 70% of your dots fall within
>    3 px of one registry raster's dots, you have drifted into another lane: log it as a duplicate and
>    stop. Check this on the surface before placement AND on the final dots.
> 2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_holdout.py and
>    submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer,
>    derive every catalogue-based feature only from the visible faults, mask visible faults
>    pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is
>    wrong, fix it once in the template and report it; never keep a private fork.
> 3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or
>    ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a
>    score.
> 4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC above 0.90
>    means leakage until proven otherwise.
> 5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault process that could
>    mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output (no
>    NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name + note of
>    at most 140 characters; verdict promote / negative. Negative results are deliverables.
> 6. BUDGET. Stop after 3 experiments or 2 hours. Do not pick submissions: promotion to a real slot is
>    a separate selector step, within the weekly cap shown on the submission page.
>
> *(This project's note: the remainder of the original session prompt — the list of sibling GEMSDOE*
> sites and their self-reported scores, the DriveData competition links, the DOE PDF link, the
> Dropbox/GDR data links, the request for an executive summary and submission guide, the Arena Core
> Values text, and the multi-pass implement/review/re-check instructions — has been read in full and
> acted on throughout this repository. It is not re-quoted verbatim here for length, but every concrete
> instruction in it is reflected in `docs/`, `src/`, `scripts/`, `tests/`, `LIMITATIONS.md`, and this
> README. The two Arena Core Values quoted in that prompt — Maximize P(Win) and Own the Outcome — are
> reproduced verbatim at the top of this file and are the standing frame for every future session.)*

</details>
