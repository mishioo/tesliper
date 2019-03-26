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
    if not is_triangular(len(values[0])):
        raise ValueError(
            'Number of elements should be a triangular number when "unpack"'
            f' argument is True. {len(values[0])} is not triangular.'
        )
    base = get_triangular_base(len(values[0]))
    shape = len(values), base, base
    arr = np.zeros(shape)
    it = np.nditer(arr, flags=['multi_index'], op_flags=['writeonly'])
    while not it.finished:
        conf, row, col = it.multi_index
        if col > row:
            # swap if we are in upper triangle
            col, row = row, col
        ind = row * (row + 1) // 2 + col
        it[0] = values[conf][ind]
        it.iternext()
    return arr


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
        remaining = np.empty(0, dtype=coupling_constants.dtype)
    elif not confs:
        remaining = coupling_constants[mask].reshape(x, x-1)
    else:
        remaining = coupling_constants[:, mask, ...]
        remaining = remaining.reshape(confs, x, x-1, *other)
    return remaining


def couple(shieldings, coupling_constants):
    # TO DO: check if can be used when diagonal discarded
    n = coupling_constants.shape[1]
    base = [[1, -1]] * n
    # create a cartesian product of n [1, -1] arrays, to form a framework
    # for evaluation of values of coupled peaks' distances from base value
    # i.e. all 2**n n-element ordered subsets of list [1, -1] * n
    frame = np.array(np.meshgrid(*base, copy=False)).T.reshape(-1, n)
    # transpose it to make it usable in np.dot with coupling values
    frame = frame.T
    halved = coupling_constants / 2
    # calculate list of actual distances of coupled peaks' from base value
    # and add it to base value to find actual coupled peak values
    # transposes needed to use numpy's brodcasting
    coup = np.dot(halved, frame).T
    return (shieldings + coup).T
    # if 3d-array:
    # coup = np.dot(halved, frame).transpose(0, 2, 1)
    # return (shield + coup).transpose(0, 2, 1)
