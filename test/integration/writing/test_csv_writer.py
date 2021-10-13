import csv
from itertools import repeat
from pathlib import Path

import numpy as np
import pytest

from tesliper.extraction import Soxhlet
from tesliper.glassware import Conformers, SingleSpectrum, Spectra
from tesliper.glassware import arrays as ar
from tesliper.writing.csv_writer import CsvWriter


@pytest.fixture
def filenames():
    return ["meoh-1", "meoh-2"]


@pytest.fixture
def fixturesdir():
    return Path(__file__).parent.with_name("fixtures")


@pytest.fixture
def mols(filenames, fixturesdir):
    s = Soxhlet(fixturesdir)
    s.wanted_files = filenames
    return Conformers(s.extract())


@pytest.fixture
def spc(filenames):
    return SingleSpectrum(
        "ir",
        [0.3, 0.2, 10, 300, 2],
        [10, 20, 30, 40, 50],
        width=5,
        fitting="gaussian",
        filenames=filenames,
        averaged_by="gib",
    )


@pytest.fixture
def spectra(filenames):
    return Spectra(
        genre="ir",
        values=[[0.3, 0.2, 10, 300, 2], [0.5, 0.8, 12, 150, 5]],
        abscissa=[10, 20, 30, 40, 50],
        width=5,
        fitting="gaussian",
        filenames=filenames,
    )


@pytest.fixture
def writer(tmp_path):
    return CsvWriter(tmp_path)


@pytest.fixture
def gib_with_corr(mols):
    gib = mols.arrayed("gib")
    corr = mols.arrayed("gibcorr")
    return (
        gib,
        corr,
        zip(
            gib.filenames,
            gib.populations,
            gib.min_factors,
            gib.deltas,
            gib.values,
            corr.values,
        ),
    )


@pytest.fixture
def gib_no_corr(mols):
    gib = mols.arrayed("gib")
    return (
        gib,
        zip(
            gib.filenames,
            gib.populations,
            gib.min_factors,
            gib.deltas,
            gib.values,
        ),
    )


def str_or_float(value):
    try:
        return float(value)
    except ValueError:
        return value


def test_non_existent_dialect(tmp_path):
    with pytest.raises(csv.Error):
        CsvWriter(tmp_path, dialect="no-dialect")


def test_fmt_parameter(tmp_path):
    CsvWriter(tmp_path, delimiter=";")


def test_invalid_fmt_parameter(tmp_path):
    with pytest.raises(TypeError):
        CsvWriter(tmp_path, invalidparam="wrong")


def test_energies(writer, gib_with_corr):
    gib, corr, values = gib_with_corr
    writer.energies(gib, corr)
    header = ["Gaussian output file"]
    header += "population min_factor delta energy corrections".split(" ")
    with Path(writer._handle.name).open("r", newline="") as file:
        reader = csv.reader(file)
        assert next(reader) == header
        for given, got in zip(values, reader):
            assert given == tuple(str_or_float(v) for v in got)


def test_energies_no_header(writer, gib_with_corr):
    writer.include_header = False
    gib, corr, values = gib_with_corr
    writer.energies(gib, corr)
    with Path(writer._handle.name).open("r", newline="") as file:
        reader = csv.reader(file)
        for given, got in zip(values, reader):
            assert given == tuple(str_or_float(v) for v in got)


def test_energies_no_corr_no_header(writer, gib_no_corr):
    writer.include_header = False
    gib, values = gib_no_corr
    writer.energies(gib)
    with Path(writer._handle.name).open("r", newline="") as file:
        reader = csv.reader(file)
        for given, got in zip(values, reader):
            assert given == tuple(str_or_float(v) for v in got)


def test_spectrum_no_header(writer, spc):
    writer.include_header = False
    writer.single_spectrum(spc)
    with Path(writer._handle.name).open("r", newline="") as file:
        reader = csv.reader(file)
        for given, got in zip(zip(spc.abscissa, spc.values), reader):
            assert given == tuple(float(v) for v in got)


def test_spectrum(writer, spc):
    writer.single_spectrum(spc)
    header = [spc.units["y"], spc.units["x"]]
    with Path(writer._handle.name).open("r", newline="") as file:
        reader = csv.reader(file)
        assert next(reader) == header
        for given, got in zip(zip(spc.abscissa, spc.values), reader):
            assert given == tuple(float(v) for v in got)


def test_serial_bars(writer, mols):
    freq, bars = mols.arrayed("freq"), [mols.arrayed("iri")]
    writer.spectral_data(freq, bars)
    values = list(zip(freq.values, *[b.values for b in bars]))
    header = [CsvWriter._header[bar.genre] for bar in [freq, *bars]]
    for name, values in zip(freq.filenames, values):
        file = writer.destination.joinpath(name).with_suffix(".freq.csv")
        with file.open("r", newline="") as file:
            reader = csv.reader(file)
            assert next(reader) == header
            for *given, got in zip(*values, reader):
                assert given == [float(v) for v in got]


def test_serial_bars_no_header(writer, mols):
    writer.include_header = False
    freq, bars = mols.arrayed("freq"), [mols.arrayed("iri")]
    writer.spectral_data(freq, bars)
    values = list(zip(freq.values, *[b.values for b in bars]))
    for name, values in zip(freq.filenames, values):
        file = writer.destination.joinpath(name).with_suffix(".freq.csv")
        with file.open("r", newline="") as file:
            reader = csv.reader(file)
            for *given, got in zip(*values, reader):
                assert given == [float(v) for v in got]


def test_serial_spectra(writer, spectra):
    writer.spectra(spectra)
    header = [spectra.units["y"], spectra.units["x"]]
    for name, values in zip(spectra.filenames, spectra.values):
        file = writer.destination.joinpath(name).with_suffix(".ir.csv")
        with file.open("r") as file:
            reader = csv.reader(file)
            assert next(reader) == header
            for line, y, x in zip(reader, spectra.abscissa, values):
                assert [float(v) for v in line] == [y, x]


def test_serial_spectra_no_header(writer, spectra):
    writer.include_header = False
    writer.spectra(spectra)
    for name, values in zip(spectra.filenames, spectra.values):
        file = writer.destination.joinpath(name).with_suffix(".ir.csv")
        with file.open("r") as file:
            reader = csv.reader(file)
            for line, y, x in zip(reader, spectra.abscissa, values):
                assert [float(v) for v in line] == [y, x]


def test_write(writer, mols, filenames):
    data = [mols.arrayed(genre) for genre in ["freq", "iri", "gib", "zpe", "gibcorr"]]
    writer.write(data)
    assert len(list(writer.destination.iterdir())) == len(filenames) + 2


@pytest.fixture
def filenamestd():
    return ["fal-td.out"]


@pytest.fixture
def molstd(filenamestd, fixturesdir):
    s = Soxhlet(fixturesdir)
    s.wanted_files = filenamestd
    return Conformers(s.extract())


def test_serial_transitions_header(writer, molstd):
    trans, wave = molstd.arrayed("transitions"), molstd.arrayed("wavelen")
    writer.transitions(trans, wave, only_highest=True)
    values = list(zip(wave.wavelen, *trans.highest_contribution))
    header = ["wavelength/nm", "ground", "excited", "coefficient", "contribution"]
    for name, values in zip(trans.filenames, values):
        file = writer.destination.joinpath(name).with_suffix(".transitions.csv")
        with file.open("r", newline="") as file:
            reader = csv.reader(file)
            assert next(reader) == header
            for *given, got in zip(*values, reader):
                got = list(map(float, got))
                assert given == got


def test_serial_transitions_only_highest(writer, molstd, filenamestd):
    writer.include_header = False
    trans, wave = molstd.arrayed("transitions"), molstd.arrayed("wavelen")
    writer.transitions(trans, wave, only_highest=True)
    values = list(zip(wave.wavelen, *trans.highest_contribution))
    for name, values in zip(trans.filenames, values):
        file = writer.destination.joinpath(name).with_suffix(".transitions.csv")
        with file.open("r", newline="") as file:
            reader = csv.reader(file)
            for *given, got in zip(*values, reader):
                got = list(map(float, got))
                assert given == got


def test_serial_transitions_all(writer, molstd, filenamestd):
    writer.include_header = False
    trans, wave = molstd.arrayed("transitions"), molstd.arrayed("wavelen")
    writer.transitions(trans, wave, only_highest=False)
    for name, values in zip(trans.filenames, trans.values):
        file = writer.destination.joinpath(name).with_suffix(".transitions.csv")
        with file.open("r", newline="") as file:
            reader = csv.reader(file)
            # TODO: should also check if correct wavelength assigned
            expected_len = values.count()  # count non-masked
            assert len(list(reader)) == expected_len
