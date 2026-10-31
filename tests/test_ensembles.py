from datetime import datetime,timezone
import numpy as np
import pytest
from ensembles.data import probability,choose,cycles,GEFS_MEMBERS,record
import importlib,json
from contextlib import nullcontext


def test_complete_member_fractions_and_exact_thresholds():
    values=np.array([[[0.,1.]],[[1.,1.]],[[2.,0.]]])
    assert probability(values,1,'ge',3)==pytest.approx(np.array([[200/3,200/3]]))
    assert probability(values,1,'gt',3)==pytest.approx(np.array([[100/3,0]]))
    assert probability(values,1,'lt',3)==pytest.approx(np.array([[100/3,100/3]]))
    with pytest.raises(ValueError,match='expected ensemble'):probability(values,1,'ge',31)
    values[0,0,0]=np.nan
    with pytest.raises(ValueError,match='finite'):probability(values,1,'ge',3)
    assert len(set(GEFS_MEMBERS))==31 and GEFS_MEMBERS[0]=='c00' and GEFS_MEMBERS[-1]=='p30'


def test_unique_record_selection_and_recent_cycle_boundaries():
    with pytest.raises(ValueError,match='one matching'):choose([],lambda _:True)
    with pytest.raises(ValueError,match='one matching'):choose([{'line':'x'},{'line':'x'}],lambda _:True)
    runs=cycles(datetime(2026,10,30,13,tzinfo=timezone.utc))
    assert [r.hour for r in runs]==[6,0,18]
    assert all(r.hour%6==0 for r in runs)


def test_byte_range_download_must_be_bounded(tmp_path):
    with pytest.raises(ValueError,match='Unbounded'):
        record('https://example.test',{'offset':0,'end':None},tmp_path/'x.grib2')


def test_incomplete_second_ensemble_preserves_previous_publication(tmp_path,monkeypatch):
    pipeline=importlib.import_module('ensembles.__main__')
    monkeypatch.setattr(pipeline,'ROOT',tmp_path)
    monkeypatch.setattr(pipeline,'session',lambda:nullcontext(object()))
    monkeypatch.setattr(pipeline,'geography',lambda *_:(None,[],[]))
    monkeypatch.setattr(pipeline,'refs_frame',lambda *_:({'freeze':np.zeros((2,2))},{},dict(member_count=14,source_urls=[])))
    def incomplete(*_):raise ValueError('missing GEFS member')
    monkeypatch.setattr(pipeline,'gefs_frame',incomplete)
    staged=[]
    def render(path,*_):
        path.write_bytes(b'staged new map');staged.append(path.name)
        return dict(filename='unused.bin.gz')
    monkeypatch.setattr(pipeline,'render',render)
    output=tmp_path/'generated/ensembles';output.mkdir(parents=True)
    (output/'latest.json').write_text('{"previous":true}')
    (output/'previous.png').write_bytes(b'previous successful map')
    with pytest.raises(RuntimeError,match='No complete recent gefs'):
        pipeline.run()
    assert len(staged)==10
    assert json.loads((output/'latest.json').read_text())=={'previous':True}
    assert (output/'previous.png').read_bytes()==b'previous successful map'
    assert len(list(output.iterdir()))==2
