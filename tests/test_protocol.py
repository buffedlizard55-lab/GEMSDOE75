import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from gems57 import gates, uniqueness, metric
from gems57.submission_writer import write_submission
from gems57.evaluate_holdout import evaluate, pooled_summary
from scripts.fetch_inputs import fetch

ROOT=Path(__file__).resolve().parents[1]


def tif(path, values, transform=None, crs='EPSG:32611'):
    with rasterio.open(path,'w',driver='GTiff',height=values.shape[0],width=values.shape[1],
                       count=1,dtype='float32',crs=crs,transform=transform or from_origin(0,1000,100,100)) as dst:
        dst.write(values.astype('float32'),1)
    return path


def test_template_unchanged():
    pin=json.loads((ROOT/'evidence/template-pin.json').read_text())
    for f in pin['files']:
        assert hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest()==f['sha256']


@pytest.mark.parametrize('bad',[-1.,1.01,np.nan,np.inf,-np.inf])
def test_range_rejection(tmp_path,bad):
    a=np.zeros((5,5),np.float32);a[1,1]=bad
    p=tif(tmp_path/'prediction.tif',a)
    ref=tif(tmp_path/'reference.tif',np.zeros_like(a))
    assert not gates.format_report(p,ref)['ok']
    with pytest.raises(ValueError,match='normalized'):
        write_submission(tmp_path/'new.tif',a,ref,np.ones_like(a,bool),note='test',name='test')
    assert not (tmp_path/'new.tif').exists()


@pytest.mark.parametrize('change',['crs','transform','shape'])
def test_grid_rejection(tmp_path,change):
    a=np.zeros((5,5),np.float32)
    ref=tif(tmp_path/'ref.tif',a)
    kw={'crs':'EPSG:4326'} if change=='crs' else {'transform':from_origin(1,1000,100,100)} if change=='transform' else {}
    p=tif(tmp_path/'candidate.tif',a[:4] if change=='shape' else a,**kw)
    assert not gates.format_report(p,ref)['ok']


def test_literal_saturation(tmp_path):
    a=np.full((10,10),.001,np.float32)
    p=tif(tmp_path/'witness.tif',a)
    with rasterio.open(p) as src:
        grid=src.shape,src.crs,src.transform
    cert=uniqueness.saturation_certificate(p,np.ones_like(a,bool),expected_grid=grid)
    assert cert['universal_overlap_blocker']
    b=np.zeros_like(a);b[5,5]=1
    assert uniqueness.dot_overlap(b,a)==1


def test_saturation_rejects_shifted_grid(tmp_path):
    a=np.ones((5,5),np.float32)
    p=tif(tmp_path/'witness.tif',a)
    with pytest.raises(ValueError,match='CRS/transform'):
        uniqueness.saturation_certificate(p,a.astype(bool),expected_grid=(a.shape,rasterio.crs.CRS.from_epsg(32611),from_origin(1,1000,100,100)))


def test_overlap_euclidean_radius():
    a=np.zeros((11,11));b=a.copy();a[5,5]=1;b[5,8]=1
    assert uniqueness.dot_overlap(a,b)==1
    b[:]=0;b[8,8]=1
    assert uniqueness.dot_overlap(a,b)==0


def test_visible_faults_masked():
    truth=np.zeros((12,12),bool);truth[4,4]=True
    visible=np.zeros_like(truth);visible[8,8]=True
    fold=dict(truth=truth,visible=visible,region=np.ones_like(truth))
    p=truth.astype(float);p[8,8]=1
    result,_=evaluate(p,fold,np.ones_like(truth),block_side=3)
    assert result['dti']==pytest.approx(1)
    assert result['n_emitted']==1


def test_metric_matches_bruteforce():
    rng=np.random.default_rng(75)
    p=rng.random((7,8)).astype(np.float32)
    truth=rng.random(p.shape)>.8
    assert metric.dti_exact(p,truth)['dti']==pytest.approx(metric.dti_bruteforce(p,truth)['dti'])


def test_ci_requires_aligned_truth():
    a=np.array([[1,1,1,2],[1,1,1,2]],float);b=a.copy();b[0,3]=3
    with pytest.raises(ValueError,match='same integer truth'):
        pooled_summary({'candidate':a,'control':b},candidate='candidate')


def test_bad_download_does_not_replace_verified_path(tmp_path,monkeypatch):
    dest=tmp_path/'a.tif';dest.write_bytes(b'old')
    def fake_run(args,stdout,check): stdout.write(b'corrupt')
    monkeypatch.setattr('scripts.fetch_inputs.subprocess.run',fake_run)
    record=dict(name='a.tif',repo='r',path='p',commit='c',sha256='f'*64)
    with pytest.raises(ValueError,match='SHA-256'):
        fetch(record,tmp_path)
    assert dest.read_bytes()==b'old'
    assert list(tmp_path.iterdir())==[dest]


def test_negative_card_does_not_invent_artifact():
    card=json.loads((ROOT/'evidence/run-card.json').read_text())
    assert card['verdict']=='negative' and not card['approved_for_submission']
    assert card['raster_sha256'] is None and card['submission_name'] is None
    assert card['holdout_dti']['dti'] is None
    assert card['submission_slots_used']==0
    assert len(card['note'])<=140
