import pytest
from datetime import datetime,timezone
from models.woof import ranges,cycles
from models.fields import available_products
from models.catalog import MODELS

def inventory():
    from models.woof import FIELDS
    lines=[f'{i+1}:{i*100}:d=2026110506:{v}:{level}:24 hour fcst:' for i,(v,level) in enumerate(FIELDS)]
    lines.extend(f'{i+1}:{i*100}:d=2026110506:IGNORED:surface:24 hour fcst:' for i in range(len(lines),120))
    return '\n'.join(lines)

def test_only_bounded_required_ranges():
    from models.woof import FIELDS
    assert ranges(inventory())==[(0,len(FIELDS)*100-1)]

def test_missing_precip_flags_not_manufactured():
    assert 'precip' not in available_products('woofnam')
    assert 'ptype' in available_products('woofnam')
    assert MODELS['woofnam']['airports'] is False

def test_missing_required_field_fails():
    with pytest.raises(ValueError):ranges(inventory().replace(':PRMSL:',':OTHER:'))

def test_backwards_offsets_fail():
    with pytest.raises(ValueError):ranges(inventory().replace('2:100:', '2:0:'))

def test_unsupported_old_layout_not_selected():
    class Response:
        content=b'{}'
        def raise_for_status(self):pass
        def json(self):return {'cycles':[{'cycle':'2026-11-05T00:00:00Z','state':'complete','hours_available':84}]}
    class HTTP:
        def get(self,*a,**kw):return Response()
    with pytest.raises(ValueError):cycles(HTTP(),datetime(2026,11,5,12,tzinfo=timezone.utc))
