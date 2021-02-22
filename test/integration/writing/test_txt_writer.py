from pathlib import Path

import pytest

from tesliper.writing.txt_writer import TxtWriter, TxtSerialWriter
from tesliper.glassware import arrays as ar, SingleSpectrum, Spectra
from tesliper.extraction import Soxhlet
from tesliper.glassware import Molecules


@pytest.fixture
def filenames():
    return ["meoh-1.out", "meoh-2.out"]


@pytest.fixture
def filenamestd():
    return ["fal-td.out"]


@pytest.fixture
def fixturesdir():
    return Path(__file__).parent.with_name("fixtures")


@pytest.fixture
def mols(filenames, fixturesdir):
    s = Soxhlet(fixturesdir)
    s.wanted_files = filenames
    return Molecules(s.extract())


@pytest.fixture
def molstd(filenamestd, fixturesdir):
    s = Soxhlet(fixturesdir)
    s.wanted_files = filenamestd
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
    return TxtWriter(tmp_path.joinpath("overview.txt"))


@pytest.fixture
def serial_writer(tmp_path):
    return TxtSerialWriter(tmp_path)


def test_overview_basic(writer, mols):
    writer.overview(
        [mols.arrayed(grn) for grn in ar.Energies.associated_genres],
        frequencies=mols.arrayed("freq"),
        stoichiometry=mols.arrayed("stoichiometry"),
    )
    with writer.destination.open("r") as outcome:
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


def test_overview_no_freqs(writer, mols):
    writer.overview(
        [mols.arrayed(grn) for grn in ar.Energies.associated_genres],
        stoichiometry=mols.arrayed("stoichiometry"),
    )
    with writer.destination.open("r") as outcome:
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


def test_overview_no_stoichiometry(writer, mols):
    writer.overview(
        [mols.arrayed(grn) for grn in ar.Energies.associated_genres],
        frequencies=mols.arrayed("freq"),
    )
    with writer.destination.open("r") as outcome:
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


def test_energies_basic(writer, mols):
    writer.energies(mols.arrayed("gib"), mols.arrayed("gibcorr"))
    with writer.destination.open("r") as outcome:
        assert (
            outcome.read()
            == """\
Gaussian output file | Population/% | Min.B.Factor | DE/(kcal/mol) | Energy/Hartree | Corr/Hartree
--------------------------------------------------------------------------------------------------
meoh-1.out           |      54.0423 |       1.0000 |        0.0000 |    -113.505977 |     0.038089
meoh-2.out           |      45.9577 |       0.8504 |        0.0960 |    -113.505824 |     0.038105
"""
        )


def test_energies_no_corr(writer, mols):
    writer.energies(mols.arrayed("gib"))
    with writer.destination.open("r") as outcome:
        assert (
            outcome.read()
            == """\
Gaussian output file | Population/% | Min.B.Factor | DE/(kcal/mol) | Energy/Hartree
-----------------------------------------------------------------------------------
meoh-1.out           |      54.0423 |       1.0000 |        0.0000 |    -113.505977
meoh-2.out           |      45.9577 |       0.8504 |        0.0960 |    -113.505824
"""
        )


def test_spectrum_basic(writer, spc):
    writer.spectrum(spc)
    with writer.destination.open("r") as outcome:
        assert (
            outcome.read()
            == """\
ir calculated with peak width = 5 cm-1 and gaussian fitting, shown as Frequency / cm^(-1) vs. Epsilon
2 conformers averaged base on Gibbs
  10.00\t    0.3000
  20.00\t    0.2000
  30.00\t   10.0000
  40.00\t  300.0000
  50.00\t    2.0000"""
        )


def test_spectrum_not_averaged(writer, spc):
    spc.filenames, spc.averaged_by = None, None
    writer.spectrum(spc)
    with writer.destination.open("r") as outcome:
        assert (
            outcome.read()
            == """\
ir calculated with peak width = 5 cm-1 and gaussian fitting, shown as Frequency / cm^(-1) vs. Epsilon
  10.00\t    0.3000
  20.00\t    0.2000
  30.00\t   10.0000
  40.00\t  300.0000
  50.00\t    2.0000"""
        )


def test_serial_bars(serial_writer, mols, filenames):
    serial_writer.bars(mols.arrayed("freq"), [mols.arrayed("iri")])
    assert set(p.name for p in serial_writer.destination.iterdir()) == {
        Path(f).with_suffix(".freq.txt").name for f in filenames
    }
    with serial_writer.destination.joinpath("meoh-1.freq.txt").open("r") as handle:
        cont = handle.read()
    listed = cont.split("\n")
    assert "Frequencies" in listed[0]
    assert "IR Int." in listed[0]
    # len = +2 because of header and empty last line
    assert len(listed) == (len(mols["meoh-1.out"]["freq"]) + 2)


def test_serial_spectra(serial_writer, spectra, filenames):
    serial_writer.spectra(spectra)
    for name, values in zip(spectra.filenames, spectra.values):
        file = serial_writer.destination.joinpath(name).with_suffix(".ir.txt")
        with file.open("r") as f:
            output = f.readlines()
        assert "ir calculated" in output[0]
        assert "width = 5 cm-1" in output[0]
        assert "gaussian fitting" in output[0]
        assert "Frequency / cm^(-1) vs. Epsilon" in output[0]
        for line, y, x in zip(output[1:], spectra.abscissa, values):
            assert [float(v) for v in line.split()] == [y, x]


def test_serial_transitions_only_highest(serial_writer, molstd, filenamestd):
    serial_writer.transitions(
        molstd.arrayed("transitions"), molstd.arrayed("wavelen"), only_highest=True
    )
    output_file_path = serial_writer.destination.joinpath(filenamestd[0])
    output_file_path = output_file_path.with_suffix(".transitions.txt")
    with output_file_path.open("r") as handle:
        cont = iter(handle.readlines())
    assert "of highest contribution" in next(cont)
    assert next(cont).startswith(
        "wavelength: ground -> excited, coefficient, contribution"
    )
    assert not next(cont).strip()
    outs = [
        "326.42 nm: 8 ->  9  0.69982".split(),
        "149.31 nm: 6 ->  9  0.70461".split(),
        "135.60 nm: 7 ->  9  0.68192".split(),
    ]
    for line, out in zip(cont, outs):
        out += [f"{2 * float(out[-1]) ** 2:.0%}"]
        assert line.split() == out


def test_serial_transitions_all(serial_writer, molstd, filenamestd):
    serial_writer.transitions(
        molstd.arrayed("transitions"), molstd.arrayed("wavelen"), only_highest=False
    )
    output_file_path = serial_writer.destination.joinpath(filenamestd[0])
    output_file_path = output_file_path.with_suffix(".transitions.txt")
    with output_file_path.open("r") as handle:
        cont = iter(handle.readlines())
    assert "contributing" in next(cont)
    assert next(cont).startswith(
        "wavelength: ground -> excited, coefficient, contribution"
    )
    assert not next(cont).strip()
    outs = [
        "326.42 nm: 5 ->  9  0.10410".split(),
        "           8 ->  9  0.69982".split(),
        "149.31 nm: 6 ->  9  0.70461".split(),
        "135.60 nm: 6 -> 12  0.12121".split(),
        "           7 ->  9  0.68192".split(),
        "           8 -> 11 -0.11535".split(),
    ]
    for line, out in zip(cont, outs):
        out += [f"{2 * float(out[-1]) ** 2:.0%}"]
        assert line.split() == out
