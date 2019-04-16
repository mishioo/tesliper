# IMPORTS
import logging as lgg
import numpy as np
from .helpers import is_triangular, get_triangular, get_triangular_base


# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# MODULE FUNCTIONS
def unpack(values):
    """Unpacks list of flat representations of symmetric arrays into
    array of symmetric two-dimensional arrays.

    Parameters
    ----------
    values: list or np.ndarray
        list of flat representations of symmetric arrays; all inner lists
        should have the same length

    Returns
    -------
    np.ndarray
        array of symmetric two-dimensional arrays (tree dimensions total)

    Raises
    ------
    ValueError
        if values cannot be transformed into symmetric matrix"""
    try:
        length = len(values[0])
    except TypeError:
        length = len(values)
        values = [values]
    if not is_triangular(length):
        raise ValueError(
            'Number of elements should be a triangular number when "unpack"'
            f' argument is True. {length} is not triangular.'
        )
    base = get_triangular_base(length)
    shape = len(values), base, base
    arr = np.zeros(shape, dtype=np.asarray(values[0][0]).dtype)
    it = np.nditer(arr, flags=['multi_index'], op_flags=['writeonly'])
    while not it.finished:
        conf, row, col = it.multi_index
        if col > row:
            # swap if we are in an upper triangle
            col, row = row, col
        ind = row * (row + 1) // 2 + col
        it[0] = values[conf][ind]
        it.iternext()
    # remove additional dimension if only one conformer given
    return arr if len(values) > 1 else arr[0]


def drop_diagonals(coupling_constants):
    """Reduces symmetrically sized array by removing its diagonal.
    If input array has more than 2 dimensions (N), it is treated as a list of
    symmetrically sized arrays. Returned array is empty (N < 2), has shorter
    second (N == 2) or third (N > 2) dimension.

    >>> drop_diagonals(np.array([0]))
    array([])
    >>> drop_diagonals(np.arange(9).reshape(3, 3))
    array([[1, 2], [3, 5], [6, 7]])
    >>> drop_diagonals(np.arange(18).reshape(2, 3, 3))
    array([[[1, 2], [3, 5], [6, 7]], [[10, 11], [12, 14], [15, 16]]])

    Parameters
    ----------
    coupling_constants: list of lists or numpy.ndarray
        N-dimensional array; if N>2, dimensions 1 and 2 (assuming 0-indexing)
        should be of the same size

    Returns
    -------
    numpy.ndarray
        reduced array, empty if input array has less than two dimensions

    Raises
    ------
    ValueError
        if input array cannot be interpreted as symmetric"""
    coupling_constants = np.asarray(coupling_constants)
    shape = coupling_constants.shape
    try:
        confs, x, y, *other = shape
    except ValueError:
        confs, x, y, *other = None, *shape, None
    if y and not x == y or not y and x > 1:
        raise ValueError(
            f"Value of 'coupling_constants' should be a symmetric array or "
            f"array of symmetric arrays. Array of shape "
            f"{coupling_constants.shape} is not symmetric."
        )
    mask = np.invert(np.eye(x, dtype=bool))
    if not y or not coupling_constants.size:
        # one-dimensional or empty input
        remaining = np.empty(0, dtype=coupling_constants.dtype)
    elif not confs:
        # two-dimensional input
        remaining = coupling_constants[mask].reshape(x, x-1)
    else:
        remaining = coupling_constants[:, mask, ...]
        remaining = remaining.reshape(confs, x, x-1, *other)
    return remaining


def couple(shieldings, coupling_constants, separate_peaks=False):
    """Creates a list of coupled shieldings values, given a list of base
    shielding values and a list of coupling constants' lists.

    >>> couple([15, 45, 95], [[0, 2, 6], [2, 0, 4], [6, 4, 0]])
    array([[19, 17, 19, 17, 13, 11, 13, 11, 48, 48, 46, 46, 44, 44, 42, 42,
            100, 96, 94, 90, 100, 96, 94, 90]])

    To avoid values duplication and save memory, omit diagonal of coupling
    constants' matrix:

    >>> couple([15, 45, 95], [[2, 6], [2, 4], [6, 4]])
    array([[19, 13, 17, 11, 48, 44, 46, 42, 100, 96, 94, 90]])

    Both parameters can contain information for one or more conformers. If only
    one of them is one conformer in size, its values are used for all conformers
    of the other.

    >>> couple([[10, 30, 50], [25, 35, 45]], [[1, 4], [1, 3], [4, 3]])
    array([[12.5,  8.5, 11.5,  7.5, 32. , 29. , 31. , 28. , 53.5, 50.5, 49.5,
            46.5],
           [27.5, 23.5, 26.5, 22.5, 37. , 34. , 36. , 33. , 48.5, 45.5, 44.5,
            41.5]])

    Parameters
    ----------
    shieldings: Iterable or numpy.ndarray
        list of shielding values for each atom; should be an one-dimensional
        array of values for each atom or two-dimensional array of shape
        (conformers, atoms)
    coupling_constants: Iterable or numpy.ndarray
        matrix of coupling constants' values for each atom; should be
        a two-dimensional array of shape (atoms, constants) or
        a tree-dimensional array of shape (conformers, atoms, constants);
        should have the same number of values for conformer as 'shieldings'
    separate_peaks: bool, optional
        if evaluates to True, output array is tree-dimensional with each peaks'
        coupled shielding values separated; if evaluates to False, then
        a two-dimensional array is returned, with all values for conformer
        in one dimension; defaults to False

    Returns
    -------
    numpy.ndarray
        list of coupled shieldings' values for each conformer

    Raises
    ------
    ValueError
        if arrays of inappropriate shape given"""
    shieldings = np.asarray(shieldings)
    coupling_constants = np.asarray(coupling_constants)
    if len(shieldings.shape) > 2:
        raise ValueError(
            f'Shieldings should be at most two-dimensional, got array with '
            f'{len(shieldings.shape)} dimensions.'
        )
    if not 1 < len(coupling_constants.shape) <= 3:
        raise ValueError(
            f'Coupling constants should be two- or tree-dimensional, got '
            f'array with {len(coupling_constants.shape)} dimensions.'
        )
    n = coupling_constants.shape[-1]  # number of coupling constants per atom
    base = [[1, -1]] * n
    # create a cartesian product of n [1, -1] arrays, to form a framework
    # for evaluation of values of coupled peaks' distances from base value
    # i.e. all 2**n n-element ordered subsets of list [1, -1] * n
    frame = np.array(np.meshgrid(*base, copy=False)).T.reshape(-1, n)
    # transpose it to work properly with coupling values in np.matmul
    frame = frame.T
    halved = coupling_constants / 2
    # calculate list of actual of coupled peaks' from base peak value
    # and add it to base value to find actual coupled peaks' values
    coup = np.matmul(halved, frame)
    # ensure proper shapes
    if len(shieldings.shape) == 1:
        shieldings = shieldings[np.newaxis, ...]
    if len(shieldings.shape) == len(coup.shape):
        coup = coup[np.newaxis, ...]
    # transposes are needed to use numpy's brodcasting
    out = (shieldings.T + coup.T).T
    if not separate_peaks:
        out = out.reshape(out.shape[0], -1)
    return out
