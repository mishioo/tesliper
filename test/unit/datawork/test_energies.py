from unittest import mock

import numpy as np
from hypothesis import given, strategies as st

from tesliper.datawork import energies as en
import pytest


def test_calculate_deltas_wrong_type_string():
    with pytest.raises(ValueError):
        en.calculate_deltas("string")


def test_calculate_deltas_wrong_type_integer():
    with pytest.raises(TypeError):
        en.calculate_deltas(1)


def test_calculate_deltas_not_iterable():
    with pytest.raises(TypeError):
        en.calculate_deltas(object())


def test_calculate_deltas_empty():
    out = en.calculate_deltas([])
    assert out.tolist() == []


def test_calculate_deltas_one_value():
    out = en.calculate_deltas([1])
    assert out.tolist() == [0]


def test_calculate_deltas_convertible_string():
    out = en.calculate_deltas(["1"])
    assert out.tolist() == [0]


@given(st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1))
def test_calculate_deltas_more_values(data):
    m = min(data)
    out = en.calculate_deltas(data)
    assert out.tolist() == [d - m for d in data]


@pytest.fixture
def deltas(monkeypatch):
    monkeypatch.setattr(en, "calculate_deltas", mock.Mock())


def test_calculate_min_factors_empty(deltas):
    en.calculate_deltas.return_value = np.array([])
    out = en.calculate_min_factors([])
    assert out.tolist() == []


def test_calculate_min_factors_one_value(deltas):
    en.calculate_deltas.return_value = np.array([0])
    out = en.calculate_min_factors([1])
    assert out.tolist() == [1]


def test_calculate_min_factors_more_values(deltas):
    en.calculate_deltas.return_value = np.array([0, 0.6275095, 2 * 0.6275095])
    out = en.calculate_min_factors([0, 0.001, 0.002])
    assert np.round(out, decimals=8).tolist() == [1, 0.34676265, 0.12024433]


def test_calculate_min_factors_other_temp(deltas):
    en.calculate_deltas.return_value = np.array([0, 0.6275095, 2 * 0.6275095])
    out = en.calculate_min_factors([0, 0.001, 0.002], t=200)
    assert np.round(out, decimals=8).tolist() == [1, 0.20620689, 0.04252128]


@pytest.fixture
def factors(monkeypatch):
    monkeypatch.setattr(en, "calculate_min_factors", mock.Mock())


def test_calculate_populations_empty(factors):
    en.calculate_min_factors.return_value = np.array([])
    out = en.calculate_populations([])
    assert out.tolist() == []


def test_calculate_populations_one_value(factors):
    en.calculate_min_factors.return_value = np.array([1])
    out = en.calculate_populations([1])
    assert out.tolist() == [1]


def test_calculate_populations_more_values(factors):
    en.calculate_min_factors.return_value = np.array([1, 0.34676265, 0.12024433])
    out = en.calculate_populations([0, 0.001, 0.002])
    assert np.round(out, decimals=8).tolist() == [0.68166002, 0.23637423, 0.08196575]


def test_calculate_populations_other_temp(factors):
    en.calculate_min_factors.return_value = np.array([1, 0.20620689, 0.04252128])
    out = en.calculate_populations([0, 0.001, 0.002], t=200)
    assert np.round(out, decimals=8).tolist() == [0.8008148, 0.16513353, 0.03405167]
