"""Bounded official forecast geometry downloads; never infer from image colors."""
from datetime import datetime,timezone,timedelta,date
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import tempfile,calendar,re
from shapely.geometry import shape
from cartopy.io.shapereader import Reader
from pyproj import CRS,Transformer
from shapely.ops import transform
from shapely import make_valid


def payload(http,url,maximum=20_000_000):
    with http.get(url,timeout=(15,60),stream=True) as r:
        r.raise_for_status();result=bytearray()
        for part in r.iter_content(65536):
            result.extend(part)
            if len(result)>maximum:raise ValueError('Oversized forecast geometry download')
    if not result:raise ValueError('Empty forecast geometry download')
    return bytes(result)


def archive_records(data,selector):
    result=[]
    with ZipFile(BytesIO(data)) as z,tempfile.TemporaryDirectory() as tmp:
        names=z.namelist()
        if len(names)>500 or sum(i.file_size for i in z.infolist())>150_000_000:raise ValueError('Oversized GIS archive')
        selected=[n for n in names if n.endswith('.shp') and selector(Path(n).name)]
        if not selected:raise ValueError('Expected forecast shapefile missing')
        for shp in selected:
            stem=shp[:-4];base=Path(shp).stem
            for extension in ('.shp','.shx','.dbf','.prj'):
                member=stem+extension
                if member not in names:raise ValueError('Incomplete forecast shapefile')
                Path(tmp,base+extension).write_bytes(z.read(member))
            source=CRS.from_wkt(Path(tmp,base+'.prj').read_text())
            project=Transformer.from_crs(source,4326,always_xy=True).transform if not source.equals(CRS.from_epsg(4326),ignore_axis_order=True) else None
            reader=Reader(Path(tmp,base+'.shp'))
            try:
                for row in reader.records():
                    geom=row.geometry
                    if geom is None or geom.is_empty:continue
                    if project:geom=transform(project,geom)
                    repaired=not geom.is_valid
                    if repaired:geom=make_valid(geom)
                    if geom.geom_type=='GeometryCollection':
                        from shapely.ops import unary_union
                        geom=unary_union([g for g in geom.geoms if g.geom_type in ('Polygon','MultiPolygon')])
                    if geom.is_empty or not geom.is_valid:raise ValueError('Unusable official forecast geometry')
                    if min(geom.bounds)<-180.01 or max(geom.bounds)>180.01:raise ValueError('Non-geographic forecast coordinates')
                    result.append(dict(geometry=geom,properties=dict(row.attributes),shapefile=Path(shp).name,geometry_repaired=repaired))
            finally:reader.close()
    return result,selected


def cpc_dates(attributes):
    issued=attributes['Fcst_Date']
    if not isinstance(issued,date):issued=date.fromisoformat(str(issued))
    if 'Start_Date' in attributes:
        start=date.fromisoformat(str(attributes['Start_Date']));end=date.fromisoformat(str(attributes['End_Date']))
    else:
        label=attributes['Valid_Seas'];match=re.fullmatch(r'([A-Za-z]{3}) (\d{4})(?:-(\d{4}))?',label)
        if not match:raise ValueError('Unknown CPC valid period')
        token,y,_=match.groups();year=int(y)
        seasons={'JFM':1,'FMA':2,'MAM':3,'AMJ':4,'MJJ':5,'JJA':6,'JAS':7,'ASO':8,'SON':9,'OND':10,'NDJ':11,'DJF':12}
        month=seasons.get(token)
        count=3 if month else 1
        if not month:month=datetime.strptime(token,'%b').month
        start=date(year,month,1);last=year*12+month-1+count-1;ey,em=divmod(last,12);end=date(ey,em+1,calendar.monthrange(ey,em+1)[1])
    if end<start or issued>end:raise ValueError('Invalid CPC dates')
    return dict(issued_date=issued.isoformat(),valid_start_date=start.isoformat(),valid_end_date=end.isoformat(),valid_period_label=f'{start:%b %d, %Y} - {end:%b %d, %Y}')


def cpc(http,item,now):
    _,lead,variable=item['id'].split('-');field='temp' if variable=='temperature' else 'prcp'
    file=(lead+field+'_latest.zip') if lead in ('610','814') else ('wk34'+field+'_latest.zip') if lead=='34' else ('monthupd_'+field+'_latest.zip') if lead=='month' else ('seas'+field+'_latest.zip')
    url='https://ftp.cpc.ncep.noaa.gov/GIS/us_tempprcpfcst/'+file
    if lead=='season':
        url='https://ftp.cpc.ncep.noaa.gov/GIS/us_tempprcpfcst/seaskmls_latest.zip'
        rows=cpc_season_kml(payload(http,url),field)
    else:
        rows,_=archive_records(payload(http,url),lambda name:True)
    if not rows:raise ValueError('Empty CPC forecast')
    dates=cpc_dates(rows[0]['properties'])
    for row in rows:
        if cpc_dates(row['properties'])!=dates:raise ValueError('Mixed CPC forecast issuances or periods')
        cat=row['properties']['Cat'];prob=float(row['properties']['Prob'])
        if cat not in ('Above','Below','Normal','EC') or not 0<=prob<=100:raise ValueError('Unknown CPC probability category')
        row.update(category=cat,value=prob)
    issue=date.fromisoformat(dates['issued_date']);end=date.fromisoformat(dates['valid_end_date'])
    allowed={'610':3,'814':3,'34':10,'month':45,'season':45}[lead]
    if (now.date()-issue).days not in range(-1,allowed+1) or end<now.date():raise ValueError('CPC forecast is stale or future')
    return rows,dict(dates,data_source_url=url,presentation='CH Weather rendering of official CPC guidance',domain='CONUS',geometry_repair_count=sum(r.get('geometry_repaired',False) for r in rows))


def cpc_season_kml(data,field):
    """Use CPC's much smaller official KML bundle, selecting lead 1 only."""
    import xml.etree.ElementTree as ET
    from shapely.geometry import Polygon,MultiPolygon
    with ZipFile(BytesIO(data)) as z:
        name=f'lead1_{field}.kml'
        if name not in z.namelist() or z.getinfo(name).file_size>20_000_000:raise ValueError('Missing or oversized CPC lead-1 KML')
        root=ET.fromstring(z.read(name))
    ns={'k':'http://www.opengis.net/kml/2.2'}
    title=root.findtext('k:Document/k:name',namespaces=ns) or ''
    header=re.search(r'Created: (\d{2}/\d{2}/\d{4}) - Valid (.+)$',title)
    if not header:raise ValueError('CPC KML lacks issue and valid dates')
    issued=datetime.strptime(header[1],'%m/%d/%Y').date();result=[]
    def coordinates(text):
        points=[tuple(map(float,v.split(',')[:2])) for v in (text or '').split()]
        if len(points)<4 or any(not -180<=x<=180 or not -90<=y<=90 for x,y in points):raise ValueError('Invalid CPC KML ring')
        return points
    for feature in root.findall('.//k:Placemark',ns):
        description=feature.findtext('k:description',namespaces=ns) or ''
        def attribute(key):
            match=re.search(r'<td>\s*'+key+r'\s*</td>\s*<td>\s*([^<]+?)\s*</td>',description)
            if not match:raise ValueError('CPC KML missing '+key)
            return match[1]
        cat=attribute('Category');prob=float(attribute('Probability'))
        polys=[]
        for polygon in feature.findall('.//k:Polygon',ns):
            outer=coordinates(polygon.findtext('k:outerBoundaryIs/k:LinearRing/k:coordinates',namespaces=ns))
            holes=[coordinates(n.text) for n in polygon.findall('k:innerBoundaryIs/k:LinearRing/k:coordinates',ns)]
            geom=Polygon(outer,holes)
            if not geom.is_valid:geom=make_valid(geom)
            if geom.geom_type=='Polygon':polys.append(geom)
            elif geom.geom_type=='MultiPolygon':polys.extend(geom.geoms)
            else:raise ValueError('CPC KML polygon cannot be repaired')
        if not polys:raise ValueError('CPC KML feature has no areal geometry')
        result.append(dict(geometry=MultiPolygon(polys),properties=dict(Fcst_Date=issued,Valid_Seas=header[2],Cat=cat,Prob=prob)))
    return result


def wpc(http,item,now):
    if item['group']=='ero':
        day=int(item['id'].split('-')[-1]);layer={1:0,2:1,3:2}[day]
        service=f'https://mapservices.weather.noaa.gov/vector/rest/services/hazards/wpc_precip_hazards/MapServer/{layer}'
    else:
        layer={'wpc-qpf-day1':1,'wpc-qpf-day1-3':9,'wpc-qpf-day1-5':10,'wpc-qpf-day1-7':11}[item['id']]
        service=f'https://mapservices.weather.noaa.gov/vector/rest/services/precip/wpc_qpf/MapServer/{layer}'
    url=service+'/query?where=1%3D1&outFields=*&f=geojson&outSR=4326'
    import json
    import time
    for attempt in range(3):
        data=json.loads(payload(http,url,maximum=25_000_000))
        if not data.get('error'):break
        if attempt<2:time.sleep(1)
    if data.get('error') or data.get('exceededTransferLimit'):raise ValueError('Incomplete WPC service response')
    if not data.get('features'):
        if item['group']!='ero':raise ValueError('Empty WPC precipitation layer')
        text_url='https://www.wpc.ncep.noaa.gov/qpf/'+{1:'94',2:'98',3:'99'}[day]+'epoints.txt'
        text=payload(http,text_url,maximum=200_000).decode('utf-8')
        if f'Day {day} Excessive Rainfall Threat Area' not in text or not re.search(r'RAINFALL IS NOT EXPECTED TO EXCEED FLASH FLOOD\s+GUIDANCE VALUES THIS FORECAST PERIOD',text):raise ValueError('Empty WPC layer not supported by an explicit dated no-risk bulletin')
        valid=re.search(r'Valid (\d{2})Z \w{3} (\w{3}) (\d{1,2}) (\d{4}) - (\d{2})Z \w{3} (\w{3}) (\d{1,2}) (\d{4})',text)
        issued=re.search(r'(\d{3,4}) (AM|PM) (EST|EDT) \w{3} (\w{3}) (\d{1,2}) (\d{4})',text)
        if not valid or not issued:raise ValueError('WPC no-risk bulletin lacks parseable dates')
        from zoneinfo import ZoneInfo
        a=valid.groups();start=datetime.strptime(' '.join(a[:4]),'%H %b %d %Y').replace(tzinfo=timezone.utc);end=datetime.strptime(' '.join(a[4:]),'%H %b %d %Y').replace(tzinfo=timezone.utc)
        hhmm,ampm,zone,month,dd,yyyy=issued.groups();issue=datetime.strptime(f'{hhmm.zfill(4)} {ampm} {month} {dd} {yyyy}','%I%M %p %b %d %Y').replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
        if end<=now or end<=start or issue>now+timedelta(hours=1) or now-issue>timedelta(days=3):raise ValueError('Stale WPC no-risk bulletin')
        return [],dict(issued_at_utc=issue.isoformat().replace('+00:00','Z'),valid_start_utc=start.isoformat().replace('+00:00','Z'),valid_end_utc=end.isoformat().replace('+00:00','Z'),valid_period_label=start.strftime('%b %d %HZ')+' - '+end.strftime('%b %d %HZ UTC'),data_source_url=text_url,geometry_source_url=url,presentation='CH Weather rendering of official WPC guidance',domain='CONUS',empty_forecast_statement='WPC: Rainfall not expected to exceed flash-flood guidance.')
    rows=[];dates=None
    for feature in data['features']:
        p=feature['properties'];current={k:p[k] for k in ('issue_time','start_time','end_time')}
        if dates is not None and dates!=current:raise ValueError('Mixed WPC issue/valid times')
        dates=current
        if item['group']=='qpf':
            if p.get('units')!='Inches':raise ValueError('Unexpected WPC accumulation units')
            value=float(p['qpf']);cat='QPF'
            if not 0<value<=100:raise ValueError('Invalid WPC precipitation contour')
        else:
            text=p['outlook'];cat=next((n for n in ('Marginal','Slight','Moderate','High') if text.startswith(n)),None)
            if not cat:raise ValueError('Unknown WPC excessive rainfall category')
            value={'Marginal':5,'Slight':15,'Moderate':40,'High':70}[cat]
        geom=shape(feature['geometry'])
        if geom.is_empty or not geom.is_valid:raise ValueError('Invalid WPC geometry')
        rows.append(dict(geometry=geom,properties=p,category=cat,value=value))
    times={k:datetime.fromisoformat(v).replace(tzinfo=timezone.utc) for k,v in dates.items()}
    if times['end_time']<=now or times['issue_time']>now+timedelta(hours=1) or now-times['issue_time']>timedelta(days=3):raise ValueError('WPC data stale or future')
    if times['end_time']<=times['start_time']:raise ValueError('Invalid WPC window')
    return rows,dict(issued_at_utc=times['issue_time'].isoformat().replace('+00:00','Z'),valid_start_utc=times['start_time'].isoformat().replace('+00:00','Z'),valid_end_utc=times['end_time'].isoformat().replace('+00:00','Z'),
        valid_period_label=times['start_time'].strftime('%b %d %HZ')+' - '+times['end_time'].strftime('%b %d %HZ UTC'),data_source_url=url,presentation='CH Weather rendering of official WPC guidance',domain='CONUS')
