from datetime import datetime,timezone
from optics.context import satellite


class Response:
    def __init__(self,text):self.text=text;self.content=text.encode()
    def raise_for_status(self):pass


def test_satellite_does_not_accept_stale_wrong_band_or_untrusted_images(tmp_path):
    class HTTP:
        def get(self,*args,**kwargs):return Response('<img id="F_1" src="https://evil.invalid/20263061600_GOES19-ABI-CONUS-04-a.png"><img id="F_2" src="https://cdn.star.nesdis.noaa.gov/GOES19/ABI/CONUS/04/20260011600_GOES19-ABI-CONUS-04-a.png">')
    result=satellite(HTTP(),tmp_path,datetime(2026,11,2,16,tzinfo=timezone.utc))
    assert result['status']=='unavailable'
    assert not result['observations']
    assert result['used_in_forecast_score'] is False
    assert not list(tmp_path.iterdir())


def test_satellite_uses_only_newest_matching_timestamp(monkeypatch,tmp_path):
    import optics.context as context
    from PIL import Image
    class HTTP:
        def get(self,url,**kwargs):
            from urllib.parse import parse_qs,urlparse
            q=parse_qs(urlparse(url).query);p=q['sat'][0][1:];b=q['band'][0]
            return Response(''.join(f'<img id="F_{n}" src="https://cdn.star.nesdis.noaa.gov/GOES{p}/ABI/CONUS/{b}/202630615{m}_GOES{p}-ABI-CONUS-{b}-1250x750.jpg">' for n,m in enumerate(('00','55'))))
    downloaded=[]
    def download(http,url,path,**kwargs):downloaded.append(url);Image.new('RGB',(10,10)).save(path)
    monkeypatch.setattr(context,'download',download)
    result=satellite(HTTP(),tmp_path,datetime(2026,11,2,16,tzinfo=timezone.utc))
    assert len(result['observations'])==4
    assert all('1555_GOES' in u for u in downloaded)
    assert all(p['observed_at_utc']=='2026-11-02T15:55:00Z' for p in result['observations'])
