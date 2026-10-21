"""Negative preflight, using unmodified shared gates. No model experiment or emission."""
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))
sys.path.insert(0, str(ROOT))
from gems57 import gates, uniqueness
from scripts.fetch_inputs import sha256


def check_pins():
    pin = json.loads((ROOT / 'evidence/template-pin.json').read_text())
    for entry in pin['files']:
        if sha256(ROOT / entry['path']) != entry['sha256']:
            raise ValueError(f"Modified shared tool: {entry['path']}")
    manifest = json.loads((ROOT / 'evidence/input-manifest.json').read_text())
    for entry in manifest['files']:
        if sha256(ROOT / '.cache/inputs' / entry['name']) != entry['sha256']:
            raise ValueError(f"Input hash mismatch: {entry['name']}")


def read_aligned(path, expected):
    with rasterio.open(path) as src:
        if src.count != 1 or (src.shape, src.crs, src.transform) != expected:
            raise ValueError(f'Grid mismatch: {path.name}')
        return src.read(1)


def run():
    check_pins()
    folder = ROOT / '.cache/inputs'
    with rasterio.open(folder / 'sample_submission.tif') as sample:
        expected = (sample.shape, sample.crs, sample.transform)
        footprint = np.isfinite(sample.read(1))
    catalogue = read_aligned(folder / 'existing_faults.tif', expected) > 0
    h33 = read_aligned(folder / 'h33.tif', expected)
    witness = read_aligned(folder / 'registry-witness.tif', expected)
    saturation = uniqueness.saturation_certificate(folder / 'registry-witness.tif', footprint,
                        catalogue, expected_grid=expected)
    saturation['witness_file'] = '.cache/inputs/registry-witness.tif'
    validator = gates.format_report(folder / 'h33.tif', folder / 'sample_submission.tif', footprint=footprint)
    validator['path'] = '.cache/inputs/h33.tif'
    distances = distance_transform_edt(~catalogue)[h33 > 0] * 100
    rho = uniqueness.surface_rho(h33, witness, footprint)
    rho = {k: None if isinstance(v, float) and not np.isfinite(v) else v for k, v in rho.items()}
    audit = dict(evidence_class='RASTER-AUDIT-NOT-A-SCORE', date_utc='2026-10-21',
        inventory_scope='One saturation witness and historical H33; not a full registry scan',
        template_pin='evidence/template-pin.json', saturation=saturation,
        h33_educational_only=dict(sha256=sha256(folder / 'h33.tif'), validator=validator,
            positive_pixels=int((h33 > 0).sum()), catalogue_intersections=int(((h33 > 0) & catalogue).sum()),
            median_catalogue_distance_m=float(np.median(distances)),
            fraction_within_300m=float(np.mean(distances <= 300)),
            forward_overlap_vs_witness=uniqueness.dot_overlap(np.where(footprint,h33,0),np.where(footprint,witness,0)),
            rank_comparison=rho),
        policy_interpretation='Shared template defines dots as finite values > 0. Continuous probabilities are not necessarily discrete detections; no exemption was authorized.',
        decision='STOP: no lane specified; literal support gate saturated. No candidate built, no copied submission offered.')
    (ROOT / 'evidence/audit.json').write_text(json.dumps(audit, indent=2, allow_nan=False)+'\n')
    card = dict(hypothesis='Deferred: magnetic contact lateral-offset consistency under cover',
        mechanism='Test repeated along-strike displacement of independent magnetic contact profiles, not edge amplitude alone.',
        non_fault_mimic='Meandering intrusive contact and survey levelling stripes',
        holdout_dti=dict(evidence_class='HOLDOUT-DTI',status='NOT RUN: preflight stopped before experiments',
            evaluator_version='gems57-pooled-hide-v2 (pinned, not executed)',withheld_positives=None,dti=None,ci95=None),
        registry=dict(candidate_surface_rank_correlation=None,candidate_dot_overlap=None,
            reason='No candidate exists',saturation_coverage_fraction=saturation['covered_allowed_fraction'],
            support_definition=saturation['support_definition'],scope=audit['inventory_scope']),
        raster_sha256=None,validator=dict(status='NOT RUN: no generated raster',no_nan_inside_footprint=None,
            values_in_0_1=None,crs_match=None,shape_match=None,transform_match=None),
        submission_name=None,note='Negative preflight: lane missing; positive-support registry gate saturated. No TIFF approved or generated.',
        verdict='negative',experiments_used=0,submission_slots_used=0,approved_for_submission=False,
        blockers=['No single-method lane supplied','Shared positive-support overlap rule is universally blocked on this footprint',
            'No organizer receipt or authenticated current weekly cap','No comparable current-best holdout in this repository'])
    (ROOT / 'evidence/run-card.json').write_text(json.dumps(card, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(status='NEGATIVE PREFLIGHT',covered_allowed_fraction=saturation['covered_allowed_fraction'],
                         h33_dots=audit['h33_educational_only']['positive_pixels']),indent=2))


if __name__ == '__main__':
    run()
