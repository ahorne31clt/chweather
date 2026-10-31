from pathlib import Path
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import hashlib,json,logging,os,tempfile
from PIL import Image
from sunset.data import session,download

ROOT=Path(__file__).resolve().parent.parent
BASINS=[('atl','Atlantic','atlc','at','al'),('pac','Eastern Pacific','epac','ep','ep'),('cpac','Central Pacific','cpac','cp','cp')]


def iso(value):return value.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')


class BulletinText(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.blocked=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.blocked+=1
        if tag in ('br','p','div','pre'):self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.blocked=max(0,self.blocked-1)
    def handle_data(self,text):
        if not self.blocked:self.parts.append(text)


def parse_outlook(xml):
    if len(xml)>2_000_000:raise ValueError('Oversized NHC feed')
    root=ET.fromstring(xml);items=root.findall('./channel/item')
    outlook=next((item for item in items if 'Tropical Weather Outlook' in (item.findtext('title') or '')),None)
    if outlook is None:raise ValueError('NHC feed contains no tropical outlook bulletin')
    parser=BulletinText();parser.feed(outlook.findtext('description') or '')
    text=''.join(parser.parts).strip()
    if len(text)<50:raise ValueError('Incomplete NHC outlook text')
    issued=parsedate_to_datetime(outlook.findtext('pubDate'))
    link=outlook.findtext('link') or ''
    if urlparse(link).hostname!='www.nhc.noaa.gov':raise ValueError('Unexpected NHC bulletin link')
    return dict(title=outlook.findtext('title'),published_at_utc=iso(issued),text=text,source_url=link)


def run():
    output=ROOT/'generated/tropical';output.mkdir(parents=True,exist_ok=True)
    with session() as http,tempfile.TemporaryDirectory(dir=output) as temp:
        temp=Path(temp);basins=[]
        response=http.get('https://www.nhc.noaa.gov/CurrentStorms.json',timeout=(15,45));response.raise_for_status()
        systems=response.json().get('activeStorms')
        if not isinstance(systems,list):raise ValueError('Invalid NHC current-system list')
        cleaned=[]
        for storm in systems:
            ident=str(storm.get('id',''));advisory=storm.get('publicAdvisory') or {}
            url=advisory.get('url') or 'https://www.nhc.noaa.gov/'
            if urlparse(url).hostname!='www.nhc.noaa.gov':url='https://www.nhc.noaa.gov/'
            cleaned.append(dict(id=ident,name=storm.get('name') or ident,classification=storm.get('classification'),last_update_utc=storm.get('lastUpdate'),advisory_url=url))
        for key,name,basin,rss,prefix in BASINS:
            feed=f'https://www.nhc.noaa.gov/index-{rss}.xml'
            response=http.get(feed,timeout=(15,45));response.raise_for_status();bulletin=parse_outlook(response.content)
            images=[]
            for days in (2,7):
                url=f'https://www.nhc.noaa.gov/xgtwo/two_{key}_{days}d0.png'
                filename=f'{key}-{days}day.png';path=temp/filename;download(http,url,path,maximum=5_000_000)
                with Image.open(path) as image:
                    if image.format!='PNG' or image.width<500 or image.height<300:raise ValueError('Invalid NHC outlook graphic')
                    width,height=image.size;image.verify()
                images.append(dict(days=days,image_filename=filename,image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),width=width,height=height,source_url=url))
            basins.append(dict(id=key,name=name,official_basin_id=basin,bulletin=bulletin,feed_url=feed,images=images,
                active_systems=[system for system in cleaned if system['id'].startswith(prefix)]))
        result=dict(schema_version=1,generated_at_utc=iso(datetime.now(timezone.utc)),basins=basins,
            active_system_count=len(cleaned),systems_source='https://www.nhc.noaa.gov/CurrentStorms.json',
            notes=['Official NHC/CPHC graphics, preserved unchanged. Issuance is printed on each graphic.',
                'Formation probability is not the probability of landfall, local impact, or hurricane strength.',
                'This is a dated snapshot. Check official advisories for changing conditions.'])
        target=temp/'latest.json';target.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        for path in temp.glob('*.png'):os.replace(path,output/path.name)
        os.replace(target,output/'latest.json')
    print('Published official tropical outlooks for three basins',flush=True)
    return result


if __name__=='__main__':
    try:run()
    except Exception:logging.exception('Tropical refresh failed; no substitute outlook created');raise SystemExit(1)
