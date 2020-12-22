import csv
from pathlib import Path

import pytest

from tesliper.writing.csv_writer import CsvWriter, CsvSerialWriter
from tesliper.glassware import arrays as ar, SingleSpectrum, Spectra
from tesliper.extraction import Soxhlet
from tesliper.glassware import Molecules


@pytest.fixture
def filenames():
    return ["meoh-1.out", "meoh-2.out"]


@pytest.fixture
def fixturesdir():
    return Path(__file__).parent.with_name("fixtures")


@pytest.fixture
def mols(filenames, fixturesdir):
    s = Soxhlet(fixturesdir)
    s.wanted_files = filenames
    return Molecules(s.extract())


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
    return CsvWriter(tmp_path.joinpath("test.scv"))


@pytest.fixture
def serial_writer(tmp_path):
    return CsvSerialWriter(tmp_path)


@pytest.fixture
def gib_with_corr(mols):
    gib = mols.arrayed('gib')
    corr = mols.arrayed('gibcorr')
    return gib, corr, zip(
        gib.filenames,
        gib.populations,
        gib.min_factors,
        gib.deltas,
        gib.values,
        corr.values,
    )


@pytest.fixture
def gib_no_corr(mols):
    gib = mols.arrayed('gib')
    return gib, zip(
        gib.filenames,
        gib.populations,
        gib.min_factors,
        gib.deltas,
        gib.values,
    )


def str_or_float(value):
    try:
        return float(value)
    except ValueError:
        return value


def test_non_existent_dialect(tmp_path):
    with pytest.raises(csv.Error):
        CsvWriter(tmp_path.joinpath("test.scv"), dialect="no-dialect")


def test_energies(writer, gib_with_corr):
    gib, corr, values = gib_with_corr
    writer.energies(gib, corr)
    header = ["Gaussian output file"]
    header += "population min_factor delta energy corrections".split(" ")
    with writer.destination.open('r', newline='') as file:
        reader = csv.reader(file)
        assert next(reader) == header
        for given, got in zip(values, reader):
            assert given == tuple(str_or_float(v) for v in got)


def test_energies_no_header(writer, gib_with_corr):
    gib, corr, values = gib_with_corr
    writer.energies(gib, corr, include_header=False)
    with writer.destination.open('r', newline='') as file:
        reader = csv.reader(file)
        for given, got in zip(values, reader):
            assert given == tuple(str_or_float(v) for v in got)


def test_energies_no_corr_no_header(writer, gib_no_corr):
    gib, values = gib_no_corr
    writer.energies(gib, include_header=False)
    with writer.destination.open('r', newline='') as file:
        reader = csv.reader(file)
        for given, got in zip(values, reader):
            assert given == tuple(str_or_float(v) for v in got)


def test_spectrum(writer, spc):
    writer.spectrum(spc)
    with writer.destination.open('r', newline='') as file:
        reader = csv.reader(file)
        for given, got in zip(zip(spc.abscissa, spc.values), reader):
            assert given == tuple(float(v) for v in got)


@pytest.mark.xfail(reason="Not supported yet")
def test_spectrum_with_header(writer, spc):
    writer.spectrum(spc, include_header=True)
    header = [spc.units['y'], spc.units['x']]
    with writer.destination.open('r', newline='') as file:
        reader = csv.reader(file)
        assert next(reader) == header
        for given, got in zip(zip(spc.abscissa, spc.values), reader):
            assert given == tuple(float(v) for v in got)


def test_serial_bars(serial_writer, mols):
    freq, bars = mols.arrayed("freq"), [mols.arrayed("iri")]
    serial_writer.bars(freq, bars)
    values = list(zip(freq.values, *[b.values for b in bars]))
    header = [CsvSerialWriter._header[bar.genre] for bar in [freq, *bars]]
    for name, values in zip(freq.filenames, values):
        file = serial_writer.destination.joinpath(name).with_suffix('.freq.csv')
        with file.open('r', newline='') as file:
            reader = csv.reader(file)
            assert next(reader) == header
            for *given, got in zip(*values, reader):
                assert given == [float(v) for v in got]


def test_serial_bars_no_header(serial_writer, mols):
    freq, bars = mols.arrayed("freq"), [mols.arrayed("iri")]
    serial_writer.bars(freq, bars, include_header=False)
    values = list(zip(freq.values, *[b.values for b in bars]))
    for name, values in zip(freq.filenames, values):
        file = serial_writer.destination.joinpath(name).with_suffix('.freq.csv')
        with file.open('r', newline='') as file:
            reader = csv.reader(file)
            for *given, got in zip(*values, reader):
                assert given == [float(v) for v in got]


@pytest.mark.xfail(reason="Not supported yet")
def test_serial_spectra(serial_writer, spectra):
    serial_writer.spectra(spectra)
    header = ''
    for name, values in zip(spectra.filenames, spectra.values):
        file = serial_writer.destination.joinpath(name).with_suffix('.ir.csv')
        with file.open('r') as file:
            reader = csv.reader(file)
            assert next(reader) == header
            for line, y, x in zip(reader, spectra.abscissa, values):
                assert [float(v) for v in line] == [y, x]


def test_serial_spectra_no_header(serial_writer, spectra):
    serial_writer.spectra(spectra, include_header=False)
    for name, values in zip(spectra.filenames, spectra.values):
        file = serial_writer.destination.joinpath(name).with_suffix('.ir.csv')
        with file.open('r') as file:
            reader = csv.reader(file)
            for line, y, x in zip(reader, spectra.abscissa, values):
                assert [float(v) for v in line] == [y, x]
