from enso.__main__ import parse_seasons,parse_weekly,parse_discussion
import pytest


def test_seasons_missing_values_and_center_year():
    records=parse_seasons('SEAS YR ANOM\nDJF 2026 -.91\nJFM 2026 -99.9\nMAM 2026 -.04','roni')
    assert records[0]==dict(season='DJF',year=2026,center_month=1,anomaly_c=-.91)
    assert records[1]['anomaly_c'] is None
    assert records[2]['center_month']==4
    oni=parse_seasons('SEAS YR TOTAL ANOM\nJAS 2026 29.12 2.16','oni')
    assert oni[0]['anomaly_c']==2.16
    with pytest.raises(ValueError,match='Duplicate'):parse_seasons('JAS 2026 1.69\nJAS 2026 1.70','roni')


def test_weekly_adjacent_negative_fields_do_not_shift_nino34():
    result=parse_weekly('Week SST SSTA\n 02SEP1981 20.6-0.1 24.8-0.1 26.5-0.2 28.3-0.3\n')
    assert result==[dict(week_centered='1981-09-02',sst_c=26.5,anomaly_c=-.2)]


def test_official_status_not_inferred_from_index():
    html='''<p>CLIMATE PREDICTION CENTER/NCEP/NWS 8 October 2026</p>
    <strong>ENSO Alert System Status: </strong>Not Active
    <p><u>Synopsis:</u>&nbsp;<strong>ENSO-neutral conditions are present in this test bulletin.</strong></p>
    <p>The next ENSO Diagnostics Discussion is scheduled for 12 November 2026.</p>'''
    result=parse_discussion(html)
    assert result['alert_status']=='Not Active'
    assert result['issued_date']=='2026-10-08'
    assert result['next_scheduled_date']=='2026-11-12'
    assert result['synopsis']=='ENSO-neutral conditions are present in this test bulletin.'
    with pytest.raises(ValueError,match='official'):parse_discussion('<html>Service unavailable</html>')
