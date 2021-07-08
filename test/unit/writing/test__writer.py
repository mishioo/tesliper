from pathlib import Path
from unittest import mock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tesliper import Energies, InfoArray, Spectra
from tesliper.glassware import (
    ElectronicBars,
    FloatArray,
    SingleSpectrum,
    VibrationalBars,
)
from tesliper.writing import SerialWriter, Writer

normal_writers = [Writer]
serial_writers = [SerialWriter]
all_writers = [Writer, SerialWriter]


@pytest.fixture
def destination_is_dir(monkeypatch):
    monkeypatch.setattr(Path, "is_dir", lambda _: True)


@pytest.fixture
def destination_is_not_dir(monkeypatch):
    monkeypatch.setattr(Path, "is_dir", lambda _: False)


@pytest.fixture
def destination_is_file(monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda _: True)


@pytest.fixture
def destination_is_not_file(monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda _: False)


@pytest.fixture
def destination_exists(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda _: True)


@pytest.mark.usefixtures("destination_is_not_file", "destination_is_not_dir")
@pytest.fixture
def destination_doesnt_exists(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda _: False)


@pytest.fixture
def no_parent_dir(monkeypatch):
    parent = mock.Mock()
    parent.exists = mock.Mock(return_value=False)
    monkeypatch.setattr(Path, "parent", parent)


arrays_by_type = dict(
    energies=Energies("gib", [""], [1]),
    vibrational=VibrationalBars("iri", [""], [[1]], [[1]]),
    electronic=ElectronicBars("ex_en", [""], [[1]], [[1]]),
    spectra=Spectra("ir", [""], [[1, 2]], [1, 2]),
    single=SingleSpectrum("ir", [1, 2], [1, 2]),
    other=InfoArray("command", [""], [""]),
    corrections=FloatArray("gibcorr", [""], [1]),
    frequencies=VibrationalBars("freq", [""], [[1]], [[1]]),
    wavelengths=ElectronicBars("wave", [""], [[1]], [[1]]),
    stoichiometry=InfoArray("stoichiometry", [""], [""]),
)


@pytest.mark.parametrize("writer_class", serial_writers)
@given(st.text())
def test_writer_mode_init(writer_class, mode):
    if mode not in ("a", "x", "w"):
        with pytest.raises(ValueError):
            writer_class(destination="", mode=mode)


@pytest.mark.usefixtures("destination_doesnt_exists")
@pytest.mark.parametrize("writer_class", normal_writers)
def test_writer_init_append_no_dest(writer_class):
    with pytest.raises(FileNotFoundError):
        writer_class(destination="", mode="a")


@pytest.mark.usefixtures("destination_doesnt_exists")
@pytest.mark.parametrize("writer_class", normal_writers)
def test_writer_init_overwrite_no_dest(writer_class, monkeypatch):
    parent_mock = mock.Mock()
    parent_mock.exists = mock.Mock(return_value=True)
    monkeypatch.setattr(Path, "parent", parent_mock)
    wrt = writer_class(destination="", mode="w")
    assert wrt.mode == "w"


@pytest.mark.usefixtures("destination_exists")
@pytest.mark.parametrize("writer_class", normal_writers)
def test_writer_init_overwrite(writer_class):
    wrt = writer_class(destination="", mode="w")
    assert wrt.mode == "w"


@pytest.mark.usefixtures("destination_doesnt_exists")
@pytest.mark.usefixtures("no_parent_dir")
@pytest.mark.parametrize("writer_class", normal_writers)
def test_writer_init_no_parent_dir(writer_class):
    with pytest.raises(FileNotFoundError):
        writer_class(destination="", mode="w")


@pytest.mark.usefixtures("destination_exists")
@pytest.mark.parametrize("writer_class", normal_writers)
def test_writer_init_new_only_no_dest(writer_class):
    with pytest.raises(FileExistsError):
        writer_class(destination="", mode="x")


@pytest.mark.usefixtures("destination_is_not_dir")
@pytest.mark.parametrize("mode", ("a", "x", "w"))
@pytest.mark.parametrize("writer_class", serial_writers)
def test_serial_writer_init_no_dest(writer_class, mode):
    with pytest.raises(FileNotFoundError):
        writer_class(destination="", mode=mode)


@pytest.mark.parametrize("arraytype,array", tuple(arrays_by_type.items()))
def test_distribution(arraytype, array):
    output = Writer.distribute_data([array])
    assert isinstance(output, dict)
    assert output[arraytype], f"arraytype: {arraytype}, output: {output}"
