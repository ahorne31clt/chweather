"""Bounded public NOAA downloads, strict NetCDF coordinates, and ACIS observations."""
from datetime import datetime,timezone
from pathlib import Path
from hashlib import sha256
import json,re,time
import numpy as np
from scipy.io import netcdf_file
from sunset.data import download
from enso.__main__ import parse_seasons,SOURCES
from .science import add_month

BASE='https://ftp.cpc.ncep.noaa.gov/NMME'
ACIS='https://data.rcc-acis.org/'
STATIONS='SEA PDX GEG BOI MSO BIL GTF BZN RNO SLC ELY LAS SFO SAC FAT LAX SAN PHX TUS FLG ABQ ELP DEN COS GJT PUB CYS CPR BIS BTM RAP FSD FAR MSP DLH DSM OMA LBF DDC ICT OKC TUL DFW AMA SAT AUS IAH MAF LBB LIT SHV MSY JAN MEM BHM ATL BNA SDF STL ORD MKE GRB DTW IND CLE CMH PIT BUF SYR ALB BTV BOS PWM NYC PHL BWI DCA RIC ROA AVL CLT GSO RDU ILM CHS CAE SAV JAX TLH MCO TPA MIA'.split()


def cached(http,url,cache,maximum=8_000_000,ttl=86400,params=None):
    path=cache/(sha256((url+json.dumps(params,sort_keys=True)).encode()).hexdigest()+'.data')
    if not path.exists() or time.time()-path.stat().st_mtime>ttl:
        import os
        candidate=path.with_name(path.name+f'.{os.getpid()}')
        try:
            download(http,url,candidate,params=params,maximum=maximum)
            candidate.replace(path)
        finally:candidate.unlink(missing_ok=True)
    return path


def latest_cycles(http,cache,now):
    url=BASE+'/realtime_anom/ENSMEAN/'
    text=cached(http,url,cache,maximum=300_000,ttl=3600).read_text()
    cycles=sorted(set(re.findall(r'href="(\d{10})/"',text)),reverse=True)
    return [c for c in cycles if datetime.strptime(c,'%Y%m%d%H').replace(tzinfo=timezone.utc)<=now
            and (now.year*12+now.month)-(int(c[:4])*12+int(c[4:6]))<=2][:3]


def read_netcdf(path,cycle,names,bounds=None):
    with netcdf_file(path,mmap=False) as ds:
        lon=np.asarray(ds.variables['lon'].data,dtype=float);lat=np.asarray(ds.variables['lat'].data,dtype=float)
        target=ds.variables['target'];unit=target.units.decode()
        if not unit.startswith('months since 1960-01-'):raise ValueError('Unexpected seasonal target calendar')
        offsets=np.array(target.data,dtype=float)
        if not np.equal(offsets,np.round(offsets)).all():raise ValueError('Fractional target months unsupported')
        dates=[add_month(1960,1,int(v)) for v in offsets]
        initial=float(ds.variables['initial_time'].data[0])
        if add_month(1960,1,int(initial))!=(int(cycle[:4]),int(cycle[4:6])):raise ValueError('Seasonal model initialization mismatch')
        if lon.shape!=(360,) or lat.shape!=(181,) or not np.array_equal(lon,np.arange(360)) or not np.array_equal(lat,np.arange(90,-91,-1)):
            raise ValueError('Unexpected NMME grid; do not guess orientation')
        west,east,south,north=bounds or (233,295,23,51)
        x=np.where((lon>=west)&(lon<=east))[0];y=np.where((lat>=south)&(lat<=north))[0]
        values={};units={}
        for name in names:
            var=ds.variables[name]
            if var.dimensions!=('target','lat','lon'):raise ValueError('Unexpected forecast dimensions')
            data=np.array(var.data,dtype=float)
            for flag in ('_FillValue','missing_value'):
                if hasattr(var,flag):data[data==float(getattr(var,flag))]=np.nan
            data[abs(data)>1e10]=np.nan
            values[name]=data[:,y][:,:,x];units[name]=var.units.decode()
        return dict(lat=lat[y],lon=lon[x]-360,dates=dates,values=values,units=units)


def model_source(http,cache,cycle,model,variable,cache_ttl=86400,bounds=None):
    field={'temperature':'tmp2m','precipitation':'prate','sst':'tmpsfc'}[variable]
    url=f'{BASE}/realtime_anom/ENSMEAN/{cycle}/{model}.{field}.{cycle[:6]}.ENSMEAN.anom.nc'
    import requests
    try:
        path=cached(http,url,cache,ttl=cache_ttl)
        d=read_netcdf(path,cycle,['fcst'],bounds) if bounds is not None else read_netcdf(path,cycle,['fcst'])
    except requests.HTTPError as error:
        if error.response.status_code!=404 or model!='NMME':raise
        url=f'{BASE}/realtime_anom/ENSMEAN/{cycle}/{field}.{cycle}.ENSMEAN.ensmean.anom.1x1.grb'
        d=read_legacy_grib(cached(http,url,cache,ttl=cache_ttl),cycle,variable,bounds)
    if d['units']['fcst'] not in ({'K','C','degC'} if variable in ('temperature','sst') else {'mm/day','mm/d','mm/s','kg m-2 s-1','kg m**-2 s**-1'}):
        raise ValueError('Unexpected anomaly units: '+d['units']['fcst'])
    if variable=='precipitation' and d['units']['fcst'] in {'mm/s','kg m-2 s-1','kg m**-2 s**-1'}:
        d['values']['fcst']*=86400
    return d,url


def probabilities(http,cache,cycle,variable):
    field={'temperature':'tmp2m','precipitation':'prate'}[variable]
    url=f'{BASE}/prob/netcdf/{field}.{cycle[:6]}.prob.adj.seas.nc'
    return read_netcdf(cached(http,url,cache),cycle,['prob_above','prob_norm','prob_below']),url


def acis(http,cache,endpoint,params,ttl=2592000):
    path=cached(http,ACIS+endpoint,cache,params={'params':json.dumps(params,separators=(',',':'))},maximum=15_000_000,ttl=ttl)
    try:result=json.loads(path.read_text())
    except (ValueError,UnicodeError):
        path.unlink(missing_ok=True);raise
    if 'error' in result:
        path.unlink(missing_ok=True);raise ValueError('ACIS: '+str(result['error']))
    return result


def observations(http,cache,now):
    # ThreadEx city series preserve long climate records; present-day airport
    # locations are map anchors, not a claim all observations used one site.
    metadata=acis(http,cache,'StnMeta',{'sids':['K'+s for s in STATIONS],'meta':'name,ll,sids'})['meta']
    coords={}
    for r in metadata:
        for sid in r['sids']:
            if sid.endswith(' 5') and 'll' in r:coords[sid.split()[0][1:]]=r['ll']
    end=add_month(now.year,now.month,-1)
    params={'sids':[s+'thr 9' for s in STATIONS if s in coords],
        'sdate':'1950-01','edate':f'{end[0]}-{end[1]:02d}','meta':'name,sids',
        'elems':[{'name':name,'interval':'mly','duration':'mly','reduce':'mean' if name=='avgt' else 'sum','maxmissing':0}
                 for name in ['avgt','pcpn','snow']]}
    rows=acis(http,cache,'MultiStnData',params)['data'];stations=[]
    def number(v):
        if v=='T':return 0.
        try:return float(v) if not str(v).endswith('A') else np.nan
        except (TypeError,ValueError):return np.nan
    expected=(end[0]-1950)*12+end[1]
    for r in rows:
        sid=next((s.split('thr')[0] for s in r['meta']['sids'] if 'thr 9' in s),None)
        if sid not in coords or len(r['data'])!=expected:raise ValueError('Unexpected ACIS station/date alignment')
        series={add_month(1950,1,i):[number(v) for v in row] for i,row in enumerate(r['data'])}
        stations.append(dict(id=sid,name=r['meta']['name'],lon=coords[sid][0],lat=coords[sid][1],series=series))
    if len(stations)<60:raise ValueError('Insufficient observed climate stations')
    oni_path=cached(http,SOURCES['oni'],cache,maximum=200_000,ttl=86400)
    oni=parse_seasons(oni_path.read_text(),'oni')
    return stations,oni,dict(oni_url=SOURCES['oni'],observations_url=ACIS+'MultiStnData',
        observation_end_month=f'{end[0]}-{end[1]:02d}',station_count=len(stations),
        observation_request=params,station_location_note='ThreadEx city climate series anchored to present-day airport locations; station moves and composite records apply.')


INDEX_URLS={
 'ao':'https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/monthly.ao.index.b50.current.ascii',
 'nao':'https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/norm.nao.monthly.b5001.current.ascii',
 'pna':'https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/norm.pna.monthly.b5001.current.ascii'}


def atmosphere(http,cache,now):
    indices={};meta={}
    for key,url in INDEX_URLS.items():
        text=cached(http,url,cache,maximum=200_000,ttl=86400).read_text()
        records={}
        for line in text.splitlines():
            row=line.split()
            if len(row)!=3:continue
            year,month,value=int(row[0]),int(row[1]),float(row[2])
            if not 1<=month<=12 or not np.isfinite(value):raise ValueError('Invalid atmospheric index')
            if abs(value)<20:records[year,month]=value
        latest=max(records)
        if now.year*12+now.month-latest[0]*12-latest[1]>3:raise ValueError('Atmospheric index is stale')
        indices[key]=records;meta[key]=dict(source_url=url,latest_month=f'{latest[0]}-{latest[1]:02d}',value=records[latest])
    return indices,meta


def dense_observations(http,cache,now,existing):
    url='https://www.ncei.noaa.gov/pub/data/ushcn/v2.5/ushcn-v2.5-stations.txt'
    text=cached(http,url,cache,maximum=300_000,ttl=2592000).read_text()
    bins={}
    for line in text.splitlines():
        if not line.startswith('USH'):continue
        sid=line[:11][-6:]+' 2';lat,lon=float(line[12:20]),float(line[21:30]);elevation=float(line[31:37])
        if not 24<=lat<=50 or not -125<=lon<=-66:continue
        key=(round(lat),round(lon))
        entry=dict(sid=sid,lat=lat,lon=lon,elevation_m=elevation,state=line[38:40].strip())
        if key not in bins or elevation>bins[key]['elevation_m']:bins[key]=entry
    catalog=sorted(bins.values(),key=lambda x:x['sid']);all_stations=list(existing);failed=[]
    end=add_month(now.year,now.month,-1);expected=(end[0]-1950)*12+end[1]
    for start in range(0,len(catalog),40):
        import logging
        logging.getLogger('seasonal').info('Loading long-record station batch %s/%s',start//40+1,(len(catalog)+39)//40)
        batch=catalog[start:start+40]
        params={'sids':[r['sid'] for r in batch],'sdate':'1950-01','edate':f'{end[0]}-{end[1]:02d}',
                'meta':'name,ll,sids,elev','elems':[{'name':n,'interval':'mly','duration':'mly','reduce':'mean' if n=='avgt' else 'sum','maxmissing':0} for n in ['avgt','pcpn','snow']]}
        rows=None
        for attempt in range(2):
            try:
                rows=acis(http,cache,'MultiStnData',params)['data'];break
            except Exception as error:
                logging.getLogger('seasonal').warning('Station batch %s attempt %s unavailable: %s',start//40+1,attempt+1,error)
                if attempt:failed.append(str(error))
        if rows is None:continue
        for r in rows:
            sid=next((s for s in r['meta']['sids'] if s.endswith(' 2')),None)
            if not sid or len(r['data'])!=expected or 'll' not in r['meta']:continue
            def number(v):
                if v=='T':return 0.
                try:return float(v) if not str(v).endswith('A') else np.nan
                except (ValueError,TypeError):return np.nan
            series={add_month(1950,1,i):[number(v) for v in row] for i,row in enumerate(r['data'])}
            source=next((v for v in batch if v['sid']==sid),{})
            all_stations.append(dict(id=sid.split()[0],name=r['meta']['name'],lon=r['meta']['ll'][0],lat=r['meta']['ll'][1],series=series,state=source.get('state'),elevation_m=source.get('elevation_m')))
    if failed:raise RuntimeError('Observation batches failed after retry: '+'; '.join(failed))
    if len(all_stations)<350:raise ValueError('Dense observation network incomplete: '+str(len(all_stations)))
    return all_stations,dict(inventory_url=url,requested_coop_stations=len(catalog),loaded_stations=len(all_stations),failed_batches=len(failed))


def historical_models(http,cache,init,now):
    history={};errors=[]
    for year in range(2011,init[0]):
        cycle=f'{year}{init[1]:02d}0800'
        try:history[year]={v:model_source(http,cache,cycle,'NMME',v,cache_ttl=365*86400)[0] for v in ['temperature','precipitation']}
        except Exception as error:errors.append(dict(year=year,error=str(error)))
    if len(history)<6:raise ValueError('Too few archived NMME years to estimate blend weights')
    return history,dict(years=sorted(history),missing_years=errors,source='NOAA CPC archived NMME initializations; model membership and climatologies evolved over this period')


SNOW_NORMALS_BASE='https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/'
SNOW_NORMALS_ARCHIVE=SNOW_NORMALS_BASE+'archive/us-climate-normals_1991-2020_v1.0.1_monthly_precipitation_by-variable_c20230404.tar.gz'


def snowfall_normals(http,cache):
    import csv,io,tarfile
    inventory=cached(http,SNOW_NORMALS_BASE+'doc/inventory_30yr.txt',cache,maximum=4_000_000,ttl=365*86400).read_text()
    locations={}
    for line in inventory.splitlines():
        row=line.split(maxsplit=4)
        if len(row)<4 or not row[0].startswith('US'):continue
        lat,lon=float(row[1]),float(row[2])
        if 24<=lat<=50 and -125<=lon<=-66:locations[row[0]]=(lat,lon)
    archive=cached(http,SNOW_NORMALS_ARCHIVE,cache,maximum=35_000_000,ttl=365*86400)
    with tarfile.open(archive,'r:gz') as bundle:
        member=bundle.getmember('mly-snow-normal-custom-30yr.csv')
        if member.size>15_000_000:raise ValueError('Oversized snowfall normal table')
        table=bundle.extractfile(member).read().decode('ascii')
    stations={}
    for row in csv.DictReader(io.StringIO(table)):
        sid=row['GHCN_ID']
        if sid not in locations:continue
        try:value=float(row['MLY-SNOW-NORMAL']);years=int(row['years_MLY-SNOW-NORMAL'])
        except ValueError:continue
        if not np.isfinite(value) or not 0<=value<=300 or years<10:continue
        if row['meas_flag_MLY-SNOW-NORMAL'].strip() not in ('','X'):continue
        if sid not in stations:stations[sid]=dict(id=sid,lat=locations[sid][0],lon=locations[sid][1],months={})
        stations[sid]['months'][int(row['month'])]=value
    if len(stations)<2000:raise ValueError('Incomplete NOAA snowfall normal network')
    return list(stations.values()),dict(source_url=SNOW_NORMALS_ARCHIVE,inventory_url=SNOW_NORMALS_BASE+'doc/inventory_30yr.txt',
        station_count=len(stations),units='inches',period='1991-2020',method='Published monthly normals with at least ten contributing years; flags and publisher infilling apply. Interpolated in log1p space, not an official gridded snowfall product.')


def read_legacy_grib(path,cycle,variable,bounds=None):
    import eccodes as ec
    fields=[];dates=[];units=None
    with Path(path).open('rb') as stream:
        while (g:=ec.codes_grib_new_from_file(stream)) is not None:
            try:
                if ec.codes_get(g,'edition')!=1 or ec.codes_get(g,'indicatorOfUnitOfTimeRange')!=3 or ec.codes_get(g,'timeRangeIndicator')!=3:
                    raise ValueError('Unsupported legacy seasonal GRIB interval')
                if ec.codes_get(g,'dataDate')!=int(cycle[:8]):raise ValueError('Legacy initialization mismatch')
                a,b=ec.codes_get(g,'P1'),ec.codes_get(g,'P2')
                if b-a!=1:raise ValueError('Legacy seasonal record is not one monthly mean')
                if (ec.codes_get(g,'Ni'),ec.codes_get(g,'Nj'))!=(360,181):raise ValueError('Unexpected legacy grid')
                latitudes=ec.codes_get_array(g,'latitudes').reshape(181,360)
                longitudes=np.mod(ec.codes_get_array(g,'longitudes').reshape(181,360),360)
                lat=latitudes[:,0];lon=longitudes[0]
                if not np.allclose(latitudes,lat[:,None]) or not np.allclose(longitudes,lon[None,:]) or not np.array_equal(lon,np.arange(360)) or not np.array_equal(lat,np.arange(90,-91,-1)):
                    raise ValueError('Unexpected legacy scan orientation')
                west,east,south,north=bounds or (233,295,23,51)
                x=np.where((lon>=west)&(lon<=east))[0];y=np.where((lat>=south)&(lat<=north))[0]
                array=ec.codes_get_array(g,'values').reshape(181,360).astype(float)
                array[array==ec.codes_get(g,'missingValue')]=np.nan
                unit=ec.codes_get(g,'units')
                if units is not None and unit!=units:raise ValueError('Mixed legacy units')
                units=unit;fields.append(array[y][:,x]);dates.append(add_month(int(cycle[:4]),int(cycle[4:6]),a))
            finally:ec.codes_release(g)
    if len(fields)<7 or len(set(dates))!=len(dates):raise ValueError('Incomplete legacy forecast')
    return dict(lat=lat[y],lon=lon[x]-360,dates=dates,values={'fcst':np.stack(fields)},units={'fcst':units})


def parse_year_index(text,maximum=90):
    result={}
    for line in text.splitlines():
        match=re.match(r'^\s*(\d{4})\s+(.+)$',line)
        if not match:continue
        values=[float(v) for v in re.findall(r'[+-]?\d+(?:\.\d+)?',match[2])]
        if len(values)!=12:continue
        for month,value in enumerate(values,1):
            if np.isfinite(value) and abs(value)<maximum:result.setdefault((int(match[1]),month),value)
    if len(result)<300:raise ValueError('Incomplete climate index series')
    return result


def additional_indices(http,cache,now):
    sources={'qbo':'https://www.cpc.ncep.noaa.gov/data/indices/qbo.u30.index',
             'pdo':'https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/index/ersst.v5.pdo.dat',
             'nino3':'https://psl.noaa.gov/data/correlation/nina3.data',
             'nino4':'https://psl.noaa.gov/data/correlation/nina4.data'}
    result={};metadata={}
    for key,url in sources.items():
        try:
            parsed=parse_year_index(cached(http,url,cache,maximum=200_000,ttl=86400).read_text(),20 if key=='pdo' else 90)
            if key.startswith('nino'):parsed={k:v for k,v in parsed.items() if 15<v<40}
            latest=max(parsed)
            if now.year*12+now.month-latest[0]*12-latest[1]>3:raise ValueError('Index is stale')
            result[key]=parsed;metadata[key]=dict(source_url=url,status='available',latest_month=f'{latest[0]}-{latest[1]:02d}',value=parsed[latest])
        except Exception as error:metadata[key]=dict(source_url=url,status='unavailable',reason=str(error))
    if 'nino3' in result and 'nino4' in result:
        reference={}
        for key in ['nino3','nino4']:
            reference[key]={m:float(np.mean([v for (y,mm),v in result[key].items() if mm==m and 1991<=y<=2020])) for m in range(1,13)}
        result['enso_flavor']={k:(v-reference['nino3'][k[1]])-(result['nino4'][k]-reference['nino4'][k[1]]) for k,v in result['nino3'].items() if k in result['nino4']}
    return result,metadata


def enso_forecast(http,cache,cycle):
    d,url=model_source(http,cache,cycle,'NMME','sst',cache_ttl=365*86400,bounds=(190,240,-5,5))
    return dict(dates=d['dates'],anomaly_c=[float(np.nanmean(a)) for a in d['values']['fcst']],source_url=url)
