from unittest import mock

import pytest
import numpy as np

import tesliper.glassware.arrays as ar
from tesliper.exceptions import InconsistentDataError


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
    assert arr.values.dtype == np.float64


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
def averagable():
    class Av(ar.FloatArray, ar.Averagable):
        associated_genres = ()

    return Av(genre="bla", filenames=["f1", "f2", "f3"], values=[3, 12, 15])


def test_average_conformers_energies_object(averagable, lggr, clav, get_repr_args_mock):
    en = mock.Mock(genre="foo", populations=[1, 1, 1])
    out = averagable.average_conformers(en)
    assert type(out) is type(averagable)
    assert out.values.tolist() == [10]
    assert clav.call_args[0][0].tolist() == [3, 12, 15]
    assert clav.call_args[0][1] == [1, 1, 1]
    get_repr_args_mock.assert_called()
    lggr.debug.assert_called_with("bla averaged by foo.")


def test_average_conformers_list(averagable, lggr, clav, get_repr_args_mock):
    out = averagable.average_conformers([1, 1, 1])
    assert type(out) is type(averagable)
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
        bars.genre,
        bars.values,
        bars.frequencies,
        bars.t,
        bars.laser,
    )


# test Geometry
@pytest.fixture
def geom():
    return ar.Geometry(
        genre="geometry",
        filenames=["file1.out", "file2.out"],
        values=[
            [[30, 40, 60], [40, 60, 70], [50, 80, 10]],
            [[35, 45, 65], [45, 65, 75], [55, 85, 15]],
        ],
        molecule_atoms=[[1, 1, 1]],
    )


@pytest.fixture
def geom_incons():
    return ar.Geometry(
        genre="geometry",
        filenames=["file1.out", "file2.out"],
        values=[
            [[30, 40, 60], [40, 60, 70], [50, 80, 10]],
            [[35, 45, 65], [45, 65, 75]],
        ],
        molecule_atoms=[[2, 2, 2], [2, 2]],
        allow_data_inconsistency=True,
    )


def test_molecule_atoms(geom):
    assert geom.molecule_atoms.tolist() == [[1, 1, 1]]


def test_molecule_atoms_as_symbols(geom, monkeypatch):
    monkeypatch.setattr(
        type(geom).molecule_atoms, "fsan", mock.Mock(return_value=[[6, 1, 8]])
    )
    geom.molecule_atoms = [["C", "H", "O"]]
    assert geom.molecule_atoms.tolist() == [[6, 1, 8]]


def test_molecule_atoms_two_dim(geom):
    geom.molecule_atoms = [[2, 2, 2], [2, 2, 2]]
    assert geom.molecule_atoms.tolist() == [[2, 2, 2]]


def test_molecule_atoms_two_dim_different(geom):
    with pytest.raises(InconsistentDataError):
        geom.molecule_atoms = [[2, 2, 2], [2, 1, 2]]


def test_molecule_atoms_two_dim_different_inconsistency_allowed(geom):
    geom.allow_data_inconsistency = True
    geom.molecule_atoms = [[2, 2, 2], [2, 1, 2]]
    assert geom.molecule_atoms.tolist() == [[2, 2, 2], [2, 1, 2]]


def test_molecule_values_varying_sizes_inconsistency_allowed(geom):
    geom.allow_data_inconsistency = True
    geom.values = [
        [[30, 40, 60], [40, 60, 70], [50, 80, 10]],
        [[35, 45, 65], [45, 65, 75]],
    ]
    np.testing.assert_array_equal(
        geom.values,
        [
            [[30, 40, 60], [40, 60, 70], [50, 80, 10]],
            [[35, 45, 65], [45, 65, 75], [0, 0, 0]],
        ],
    )


@pytest.mark.xfail(
    reason=(
        "Geometry.molecule_atoms.sanitizer currently "
        "does not support jagged nested lists."
    )
)
def test_molecule_atoms_varying_sizes_inconsistency_allowed(geom):
    geom.allow_data_inconsistency = True
    geom.molecule_atoms = [[2, 2, 2], [2, 2]]
    assert geom.molecule_atoms.tolist() == [[2, 2, 2], [2, 2, 0]]


def test_molecule_atoms_too_short(geom):
    with pytest.raises(ValueError):
        geom.molecule_atoms = [[2, 2]]


def test_molecule_atoms_not_matching_num_of_conformers(geom):
    with pytest.raises(ValueError):
        geom.molecule_atoms = [[2, 2, 2]] * 3


@pytest.fixture(scope="module")
def transitions_values():
    return [[[(11, 21, 0.5), (12, 22, 0.6)], [(31, 32, 1.1)]]]


@pytest.fixture
def transitions(transitions_values):
    return ar.Transitions(
        genre="transitions",
        filenames=["one"],
        values=transitions_values,
    )


def test_transitions_unpack(transitions_values):
    ground, excited, coefs = ar.Transitions.unpack_values(transitions_values)
    assert ground == [[[11, 12], [31]]]
    assert excited == [[[21, 22], [32]]]
    assert coefs == [[[0.5, 0.6], [1.1]]]


def test_transitions_highest(transitions):
    # TODO: make better tests
    i = transitions.indices_highest
    g, e, v, c = transitions.highest_contribution
    np.testing.assert_array_equal(v, transitions.values[i])
