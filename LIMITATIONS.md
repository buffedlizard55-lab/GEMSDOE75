# Limitations, blockers, and exactly what is needed to unblock them

Last verified: 2026-10-21, in this session, by direct tool calls (not inherited
from memory of prior sessions). Every claim below was reproduced live.

## 1. No access to the real competition data (the single biggest blocker)

**What's missing:** `training_features.tif`, `labels.tif`, `sample_submission.tif`,
`1m_DEM_links.csv`.

**Why:** The data download page requires an authenticated DrivenData session.
Verified today: an unauthenticated request to
<https://www.drivendata.org/competitions/306/competition-doe-gems/data/>
redirects to `/accounts/login/?next=/competitions/306/competition-doe-gems/data/`.
This agent has no DrivenData account credentials and will not ask you for a
password or token in chat (see the platform's own security rules).

**What's needed to unblock:** A human with a DrivenData account logs in,
downloads the four files from the data page, and places them in `data/raw/`
with exactly these names (see `scripts/download_competition_data.sh` for the
mapping). After that, `python scripts/prepare_data.py` runs immediately — it
is already written, tested for its error paths, and waiting.

## 2. This sandbox's own network is firewalled to six hosts

Confirmed today with direct `curl` calls from this sandbox's bash tool: only
`github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`,
`pypi.org`, and `files.pythonhosted.org` are reachable. Every other host in
this project's source list — `www.drivendata.org`, `www.dropbox.com`,
`gdr.openei.org`, `usgs.gov`, `sciencebase.gov`, `epsg.io`,
`en.wikipedia.org`, `docs.nlr.gov`, `earthquake.usgs.gov` — timed out or
refused the connection (`000` from curl).

**Consequence:** `scripts/download_competition_data.sh` cannot fetch anything
when run inside this sandbox. It is written to be run on an unrestricted
machine (your laptop, a CI runner, a DrivenData notebook) instead, and it
says so explicitly when it runs here.

## 3. The page-fetch research tool reaches more hosts, but cannot retrieve binary files

This agent also has a separate "fetch a web page as text" tool that runs on
different infrastructure and — unlike the sandbox's own network — **can**
reach `www.drivendata.org`, `gdr.openei.org`, `docs.nlr.gov`,
`community.drivendata.org`, and GitHub Pages sites. This is how every
official source cited in `docs/data/sources.json` was actually read this
session (not assumed, not remembered from training — fetched live and
quoted).

However, this tool renders pages as text/markdown. Tested directly this
session against a Dropbox GeoTIFF download link: it followed the redirect
but returned empty binary content, not an image or array. **It cannot
retrieve GeoTIFFs, zipped shapefiles, or any other binary dataset.** That
means even the *freely licensed, no-login* external data our own ranked
hypotheses need (e.g. GDR submission 1391's Quaternary Volcanics shapefile)
cannot be pulled into this checkout automatically either — it needs a human,
or an unrestricted machine running `scripts/download_competition_data.sh`.

## 4. Consequence for "generate a unique, downloadable submission TIF"

Because of (1)-(3), this project has **zero bytes of the real feature stack
or fault catalogue** to detect anything from. Any raster claiming to be a
scientifically novel, high-DTI fault-detection submission, produced without
that data, would be fabricated — exactly what "no hallucinations" forbids.

What this project ships instead, and why it is still useful:

- A fully tested, from-scratch, line-by-line verified implementation of the
  organizer's own metric (`src/gems_doe/metric.py`), reproducing the
  published worked example (0.60) exactly.
- A submission writer/validator (`src/gems_doe/submission_io.py`) that
  directly fixes the two documented mechanisms behind the
  `"Predicted values must be in range [0, 1]"` error.
- A spatially-blocked hide-and-recover holdout evaluator
  (`src/gems_doe/holdout.py`), unit-tested on synthetic fault rasters,
  ready to run unchanged on the real catalogue the moment it is available.
- One artifact you *can* download today:
  `docs/downloads/gemsdoe75-zeros-SCHEMA-DEMO-DO-NOT-SUBMIT.tif` — an
  all-zeros raster (the organizer's own documented reference baseline
  behavior) on a **placeholder geometry we could not verify against the
  real file**. It is named, tagged in its own JSON receipt, and labeled on
  the website as **DO NOT SUBMIT**. It exists only to prove the writer
  code produces a format-clean file end-to-end.
- Four new, ranked, not-yet-tried geological hypotheses
  (`docs/data/hypotheses.json`) that do not duplicate anything found in the
  sibling repositories' own published hypothesis lists, each with a named
  non-fault confound and a named, checked, free/official data source.

## 5. The "scores" quoted from sibling GEMSDOE* sites are not organizer scores

Every sibling site this project could read (e.g. GEMSDOE32) states explicitly,
in its own text: *"no score in this repository is organizer-verified."* The
numbers like `0.2778` are self-reported outputs of each repo's own internal
simulation ("live-anchored truth model"), not entries confirmed by
DrivenData. The only ORGANIZER-CONFIRMED numbers in this entire project are
the ones read directly off the live public leaderboard
(<https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>),
reproduced in `docs/data/sources.json`.

**Irregularity flagged for manual review:** the task prompt states "0.3195
is the highest score right now." The live leaderboard, fetched today, shows
rank 1 at 0.4413 and rank 2 at 0.3904 — there is no 0.3195 entry near the
top. 0.3195 does not match today's snapshot; it is most likely a reading
from an earlier date (the leaderboard changes continuously — 26-43
submissions per competitor). Treat any leaderboard number not timestamped
to this session as stale until re-verified.

## 6. What a human needs to do to fully unblock this project

1. Log into DrivenData and download the four competition files (5 minutes).
2. Place them in `data/raw/` exactly as named in
   `scripts/download_competition_data.sh`.
3. Run `python scripts/prepare_data.py`.
4. For each hypothesis in `docs/data/hypotheses.json`, download its one
   external file (links and sizes given, all free/official, all under 60 MB)
   on any machine with normal internet access, and place it in
   `data/raw/external/`.
5. Re-run the test suite (`pytest tests -q`) — it will still pass, since it
   only depends on synthetic data — then build and run the per-hypothesis
   `predict_fn` and score it with `gems_doe.holdout.run_holdout` before
   anyone spends a weekly submission slot on it.

Until step 1 happens, every number this project could report about a real
fault-detection score would be invented. We will not do that.
