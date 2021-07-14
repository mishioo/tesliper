from pathlib import Path

import pytest

from tesliper import Tesliper

fixtures_dir = Path(__file__).parent / "fixtures"


@pytest.fixture
def wanted_files():
    return ["meoh-1.out", "meoh-2.out"]


@pytest.fixture
def teslpier(tmp_path, wanted_files):
    t = Tesliper(
        input_dir=fixtures_dir,
        output_dir=tmp_path,
        wanted_files=["meoh-1.out", "meoh-2.out"],
    )
    t.extract()
    t.calculate_spectra(["ir"])
    t.average_spectra()
    t.conformers.kept = [False, True]
    return t


@pytest.mark.xfail(reason="Can't compare for parameters and Spectra objects equality.")
def test_json_serialization(teslpier, tmp_path):
    file = ".tslr"
    path = tmp_path / file
    teslpier.serialize(file)
    newt = Tesliper.load(path)
    assert newt.conformers == teslpier.conformers
    assert newt.conformers.kept == teslpier.conformers.kept
    assert (
        newt.conformers.allow_data_inconsistency
        == teslpier.conformers.allow_data_inconsistency
    )
    assert newt.wanted_files == teslpier.wanted_files
    assert newt.input_dir == teslpier.input_dir
    assert newt.output_dir == teslpier.output_dir
    assert newt.spectra == teslpier.spectra
    assert newt.averaged == teslpier.averaged
