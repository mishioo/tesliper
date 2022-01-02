import re

import pytest

from tesliper.extraction import gaussian_parser as gp


def test_number_matches():
    assert re.search(gp.number, "1")
    assert re.search(gp.number, " 1")
    assert re.search(gp.number, " -1")
    assert re.search(gp.number, "23")
    assert re.search(gp.number, "0.2")
    assert re.search(gp.number, "0.243")
    assert re.search(gp.number, "123.657")
    assert re.search(gp.number, "-0.42")
    assert re.search(gp.number, "-3425.42")
    assert re.search(gp.number, ".92")
    assert re.search(gp.number, "-.42")


@pytest.mark.xfail
def test_number_not_matches():
    assert not re.search(gp.number, "-")
    assert not re.search(gp.number, ".")
    assert not re.search(gp.number, "- 1")  # matches :(
    assert not re.search(gp.number, "12-")
    assert not re.search(gp.number, "42.")


def test_number_sci_matches():
    assert re.search(gp.number, "3e24")
    assert re.search(gp.number, "3e-656")
    assert re.search(gp.number, "3E24")
    assert re.search(gp.number, "3E-24")
    assert re.search(gp.number, "-3e24")
    assert re.search(gp.number, "-3e-656")
    assert re.search(gp.number, "-3E24")
    assert re.search(gp.number, "-3E-24")
    assert re.search(gp.number, "3.23e24")
    assert re.search(gp.number, "3.23e-656")
    assert re.search(gp.number, "3.23E24")
    assert re.search(gp.number, "3.23E-24")
    assert re.search(gp.number, "-3.23e24")
    assert re.search(gp.number, "-3.23e-656")
    assert re.search(gp.number, "-3.23E24")
    assert re.search(gp.number, "-3.23E-24")


@pytest.mark.xfail
def test_number_sci_not_matches():
    assert not re.search(gp.number, "42e")
    assert not re.search(gp.number, "42e-")
    assert not re.search(gp.number, "42.e")
    assert not re.search(gp.number, "42.e-")
    assert not re.search(gp.number, "42E")
    assert not re.search(gp.number, "42E-")
    assert not re.search(gp.number, "42.E")
    assert not re.search(gp.number, "42.E-")


def test_command():
    assert re.search(
        gp.command,
        " ------------------------------------------\n"
        " #P td=(singlets,nstates=80) B3LYP/Def2TZVP\n"
        " ------------------------------------------\n",
    )
    assert re.search(
        gp.command,
        " -------------------------\n"
        " # opt freq wB97xd/6-31G**\n"
        " -------------------------\n",
    )


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
    assert gp.STOICHCRE.match(line)
