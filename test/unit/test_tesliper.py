import pytest
from hypothesis import given
from hypothesis import strategies as st

import tesliper as ts


@given(value=st.floats(max_value=0, allow_nan=False, exclude_max=True))
def test_temperature_below_zero(value):
    tslr = ts.Tesliper()
    with pytest.raises(ValueError):
        tslr.temperature = value


@given(value=st.floats(min_value=0, allow_nan=False, exclude_min=True))
def test_temeprature_clear(value):
    tslr = ts.Tesliper()
    init_value = tslr.temperature
    tslr.temperature = value
    tslr.clear()
    assert tslr.temperature == init_value
