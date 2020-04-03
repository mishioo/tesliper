from unittest import mock

import pytest

import tesliper.glassware.arrays as ar
import numpy as np


def test_filenames_array_empty():
    arr = ar.FilenamesArray()
    assert arr.filenames.tolist() == []
    assert arr.genre == "filenames"


def test_filenames_array_filenames():
    arr = ar.FilenamesArray(filenames=["one", "two"])
    assert arr.filenames.tolist() == ["one", "two"]


def test_filenames_array_values():
    arr = ar.FilenamesArray(filenames=["one", "two"])
    assert arr.filenames is arr.values


def test_dtype():
    arr = ar.FloatArray(genre="bla", filenames=["f1", "f2", "f3"], values=[3, 12, 15])
    assert arr.values.dtype == np.float


@pytest.fixture
def get_repr_args_mock(monkeypatch):
    monkeypatch.setattr(
        ar.ArrayBase,
        "get_repr_args",
        mock.Mock(
            return_value={
                "genre": "bla",
                "filenames": ["f1", "f2", "f3"],
                "values": [1, 12, 15],
                "allow_data_inconsistency": False,
            }
        ),
    )
    return ar.ArrayBase.get_repr_args


@pytest.fixture
def clav(monkeypatch):
    monkeypatch.setattr(ar.dw, "calculate_average", mock.Mock(return_value=10))
    return ar.dw.calculate_average


@pytest.fixture
def lggr(monkeypatch):
    monkeypatch.setattr(ar, "logger", mock.Mock())
    return ar.logger


@pytest.fixture
def arr():
    return ar.FloatArray(genre="bla", filenames=["f1", "f2", "f3"], values=[3, 12, 15])


def test_average_conformers_energies_object(arr, lggr, clav, get_repr_args_mock):
    en = mock.Mock(genre="foo", populations=[1, 1, 1])
    out = arr.average_conformers(en)
    assert type(out) is ar.FloatArray
    assert out.values.tolist() == [10]
    assert clav.call_args[0][0].tolist() == [3, 12, 15]
    assert clav.call_args[0][1] == [1, 1, 1]
    get_repr_args_mock.assert_called()
    lggr.debug.assert_called_with("bla averaged by foo.")


def test_average_conformers_list(arr, lggr, clav, get_repr_args_mock):
    out = arr.average_conformers([1, 1, 1])
    assert type(out) is ar.FloatArray
    assert out.values.tolist() == [10]
    assert clav.call_args[0][0].tolist() == [3, 12, 15]
    assert clav.call_args[0][1].tolist() == [1, 1, 1]
    get_repr_args_mock.assert_called()
    lggr.debug.assert_called_with("bla averaged by unknown.")


@pytest.fixture
def filenames_mock(monkeypatch):
    mocked = mock.PropertyMock(return_value=["f1", "f2", "f3"])
    monkeypatch.setattr(ar.Energies, "filenames", mocked)
    return mocked


@pytest.fixture
def values_mock(monkeypatch):
    mocked = mock.PropertyMock(return_value=[3, 12, 15])
    monkeypatch.setattr(ar.Energies, "values", mocked)
    return mocked


@pytest.fixture
def en():
    return ar.Energies(
        genre="bla", filenames=["f1", "f2", "f3"], values=[3, 12, 15], t=10
    )


def test_deltas(en, monkeypatch, filenames_mock, values_mock):
    monkeypatch.setattr(ar.dw, "calculate_deltas", mock.Mock())
    _ = en.deltas
    values_mock.assert_called()
    ar.dw.calculate_deltas.assert_called_with(en.values)


def test_min_factors(en, monkeypatch, filenames_mock, values_mock):
    monkeypatch.setattr(ar.dw, "calculate_min_factors", mock.Mock())
    _ = en.min_factors
    values_mock.assert_called()
    ar.dw.calculate_min_factors.assert_called_with(en.values, en.t)


def test_populations(en, monkeypatch, filenames_mock, values_mock):
    monkeypatch.setattr(ar.dw, "calculate_populations", mock.Mock())
    _ = en.populations
    values_mock.assert_called()
    ar.dw.calculate_populations.assert_called_with(en.values, en.t)


def test_calculate_populations(en, monkeypatch, filenames_mock, values_mock):
    monkeypatch.setattr(ar.dw, "calculate_populations", mock.Mock())
    en.calculate_populations(20)
    values_mock.assert_called()
    ar.dw.calculate_populations.assert_called_with(en.values, 20)


@pytest.fixture
def freq(monkeypatch):
    monkeypatch.setattr(
        ar.Bars, "frequencies", mock.PropertyMock(return_value=[[10, 20], [12, 21]])
    )
    return ar.Bars.frequencies


@pytest.fixture
def vals(monkeypatch):
    monkeypatch.setattr(
        ar.Bars, "values", mock.PropertyMock(return_value=[[2, 5], [3, 7]])
    )
    return ar.Bars.values


@pytest.fixture
def fnms(monkeypatch):
    monkeypatch.setattr(
        ar.Bars, "filenames", mock.PropertyMock(return_value=["f1", "f2"])
    )
    return ar.Bars.filenames


@pytest.fixture
def inten(monkeypatch):
    monkeypatch.setattr(ar.dw, "calculate_intensities", mock.Mock())
    return ar.dw.calculate_intensities


@pytest.fixture
def bars():
    return ar.Bars("bla", [], [], [])


def test_intensieties(bars, inten, fnms, vals, freq):
    _ = bars.intensities
    inten.assert_called_with(
        bars.genre, bars.values, bars.frequencies, bars.t, bars.laser,
    )
