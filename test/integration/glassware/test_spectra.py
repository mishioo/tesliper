from copy import copy
from unittest import mock

import pytest
from hypothesis import given, strategies as st

import numpy as np

from tesliper.glassware import spectra as sp
import tesliper.glassware as gw


def test_single_units():
    s = sp.SingleSpectrum("ir", [1, 2], [1, 2])
    assert all(k in s.units for k in ("x", "y", "width", "start", "stop", "step"))


@given(
    st.lists(
        st.floats(allow_nan=False, allow_infinity=False), min_size=2, max_size=100
    ),
    st.floats(allow_nan=False, allow_infinity=False),
)
def test_single_scaling(values, factor):
    s = sp.SingleSpectrum("ir", values=values, abscissa=np.arange(len(values)))
    s.scaling = factor
    assert np.allclose(s.y, s.values * factor)


@given(
    st.integers(min_value=2, max_value=100),
    st.floats(allow_nan=False, allow_infinity=False),
)
def test_single_offset(size, factor):
    np.random.seed(0)  # filler values only, but just to be sure, is shouldn't change
    s = sp.SingleSpectrum("ir", values=np.random.random(size), abscissa=np.arange(size))
    s.offset = factor
    assert np.allclose(s.x, s.abscissa + factor)


@given(
    st.lists(
        st.floats(
            max_value=1000, min_value=-1000, allow_nan=False, allow_infinity=False
        ),
        min_size=2,
        max_size=100,
    ),
    st.floats(
        min_value=0,
        exclude_min=True,
        max_value=1000,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_single_scale_to(values, factor):
    s1 = sp.SingleSpectrum("ir", values=values, abscissa=np.arange(len(values)))
    s2 = copy(s1)
    s2.scaling = factor
    s1.scale_to(s2)
    assert np.allclose(s1.y, s2.y)


@given(
    st.integers(min_value=2, max_value=100),
    st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
)
def test_single_shift_to(size, factor):
    np.random.seed(0)  # filler values only, but just to be sure, is shouldn't change
    s1 = sp.SingleSpectrum(
        "ir", values=np.random.random(size), abscissa=np.arange(size)
    )
    s2 = copy(s1)
    s2.offset = factor
    s1.shift_to(s2)
    assert np.allclose(s1.x, s2.x)


@pytest.fixture(scope="module")
def spectra():
    return sp.Spectra("ir", ["one", "two"], [[1, 2], [6, 7]], [0, 1])


@pytest.fixture(scope="module")
def en_mock():
    return mock.Mock(genre="gib", populations=[0.2, 0.8])


def test_spectra_average_return(spectra, en_mock):
    n = spectra.average(en_mock)
    assert n.averaged_by == en_mock.genre
    assert np.allclose(
        n.values, np.average(spectra.values, weights=en_mock.populations, axis=0)
    )


@given(
    factor=st.floats(
        min_value=0,
        exclude_min=True,
        max_value=1000,
        allow_nan=False,
        allow_infinity=False,
    )
)
def test_spectra_scale_to_with_en(spectra, en_mock, factor):
    n = spectra.average(en_mock)
    n.scaling = factor
    spectra.scale_to(n, en_mock)
    assert np.isclose(spectra.scaling, factor)
    spectra.scaling = 1  # reset fixture


@given(
    factor=st.floats(
        min_value=0,
        exclude_min=True,
        max_value=1000,
        allow_nan=False,
        allow_infinity=False,
    )
)
def test_spectra_scale_to_without_en(spectra, factor):
    en_mock = mock.Mock(genre="gib", populations=[0.5, 0.5])  # for easy setup
    n = spectra.average(en_mock)
    n.scaling = factor
    spectra.scale_to(n)  # no Energies provided
    assert np.isclose(spectra.scaling, factor)
    spectra.scaling = 1  # reset fixture


@given(
    factor=st.floats(
        min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False
    ),
)
def test_spectra_shift_to_with_en(spectra, en_mock, factor):
    n = spectra.average(en_mock)
    n.offset = factor
    spectra.shift_to(n, en_mock)
    assert spectra.offset == factor
    spectra.offset = 0  # reset fixture


@given(
    factor=st.floats(
        min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False
    ),
)
def test_spectra_shift_to_without_en(spectra, factor):
    en_mock = mock.Mock(genre="gib", populations=[0.5, 0.5])  # for easy setup
    n = spectra.average(en_mock)
    n.offset = factor
    spectra.shift_to(n)  # no Energies provided
    assert spectra.offset == factor
    spectra.offset = 0  # reset fixture
