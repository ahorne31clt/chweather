import numpy as np
from seasonal.verification import weighted_crps,evaluate,evaluate_snow


def cases():
    return [dict(id=str(i),region='West',year=year,actual=float((year%3)-1),model=.3,
        stats={k:0. for k in ('base','trend','extended','extended_trend')},scale=1.,climo_probability=.5)
        for year in range(2000,2009) for i in range(35)]


def test_weighted_crps_known_distribution():
    assert np.isclose(weighted_crps([0,2],[.5,.5],1),.5)
    assert weighted_crps([2],[1],2)==0


def test_outer_year_does_not_train_on_itself_or_future():
    original=cases();first=evaluate(original)
    changed=[dict(r,actual=100.) if r['year']>=2006 else r for r in original]
    second=evaluate(changed)
    key=('0',2006)
    assert first['by_case'][key]['prediction']==second['by_case'][key]['prediction']
    assert max(first['by_case'][key]['parameters']['training_years'])<2006
    assert first['report']['overall']['independent_initialization_years']==5


def test_snow_without_independent_winters_retains_climatology():
    row=dict(id='CLT',region='NC Piedmont',year=2020,actual=2.,samples=np.array([0.,2.,6.]),
        conditional=np.array([.1,.2,.7]),climo=np.ones(3)/3)
    report=evaluate_snow([row])
    assert report['strengths']['NC Piedmont']==0
    assert report['overall']['status']=='insufficient_history'


def test_current_anomaly_stays_inside_source_streams():
    from seasonal.verification import fit,predict
    rows=cases();parameters=fit(rows)
    for row in rows:
        value=predict(row,parameters)
        stat=row['stats'][parameters['variant']]
        assert min(row['model'],stat)<=value<=max(row['model'],stat)


def test_index_parser_rejects_missing_and_preserves_first_block():
    from seasonal.data import parse_year_index
    text='\n'.join(str(y)+' '+' '.join(['1.0']*11+['-999.0']) for y in range(1980,2020))
    result=parse_year_index(text+'\n1980 '+' '.join(['2.0']*12))
    assert result[1980,1]==1
    assert (1981,12) not in result
