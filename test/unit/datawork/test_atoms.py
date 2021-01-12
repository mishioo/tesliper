import pytest
from hypothesis import given, strategies as st
from tesliper.datawork import atoms


# test symbol_of_element
def test_symbol_of_elem_atomic_number_int():
    assert atoms.symbol_of_element(1) == "H"


def test_symbol_of_elem_atomic_number_float():
    assert atoms.symbol_of_element(1.0) == "H"


def test_symbol_of_elem_atomic_number_str():
    assert atoms.symbol_of_element("1") == "H"


def test_symbol_of_elem_not_atomic_number_int():
    with pytest.raises(atoms.InvalidElementError):
        atoms.symbol_of_element(0)


def test_symbol_of_elem_not_atomic_number_float():
    with pytest.raises(ValueError):
        atoms.symbol_of_element(0.5)


def test_symbol_of_elem_not_atomic_number_str():
    with pytest.raises(atoms.InvalidElementError):
        atoms.symbol_of_element("0")


def test_symbol_of_elem_element_symbol():
    assert atoms.symbol_of_element("H") == "H"


def test_symbol_of_elem_element_symbol_lowercase():
    assert atoms.symbol_of_element("he") == "He"


def test_symbol_of_elem_not_element_symbol():
    with pytest.raises(ValueError):
        atoms.symbol_of_element("bla")


# test atomic_number
def test_atomic_number_valid_symbol():
    assert atoms.atomic_number("H") == 1


def test_atomic_number_lowercase_symbol():
    assert atoms.atomic_number("he") == 2


def test_atomic_number_invalid_symbol():
    with pytest.raises(atoms.InvalidElementError):
        atoms.atomic_number("bla")


def test_atomic_number_atomic_number():
    assert atoms.atomic_number(1) == 1


def test_atomic_number_not_atomic_number():
    with pytest.raises(atoms.InvalidElementError):
        atoms.atomic_number(0)


# test validate_atoms
def test_validate_integer():
    assert atoms.validate_atoms(1) == [1]


def test_validate_float():
    assert atoms.validate_atoms(2.0) == [2]


def test_validate_string():
    assert atoms.validate_atoms("B") == [5]


def test_validate_string_with_spaces():
    assert atoms.validate_atoms("H H C") == [1, 1, 6]


def test_validate_list_of_integers():
    assert atoms.validate_atoms([1, 1, 6]) == [1, 1, 6]


def test_validate_list_of_floats():
    assert atoms.validate_atoms([1.0, 6.0]) == [1, 6]


def test_validate_list_of_strings():
    assert atoms.validate_atoms(["H", "H"]) == [1, 1]
