"""Converters between string and integer representations of atoms."""

from enum import IntEnum
from typing import List, Union

import numpy as np

from ..exceptions import InvalidElementError

_atoms = (
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu "
    "Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba "
    "La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb "
    "Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt "
    "Ds Rg Cn Nh Fl Mc Lv Ts Og"
)
atomicnums = {at: num + 1 for num, at in enumerate(_atoms.split())}
atoms_symbols = {v: k for k, v in atomicnums.items()}
Atom = IntEnum("Atom", _atoms)
Atom.__doc__ = """An enumeration that maps symbols of atoms to respective atomic numbers.

This enumeration is introduced for your convenience: whenever you need to reference
an atom by its atomic number, you may use appropriate symbol-value of this Enum instead.
Providing e.g. `Atom.Au` rather than an integer 79 for Au's atomic number is probably
a bit easier and definitely more readable.
"""


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
    except (ValueError, TypeError) as exc:
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
    elif isinstance(element, (str, int, float, np.str_, np.integer, np.float64)):
        raise InvalidElementError(f"Unknown element: {element}")
    else:
        raise TypeError(f"Expected str or int, got '{type(element)}'.")


def validate_atoms(atoms: Union[int, str, List[Union[int, str]]]) -> List[int]:
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
    if isinstance(atoms, (str, np.str_)):
        atoms = atoms.split()
    elif isinstance(atoms, (int, np.integer, float, np.float64)):
        atoms = [atoms]
    try:
        return [atomic_number(a) for a in atoms]
    except (InvalidElementError, TypeError) as exc:
        raise InvalidElementError(
            f"Cannot interpret {atoms} as list of atoms' identifiers."
        ) from exc
