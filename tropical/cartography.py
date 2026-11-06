"""NHC/CPHC vector outlooks on the shared CH Weather map canvas."""
from datetime import datetime,timezone,timedelta
import re
from centers.gis import payload,archive_records
from centers.render import render


def fetch(http,central=False):
    url='https://www.nhc.noaa.gov/xgtwo/'+('gtwo_cphc_shapefiles.zip' if central else 'gtwo_shapefiles.zip')
    rows,names=archive_records(payload(http,url,maximum=8_000_000),lambda n:'areas_' in n or 'points_' in n)
    stamps={re.search(r'_(\d{12})\.shp$',n).group(1) for n in names}
    if len(stamps)!=1:raise ValueError('Mixed NHC GIS timestamps')
    stamp=datetime.strptime(next(iter(stamps)),'%Y%m%d%H%M').replace(tzinfo=timezone.utc)
    return rows,dict(gis_generated_at_utc=stamp.isoformat().replace('+00:00','Z'),data_source_url=url)


def draw(path,root,key,name,days,bulletin,rows,source,geo,now):
    stamp=datetime.fromisoformat(source['gis_generated_at_utc'].replace('Z','+00:00'))
    issue=datetime.fromisoformat(bulletin['published_at_utc'].replace('Z','+00:00'))
    if abs(stamp-issue)>timedelta(minutes=45) or now-stamp>timedelta(hours=9) or stamp>now+timedelta(minutes=15):raise ValueError('NHC GIS and bulletin are stale or from different issuance windows')
    selected=[];points=[];matched_records=0
    for row in rows:
        p=row['properties']
        if key!='cpac' and p.get('BASIN')!=('Atlantic' if key=='atl' else 'Pacific'):continue
        matched_records+=1
        probability=str(p.get(f'PROB{days}DAY',''))
        if not re.fullmatch(r'\d{1,3}%',probability):raise ValueError('Unknown NHC formation probability')
        value=int(probability[:-1]);category=p.get(f'RISK{days}DAY')
        expected='Low' if value<40 else 'Medium' if value<=60 else 'High'
        if not 0<=value<=100 or category!=expected:raise ValueError('NHC probability/risk category mismatch')
        if value==0:continue
        result=dict(row,category=category,value=value,label='Area '+str(p['AREA']))
        (points if row['geometry'].geom_type=='Point' else selected).append(result)
    extent={'atl':[-100,-10,0,55],'pac':[-180,-75,0,45],'cpac':[-180,-130,0,45]}[key]
    meta=dict(title=f'{name} / {days}-day formation outlook',center='cphc' if key=='cpac' else 'nhc',group='tropical',domain=name,
        published_at_utc=bulletin['published_at_utc'],valid_period_label=f'Official {days}-day formation window / see bulletin',presentation='CH Weather rendering of official NHC/CPHC formation guidance',**source)
    if not selected:
        # Empty geometry requires affirmative bulletin evidence, not a failed feed.
        if points:raise ValueError('Positive NHC disturbance points lack matching area polygons')
        if not matched_records and not re.search(r'(not expected|no tropical cyclones|no significant|no areas|none)',bulletin['text'],re.I):raise ValueError('Empty NHC GIS not supported by bulletin')
        note=f'No published nonzero {days}-day development areas in this basin.'
    else:note=None
    render(path,root,meta,selected,geo,extent=extent,points=points,note=note)
    return dict(meta,area_count=len(selected),points=[dict(longitude=r['geometry'].x,latitude=r['geometry'].y,area=r['properties']['AREA'],probability=r['value']) for r in points])
