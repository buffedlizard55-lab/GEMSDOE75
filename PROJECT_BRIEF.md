# Retained source links and requirements

The README contains the deduplicated operating prompt and values. This file retains the URLs
and conflicts needed to continue the work, not a claim of verbatim preservation of the message.

## Owner-reported reference results — not verified scores

The prompt reports H33 (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`) as **0.2778**.
It also names **0.4413** as the current high score and later **0.3195** as the current high score.
These statements conflict as current-leader claims. None is ORGANIZER-CONFIRMED here, because
no submission-page receipt was available. Do not choose a target based on an invented “live” value.
A current catalogue holdout best is also absent from the starting repository.

The full list of named project repositories (GEMSDOE through the stated GEMSDOE78) and their
TIFF paths is retained in `evidence/repository-inventory.json`. GitHub tree metadata was read,
not all website prose, receipts, TIFF bytes or private submissions. Paths include input data and
quarantined files; the inventory is not a list of 1,901 distinct valid competition submissions.

## Official / organizer links supplied for review

- Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/
- Problem: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- About: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- Data: https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Official reference: https://github.com/drivendataorg/gems-prize-reference-solution
- Rules PDF supplied: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- USGS GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- GDR data: https://gdr.openei.org/submissions/1391
- INGENIOUS: https://gbcge.org/current-projects/ingenious/
- CRS background: https://epsg.io/32611
- Tversky background (not organizer authority): https://en.wikipedia.org/wiki/Tversky_index

Only the GitHub reference was directly read in this run. Other hosts are outside this runtime's
outbound allowlist; do not describe the PDF, rules, current leaderboard, data eligibility, or weekly
cap as freshly verified. The reference notebook uses Tversky *training loss* with the requested
weights, but that alone does not verify the organizer's full distance-tolerant evaluation code.

## Owner-provided mirrors (not official-origin authentication)

- https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0
- https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0
- https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0
- https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0
- https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0

Dropbox retrieval was not attempted outside the allowlist. GitHub mirrors let us audit the grid
and prior bytes without claiming authenticated competition access. Do not copy `existing_faults`
or `sample_submission` into a prediction: the mirrored sample's positive support is the catalogue.

## Required submission experience

A single-band GeoTIFF or ZIP containing exactly one GeoTIFF; finite probability values in [0,1],
exact reference CRS, shape and transform. Give it a unique informative name and a short note
(at most 140 characters). At the top of the site, state separately whether downloading is safe,
whether format validation passed, whether uniqueness passed, and whether the selector approved
submission. No raw features, labels or report PDF may masquerade as the predicted TIFF.

## Concurrent-source note

The subsequently integrated PR #2 source register reports a dated public-board observation at
0.4413. See `docs/sources.md`; this is inherited verification from that session, not an independent
re-fetch or ORGANIZER-CONFIRMED submission receipt in this run. This narrows the historical
leader ambiguity but does not establish a current live value or H33 score-to-file attribution.
