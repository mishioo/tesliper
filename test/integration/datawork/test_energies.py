import numpy as np
from tesliper.datawork import energies as en
import pytest


def test_calculate_min_factors_empty():
    out = en.calculate_min_factors([])
    assert out.tolist() == []


def test_calculate_min_factors_one_value():
    out = en.calculate_min_factors([1])
    assert out.tolist() == [1]


def test_calculate_min_factors_more_values():
    out = en.calculate_min_factors([0, 0.001, 0.002])
    assert np.round(out, decimals=8).tolist() == [1, 0.34676265, 0.12024433]


def test_calculate_min_factors_other_temp():
    out = en.calculate_min_factors([0, 0.001, 0.002], t=200)
    assert np.round(out, decimals=8).tolist() == [1, 0.20620689, 0.04252128]


def test_calculate_populations_empty():
    out = en.calculate_populations([])
    assert out.tolist() == []


def test_calculate_populations_one_value():
    out = en.calculate_populations([1])
    assert out.tolist() == [1]


def test_calculate_populations_more_values():
    out = en.calculate_populations([0, 0.001, 0.002])
    assert np.round(out, decimals=8).tolist() == [0.68166002, 0.23637423, 0.08196575]


def test_calculate_populations_other_temp():
    out = en.calculate_populations([0, 0.001, 0.002], t=200)
    assert np.round(out, decimals=8).tolist() == [0.8008148, 0.16513353, 0.03405167]
