from datetime import date,datetime,timezone
import pytest
from centers.gis import cpc_dates,wpc
from tropical.cartography import draw


def test_cpc_season_crosses_year_and_monthly_uses_calendar_end():
    result=cpc_dates(dict(Fcst_Date=date(2026,10,15),Valid_Seas='NDJ 2026-2027'))
    assert result['valid_start_date']=='2026-11-01'
    assert result['valid_end_date']=='2027-01-31'
    assert cpc_dates(dict(Fcst_Date=date(2027,1,31),Valid_Seas='Feb 2027'))['valid_end_date']=='2027-02-28'


def test_empty_wpc_service_cannot_be_labeled_no_risk(monkeypatch):
    import centers.gis as gis
    def fetch(http,url,**kwargs):return b'{"features":[]}' if '/query?' in url else b'Service unavailable'
    monkeypatch.setattr(gis,'payload',fetch)
    with pytest.raises(ValueError,match='explicit dated no-risk'):
        wpc(None,{'group':'ero','id':'wpc-ero-3'},datetime(2026,11,3,tzinfo=timezone.utc))


def test_empty_wpc_requires_and_preserves_actual_bulletin_dates(monkeypatch):
    import centers.gis as gis
    text=b'Day 3 Excessive Rainfall Threat Area\n318 AM EST Tue Nov 03 2026\nValid 12Z Thu Nov 05 2026 - 12Z Fri Nov 06 2026\nRAINFALL IS NOT EXPECTED TO EXCEED FLASH FLOOD\nGUIDANCE VALUES THIS FORECAST PERIOD.'
    monkeypatch.setattr(gis,'payload',lambda http,url,**kwargs:b'{"features":[]}' if '/query?' in url else text)
    rows,meta=wpc(None,{'group':'ero','id':'wpc-ero-3'},datetime(2026,11,3,18,tzinfo=timezone.utc))
    assert rows==[]
    assert meta['issued_at_utc']=='2026-11-03T08:18:00Z'
    assert meta['valid_start_utc']=='2026-11-05T12:00:00Z'


def test_tropical_rejects_mixed_gis_and_bulletin_times(tmp_path):
    with pytest.raises(ValueError,match='different issuance'):
        draw(tmp_path/'map.png',tmp_path,'atl','Atlantic',7,
             {'published_at_utc':'2026-11-03T17:00:00Z','text':'No tropical cyclones expected'},[],
             {'gis_generated_at_utc':'2026-11-03T11:00:00Z','data_source_url':'https://www.nhc.noaa.gov/'},None,
             datetime(2026,11,3,18,tzinfo=timezone.utc))


def test_cpc_kml_uses_lead_one_attributes_and_keeps_polygon_holes():
    from io import BytesIO
    from zipfile import ZipFile
    from centers.gis import cpc_season_kml
    content='''<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Lead 01: Created: 10/15/2026 - Valid NDJ 2026-2027</name><Placemark><description><![CDATA[<td>Category</td><td>Above</td><td>Probability</td><td>40</td><script>not executed</script>]]></description><Polygon><outerBoundaryIs><LinearRing><coordinates>-100,30 -90,30 -90,40 -100,40 -100,30</coordinates></LinearRing></outerBoundaryIs><innerBoundaryIs><LinearRing><coordinates>-98,32 -92,32 -92,38 -98,38 -98,32</coordinates></LinearRing></innerBoundaryIs></Polygon></Placemark></Document></kml>'''
    data=BytesIO()
    with ZipFile(data,'w') as z:
        z.writestr('lead1_temp.kml',content)
        z.writestr('lead2_temp.kml','invalid unrelated document')
    rows=cpc_season_kml(data.getvalue(),'temp')
    assert len(rows)==1 and rows[0]['geometry'].area==64
    assert rows[0]['properties']['Cat']=='Above'
    assert rows[0]['properties']['Prob']==40
