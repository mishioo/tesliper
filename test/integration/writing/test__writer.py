from logging import Logger
from pathlib import Path
from unittest.mock import Mock

import pytest

from tesliper.writing import Writer


@pytest.fixture
def writer_class():
    class _Writer(Writer):
        extension = "ext"

    return _Writer


@pytest.fixture
def writer_implemented():
    class _Writer(Writer):
        extension = "ext"

        def overview(self, energies, frequencies, stoichiometry):
            file = self.destination / self.filename_template.substitute(
                conf="overview", genre="", ext=self.extension, num=""
            )
            with file.open(self.mode) as handle:
                handle.write(f"energies: {repr(energies)}\n")
                handle.write(f"frequencies: {repr(frequencies)}\n")
                handle.write(f"stoichiometry: {repr(stoichiometry)}\n")

        def energies(self, energies, corrections):
            file = self.destination / self.filename_template.substitute(
                conf="energies", genre="", ext=self.extension, num=""
            )
            with file.open(self.mode) as handle:
                handle.write(f"energies: {repr(energies)}\n")
                handle.write(f"corrections: {repr(corrections)}\n")

        def single_spectrum(self, spectrum):
            file = self.destination / self.filename_template.substitute(
                conf="spectrum", genre="", ext=self.extension, num=""
            )
            with file.open(self.mode) as handle:
                handle.write(f"spectrum: {repr(spectrum)}\n")

        def spectral_data(self, band, data):
            file = self.destination / self.filename_template.substitute(
                conf="bars", genre="", ext=self.extension, num=""
            )
            with file.open(self.mode) as handle:
                handle.write(f"band: {repr(band)}\n")
                handle.write(f"data: {repr(data)}\n")

        def spectra(self, spectra):
            file = self.destination / self.filename_template.substitute(
                conf="spectra", genre="", ext=self.extension, num=""
            )
            with file.open(self.mode) as handle:
                handle.write(f"spectra: {repr(spectra)}\n")

        def transitions(self, transitions, wavelengths):
            file = self.destination / self.filename_template.substitute(
                conf="transitions", genre="", ext=self.extension, num=""
            )
            with file.open(self.mode) as handle:
                handle.write(f"transitions: {repr(transitions)}\n")
                handle.write(f"wavelengths: {repr(wavelengths)}\n")

        def geometry(self, geometry, charge, multiplicity):
            file = self.destination / self.filename_template.substitute(
                conf="geometry", genre="", ext=self.extension, num=""
            )
            with file.open(self.mode) as handle:
                handle.write(f"geometry: {repr(geometry)}\n")
                handle.write(f"charge: {repr(charge)}\n")
                handle.write(f"multiplicity: {repr(multiplicity)}\n")

    return _Writer


def test_iter_handles(writer_class, tmp_path):
    wrt = writer_class(destination=tmp_path, mode="w")
    names = ["a", "b"]
    handles = wrt._iter_handles(names, "grn")
    oldh, h = None, None
    for num, name in enumerate(names):
        oldh, h = h, next(handles)
        assert oldh is None or oldh.closed
        assert not h.closed
        # genre not used by default filename template
        assert f"{name}.ext" == Path(h.name).name
    try:
        next(handles)
    except StopIteration:
        assert h.closed
    else:
        pytest.fail("file handle should be closed")


def test_get_handle(writer_class, tmp_path):
    wrt = writer_class(destination=tmp_path, mode="w")
    name = "a"
    with wrt._get_handle(name, "grn") as handle:
        assert not handle.closed
    # genre not used by default filename template
    assert f"{name}.ext" == Path(handle.name).name
    assert handle.closed


def test_get_handle_exlusive_create(writer_class, tmp_path):
    # genre not used by default filename template
    file = tmp_path / "a.ext"
    with file.open("w") as handle:
        handle.write("")
    wrt = writer_class(destination=tmp_path, mode="x")
    with pytest.raises(FileExistsError):
        with wrt._get_handle("a", "grn"):
            pass  # shouldn't be reached anyway


def test_get_handle_append_no_file(writer_class, tmp_path):
    # genre not used by default filename template
    wrt = writer_class(destination=tmp_path, mode="a")
    with pytest.raises(FileNotFoundError):
        with wrt._get_handle("a", "grn"):
            pass  # shouldn't be reached anyway


def test_not_implemented_write(writer_class, arrays, tmp_path, monkeypatch):
    monkeypatch.setattr(Logger, "warning", Mock())
    wrt = writer_class(tmp_path)
    wrt.write(arrays)
    assert not list(tmp_path.iterdir())
    Logger.warning.assert_called()


def test_implemented_write(writer_implemented, arrays, tmp_path, monkeypatch):
    monkeypatch.setattr(Logger, "warning", Mock())
    wrt = writer_implemented(tmp_path)
    wrt.write(arrays)
    assert len(list(tmp_path.iterdir())) == 7
    assert Logger.warning.call_count == 1  # generic InfoArray not supported


def test_forbidden_double(writer_implemented, tmp_path, forbidden_double_arrays):
    wrt = writer_implemented(tmp_path)
    with pytest.raises(ValueError):
        wrt.write(forbidden_double_arrays)
