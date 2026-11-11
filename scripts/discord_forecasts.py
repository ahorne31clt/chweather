"""Send newly published forecast graphics to an opt-in Discord webhook."""
import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
from uuid import uuid4
from zoneinfo import ZoneInfo

from PIL import Image

PRODUCTS = {
    'sunset': 'Sunset outlook',
    'weather-nc': 'North Carolina weather outlook',
    'rain-nc': 'North Carolina rain chance',
    'spc-day1': 'SPC Day 1 outlook',
}


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def forecasts(read):
    sunset = read('sunset')
    weather = read('weather')
    rows = {item['id']: dict(item, folder='weather') for item in weather.get('products', [])}
    if sunset.get('status') != 'unavailable' and sunset.get('model_run'):
        rows['sunset'] = dict(sunset, folder='sunset', issued_at_utc=sunset['model_run'])
    return rows


def newer(before, after, now):
    for key in PRODUCTS:
        row = after.get(key)
        if not row or row.get('retained_from_previous_publication'):
            continue
        old = before.get(key)
        if key == 'sunset':
            valid = row['forecast_valid_date']
            if old and (valid, timestamp(row['issued_at_utc'])) <= (old['forecast_valid_date'], timestamp(old['issued_at_utc'])):
                continue
            if valid < now.astimezone(ZoneInfo("America/New_York")).date().isoformat():
                continue
        else:
            if timestamp(row['valid_end_utc']) <= now:
                continue
            if old and (timestamp(row['issued_at_utc']), timestamp(row['valid_start_utc'])) <= (timestamp(old['issued_at_utc']), timestamp(old['valid_start_utc'])):
                continue
        yield key, row


def attachment(root, key, row):
    name = row['image_filename']
    if not re.fullmatch(r'[a-zA-Z0-9_-]+\.(png|webp|jpg)', name):
        raise ValueError('Invalid forecast image filename')
    source = root / 'generated' / row['folder'] / name
    with Image.open(source) as graphic:
        graphic.thumbnail((1600, 1600))
        buffer = BytesIO()
        graphic.convert('RGB').save(buffer, format='JPEG', quality=85, optimize=True)
    return key + '.jpg', buffer.getvalue()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def send(webhook, content, files):
    url = urlsplit(webhook)
    if url.scheme != 'https' or url.netloc != 'discord.com' or not re.fullmatch(r'/api/webhooks/\d+/[a-zA-Z0-9_-]+', url.path) or url.query or url.fragment:
        raise ValueError('Use the Discord channel webhook URL from Discord Integrations')
    boundary = uuid4().hex
    payload = json.dumps({'content': content, 'allowed_mentions': {'parse': []}}).encode()
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json\r\n\r\n'.encode() + payload + b'\r\n']
    for index, (name, image) in enumerate(files):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="files[{index}]"; filename="{name}"\r\nContent-Type: image/jpeg\r\n\r\n'.encode() + image + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    request = Request(webhook + '?wait=true', data=b''.join(parts), headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}', 'User-Agent': 'CHWeather-Publisher/1.0',
    })
    try:
        with build_opener(NoRedirect()).open(request, timeout=25) as response:
            if response.status != 200:
                raise ValueError('Discord did not confirm the message')
    except HTTPError as error:
        raise ValueError(f'Discord returned HTTP {error.code}') from None
    except (OSError, URLError):
        raise ValueError('Discord request failed or timed out') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['snapshot', 'notify'])
    args = parser.parse_args()
    page = os.environ['FORECAST_PAGE_URL'].rstrip('/')
    if urlsplit(page).scheme != 'https':
        raise ValueError('Expected an HTTPS Pages URL')
    snapshot = Path(os.environ['RUNNER_TEMP']) / 'previous-discord-forecasts.json'
    if args.mode == 'snapshot':
        snapshot.unlink(missing_ok=True)

        def read_live(folder):
            url = f'{page}/generated/{folder}/latest.json?discord_snapshot={time.time_ns()}'
            with urlopen(Request(url, headers={'Cache-Control': 'no-cache'}), timeout=15) as response:
                return json.load(response)

        snapshot.write_text(json.dumps(forecasts(read_live)), encoding='utf-8')
        return
    if not snapshot.exists():
        print('Previous site snapshot unavailable. Skipping Discord announcement.')
        return
    root = Path('_site')
    after = forecasts(lambda folder: json.loads((root / 'generated' / folder / 'latest.json').read_text(encoding='utf-8')))
    changes = list(newer(json.loads(snapshot.read_text(encoding='utf-8')), after, datetime.now(timezone.utc)))
    if not changes:
        print('No new eligible forecasts to announce.')
        return
    labels = '\n'.join(f'- {PRODUCTS[key]}' for key, row in changes)
    files = [attachment(root, key, row) for key, row in changes]
    send(os.environ['DISCORD_WEBHOOK_URL'], f'**New CH Weather forecasts**\n{labels}\n<{page}/>', files)
    print('Discord confirmed the forecast announcement.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit(f'Forecast announcement step failed ({type(error).__name__}). Check the Pages URL and Discord webhook configuration.') from None
