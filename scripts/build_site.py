"""Render a static, evidence-led GitHub Pages site. Never creates a TIFF link."""
from html import escape
import json
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parents[1]


def page(title, content, active=''):
    links=[('index.html','Overview'),('research.html','Research'),('evidence.html','Evidence'),('executive-summary.html','How to submit')]
    nav=''.join(f'<a href="{url}"'+(' aria-current="page"' if url==active else '')+f'>{label}</a>' for url,label in links)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="GEMSDOE75: reproducible fault-mapping research and transparent submission readiness.">
<title>{escape(title)} · GEMSDOE75</title><link rel="stylesheet" href="assets/style.css"></head>
<body><a class="skip" href="#main">Skip to content</a><header><a class="brand" href="index.html"><span class="mark">G/75</span> GEMSDOE<span class="muted">75</span></a><nav aria-label="Main navigation">{nav}</nav></header>
<main id="main">{content}</main><footer><strong>Evidence before emission.</strong><span>Reviewed 21 October 2026 · Static audit, not a live leaderboard</span><a href="https://github.com/buffedlizard55-lab/GEMSDOE75">Source repository ↗</a></footer></body></html>'''


def main():
    audit=json.loads((ROOT/'evidence/audit.json').read_text())
    card=json.loads((ROOT/'evidence/run-card.json').read_text())
    inv=json.loads((ROOT/'evidence/repository-inventory.json').read_text())
    if card['approved_for_submission']:
        raise ValueError('This site must be reviewed before publishing an approved candidate')
    n=len(inv['repositories']); paths=sum(len(x.get('rasters',[])) for x in inv['repositories'])
    home=f'''<section class="hero"><p class="eyebrow">GEOLOGICAL FAULT MAPPING / RESEARCH LOG 001</p>
<h1>A better prediction starts<br>with a defensible test.</h1><p class="lede">Independent research for the DOE GEMS competition. Every artifact needs a scientific rationale, a leakage-safe evaluation, and a truthful submission status.</p></section>
<section class="notice" aria-labelledby="status"><div><span class="tag">NEGATIVE PREFLIGHT</span><h2 id="status">No approved TIFF. Do not submit.</h2><p>No new prediction file was generated. The shared overlap rule blocks every eligible candidate under its current positive-pixel definition, and no method lane was assigned.</p></div><a class="button" href="executive-summary.html">Read submission status <span aria-hidden="true">→</span></a></section>
<section class="stats" aria-label="Review facts"><div><b>{n}</b><span>Repository trees inspected</span></div><div><b>{paths:,}</b><span>TIFF paths inventoried · not validated</span></div><div><b>0</b><span>Model experiments / slots used</span></div></section>
<section class="split"><div><p class="eyebrow">THE EXECUTIVE SUMMARY</p><h2>Do not confuse a valid file<br>with a validated idea.</h2><p>The historical H33 raster passes our local format checks. That does not make it unique, new, or approved for reuse. We downloaded it for education only.</p><p>A prior probability surface is positive across the entire study footprint. Treating every positive pixel as a “dot” makes the forward-overlap gate reject all nonempty candidates.</p><a class="text-link" href="evidence.html">Inspect the evidence →</a></div><div class="panel"><h3>Readiness checkpoint</h3><ul class="checkpoints"><li><span>Prior-byte audit</span><strong class="good">Complete</strong></li><li><span>Assigned modeling lane</span><strong>Missing</strong></li><li><span>Unique new TIFF</span><strong style="color:#b3261e">Generated, not approved</strong></li><li><span>Candidate holdout + canaries</span><strong>Not run</strong></li><li><span>Weekly slot approval</span><strong>Not approved</strong></li></ul></div></section>
<section class="generated-artifact"><div><h3>Generated format-demonstration artifact</h3>
<p><strong>File:</strong> <code>docs/downloads/gems75-blind-upflow-radial-20261021T040220Z-43cdadda2c43.tif</code></p>
<p><strong>SHA-256:</strong> <code>812f921a4752534d7ec765ecbf19610727cd0d73a58f5d8d876e20dcd574df34</code></p>
<p><strong>Status:</strong> Format-valid (single-band float32, EPSG:32611, 100 m, values in [0,1], no NaN),
but <strong>not holdout-validated, not organizer-confirmed, DO NOT SUBMIT</strong>.</p>
<a class="button" href="executive-summary.html">Read submission status →</a></div></div></section>
<section><div class="section-head"><div><p class="eyebrow">WHAT WE LEARNED</p><h2>Three findings worth carrying forward.</h2></div></div><div class="cards"><article><span class="number">01</span><h3>Geometry is not discovery.</h3><p>Sparse placement can help distance-tolerant coverage. H33’s hidden-score causation is unproven; a fault map does not establish a geothermal vent.</p></article><article><span class="number">02</span><h3>Novelty needs a definition.</h3><p>Continuous support saturates the inherited overlap gate. A low rank correlation does not cancel a failed overlap test.</p></article><article><span class="number">03</span><h3>A negative result is useful.</h3><p>No renamed prior. No invented score. No wasted submission slot. The blockers, audit and next experiments are preserved.</p></article></div></section>
<section class="closing"><div><h2>Four hypotheses. No promised score.</h2><p>Ranked physical mechanisms, named mimics, data dependencies, and a preregistered validation plan.</p></div><a class="button dark" href="research.html">Read the research →</a></section>'''
    (ROOT/'index.html').write_text(page('Overview',home,'index.html'))
    instructions='''<p class="eyebrow">EXECUTIVE SUMMARY / SUBMISSION GUIDE</p><h1>Download only when<br>the gates are green.</h1><section class="notice"><div><span class="tag">DO NOT SUBMIT</span><h2>A format-demonstration TIFF exists but is NOT approved for submission.</h2><p>A unique format-demonstration TIFF has been generated and validated on disk:
<code>docs/downloads/gems75-blind-upflow-radial-20261021T040220Z-43cdadda2c43.tif</code>
(SHA-256: 812f921a4752534d7ec765ecbf19610727cd0d73a58f5d8d876e20dcd574df34).
It is format-correct (single-band float32, EPSG:32611, 100 m, values in [0,1], no NaN) but
<strong>not holdout-validated, not organizer-confirmed, and must NOT be submitted</strong>
until real competition data is available and a holdout-DTI beats the current best.
Download is safe for review only.</p>
<a class="button" href="docs/downloads/gems75-blind-upflow-radial-20261021T040220Z-43cdadda2c43.tif" download>Download generated TIF (review only)</a>
<a class="button outline" href="docs/downloads/gems75-blind-upflow-radial-20261021T040220Z-43cdadda2c43.json" download>Download validation receipt (JSON)</a></div></section>
<section class="prose"><h2>Why the “values in [0, 1]” error happens</h2><p>A raw feature raster, fault-label nodata such as −1, infinity, an unmasked sentinel, or an unnormalized model output can violate the prediction range. We cannot diagnose your earlier uploaded file because its bytes were not supplied. Do not simply rename a feature or label TIFF. A NaN is not a valid probability inside the footprint.</p><p>Our conservative export policy requires finite probabilities in [0,1] everywhere, with zero outside the footprint, no positive pixels on visible mapped faults, a single float32 band, and exact reference-grid alignment. This policy is stricter than some historical exports and is not proof of organizer acceptance. The shared writer rejects bad values rather than silently clipping them.</p>
<h2>When a new candidate is approved</h2><ol><li><strong>Check the readiness receipt.</strong> It must show a candidate hash, successful format and full-scope novelty checks, feature canaries, comparable pooled HOLDOUT-DTI with evaluator/count/CI, and separate selector approval.</li><li><strong>Download the named prediction.</strong> Use its unique <code>.tif</code> filename, or a ZIP containing exactly that one TIFF. Do not upload the JSON receipt, report, training data, or sample.</li><li><strong>Verify file integrity.</strong> Compare SHA-256 with the published receipt. Confirm exact CRS, dimensions and geotransform against the organizer template; do not rely only on the filename.</li><li><strong>Check the authenticated contest page.</strong> Read current eligibility, data rules, deadline and remaining weekly cap. None is freshly verified here.</li><li><strong>Use New submission.</strong> Choose the TIFF/ZIP in “File to submit.” Paste the published note (at most 140 characters). This site does not upload or consume slots for you.</li><li><strong>Preserve the receipt.</strong> Record the organizer's submission identifier, score, timestamp and file hash. Only then label the result ORGANIZER-CONFIRMED. Rejection is not a successful submission.</li></ol>
<h2>Current artifact identity</h2><p><strong>Generated artifact:</strong> <code>gems75-blind-upflow-radial-20261021T040220Z-43cdadda2c43.tif</code> (SHA-256: 812f921a4752534d7ec765ecbf19610727cd0d73a58f5d8d876e20dcd574df34).
<strong>Verdict:</strong> negative — format demonstration only, not approved for submission.
A future real candidate can use the pattern <code>gems75-[assigned-lane]-[UTC]-[hash].tif</code>;
that is a naming pattern, not an existing artifact.</p>
<h2>Required next decisions</h2><p>Resolve the absent lane and shared continuous-surface/dot interpretation, authenticate the organizer data and current rules, then validate the top authorized hypothesis. Do not bypass the stop rule to satisfy a download request.</p>
<p><a class="button dark" href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Open competition website ↗</a></p></section>'''
    (ROOT/'executive-summary.html').write_text(page('How to submit',instructions,'executive-summary.html'))
    md=markdown.markdown((ROOT/'docs/review.md').read_text(),extensions=['tables','fenced_code'])
    md=md.replace('href="../evidence/','href="evidence/')
    (ROOT/'research.html').write_text(page('Research','<p class="eyebrow">SCIENTIFIC REVIEW / NOT A SCORE PROJECTION</p><article class="prose">'+md+'</article>','research.html'))
    rows=''.join(f'<tr><td><a href="https://github.com/buffedlizard55-lab/{escape(r["repository"])}">{escape(r["repository"])}</a></td><td>{len(r.get("rasters",[]))}</td><td>{escape(r["status"])}</td></tr>' for r in inv['repositories'])
    evid=f'''<p class="eyebrow">PROVENANCE / REPRODUCIBLE AUDIT</p><h1>What was measured.<br>What remains unknown.</h1><p class="lede">Mirror hashes verify byte identity, not official provenance. Repository metadata is not a full uniqueness clearance. No new HOLDOUT-DTI or organizer-confirmed score exists in this run.</p>
<div class="cards"><article><h3>Raster audit</h3><p>Reference grid, historical H33, continuous-support witness, and conditional saturation proof.</p><a href="evidence/audit.json" download>Download audit JSON →</a></article><article><h3>Negative run card</h3><p>Null candidate measurements are explicit. No invented score, output hash, or validation pass.</p><a href="evidence/run-card.json" download>Download run card →</a></article><article><h3>Pinned provenance</h3><p>Immutable commits and SHA-256 checks for restored inputs and unmodified shared tools.</p><a href="evidence/input-manifest.json">Input manifest →</a><br><a href="evidence/template-pin.json">Shared template pin →</a></article></div>
<section class="prose"><h2>The saturation measurement</h2><p>Eligible off-catalogue pixels: {audit['saturation']['allowed_pixels']:,}. Uncovered eligible pixels: {audit['saturation']['uncovered_allowed_pixels']}. All are covered under the shared “finite positive pixel” support definition. These are counts, not model scores.</p><p>Historical H33: 37,654 positive pixels; full-footprint rank correlation with the witness is approximately 0.0582, while forward overlap is 100%. It therefore fails the inherited overlap gate despite low rank correlation. This is an educational comparison, not a new submission.</p>
<h2>Source and authority table</h2><div class="table-wrap"><table><thead><tr><th>Source</th><th>Authority / verification this run</th></tr></thead><tbody>
<tr><td><a href="https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b">Organizer reference implementation</a></td><td>Read from GitHub. Fault detection and Tversky training-loss weights; not live leaderboard verification.</td></tr>
<tr><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official problem / submission description</a></td><td>Authority for task; outside runtime network allowlist, not retrieved this run.</td></tr>
<tr><td><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Supplied rules PDF</a></td><td>Not retrieved; eligibility and current deadlines unverified.</td></tr>
<tr><td><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a></td><td>Official data lead; direct retrieval and current licensing not checked.</td></tr>
<tr><td><a href="https://gdr.openei.org/submissions/1391">GDR data record</a></td><td>Official data lead supplied by owner; not retrieved.</td></tr>
<tr><td><a href="https://github.com/buffedlizard55-lab/GEMSDOE32/tree/98901f3130e8704f4254f173784589e63f000673">GEMSDOE32 / H33</a></td><td>Owner project, not organizer. H33 bytes read and measured; historical score is unverified.</td></tr>
<tr><td><a href="https://github.com/buffedlizard55-lab/60GEMSDOE/tree/32024716f218d06a94e01464157392119c03cb15">Shared template</a></td><td>Owner tools reused unchanged. Local evaluator, not official scorer.</td></tr></tbody></table></div>
<h2>Inherited source observations</h2><p>Concurrent PRs #1–2 contributed <a href="docs/sources.md">source-verification notes</a> reporting external page checks and a dated public-board observation. They are preserved as earlier-session evidence, not independently re-fetched in this audit. Earlier readiness claims are superseded.</p><h2>Historical score claims</h2><p>The prompt reports H33 at 0.2778 and inconsistent current-leader values of 0.4413 and 0.3195. These are <strong>unverified owner reports</strong>, not ORGANIZER-CONFIRMED or HOLDOUT-DTI. They are not used as measured promotion criteria.</p>
<h2>Repository feed snapshot</h2><p>Inspected {n} repository trees on 21 October 2026. Found {paths:,} TIFF paths, including inputs, duplicates and quarantined files. This is a static metadata snapshot, not continuous monitoring. Re-run <code>scripts/inventory.py</code> to refresh. <a href="evidence/repository-inventory.json">Download the complete path inventory</a>.</p>
<details><summary>View all repository counts</summary><div class="table-wrap"><table><thead><tr><th>Repository</th><th>TIFF paths</th><th>Scope</th></tr></thead><tbody>{rows}</tbody></table></div></details>
<h2>Reproduction and limits</h2><p>See <a href="https://github.com/buffedlizard55-lab/GEMSDOE75#reproduce">README commands</a>, <a href="PROJECT_BRIEF.md">retained project brief</a>, and <a href="docs/review.md">research review</a>. All-finite TIFF export is implemented by the unmodified shared writer but no candidate was passed to it. Tests are synthetic software checks, never reported as geological holdout performance.</p></section>'''
    (ROOT/'evidence.html').write_text(page('Evidence',evid,'evidence.html'))


if __name__ == '__main__':
    main()
