from pathlib import Path

import pytest

from tesliper import Energies
from tesliper.writing.xlsx_writer import XlsxWriter
from tesliper.glassware import SingleSpectrum, Spectra
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
    return XlsxWriter(tmp_path.joinpath("output.xlsx"))


def test_energies(writer, mols):
    writer.energies(
        [mols.arrayed(grn) for grn in Energies.associated_genres],
        frequencies=mols.arrayed("freq"),
        stoichiometry=mols.arrayed("stoichiometry"),
    )
    assert writer.destination.exists()


def test_bars(writer, mols):
    writer.bars(mols.arrayed("freq"), [mols.arrayed("iri")])
    assert writer.destination.exists()


def test_spectra(writer, mols, spectra):
    writer.spectra(spectra)
    assert writer.destination.exists()


def test_single_spectrum(writer, mols, spc):
    writer.single_spectrum(spc)
    assert writer.destination.exists()
