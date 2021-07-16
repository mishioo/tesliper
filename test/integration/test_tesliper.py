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
    # FIXME: no relevant spectral data in test set, returns empty Spectra object
    extracted.calculate_spectra(["ir"])
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


def test_serialization_spectra(calculated, tmp_path):
    resurrected = resurect(calculated, tmp_path)
    for genre, spc in resurrected.spectra.items():
        for key, value in spc.__dict__.items():
            if not isinstance(value, np.ndarray):
                assert value == calculated.spectra[genre].__dict__[key]
            else:
                assert np.array(value == calculated.spectra[genre].__dict__[key]).all()


def test_serialization_averaged(averaged, tmp_path):
    resurrected = resurect(averaged, tmp_path)
    for genre, spc in resurrected.averaged.items():
        for key, value in spc.__dict__.items():
            if not isinstance(value, np.ndarray):
                assert value == averaged.averaged[genre].__dict__[key]
            else:
                assert np.array(value == averaged.averaged[genre].__dict__[key]).all()


@pytest.mark.xfail(reason="Not implemented yet.")
def test_serialization_experimental(experimental, tmp_path):
    resurrected = resurect(experimental, tmp_path)
    assert resurrected.experimental == experimental.experimental
