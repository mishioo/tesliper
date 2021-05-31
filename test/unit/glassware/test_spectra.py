import pytest
from hypothesis import given, strategies as st

import numpy as np

from tesliper.glassware import spectra as sp


@pytest.mark.parametrize("genre", list(sp.SingleSpectrum._units.keys()))
def test_single_units(genre):
    s = sp.SingleSpectrum(genre, [1, 2], [1, 2])
    assert all(k in s.units for k in ("x", "y", "width", "start", "stop", "step"))


@given(st.integers(min_value=2, max_value=100))
def test_single_length(size):
    np.random.seed(0)  # filler values only, but just to be sure, is shouldn't change
    s = sp.SingleSpectrum("ir", np.random.random(size), np.random.random(size))
    assert len(s) == size
