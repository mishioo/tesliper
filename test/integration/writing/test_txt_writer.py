from pathlib import Path

import pytest

from tesliper.writing.txt_writer import TxtOverviewWriter
from tesliper.glassware import arrays as ar
from tesliper.extraction import Soxhlet
from tesliper.glassware import Molecules


@pytest.fixture
def filenames():
    return ["meoh-1.out", "meoh-2.out"]


@pytest.fixture
def fixturesdir():
    return Path().joinpath("../fixtures")


@pytest.fixture
def mols(filenames, fixturesdir):
    s = Soxhlet(fixturesdir)
    s.wanted_files = filenames
    return Molecules(s.extract())


@pytest.fixture
def overview_writer(tmp_path):
    return TxtOverviewWriter(tmp_path.joinpath("overview.txt"))


def test_overview_basic(overview_writer, mols):
    overview_writer.write(
        [mols.arrayed(grn) for grn in ar.Energies.associated_genres],
        frequencies=mols.arrayed("freq"),
        stoichiometry=mols.arrayed("stoichiometry"),
    )
    with overview_writer.destination.open("r") as outcome:
        assert (
            outcome.read()
            == """\
Gaussian output file |                   Population / %                   |                            Energy / Hartree                            | Imag | Stoichiometry
                     | SCF       Zero-point  Thermal   Enthalpy  Gibbs    | SCF             Zero-point    Thermal       Enthalpy      Gibbs        |      |              
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------
meoh-1.out           |  53.6047     54.0160   54.0160   54.0160   54.0423 |  -113.54406542   -113.483474   -113.480579   -113.479635   -113.505977 |   1  | CH4O         
meoh-2.out           |  46.3953     45.9840   45.9840   45.9840   45.9577 |  -113.54392904   -113.483322   -113.480427   -113.479483   -113.505824 |   1  | CH4O         
"""
        )


def test_overview_no_freqs(overview_writer, mols):
    overview_writer.write(
        [mols.arrayed(grn) for grn in ar.Energies.associated_genres],
        stoichiometry=mols.arrayed("stoichiometry"),
    )
    with overview_writer.destination.open("r") as outcome:
        assert (
            outcome.read()
            == """\
Gaussian output file |                   Population / %                   |                            Energy / Hartree                            | Stoichiometry
                     | SCF       Zero-point  Thermal   Enthalpy  Gibbs    | SCF             Zero-point    Thermal       Enthalpy      Gibbs        |              
------------------------------------------------------------------------------------------------------------------------------------------------------------------
meoh-1.out           |  53.6047     54.0160   54.0160   54.0160   54.0423 |  -113.54406542   -113.483474   -113.480579   -113.479635   -113.505977 | CH4O         
meoh-2.out           |  46.3953     45.9840   45.9840   45.9840   45.9577 |  -113.54392904   -113.483322   -113.480427   -113.479483   -113.505824 | CH4O         
"""
        )


def test_overview_no_stoichiometry(overview_writer, mols):
    overview_writer.write(
        [mols.arrayed(grn) for grn in ar.Energies.associated_genres],
        frequencies=mols.arrayed("freq"),
    )
    with overview_writer.destination.open("r") as outcome:
        assert (
            outcome.read()
            == """\
Gaussian output file |                   Population / %                   |                            Energy / Hartree                            | Imag
                     | SCF       Zero-point  Thermal   Enthalpy  Gibbs    | SCF             Zero-point    Thermal       Enthalpy      Gibbs        |     
---------------------------------------------------------------------------------------------------------------------------------------------------------
meoh-1.out           |  53.6047     54.0160   54.0160   54.0160   54.0423 |  -113.54406542   -113.483474   -113.480579   -113.479635   -113.505977 |   1 
meoh-2.out           |  46.3953     45.9840   45.9840   45.9840   45.9577 |  -113.54392904   -113.483322   -113.480427   -113.479483   -113.505824 |   1 
"""
        )


def test_energies_basic(overview_writer, mols):
    overview_writer.energies(mols.arrayed("gib"), mols.arrayed("gibcorr"))
    with overview_writer.destination.open("r") as outcome:
        assert (
            outcome.read()
            == """\
Gaussian output file | Population/% | Min.B.Factor | DE/(kcal/mol) | Energy/Hartree | Corr/Hartree
--------------------------------------------------------------------------------------------------
meoh-1.out           |      54.0423 |       1.0000 |        0.0000 |    -113.505977 |     0.038089
meoh-2.out           |      45.9577 |       0.8504 |        0.0960 |    -113.505824 |     0.038105
"""
        )


def test_energies_no_corr(overview_writer, mols):
    overview_writer.energies(mols.arrayed("gib"))
    with overview_writer.destination.open("r") as outcome:
        assert (
            outcome.read()
            == """\
Gaussian output file | Population/% | Min.B.Factor | DE/(kcal/mol) | Energy/Hartree
-----------------------------------------------------------------------------------
meoh-1.out           |      54.0423 |       1.0000 |        0.0000 |    -113.505977
meoh-2.out           |      45.9577 |       0.8504 |        0.0960 |    -113.505824
"""
        )
