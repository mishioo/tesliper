from itertools import chain
from pathlib import Path

import numpy as np
import pytest

from tesliper import Tesliper

fixtures_dir = Path(__file__).parent / "fixtures"


@pytest.fixture
def wanted_files():
    return ["meoh-1.out", "meoh-2.out"]


@pytest.fixture
def tesliper(tmp_path, wanted_files):
    return Tesliper(
        input_dir=fixtures_dir, output_dir=tmp_path, wanted_files=wanted_files
    )


@pytest.fixture
def inconsistent(tesliper):
    tesliper.allow_data_inconsistency = True
    return tesliper


@pytest.fixture
def extracted(tesliper):
    tesliper.extract()
    return tesliper


@pytest.fixture
def trimmed(extracted):
    extracted.conformers.kept = [False, True]
    return extracted


@pytest.fixture
def calculated(extracted):
    extracted.calculate_spectra(["iri"])
    return extracted


@pytest.fixture
def averaged(calculated):
    calculated.average_spectra()
    return calculated


def resurect(tesliper, path):
    file = path / ".tslr"
    tesliper.serialize(file)
    return Tesliper.load(file)


def test_serialization_init_params(tesliper, tmp_path):
    resurrected = resurect(tesliper, tmp_path)
    assert resurrected.wanted_files == tesliper.wanted_files
    assert resurrected.input_dir == tesliper.input_dir
    assert resurrected.output_dir == tesliper.output_dir


def test_serialization_calc_params(tesliper, tmp_path):
    resurrected = resurect(tesliper, tmp_path)
    old_params = {key: params.copy() for key, params in tesliper.parameters.items()}
    new_params = {key: params.copy() for key, params in resurrected.parameters.items()}
    for params in chain(old_params.values(), new_params.values()):
        params["fitting"] = params["fitting"].__name__
    assert new_params == old_params


def test_serialization_conformers(extracted, tmp_path):
    resurrected = resurect(extracted, tmp_path)
    assert resurrected.conformers == extracted.conformers


def test_serialization_trimmed(trimmed, tmp_path):
    resurrected = resurect(trimmed, tmp_path)
    assert resurrected.conformers.kept == trimmed.conformers.kept


def test_serialization_inconsistent(inconsistent, tmp_path):
    resurrected = resurect(inconsistent, tmp_path)
    assert (
        resurrected.conformers.allow_data_inconsistency
        == inconsistent.conformers.allow_data_inconsistency
    )


def assert_spectra_equal(new, old):
    for key, value in new.__dict__.items():
        if not isinstance(value, np.ndarray):
            assert value == getattr(old, key)
        else:
            assert np.array(value == getattr(old, key)).all()


def test_serialization_spectra(calculated, tmp_path):
    resurrected = resurect(calculated, tmp_path)
    for genre, spc in resurrected.spectra.items():
        assert_spectra_equal(spc, calculated.spectra[genre])


def test_serialization_averaged(averaged, tmp_path):
    resurrected = resurect(averaged, tmp_path)
    for key, spc in resurrected.averaged.items():
        assert_spectra_equal(spc, averaged.averaged[key])


@pytest.mark.xfail(reason="Not implemented yet.")
def test_serialization_experimental(experimental, tmp_path):
    resurrected = resurect(experimental, tmp_path)
    assert resurrected.experimental == experimental.experimental


def test_export_data(averaged, wanted_files):
    averaged.export_data(["iri", "scf"])
    files = list(averaged.output_dir.iterdir())
    expected = {
        Path(f).with_suffix(".activities-vibrational").name for f in wanted_files
    }
    expected.update({"overview", "distribution-scf"})
    assert {f.stem for f in files} == expected


def test_export_data_empty(averaged):
    averaged.export_data(["rot", "gib"])
    files = list(averaged.output_dir.iterdir())
    expected = {"overview", "distribution-gib"}
    assert {f.stem for f in files} == expected


@pytest.mark.parametrize("fmt", ["txt", "csv", "xlsx"])
def test_export_energies(extracted, fmt):
    extracted.export_energies(fmt=fmt)
    files = list(extracted.output_dir.iterdir())
    expected = {f"distribution-{e}" for e in ("gib", "ent", "zpe", "ten", "scf")}
    if fmt == "xlsx":
        assert len(files) == 1
        assert files[0].suffix == ".xlsx"
    elif fmt == "txt":
        expected.add("overview")
        assert {f.stem for f in files} == expected
    elif fmt == "csv":
        assert {f.stem for f in files} == expected


@pytest.mark.parametrize("fmt", ["txt", "csv", "xlsx"])
def test_export_spectral_data(extracted, fmt, wanted_files):
    extracted.export_spectral_data(fmt=fmt)
    files = list(extracted.output_dir.iterdir())
    if fmt == "xlsx":
        assert len(files) == 1
        assert files[0].suffix == ".xlsx"
    elif fmt == "txt":
        expected = {
            Path(f).with_suffix(f".data-{t}").name
            for f in wanted_files
            for t in ("vibrational", "scattering")
        }
        assert {f.stem for f in files} == expected


@pytest.mark.parametrize("fmt", ["txt", "csv", "xlsx"])
def test_export_activities(extracted, fmt, wanted_files):
    extracted.export_activities(fmt=fmt)
    files = list(extracted.output_dir.iterdir())
    if fmt == "xlsx":
        assert len(files) == 1
        assert files[0].suffix == ".xlsx"
    else:
        expected = {
            Path(f).with_suffix(f".activities-{t}").name
            for f in wanted_files
            for t in ("vibrational", "scattering")
        }
        assert {f.stem for f in files} == expected


@pytest.mark.parametrize("fmt", ["txt", "csv", "xlsx"])
def test_export_spectra(calculated, fmt, wanted_files):
    calculated.export_spectra(fmt=fmt)
    files = list(calculated.output_dir.iterdir())
    if fmt == "xlsx":
        assert len(files) == 1
        assert files[0].suffix == ".xlsx"
    else:
        assert {f.stem for f in files} == {
            Path(f).with_suffix(".ir").name for f in wanted_files
        }


@pytest.mark.parametrize("fmt", ["txt", "csv", "xlsx"])
def test_export_averaged(averaged, fmt):
    averaged.export_averaged(fmt=fmt)
    files = list(averaged.output_dir.iterdir())
    if fmt == "xlsx":
        assert len(files) == 1
        assert files[0].suffix == ".xlsx"
    else:
        assert {f.stem for f in files} == {
            f"spectrum.ir-{e}" for e in ("gib", "ent", "zpe", "ten", "scf")
        }


def test_export_job_file(extracted, wanted_files):
    extracted.export_job_file()
    files = list(extracted.output_dir.iterdir())
    assert {f.name for f in files} == {
        Path(f).with_suffix(".gjf").name for f in wanted_files
    }
