import pytest
from enso.__main__ import parse_forecast_table

def table(values='-1 -.8 -.6 0 .6 .8 1'):
    rows=''.join('<tr><th>'+s+'</th>'+''.join('<td>'+v+'</td>' for v in values.split())+'</tr>' for s in ['SON','OND','NDJ','DJF','JFM','FMA'])
    return '<table id="outlook-table">'+rows+'</table>'

def test_quantiles_preserved():
    rows=parse_forecast_table(table())
    assert rows[0]['season']=='SON'
    assert rows[0]['quantiles_c']==[-1,-.8,-.6,0,.6,.8,1]

def test_crossing_quantiles_rejected():
    with pytest.raises(ValueError):parse_forecast_table(table('1 .8 .6 0 -.6 -.8 -1'))

def test_missing_forecast_rejected():
    with pytest.raises(ValueError):parse_forecast_table('<html>Unavailable</html>')
