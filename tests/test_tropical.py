from tropical.__main__ import parse_outlook
import pytest


def test_outlook_uses_its_own_issue_time_and_safe_text():
    xml=b'''<rss><channel><pubDate>Fri, 30 Oct 2026 12:00:00 GMT</pubDate><item><title>Atlantic Tropical Weather Outlook</title><pubDate>Fri, 30 Oct 2026 11:18:00 GMT</pubDate><link>https://www.nhc.noaa.gov/gtwo.php?basin=atlc</link><description><![CDATA[Tropical Weather Outlook<br>Official forecast information with sufficient text to validate the bulletin.<script>bad()</script>]]></description></item></channel></rss>'''
    result=parse_outlook(xml)
    assert result['published_at_utc']=='2026-10-30T11:18:00Z'
    assert '\n' in result['text'] and 'bad()' not in result['text']


def test_missing_outlook_is_not_treated_as_no_tropical_activity():
    with pytest.raises(ValueError,match='no tropical outlook'):
        parse_outlook(b'<rss><channel><item><title>Service unavailable</title></item></channel></rss>')
