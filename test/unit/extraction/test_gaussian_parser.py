import re

import pytest

from tesliper.extraction import gaussian_parser as gp


@pytest.mark.parametrize(
    "value",
    [
        "1",
        " 1",
        " -1",
        "23",
        "0.2",
        "0.243",
        "123.657",
        "-0.42",
        "-3425.42",
        ".92",
        "-.42",
    ],
)
def test_number_matches(value):
    assert re.search(gp.number, value)


@pytest.mark.xfail
@pytest.mark.parametrize("value", ["-", ".", "- 1", "12-", "42."])
def test_number_not_matches(value):
    assert not re.search(gp.number, value)


@pytest.mark.parametrize(
    "value",
    [
        "3e24",
        "3e-656",
        "3E24",
        "3E-24",
        "-3e24",
        "-3e-656",
        "-3E24",
        "-3E-24",
        "3.23e24",
        "3.23e-656",
        "3.23E24",
        "3.23E-24",
        "-3.23e24",
        "-3.23e-656",
        "-3.23E24",
        "-3.23E-24",
    ],
)
def test_number_sci_matches(value):
    assert re.search(gp.number, value)


@pytest.mark.xfail
@pytest.mark.parametrize(
    "value", ["42e", "42e-", "42.e", "42.e-", "42E", "42E-", "42.E", "42.E-"]
)
def test_number_sci_not_matches(value):
    assert not re.search(gp.number, value)


@pytest.mark.parametrize(
    "line",
    [
        " Stoichiometry    CH4O\n",
        " Stoichiometry    CH4O(1+)\n",
        " Stoichiometry    CH4O(1-)\n",
        " Stoichiometry    CH4O(1+,2)\n",
        " Stoichiometry    CH4O(1-,2)\n",
        " Stoichiometry    CH4O(3)\n",
    ],
)
def test_stoichiometry(line):
    assert gp.STOICH_CRE.match(line)
