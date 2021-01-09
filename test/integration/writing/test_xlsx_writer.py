from pathlib import Path

import pytest
import openpyxl as oxl

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
    wb = oxl.load_workbook(writer.destination)
    assert wb.sheetnames == ["Collective overview"] + [
        XlsxWriter._header[grn] for grn in Energies.associated_genres
    ]
    ws = wb.get_sheet_by_name("Collective overview")
    assert len(list(ws.columns)) == 13
    assert len(list(ws.rows)) == 2 + len(list(mols.keys()))
    for grn in Energies.associated_genres:
        ws = wb.get_sheet_by_name(XlsxWriter._header[grn])
        assert len(list(ws.columns)) == 5
        assert len(list(ws.rows)) == 1 + len(list(mols.keys()))


def test_bars(writer, mols, filenames):
    writer.bars(mols.arrayed("freq"), [mols.arrayed("iri")])
    assert writer.destination.exists()
    wb = oxl.load_workbook(writer.destination)
    assert wb.sheetnames == filenames
    for file in filenames:
        ws = wb.get_sheet_by_name(file)
        assert len(list(ws.columns)) == 2
        assert len(list(ws.rows)) == 1 + mols.arrayed("freq").values.shape[1]


def test_spectra(writer, mols, spectra):
    writer.spectra(spectra)
    assert writer.destination.exists()
    wb = oxl.load_workbook(writer.destination)
    ws = wb.get_sheet_by_name(spectra.genre)
    assert len(list(ws.columns)) == 1 + spectra.filenames.size
    assert len(list(ws.rows)) == 1 + spectra.values.shape[1]


def test_single_spectrum(writer, mols, spc):
    writer.single_spectrum(spc)
    assert writer.destination.exists()
    wb = oxl.load_workbook(writer.destination)
    ws = wb.get_sheet_by_name(f"{spc.genre}_{spc.averaged_by}")
    assert len(list(ws.columns)) == 2
    assert len(list(ws.rows)) == 1 + spc.values.size
