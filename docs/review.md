# Scientific review and negative preflight · 2026-10-21

## Scope and answer

**No new TIFF was generated. No competition slot was used.** The requirement to produce a unique
file is unmet; the stop rule prevents claiming successful completion. The run card is negative.
The starting repo was a README only. No earlier local experiment or runnable training pipeline existed.

The official reference describes **fault detection**, not a direct geothermal-vent prediction task.
Geothermal interpretation motivates fault mapping, but a high raster score would not verify a
reservoir, heat source, permeability, well productivity, or a discovered vent.

## What the H33 audit actually establishes

The pinned H33 bytes contain 37,654 positive pixels, all off the mirrored catalogue, finite values
in [0,1], and a matching CRS/shape/transform. Median catalogue distance is approximately 1,965 m;
about 5.77% of dots are within 300 m. These are **raster measurements**, not scores. See
[evidence/audit.json](../evidence/audit.json), input pins, and the upstream H33 builder snapshot.

The prior project's analysis describes H33 as a subset of earlier sparse candidates after
near-catalogue removals. We reviewed that explanation but did not independently reconstruct the
entire D28→H27→H33 lineage. Do not mislabel that narrative as a new causal experiment.

The shared local metric uses `DTI=T/(T+0.2*FP+0.8*FN)` with a distance-decaying 300 m triangular
kernel. Spreading dots can improve coverage per emitted pixel; removing a dot with little truth
credit can reduce false-positive mass. Removing a useful dot can instead lose recall. Thus the
H33 geometry is a plausible metric-efficiency explanation, not proof of why the hidden evaluator
returned the owner-reported value. It is particularly unsafe to interpret higher coverage of
known fault habitats as evidence of independent geological discovery.

**Can a new method beat the reported H33 value?** Possibly; no result in this run establishes it.
A scientifically useful route is to test additional physical information conditional on terrain,
coverage and catalogue distance, rather than simply optimizing dot count on a repeatedly used
proxy. Catalogue-hide recovery and newly mapped fault discovery have different selection biases.
Even a valid holdout win is not a leaderboard projection.

## Ranked hypotheses — proposals, not an assigned lane

All are new to this originally empty repository. **Global novelty across all 78 projects is not
established.** The inventory is metadata only. In particular, prior names already mention scarp,
radiometric fusion, Euler depth, relay ramps, contact termination and multi-physics concurrence.
The distinctions below are hypotheses to verify against source code before adopting any lane.
No expected numeric DTI gains are invented. Priority ranks reflect scientific testability and
incremental implementation effort, not measured performance. None was implemented or trained.

| Priority / cost | Specific layers and physical transform | Why a missing fault might appear | Non-fault mimic / distinction from reviewed approaches |
|---|---|---|---|
| 1 / medium | Cached `rtp`, `tmi` / magnetic-anomaly fields: fit paired cross-contact profiles, measure signed lateral displacement and persistence along strike; require consistency across scales | A buried lateral offset can interrupt a coherent contact despite weak topographic expression; hypothesis, not proof of mapping bias | Meandering intrusive contacts or levelling stripes. Tests displacement consistency rather than simply magnetic edge amplitude, contact termination or sparse catalogue halos |
| 2 / medium | Cached `det_elev` and LiDAR `step_max`, `downface_max`: pair opposite-signed curvature lobes and test same-sense vertical offset across adjacent drainage divides | A subdued discontinuous scarp might be detectable by repeated cross-profile geometry where a single ridge score fails | Terrace risers, road cuts and resistant bedding. Tests cross-divide displacement sign rather than a single scarp-strength threshold |
| 3 / medium–high | Cached GeoDAWN K/Th/TC and magnetic fields: test lateral displacement of a radiometric contact with matching magnetic offset, using within-lithology ranks | Offset across two different physical contrasts could reveal a covered or subtle cross-cutting structure | Soil moisture, alluvial sorting and lithologic juxtaposition without displacement. Tests offset direction agreement, not alteration brightness or generic feature fusion |
| 4 / high | Cached `iso_grav_anom`, `depth_to_base_surf`, `det_elev`: compare localized opposing basin-curvature lobes to smooth flexure controls at matched basin depth | Differential basement throw may create asymmetric basin geometry without an exposed surface scarp | Sedimentary compaction, volcanic loading and interpolation artifacts. Tests rejection of smooth-flexure alternatives rather than absolute depth or Euler clustering |

Band names above come from the prior project documentation, not freshly authenticated official
band descriptions. The shared manifest identifies existing cached products and a feature-stack
mirror; metadata availability does not validate scientific semantics or licensing. For all four,
first restore the cache, inspect bands/masks, and confirm provenance; do not fetch replacements
or rebuild features unnecessarily. Proposals 1 and 4 may involve nonindependent derived bands;
corroboration between two transforms of one measurement is not independent evidence.

No proposal relies on a newly claimed available external dataset. Official fallbacks are the
USGS GeoDAWN release and USGS 3DEP elevation products, plus the organizer feature download.
Their hosts are inaccessible under the current allowlist, so new external retrieval and licensing
are **not verified** and such additions are not designated viable here. The owner mirror's
LiDAR manifest reports incomplete tile coverage; missing tiles must be masked, never treated as
zero-valued geological evidence.

## Preregistered validation plan after blockers resolve

1. Assign one lane; stop if it already matches a registry method. Freeze at most three experiments.
2. Hide whole connected fault segments with a buffer. Audit the shared segment splitter: its
   documented maximum length is 12 pixels, not necessarily a complete fault. Ensure train/test
   tails do not share a connected segment; fix upstream before trusting results.
3. Recompute catalogue distances, orientation, density, fitting labels and normalization exclusively
   from visible/training information. Physical rasters must also be checked for catalogue-derived
   preprocessing. Exactly mask visible fault pixels at evaluation, not a broad convenience halo.
4. Run each feature alone as a leakage canary on the fixed spatial holdout. Record AUC and its
   sampling definition; AUC above 0.90 means investigate leakage before continuing. Low AUC
   does not prove absence of leakage. No canary has run in this session.
5. Compare candidate and current-best baseline on identical folds, valid masks and dot budgets.
   Pool TP/FP/FN before taking DTI. Use shared evaluator version/hashes, withheld counts and
   paired spatial-cluster 95% intervals. Keep development tuning separate from final validation.
6. Compare the pre-placement surface against every accessible registry prior; then compare final
   dots. A hash change is not novelty. A metadata-only scan or low average overlap is not enough.
7. Shared writer, all-finite export, read-back checks, hash and one-TIFF ZIP. Only then publish;
   selector approval and the authenticated weekly cap remain independent requirements.

## Irregularity register

| ID | Finding | Consequence / resolution |
|---|---|---|
| IR75-01 | No method paragraph assigns a lane | No modeling authorized; do not infer one from project number |
| IR75-02 | Every eligible pixel is within the literal positive-support registry witness | Universal overlap stop under current shared definition. No density exemption was introduced |
| IR75-03 | Continuous probabilities and binary dots are conflated by the inherited gate | This is a protocol ambiguity, not evidence all physics are duplicates; resolve centrally, not in a private fork |
| IR75-04 | Starting repository has no claimed pipeline or feature cache | Restored audit inputs/tools only; do not claim train→inference readiness |
| IR75-05 | Conflicting current-leader values and no authenticated score receipts | Owner reports remain unverified; no ORGANIZER-CONFIRMED number published |
| IR75-06 | Official rules/data/PDF hosts outside network allowlist | Links provided for review, not described as retrieved or currently valid |
| IR75-07 | Shared holdout uses capped-length segments | Buffered whole-fault independence needs explicit audit before use |
| IR75-08 | Mirror sample contains catalogue positives | Never use the sample/labels as a new submission |
| IR75-09 | Metadata inventory includes inputs and archived/quarantined files | 1,901 paths are not 1,901 unique submissions; no full byte-level uniqueness claim |
| IR75-10 | Upstream narrative contains inconsistent causal claims about H33 | Local measurements take precedence; hidden-score causation is unproven |
| IR75-11 | Supplied prompt is retained in deduplicated form, not verbatim | Original conversation remains authoritative; do not claim exact archival completeness |

The saturation witness is pinned and independently re-measured. It has positive support over
5,167,373 footprint pixels and covers all 5,106,385 off-catalogue eligible pixels. H33 forward overlap
is 1.0 while its full-footprint rank correlation with the witness is approximately 0.0582. Those are
**REGISTRY/RASTER MEASUREMENTS**, not HOLDOUT-DTI or competition scores. Low rank correlation
does not override the forward-overlap stop. The proof needs one witness, not the entire inventory;
passing novelty would require much broader checks. No candidate exists to label a duplicate.
