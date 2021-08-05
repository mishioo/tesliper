from pathlib import Path
from unittest import mock

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from tesliper import Energies, InfoArray, Spectra
from tesliper.glassware import (
    ElectronicData,
    FloatArray,
    ScatteringData,
    SingleSpectrum,
    VibrationalData,
)
from tesliper.writing import Writer


@pytest.fixture(scope="session")
def writer_class():
    class _Writer(Writer):
        extension = "txt"

    return _Writer


@pytest.fixture
def path_is_dir(monkeypatch):
    monkeypatch.setattr(Path, "is_dir", lambda _: True)


@pytest.fixture
def path_is_not_dir(monkeypatch):
    monkeypatch.setattr(Path, "is_dir", lambda _: False)


@pytest.fixture
def path_is_file(monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda _: True)


@pytest.fixture
def path_is_not_file(monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda _: False)


@pytest.fixture
def path_exists(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda _: True)


@pytest.fixture
def path_doesnt_exists(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda _: False)


@pytest.mark.usefixtures("path_is_not_file", "path_is_not_dir", "path_doesnt_exist")
@pytest.fixture
def path_truly_doesnt_exist():
    yield


@pytest.fixture
def no_parent_dir(monkeypatch):
    parent = mock.Mock()
    parent.exists = mock.Mock(return_value=False)
    monkeypatch.setattr(Path, "parent", parent)


@given(mode=st.text())
def test_writer_mode_init(writer_class, mode):
    assume(mode not in ("a", "x", "w"))
    with pytest.raises(ValueError):
        writer_class(destination="", mode=mode)


@pytest.mark.usefixtures("path_exists")
@pytest.mark.parametrize("mode", ["a", "x", "w"])
def test_writer_mode_ok_init(writer_class, mode):
    wrt = writer_class(destination="", mode=mode)
    assert wrt.mode == mode


@pytest.mark.usefixtures("path_is_not_dir")
@pytest.mark.parametrize("mode", ["a", "x", "w"])
def test_writer_init_dest_is_not_dir(writer_class, mode):
    with pytest.raises(FileNotFoundError):
        writer_class(destination="", mode=mode)


@pytest.mark.usefixtures("path_doesnt_exists")
def test_writer_check_file_no_dest(writer_class, monkeypatch):
    parent_mock = mock.Mock()
    parent_mock.exists = mock.Mock(return_value=True)
    monkeypatch.setattr(Path, "parent", parent_mock)
    wrt = writer_class(destination="", mode="w")
    assert wrt.check_file("") == Path("")


@pytest.mark.usefixtures("path_exists")
def test_writer_check_file_overwrite(writer_class):
    wrt = writer_class(destination="", mode="w")
    assert wrt.check_file("") == Path("")


@pytest.mark.usefixtures("path_doesnt_exists")
@pytest.mark.usefixtures("no_parent_dir")
def test_writer_check_file_no_parent_dir(writer_class):
    wrt = writer_class(destination="", mode="w")
    with pytest.raises(FileNotFoundError):
        wrt.check_file("")


@pytest.mark.usefixtures("path_exists")
def test_writer_check_file_new_only_no_dest(writer_class):
    wrt = writer_class(destination="", mode="x")
    with pytest.raises(FileExistsError):
        wrt.check_file("")


arrays_by_type = dict(
    energies=Energies("gib", [""], [1]),
    vibrationaldata=VibrationalData("iri", [""], [[1]], [[1]]),
    scatteringdata=ScatteringData("ramact", [""], [[1]], [[1]]),
    electronicdata=ElectronicData("ex_en", [""], [[1]], [[1]]),
    spectra=Spectra("ir", [""], [[1, 2]], [1, 2]),
    singlespectrum=SingleSpectrum("ir", [1, 2], [1, 2]),
    infoarray=InfoArray("command", [""], [""]),
)
extras_by_type = dict(
    corrections=FloatArray("gibcorr", [""], [1]),
    frequencies=VibrationalData("freq", [""], [[1]], [[1]]),
    wavelengths=ElectronicData("wave", [""], [[1]], [[1]]),
    stoichiometry=InfoArray("stoichiometry", [""], [""]),
)


@pytest.mark.parametrize("arraytype,array", tuple(arrays_by_type.items()))
def test_distribution_data(writer_class, arraytype, array):
    output, extras = writer_class.distribute_data([array])
    assert isinstance(output, dict)
    assert arraytype in output
    assert output[arraytype] is not None


@pytest.mark.parametrize("arraytype,array", tuple(extras_by_type.items()))
def test_distribution_extras(writer_class, arraytype, array):
    output, extras = writer_class.distribute_data([array])
    assert isinstance(extras, dict)
    assert arraytype in extras
    assert extras[arraytype] is not None


writer_methods = {
    "overview": dict(
        energies=None,
        frequencies=None,
        stoichiometry=None,
    ),
    "energies": dict(energies=None, corrections=None),
    "spectrum": dict(spectrum=None),
    "bars": dict(band=None, bars=None),
    "spectra": dict(spectra=None),
    "transitions": dict(
        transitions=None,
        wavelengths=None,
        only_highest=True,
    ),
    "geometry": dict(
        geometry=None,
        charge=None,
        multiplicity=None,
    ),
}


@pytest.mark.parametrize("method,signature", tuple(writer_methods.items()))
def test_not_implemented_methods(writer_class, method, signature):
    wrt = writer_class(destination="")
    m = getattr(wrt, method)
    with pytest.raises(NotImplementedError):
        m(**signature)
