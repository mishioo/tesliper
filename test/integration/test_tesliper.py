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
            listoflists=[[1, 2], [3, 4], [5, 6]],
        ),
        two=dict(
            string="other_value",
            integer=-5,
            floating=0.22,
            listoffloats=[0.4, 0.5, 0.6],
            listoflists=[[3, 4], [5, 6], [7, 8]],
        ),
    )


@pytest.fixture
def teslpier(molecules):
    t = Tesliper()
    t.molecules.update(molecules)
    t.molecules.kept = [0, 1]
    return t


def test_json_serialization(teslpier, molecules, tmp_path):
    jsonfile = tmp_path / "tslr.json"
    teslpier.serialize(jsonfile)
    newt = Tesliper.load(jsonfile)
    assert newt.molecules == molecules
    assert newt.molecules.kept == teslpier.molecules.kept
    assert (
        newt.molecules.allow_data_inconsistency
        == teslpier.molecules.allow_data_inconsistency
    )
