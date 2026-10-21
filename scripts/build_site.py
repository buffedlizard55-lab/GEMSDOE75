"""Render a static, evidence-led GitHub Pages site. Never creates a TIFF link."""
from html import escape
import json
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parents[1]


def page(title, content, active=''):
    links=[('index.html','Overview'),('download.html','Download'),('research.html','Research'),('evidence.html','Evidence'),('executive-summary.html','How to submit')]
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
    n=len(inv['repositories']); paths=sum(len(x.get('rasters',[])) for x in inv['repositories'])
    tag_text = 'NOT_APPROVED_TO_SUBMIT' if not card['approved_for_submission'] else 'APPROVED_FOR_REVIEW'
    status_head = 'Submission candidate: format-validated, not score-validated.' if not card['approved_for_submission'] else 'Approved for selector review.'
    status_body = ('A candidate TIFF exists (' + Path(card['output_file']).name + ') and passed every local '
                   'format check, but it is <strong>not OK to submit to the contest yet</strong>: the geometry is '
                   'placeholder data because this sandbox cannot reach the login-walled DrivenData data page, and '
                   'no holdout DTI, leakage canary, or registry uniqueness check could be run. Download for review only.'
                   if not card['approved_for_submission']
                   else 'This candidate has passed format validation, holdout evaluation, leakage canary, and registry '
                   'uniqueness checks. It is ready for the DrivenData submission form.')
    section_notice = '<section class="notice" aria-labelledby="status"><div><span class="tag">' + tag_text + '</span><h2 id="status">' + status_head + '</h2><p>' + status_body + '</p></div><a class="button" href="download.html">Read submission status <span aria-hidden="true">→</span></a></section>'
    home=f'''<section class="hero"><p class="eyebrow">GEOLOGICAL FAULT MAPPING / RESEARCH LOG 001</p>
<h1>A better prediction starts<br>with a defensible test.</h1><p class="lede">Independent research for the DOE GEMS competition. Every artifact needs a scientific rationale, a leakage-safe evaluation, and a truthful submission status.</p></section>
{section_notice}
<section class="stats" aria-label="Review facts"><div><b>{n}</b><span>Repository trees inspected</span></div><div><b>{paths:,}</b><span>TIFF paths inventoried · not validated</span></div><div><b>1</b><span>Model experiment / 0 slots used</span></div></section>
<section class="split"><div><p class="eyebrow">THE EXECUTIVE SUMMARY</p><h2>Do not confuse a valid file<br>with a validated idea.</h2><p>The historical H33 raster passes our local format checks. That does not make it unique, new, or approved for reuse. We downloaded it for education only.</p><p>A prior probability surface is positive across the entire study footprint. Treating every positive pixel as a “dot” makes the forward-overlap gate reject all nonempty candidates.</p><a class="text-link" href="evidence.html">Inspect the evidence →</a></div><div class="panel"><h3>Readiness checkpoint</h3><ul class="checkpoints"><li><span>Prior-byte audit</span><strong class="good">Complete</strong></li><li><span>Assigned modeling lane</span><strong class="good">fault_tip_halo (unique rule)</strong></li><li><span>Unique new TIFF</span><strong class="good">Generated (schema-demo, DO-NOT-SUBMIT)</strong></li><li><span>Candidate holdout + canaries</span><strong>Not run</strong></li><li><span>Weekly slot approval</span><strong>Not approved</strong></li></ul></div></section>
<section><div class="section-head"><div><p class="eyebrow">WHAT WE LEARNED</p><h2>Three findings worth carrying forward.</h2></div></div><div class="cards"><article><span class="number">01</span><h3>Geometry is not discovery.</h3><p>Sparse placement can help distance-tolerant coverage. H33’s hidden-score causation is unproven; a fault map does not establish a geothermal vent.</p></article><article><span class="number">02</span><h3>Novelty needs a definition.</h3><p>Continuous support saturates the inherited overlap gate. A low rank correlation does not cancel a failed overlap test.</p></article><article><span class="number">03</span><h3>A negative result is useful.</h3><p>No renamed prior. No invented score. No wasted submission slot. The blockers, audit and next experiments are preserved.</p></article></div></section>
<section class="closing"><div><h2>Four hypotheses. No promised score.</h2><p>Ranked physical mechanisms, named mimics, data dependencies, and a preregistered validation plan.</p></div><a class="button dark" href="research.html">Read the research →</a></section>'''
    (ROOT/'index.html').write_text(page('Overview',home,'index.html'))
    instructions='''<p class="eyebrow">EXECUTIVE SUMMARY / SUBMISSION GUIDE</p><h1>Download only when<br>the gates are green.</h1><section class="notice"><div><span class="tag">FORMAT-VALIDATED, NOT SCORE-VALIDATED</span><h2>A submission TIFF exists — download only for review.</h2><p>Gems75 fault-tip-halo candidate has passed every local format check but is <strong>not OK to submit to the contest yet</strong>. The geometry is placeholder data because this sandbox cannot reach the login-walled DrivenData data page. Download the TIFF and receipt from the Download page for review; do not upload to the contest.</p></div><a class="button" href="download.html">Go to download page →</a><a class="button" href="evidence/run-card.json" download>Download run card (JSON)</a></section>
<section class="prose"><h2>Why the “values in [0, 1]” error happens</h2><p>A raw feature raster, fault-label nodata such as −1, infinity, an unmasked sentinel, or an unnormalized model output can violate the prediction range. We cannot diagnose your earlier uploaded file because its bytes were not supplied. Do not simply rename a feature or label TIFF. A NaN is not a valid probability inside the footprint.</p><p>Our conservative export policy requires finite probabilities in [0,1] everywhere, with zero outside the footprint, no positive pixels on visible mapped faults, a single float32 band, and exact reference-grid alignment. This policy is stricter than some historical exports and is not proof of organizer acceptance. The shared writer rejects bad values rather than silently clipping them.</p>
<h2>When a new candidate is approved</h2><ol><li><strong>Check the readiness receipt.</strong> It must show a candidate hash, successful format and full-scope novelty checks, feature canaries, comparable pooled HOLDOUT-DTI with evaluator/count/CI, and separate selector approval.</li><li><strong>Download the named prediction.</strong> Use its unique <code>.tif</code> filename, or a ZIP containing exactly that one TIFF. Do not upload the JSON receipt, report, training data, or sample.</li><li><strong>Verify file integrity.</strong> Compare SHA-256 with the published receipt. Confirm exact CRS, dimensions and geotransform against the organizer template; do not rely only on the filename.</li><li><strong>Check the authenticated contest page.</strong> Read current eligibility, data rules, deadline and remaining weekly cap. None is freshly verified here.</li><li><strong>Use New submission.</strong> Choose the TIFF/ZIP in “File to submit.” Paste the published note (at most 140 characters). This site does not upload or consume slots for you.</li><li><strong>Preserve the receipt.</strong> Record the organizer's submission identifier, score, timestamp and file hash. Only then label the result ORGANIZER-CONFIRMED. Rejection is not a successful submission.</li></ol>
<h2>Current artifact identity</h2><p><strong>Submission name:</strong> gems75-fault-tip-halo-20261021-SCHEMA-DEMO-DO-NOT-SUBMIT. <strong>Prediction SHA-256:</strong> 89d57a586634dafa256dc752a5d8a08815be23f26de4f651063378a198742098. <strong>Verdict:</strong> negative — format-validated, not score-validated, not approved for submission. Download from the Download page for review only.</p>
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
    # --- Download page: the one place a candidate TIFF may be linked ---
    download = f'''<p class="eyebrow">DOWNLOAD SUBMISSION CANDIDATE</p><h1>One file to submit.<br>Read the status first.</h1>
<section class="notice" aria-labelledby="download-status"><div>
<span class="tag">{"APPROVED_FOR_REVIEW" if card["approved_for_submission"] else "NOT_APPROVED_TO_SUBMIT"}</span>
<h2 id="download-status">{"Submission slot not used — format-validated, not score-validated." if not card["approved_for_submission"] else "Approved for selector review."}</h2>
<p>{"This file passed every local format check (single band, float32, EPSG:32611, 100 m, values in [0,1], no NaN, exact template geometry on the placeholder grid). It is <strong>not</strong> OK to submit to the contest yet: the geometry is placeholder data because this sandbox cannot reach the login-walled DrivenData data page, and no holdout DTI, leakage canary, or registry uniqueness check could be run. Download for review only." if not card["approved_for_submission"] else "This candidate has passed format validation, holdout evaluation, leakage canary, and registry uniqueness checks. It is ready for the DrivenData submission form."}</p>
</div><a class="button" href="{card["output_file"]}" download>Download {Path(card["output_file"]).name}</a><a class="button" href="{card["output_file"][:-4]}.json" download>Download validation receipt (JSON)</a></section>
<section class="prose"><h2>File identity</h2>
<ul>
<li><strong>Name:</strong> {Path(card["output_file"]).name}</li>
<li><strong>SHA-256:</strong> {card["raster_sha256"] or "not yet generated"}</li>
<li><strong>Mode:</strong> {card["mode"]}</li>
<li><strong>Rule:</strong> {card.get("rule","n/a")}</li>
<li><strong>Ready to submit:</strong> <strong class="{'good' if card["approved_for_submission"] else ''}">{card["approved_for_submission"]}</strong></li>
<li><strong>Verdict:</strong> {card["verdict"]}</li>
</ul>
<h2>What must happen before this file can be submitted</h2>
<ol>
<li><strong>Get real data.</strong> A human with a DrivenData account downloads training_features.tif, labels.tif, and sample_submission.tif from the organizer's data page and places them in data/raw/. This sandbox cannot reach that login-walled page.</li>
<li><strong>Re-generate in REAL mode.</strong> Run <code>python scripts/make_submission.py --rule fault_tip_halo</code> so the template is derived from the real training_features.tif, not a placeholder.</li>
<li><strong>Validate geometry.</strong> Run <code>python scripts/verify_submission.py docs/downloads/&lt;name&gt;.tif --template data/raw/training_features.tif</code> to confirm exact CRS, shape, and transform match the organizer's grid.</li>
<li><strong>Run the holdout and canaries.</strong> Score the rule with <code>gems_doe.holdout.run_holdout</code> and <code>leakage_canary</code> against the real catalogue. Only a holdout DTI that beats the current best is eligible for a weekly slot.</li>
<li><strong>Check uniqueness.</strong> Compare against registry rasters (Spearman > 0.90 or &gt;70% of dots within 3 px = duplicate, stop).</li>
<li><strong>Get selector approval.</strong> Promotion to a competition slot is a separate decision within the weekly cap shown on the submission page.</li>
</ol>
<h2>Why the “values in [0, 1]” error cannot happen with this file</h2>
<p>The writer strips the documented float32 sentinel (−3.4028234663852886e38) and any NaN/inf, clips all values to [0,1], writes every pixel as finite (0.0 outside the footprint), and omits a nodata tag. The file is re-opened from disk and re-validated before the receipt is issued. Both documented mechanisms behind the portal error are closed by construction.</p>
<p><a class="button dark" href="executive-summary.html">Full submission guide →</a></p></section>'''
    (ROOT/'download.html').write_text(page('Download candidate',download,'download.html'))

    (ROOT/'evidence.html').write_text(page('Evidence',evid,'evidence.html'))


if __name__ == '__main__':
    main()
