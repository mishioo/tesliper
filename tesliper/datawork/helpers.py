import numpy as np
from collections.abc import Iterable
from ..exceptions import InvalidElementError

_atomicnum = {
    'H': 1, 'He': 2, 'Li': 3, 'Be': 4, 'B': 5, 'C': 6, 'N': 7, 'O': 8,
    'F': 9, 'Ne': 10, 'Na': 11, 'Mg': 12, 'Al': 13, 'Si': 14, 'P': 15,
    'S': 16, 'Cl': 17, 'Ar': 18, 'K': 19, 'Ca': 20, 'Sc': 21, 'Ti': 22,
    'V': 23, 'Cr': 24, 'Mn': 25, 'Fe': 26, 'Co': 27, 'Ni': 28, 'Cu': 29,
    'Zn': 30, 'Ga': 31, 'Ge': 32, 'As': 33, 'Se': 34, 'Br': 35, 'Kr': 36,
    'Rb': 37, 'Sr': 38, 'Y': 39, 'Zr': 40, 'Nb': 41, 'Mo': 42, 'Tc': 43,
    'Ru': 44, 'Rh': 45, 'Pd': 46, 'Ag': 47, 'Cd': 48, 'In': 49, 'Sn': 50,
    'Sb': 51, 'Te': 52, 'I': 53, 'Xe': 54, 'Cs': 55, 'Ba': 56, 'La': 57,
    'Ce': 58, 'Pr': 59, 'Nd': 60, 'Pm': 61, 'Sm': 62, 'Eu': 63, 'Gd': 64,
    'Tb': 65, 'Dy': 66, 'Ho': 67, 'Er': 68, 'Tm': 69, 'Yb': 70, 'Lu': 71,
    'Hf': 72, 'Ta': 73, 'W': 74, 'Re': 75, 'Os': 76, 'Ir': 77, 'Pt': 78,
    'Au': 79, 'Hg': 80, 'Tl': 81, 'Pb': 82, 'Bi': 83, 'Po': 84, 'At': 85,
    'Rn': 86, 'Fr': 87, 'Ra': 88, 'Ac': 89, 'Th': 90, 'Pa': 91, 'U': 92,
    'Np': 93, 'Pu': 94, 'Am': 95, 'Cm': 96, 'Bk': 97, 'Cf': 98, 'Es': 99,
    'Fm': 100, 'Md': 101, 'No': 102, 'Lr': 103, 'Rf': 104, 'Db': 105,
    'Sg': 106, 'Bh': 107, 'Hs': 108, 'Mt': 109, 'Ds': 110, 'Rg': 111,
    'Cn': 112, 'Uut': 113, 'Fl': 114, 'Uup': 115, 'Lv': 116, 'Uus': 117,
    'Uuo': 118
}
_symbol = {v: k for k, v in _atomicnum.items()}


def symbol_of_element(element):
    """Returns symbol of given element. If element is a symbol of an element
    already, it is returned without change.

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
    InvalidElementError
        when 'element' cannot be converted to element's symbol"""
    try:
        _element = int(element)
    except ValueError:
        _element = element
    if _element in _atomicnum:
        return _element
    elif _element in _symbol:
        return _symbol[_element]
    else:
        raise InvalidElementError(f'Unknown element: {element}')


def atomic_number(element):
    """Returns atomic number of given element. If element is an atomic number
    already, it is returned without change.

    Parameters
    ----------
    element: str or int
        element's symbol

    Returns
    -------
    str
        atomic number of an element

    Raises
    ------
    InvalidElementError
        when 'element' cannot be converted to element's atomic number"""
    if element in _atomicnum:
        return _atomicnum[element]
    elif element in _symbol:
        return element
    else:
        raise InvalidElementError(f'Unknown element: {element}')


def take_atoms(values, atoms, wanted) -> np.ndarray:
    """Filters given values, returning those corresponding to atoms specified
    as wanted. Roughly equivalent to:
    >>> numpy.take(values, numpy.where(numpy.equal(atoms, wanted))[0], 1)
    but returns empty array, if no atom in 'atoms' matches 'wanted' atom.
    If wanted is list of elements, numpy.isin is used instead of numpy.equal.

    Parameters
    ----------
    values: Sequence or numpy.ndarray
        array of values; it should be one-dimensional list of values or
        n-dimensional array of shape
        (conformers, values[, coordinates[, other]])
    atoms: Sequence or numpy.ndarray
        list of atoms in molecule; order should be the same as corresponding
        values for each conformer
    wanted: int or float or Iterable or numpy.ndarray
        atomic number of wanted atom, or a list of those

    Returns
    -------
    numpy.ndarray
        values trimmed to corresponding to desired atoms only; preserves
        original dimension information
    """
    if isinstance(wanted, Iterable):
        blade = np.isin(atoms, wanted)
    else:
        blade = np.equal(atoms, wanted)
    indices = np.where(blade)[0]
    if not indices.size:
        output = np.array([])
    else:
        try:
            output = np.take(values, indices, 1)
        except np.AxisError:
            output = np.take(values, indices, 0)
    return output


def drop_atoms(values, atoms, discarded):
    """Filters given values, returning those corresponding to atoms not
    specified as discarded. Roughly equivalent to:
    >>> numpy.take(values, numpy.where(~numpy.equal(atoms, discarded))[0], 1)
    If wanted is list of elements, numpy.isin is used instead of numpy.equal.

    Parameters
    ----------
    values: Sequence or numpy.ndarray
        array of values; it should be one-dimensional list of values or
        n-dimensional array of shape
        (conformers, values[, coordinates[, other]])
    atoms: Sequence or numpy.ndarray
        list of atoms in molecule; order should be the same as corresponding
        values for each conformer
    discarded: int or float or Iterable or numpy.ndarray
        atomic number of discarded atom, or a list of those

    Returns
    -------
    numpy.ndarray
        values trimmed to corresponding to desired atoms only; preserves
        original dimension information
    """
    if isinstance(discarded, Iterable):
        blade = np.isin(atoms, discarded)
    else:
        blade = np.equal(atoms, discarded)
    indices = np.where(np.logical_not(blade))[0]
    if not indices.size:
        output = np.array([])
    else:
        try:
            output = np.take(values, indices, 1)
        except np.AxisError:
            output = np.take(values, indices, 0)
    return output
