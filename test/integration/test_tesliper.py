from itertools import chain
from pathlib import Path

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
    extracted.extract()
    return extracted


@pytest.fixture
def calculated(extracted):
    extracted.conformers.kept = [False, True]
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


@pytest.mark.xfail(reason="Can't compare Spectra objects for equality.")
def test_serialization_spectra(calculated, tmp_path):
    resurrected = resurect(calculated, tmp_path)
    assert resurrected.spectra == calculated.spectra


@pytest.mark.xfail(reason="Can't compare Spectra objects for equality.")
def test_serialization_averaged(averaged, tmp_path):
    resurrected = resurect(averaged, tmp_path)
    assert resurrected.averaged == averaged.averaged


@pytest.mark.xfail(reason="Not implemented yet.")
def test_serialization_experimental(experimental, tmp_path):
    resurrected = resurect(experimental, tmp_path)
    assert resurrected.experimental == experimental.experimental
