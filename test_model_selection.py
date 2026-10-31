from types import SimpleNamespace
import pytest
from models import __main__ as generate
from models import airports


def test_single_model_job_never_downloads_other_models(tmp_path,monkeypatch):
    calls=[]
    monkeypatch.setattr(generate,'ROOT',tmp_path)
    monkeypatch.setattr(generate,'geography',lambda *args:(None,[],[]))
    def offline(http,cache,model,cycle,hour):
        calls.append(model);raise RuntimeError('offline fixture')
    monkeypatch.setattr(generate,'fetch_frame',offline)
    args=SimpleNamespace(model='gfs',gfs_end=384,gfs_step=3,hrrr_end=48,hrrr_step=1,nam_end=84,workers=1)
    with pytest.raises(RuntimeError,match='complete usable cycle'):generate.run(args)
    assert calls and set(calls)=={'gfs'}


def test_nam_cli_does_not_attempt_unsupported_airport_generation(monkeypatch):
    selected=[]
    monkeypatch.setattr('sys.argv',['models','--model','nam'])
    monkeypatch.setattr(generate,'run',lambda args:selected.append(args.model))
    def forbidden():raise AssertionError('NAM must not invoke airport generation')
    monkeypatch.setattr(airports,'generate',forbidden)
    assert generate.main()==0 and selected==['nam']
