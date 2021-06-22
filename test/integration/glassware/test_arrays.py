from pathlib import Path

import pytest
import numpy as np

from tesliper import Tesliper, glassware as gw


FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="session")
def transitions():
    tslr = Tesliper(input_dir=FIXTURES, wanted_files=["fal-td.out"])
    tslr.extract()
    return tslr.conformers.arrayed("transitions")


def test_transitions_init(transitions):
    assert isinstance(transitions, gw.Transitions)


def test_transitions_values(transitions):
    np.testing.assert_array_equal(
        transitions.ground, [[[5, 8, 0], [6, 0, 0], [6, 7, 8]]]
    )
    np.testing.assert_array_equal(
        transitions.excited, [[[9, 9, 0], [9, 0, 0], [12, 9, 11]]]
    )
    np.testing.assert_array_equal(
        transitions.values,
        [[[0.10410, 0.69982, 0], [0.70461, 0, 0], [0.12121, 0.68192, -0.11535]]],
    )


def test_transitions_indices_highest(transitions):
    np.testing.assert_array_equal(
        transitions.values.max(axis=2), transitions.values[transitions.indices_highest]
    )
