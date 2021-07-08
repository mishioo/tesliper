from collections import OrderedDict

import pytest

from tesliper import Tesliper


@pytest.fixture
def molecules():
    return OrderedDict(
        one=dict(
            string="some_value",
            integer=42,
            floating=0.73,
            listoffloats=[0.1, 0.2, 0.3],
            listoftuples=[(1, 2), (3, 4), (5, 6)],
        ),
        two=dict(
            string="other_value",
            integer=-5,
            floating=0.22,
            listoffloats=[0.4, 0.5, 0.6],
            listoftuples=[(3, 4), (5, 6), (7, 8)],
        ),
    )


@pytest.fixture
def teslpier(tmp_path, molecules):
    t = Tesliper(output_dir=tmp_path)
    t.conformers.update(molecules)
    t.conformers.kept = [0, 1]
    return t


def test_json_serialization(teslpier, molecules, tmp_path):
    file = ".tslr"
    path = tmp_path / file
    teslpier.serialize(file)
    newt = Tesliper.load(path)
    assert newt.conformers == molecules
    assert newt.conformers.kept == teslpier.conformers.kept
    assert (
        newt.conformers.allow_data_inconsistency
        == teslpier.conformers.allow_data_inconsistency
    )
