from typing import Union, List
import numpy as np
from ..exceptions import InvalidElementError

atomicnums = {
    "H": 1,
    "He": 2,
    "Li": 3,
    "Be": 4,
    "B": 5,
    "C": 6,
    "N": 7,
    "O": 8,
    "F": 9,
    "Ne": 10,
    "Na": 11,
    "Mg": 12,
    "Al": 13,
    "Si": 14,
    "P": 15,
    "S": 16,
    "Cl": 17,
    "Ar": 18,
    "K": 19,
    "Ca": 20,
    "Sc": 21,
    "Ti": 22,
    "V": 23,
    "Cr": 24,
    "Mn": 25,
    "Fe": 26,
    "Co": 27,
    "Ni": 28,
    "Cu": 29,
    "Zn": 30,
    "Ga": 31,
    "Ge": 32,
    "As": 33,
    "Se": 34,
    "Br": 35,
    "Kr": 36,
    "Rb": 37,
    "Sr": 38,
    "Y": 39,
    "Zr": 40,
    "Nb": 41,
    "Mo": 42,
    "Tc": 43,
    "Ru": 44,
    "Rh": 45,
    "Pd": 46,
    "Ag": 47,
    "Cd": 48,
    "In": 49,
    "Sn": 50,
    "Sb": 51,
    "Te": 52,
    "I": 53,
    "Xe": 54,
    "Cs": 55,
    "Ba": 56,
    "La": 57,
    "Ce": 58,
    "Pr": 59,
    "Nd": 60,
    "Pm": 61,
    "Sm": 62,
    "Eu": 63,
    "Gd": 64,
    "Tb": 65,
    "Dy": 66,
    "Ho": 67,
    "Er": 68,
    "Tm": 69,
    "Yb": 70,
    "Lu": 71,
    "Hf": 72,
    "Ta": 73,
    "W": 74,
    "Re": 75,
    "Os": 76,
    "Ir": 77,
    "Pt": 78,
    "Au": 79,
    "Hg": 80,
    "Tl": 81,
    "Pb": 82,
    "Bi": 83,
    "Po": 84,
    "At": 85,
    "Rn": 86,
    "Fr": 87,
    "Ra": 88,
    "Ac": 89,
    "Th": 90,
    "Pa": 91,
    "U": 92,
    "Np": 93,
    "Pu": 94,
    "Am": 95,
    "Cm": 96,
    "Bk": 97,
    "Cf": 98,
    "Es": 99,
    "Fm": 100,
    "Md": 101,
    "No": 102,
    "Lr": 103,
    "Rf": 104,
    "Db": 105,
    "Sg": 106,
    "Bh": 107,
    "Hs": 108,
    "Mt": 109,
    "Ds": 110,
    "Rg": 111,
    "Cn": 112,
    "Uut": 113,
    "Fl": 114,
    "Uup": 115,
    "Lv": 116,
    "Uus": 117,
    "Uuo": 118,
}
atoms_symbols = {v: k for k, v in atomicnums.items()}


def symbol_of_element(element: Union[int, str]) -> str:
    """Returns symbol of given element. If `element` is a symbol of an element
    already, it is capitalized and returned (so input's letters case doesn't
    matter).

    Parameters
    ----------
    element: int or str
        element's atomic number

    Returns
    -------
    str
        symbol of an element

    Raises
    ------
    ValueError
        when `element` is not a whole number or cannot be converted to integer
    TypeError
        if `element` cannot be interpreted as integer
    InvalidElementError
        if `element` is not an atomic number of any known element"""
    stringified = str(element).capitalize()
    if stringified in atomicnums:
        return stringified
    try:
        integerized = int(element)
    except ValueError as exc:
        if isinstance(element, str):
            raise ValueError(f"Cannot convert element {element} to integer.") from exc
        raise TypeError(
            f'Type "{type(element)}" cannot be interpreted as integer.'
        ) from exc
    if isinstance(element, float) and not element == integerized:
        raise ValueError(
            f"Element's atomic number should be a whole number, " f"{element} given."
        )
    elif integerized in atoms_symbols:
        return atoms_symbols[integerized]
    else:
        raise InvalidElementError(f"Unknown element: {element}")


def atomic_number(element: Union[int, str]) -> int:
    """Returns atomic number of given element. If `element` is an atomic number
    already, it is returned without change.

    Parameters
    ----------
    element: str or int
        element's symbol or atomic number (letters case doesn't matter if
        string is given)

    Returns
    -------
    int
        atomic number of an element

    Raises
    ------
    InvalidElementError
        when `element` cannot be converted to element's atomic number
    TypeError
        if `element` cannot be interpreted as integer or string"""
    stringified = str(element).capitalize()
    if stringified in atomicnums:
        return atomicnums[stringified]
    elif element in atoms_symbols:
        return element
    elif isinstance(element, (str, int, float, np.str, np.integer, np.float)):
        raise InvalidElementError(f"Unknown element: {element}")
    else:
        raise TypeError(f"Expected str or int, got '{type(element)}'.")


def validate_atoms(atoms: Union[int, str, List[int, str]]) -> List[int]:
    """Checks if given `atoms` represent a list of valid atom identifiers
    (symbols or atomic numbers). Returns list of atomic numbers of those atoms
    if it does or rises an exception if it doesn't.

    Parameters
    ----------
    atoms: int, str or iterable of int or str
        Atoms to validate. Atoms as space-separated string are also accepted.

    Returns
    -------
    list of int
        List of given atoms' atomic numbers.

    Rises
    -----
    InvalidElementError
        if `atoms` cannot be interpreted as list of atoms' identifiers"""
    if isinstance(atoms, (str, np.str)):
        atoms = atoms.split()
    elif isinstance(atoms, (int, np.integer, float, np.float)):
        atoms = [atoms]
    try:
        return [atomic_number(a) for a in atoms]
    except (InvalidElementError, TypeError) as exc:
        raise InvalidElementError(
            f"Cannot interpret {atoms} as list of atoms' identifiers."
        ) from exc
