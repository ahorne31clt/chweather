from datetime import datetime,timezone
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin,urlparse
import hashlib,json,logging,os,re,tempfile
from PIL import Image
from sunset.data import session

ROOT=Path(__file__).resolve().parent.parent
CPC='https://www.cpc.ncep.noaa.gov'
SOURCES=dict(roni=CPC+'/data/indices/RONI.ascii.txt',oni=CPC+'/data/indices/oni.ascii.txt',
    weekly=CPC+'/data/indices/wksst9120.for',discussion=CPC+'/products/analysis_monitoring/enso_advisory/ensodisc.shtml',
    outlook=CPC+'/products/analysis_monitoring/enso/roni/outlook/')
SEASONS=['DJF','JFM','FMA','MAM','AMJ','MJJ','JJA','JAS','ASO','SON','OND','NDJ']


class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.blocked=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.blocked+=1
        if tag in ('br','p','div','h1','h2'):self.parts.append(' ')
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.blocked=max(0,self.blocked-1)
        self.parts.append(' ')
    def handle_data(self,text):
        if not self.blocked:self.parts.append(text)


def plain(html):
    parser=Text();parser.feed(html);return ' '.join(''.join(parser.parts).split())


def parse_seasons(text,index):
    result=[];seen=set()
    for line in text.splitlines():
        row=line.split()
        if not row or row[0] not in SEASONS:continue
        if len(row)!=(3 if index=='roni' else 4):raise ValueError('Unexpected ENSO index columns')
        season,year=row[0],int(row[1]);value=float(row[-1]);key=f'{year}-{season}'
        if key in seen or not 1900<=year<=2200:raise ValueError('Duplicate or invalid ENSO season')
        seen.add(key)
        if value in (-99.9,-99.99,-999,99.9):value=None
        elif not -5<=value<=5:raise ValueError('ENSO index outside supported range')
        month=SEASONS.index(season)+1
        result.append(dict(season=season,year=year,center_month=month,anomaly_c=value))
    if not result:raise ValueError('Empty ENSO index')
    return sorted(result,key=lambda r:(r['year'],r['center_month']))


def parse_weekly(text):
    result=[];seen=set()
    for line in text.splitlines():
        match=re.match(r'^\s*(\d{2}[A-Z]{3}\d{4})\s+(.+)$',line)
        if not match:continue
        date=datetime.strptime(match[1],'%d%b%Y').date().isoformat()
        # SST/anomaly fields can touch (26.5-0.2); split() would lose columns.
        values=[float(n) for n in re.findall(r'[+-]?\d+\.\d+',match[2])]
        if len(values)!=8 or date in seen:raise ValueError('Invalid weekly SST columns or duplicate week')
        seen.add(date);sst,anomaly=values[4:6]
        if sst in (-99.9,-999) or anomaly in (-99.9,-999):continue
        if not 15<=sst<=40 or not -10<=anomaly<=10:raise ValueError('Invalid weekly Nino 3.4 SST')
        result.append(dict(week_centered=date,sst_c=sst,anomaly_c=anomaly))
    if not result:raise ValueError('Empty weekly Nino 3.4 index')
    return sorted(result,key=lambda r:r['week_centered'])


def parse_discussion(html):
    text=plain(html)
    date=re.search(r'CLIMATE PREDICTION CENTER/NCEP/NWS\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})',text,re.I)
    status=re.search(r'ENSO Alert System Status:\s*(.+?)\s*Synopsis:',text,re.I)
    synopsis=re.search(r'Synopsis:</u>\s*(?:&nbsp;)?\s*<strong>(.*?)</strong>',html,re.I|re.S)
    if not date or not status or not synopsis:raise ValueError('Cannot identify official CPC status, date or synopsis')
    label=status[1].strip();summary=plain(synopsis[1])
    if not 3<=len(label)<=150 or not 20<=len(summary)<=1200:raise ValueError('Invalid official ENSO status or synopsis')
    issued=datetime.strptime(date[1],'%d %B %Y').date().isoformat()
    next_issue=re.search(r'next ENSO Diagnostics? Discussion is scheduled for\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})',text,re.I)
    return dict(alert_status=label,synopsis=summary,issued_date=issued,
        next_scheduled_date=datetime.strptime(next_issue[1],'%d %B %Y').date().isoformat() if next_issue else None)


def fetch(http,url,maximum=1_000_000):
    with http.get(url,timeout=(15,45),stream=True) as response:
        response.raise_for_status();content=bytearray()
        for chunk in response.iter_content(65536):
            content.extend(chunk)
            if len(content)>maximum:raise ValueError('Oversized ENSO source')
    return bytes(content)


def run(output=None):
    now=datetime.now(timezone.utc);output=Path(output or ROOT/'generated/enso');output.mkdir(parents=True,exist_ok=True)
    with session() as http,tempfile.TemporaryDirectory(dir=output) as temp:
        temp=Path(temp)
        roni=parse_seasons(fetch(http,SOURCES['roni']).decode('ascii'),'roni')
        oni=parse_seasons(fetch(http,SOURCES['oni']).decode('ascii'),'oni')
        weekly=parse_weekly(fetch(http,SOURCES['weekly']).decode('ascii'))
        if len(roni)<600 or len(oni)<600 or len(weekly)<52:raise ValueError('Unexpectedly incomplete ENSO monitoring history')
        discussion=parse_discussion(fetch(http,SOURCES['discussion']).decode('windows-1252'))
        outlook=fetch(http,SOURCES['outlook']).decode('windows-1252')
        image=re.search(r'(?:src|href)=["\']([^"\']*/archives/enso/roni/images/\d{4}/enso-roni-outlook-current\.png)["\']',outlook,re.I)
        issue=re.search(r'Issued\s+([A-Za-z]+\s+\d{4})',plain(outlook))
        if not image or not issue:raise ValueError('Cannot identify official RONI forecast graphic and issue month')
        url=urljoin(SOURCES['outlook'],image[1])
        if urlparse(url).hostname not in ('www.cpc.ncep.noaa.gov','cpc.ncep.noaa.gov') or not url.startswith('https://'):raise ValueError('Unexpected ENSO outlook graphic host')
        latest_roni=next((r for r in reversed(roni) if r['anomaly_c'] is not None),None)
        latest_oni=next((r for r in reversed(oni) if r['anomaly_c'] is not None),None)
        if latest_roni is None or latest_oni is None:raise ValueError('No valid seasonal indices')
        if discussion['issued_date']>now.date().isoformat() or weekly[-1]['week_centered']>now.date().isoformat():raise ValueError('Future ENSO monitoring date')
        for latest in (latest_roni,latest_oni):
            if (latest['year'],latest['center_month'])>(now.year,now.month):raise ValueError('Future observed seasonal index')
        payload=fetch(http,url,maximum=8_000_000)
        image_hash=hashlib.sha256(payload).hexdigest()
        issue_key=datetime.strptime(issue[1],'%B %Y').strftime('%Y%m')
        path=temp/f'roni-outlook-{issue_key}-{image_hash[:12]}.png'
        with Image.open(BytesIO(payload)) as graphic:
            if graphic.format!='PNG' or min(graphic.size)<300 or max(graphic.size)>8000:raise ValueError('Invalid RONI outlook graphic')
            width,height=graphic.size;graphic.verify()
        path.write_bytes(payload)
        result=dict(schema_version=1,generated_at_utc=now.isoformat(timespec='seconds').replace('+00:00','Z'),
            discussion=discussion,roni=roni,oni=oni,weekly_nino34=weekly[-156:],latest_roni=latest_roni,latest_oni=latest_oni,
            official_outlook=dict(issued_month=issue[1],image_filename=path.name,image_sha256=image_hash,source_url=url,width=width,height=height),
            sources=SOURCES,notes=['Official ENSO alert comes from CPC discussion, never from automatic threshold classification.',
                'RONI and ONI are overlapping three-month indices; weekly Nino 3.4 is a different SST anomaly measure.',
                'Most recent seasonal index values are estimates and may be revised. Observation dates differ from website retrieval time.'])
        target=temp/'latest.json';target.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
        os.replace(path,output/path.name);os.replace(target,output/'latest.json')
    print('Published NOAA ENSO tracker: '+discussion['alert_status']+' / '+discussion['issued_date'],flush=True)
    return result


if __name__=='__main__':
    try:run()
    except Exception:logging.exception('ENSO refresh failed; previous publication retained');raise SystemExit(1)
