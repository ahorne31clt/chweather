"""python -m centers: fetch and validate official WPC/CPC graphics headlessly."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from io import BytesIO
from pathlib import Path
import hashlib
import json
import logging
import os
import tempfile

from PIL import Image
from sunset.data import session

ROOT=Path(__file__).resolve().parent.parent
WPC='https://www.wpc.ncep.noaa.gov'
CPC='https://www.cpc.ncep.noaa.gov'


def products():
    result=[]
    def add(id,center,group,title,period,path,page,description):
        host=WPC if center=='wpc' else CPC
        result.append(dict(id=id,center=center,group=group,title=title,period=period,
            source_url=host+path,official_page_url=host+page,description=description))
    for day,name in [(1,'94'),(2,'98'),(3,'99')]:
        add(f'wpc-ero-{day}','wpc','ero',f'Day {day} excessive rainfall',f'Day {day}',
            f'/qpf/{name}ewbg.gif','/qpf/excess_rain.shtml',
            'Risk of rainfall exceeding flash-flood guidance within 25 miles of a point. This is not a flood warning or a forecast rainfall total. Read the category probabilities and exact valid interval on the map.')
    for id,title,period,file in [('day1','Day 1 precipitation','Day 1','fill_94qwbg.gif'),
        ('day1-3','Days 1–3 precipitation','Days 1–3','d13_fill.gif'),
        ('day1-5','Days 1–5 precipitation','Days 1–5','p120i.gif'),
        ('day1-7','Days 1–7 precipitation','Days 1–7','p168i.gif')]:
        add('wpc-qpf-'+id,'wpc','qpf',title,period,'/qpf/'+file,'/qpf/day1-7.shtml',
            'Forecast liquid-equivalent precipitation accumulation in inches over the printed valid interval. Includes the water equivalent of frozen precipitation; this is not a probability of rain or a snowfall-depth forecast.')
    for id,period,folder,t,p,page in [
        ('610','Days 6–10','/products/predictions/610day/','610temp.new.gif','610prcp.new.gif','/products/predictions/610day/'),
        ('814','Days 8–14','/products/predictions/814day/','814temp.new.gif','814prcp.new.gif','/products/predictions/814day/'),
        ('34','Weeks 3–4','/products/predictions/WK34/gifs/','WK34temp.gif','WK34prcp.gif','/products/predictions/WK34/'),
        ('month','Monthly','/products/predictions/30day/','off14_temp.gif','off14_prcp.gif','/products/predictions/30day/'),
        ('season','Seasonal / three months','/products/predictions/long_range/lead01/','off01_temp.gif','off01_prcp.gif','/products/predictions/long_range/seasonal.php?lead=1')]:
        for field,file in [('temperature',t),('precipitation',p)]:
            add(f'cpc-{id}-{field}','cpc',field,f'{period} {field}',period,folder+file,page,
                ('Probabilities favoring above- or below-normal average temperature' if field=='temperature' else 'Probabilities favoring above- or below-normal total precipitation')+
                ' over the printed valid period. Shading is a category probability, not the size of a departure. Equal chances (EC) gives no favored category; it does not guarantee normal conditions. Use the legend on the selected product, since category conventions can differ by lead time.')
    return result


def fetch_graphic(http,url,path):
    with http.get(url,timeout=(15,45),stream=True) as response:
        response.raise_for_status()
        payload=bytearray()
        for chunk in response.iter_content(65536):
            payload.extend(chunk)
            if len(payload)>8_000_000:raise ValueError('Oversized WPC/CPC graphic')
        modified=response.headers.get('Last-Modified')
    with Image.open(BytesIO(payload)) as original:
        if original.format not in ('PNG','GIF','JPEG') or min(original.size)<300 or max(original.size)>8000 or getattr(original,'n_frames',1)!=1:
            raise ValueError('Invalid official outlook graphic')
        original.load();size=original.size
        original.convert('RGBA').save(path,format='PNG')
    with Image.open(path) as saved:saved.verify()
    iso=lambda value:value.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
    return dict(width=size[0],height=size[1],image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        retrieved_at_utc=iso(datetime.now(timezone.utc)),
        source_file_modified_at_utc=iso(parsedate_to_datetime(modified)) if modified else None)


def run(output=None):
    output=Path(output or ROOT/'generated/centers');output.mkdir(parents=True,exist_ok=True)
    with session() as http,tempfile.TemporaryDirectory(dir=output) as temp:
        temp=Path(temp);catalog=products()
        for item in catalog:
            filename=item['id']+'.png'
            logging.info('Fetching %s',item['title'])
            item.update(fetch_graphic(http,item['source_url'],temp/filename))
            item.update(image_filename=filename,issuance_and_validity='Read the issuance and valid period printed on the official graphic.')
        result=dict(schema_version=1,generated_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
            products=catalog,notes=['Official NOAA/WPC/CPC maps, visual content and legends preserved. Source GIF/JPEG may be losslessly stored as PNG.',
                'Retrieval time and source file modification time are not forecast issuance or validity.',
                'Dated snapshots; official sources may publish newer guidance between website updates.'])
        manifest=temp/'latest.json';manifest.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        for path in temp.glob('*.png'):os.replace(path,output/path.name)
        os.replace(manifest,output/'latest.json')
    print(f'Published {len(catalog)} official WPC/CPC graphics',flush=True)
    return result


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    try:run()
    except Exception:logging.exception('WPC/CPC refresh failed; previous publication preserved');raise SystemExit(1)
