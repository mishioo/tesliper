# IMPORTS
import logging as lgg
import numpy as np
from .helpers import is_triangular, get_triangular, get_triangular_base
from ..exceptions import InconsistentDataError

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# MODULE FUNCTIONS
def unpack(values):
    """Unpacks list of flat representations of symmetric arrays into
    array of symmetric two-dimensional arrays.

    >>> unpack([[0, 2, 0, 6, 4, 0], [0, 4, 0, 8, 10, 0]])
    array([[[ 0,  2,  6],
            [ 2,  0,  4],
            [ 6,  4,  0]],

           [[ 0,  4,  8],
            [ 4,  0, 10],
            [ 8, 10,  0]]])

    Output array is always three-dimensional, even if single set of values is
    given:

    >>> unpack([0, 2, 0, 6, 4, 0])
    array([[[0, 2, 6],
            [2, 0, 4],
            [6, 4, 0]]])

    Parameters
    ----------
    values: list or np.ndarray
        list of flat representations of symmetric arrays; all inner lists
        should have the same length

    Returns
    -------
    np.ndarray
        array of symmetric two-dimensional arrays (three dimensions total)

    Raises
    ------
    ValueError
        if values cannot be transformed into symmetric matrix (i.e. number
        of values given is not triangular)"""
    try:
        length = len(values[0])
    except TypeError:
        length = len(values)
        values = [values]
    if not is_triangular(length):
        raise ValueError(
            'Number of elements should be a triangular number. '
            f'{length} is not triangular.'
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
    """Creates a list of coupled shielding values, given a list of base
    shielding values and a list of coupling constants' lists.

    >>> couple(
    >>>    [[15, 45, 95],  # 1st conformer shielding values
    >>>     [25, 55, 85]],  # 2nd conformer shielding values
    >>>    [[[0, 2, 6], [2, 0, 4], [6, 4, 0]],  # 1st conf. coupling const.
    >>>     [[0, 4, 8], [4, 0, 10], [8, 10, 0]]]  # 2nd conf. coupling const.
    >>> )
    array([[ 19.,  17.,  19.,  17.,  13.,  11.,  13.,  11.,  48.,  48.,  46.,
             46.,  44.,  44.,  42.,  42., 100.,  96.,  94.,  90., 100.,  96.,
             94.,  90.],  # 1st conf. signals
           [ 31.,  27.,  31.,  27.,  23.,  19.,  23.,  19.,  62.,  62.,  58.,
             58.,  52.,  52.,  48.,  48.,  94.,  84.,  86.,  76.,  94.,  84.,
             86.,  76.]])  # 2nd conf. signals

    Both or one of the parameters can contain information for only one
    conformer. If only one of them is one conformer in size, its values are
    used for all conformers of the other, using numpy broadcasting.

    >>> couple([[10, 30, 50], [25, 35, 45]], [[[2, 4], [2, 6], [4, 6]]])
    array([[13.,  9., 11.,  7., 34., 28., 32., 26., 55., 49., 51., 45.],
           [28., 24., 26., 22., 39., 33., 37., 31., 50., 44., 46., 40.]])

    To avoid values duplication and save memory, omit diagonal of coupling
    constants' matrix:

    >>> couple([[15, 45, 95]], [[[2, 6], [2, 4], [6, 4]]])
    array([[19., 13., 17., 11., 48., 44., 46., 42., 100., 96., 94., 90.]])

    If optional parameter 'separate_peaks' is True (defaults to False), output
    array has one more dimension with each peaks' coupled shielding values
    separated. Such an array may be coupled again with another set of coupling
    constants.

    >>> separated = couple([[15, 45, 85]], [[[2, 6], [2, 4], [6, 4]]],
    >>>                    separate_peaks=True)
    >>> separated
    array([[[19., 13., 17., 11.],
            [48., 44., 46., 42.],
            [90., 86., 84., 80.]]])
    >>> couple(separated, [[[10], [16], [20]]])
    array([[ 24.,  14.,  18.,   8.,  22.,  12.,  16.,   6.,  56.,  40.,  52.,
             36.,  54.,  38.,  50.,  34., 100.,  80.,  96.,  76.,  94.,  74.,
             90.,  70.]])

     Note, that each peaks' set of values is coupled only by the corresponding
     coupling constant.

    Parameters
    ----------
    shieldings: Iterable or numpy.ndarray
        list of lists of shielding values for each conformer; should be
        a two-dimensional array of shape (conformers, atoms) or
        a tre-dimensional array of shape conformers, atoms, signals_for_peak)
    coupling_constants: Iterable or numpy.ndarray
        list of matrices of coupling constants' values for each atom, for each
        conformer; should be a three-dimensional array of shape
        (conformers, atoms, constants); should have the same number of values
        for conformer as 'shieldings'
    separate_peaks: bool, optional
        if evaluates to True, output array is three-dimensional with each peaks'
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
        if arrays of inappropriate shape given
    InconsistentDataError
        if given arrays of different sizes and both sizes > 1
        or """
    shieldings = np.asarray(shieldings)
    coupling_constants = np.asarray(coupling_constants)

    # v ERROR HANDLING
    if not 1 < len(shieldings.shape) <= 3:
        raise ValueError(
            f'Shieldings should be two- or three-dimensional, got an array '
            f'with {len(shieldings.shape)} dimensions.'
        )
    elif len(shieldings.shape) == 2:
        # no peaks given, expand dimensionality
        shieldings = shieldings[..., np.newaxis]
    if not len(coupling_constants.shape) == 3:
        raise ValueError(
            f'Coupling constants should be three-dimensional, got '
            f'an array with {len(coupling_constants.shape)} dimensions.'
        )
    s_confs, s_atoms = shieldings.shape[:2]
    c_confs, c_atoms = coupling_constants.shape[:2]
    if not (s_confs == 1 or c_confs == 1 or s_confs == c_confs):
        raise InconsistentDataError(
            f"Shielding values' and coupling constants' arrays should contain"
            f"data for the same number of conformers or for only one conformer."
            f" Sets with data for {s_confs} and {c_confs} conformers given."
        )
    if not (s_atoms == 1 or c_atoms == 1 or s_atoms == c_atoms):
        raise InconsistentDataError(
            f"Shielding values' and coupling constants' arrays should contain"
            f"data for the same number of atoms for each conformer or only one "
            f"set of values for conformer. Sets with data for {s_atoms} and "
            f"{c_atoms} atoms given."
        )
    # ^ ERROR HANDLING

    n = coupling_constants.shape[-1]  # number of coupling constants per atom
    base = [[1, -1]] * n
    # create a cartesian product of n [1, -1] arrays, to form a framework
    # for evaluation of values of coupled peaks' distances from base value
    # i.e. all 2**n n-element ordered subsets of list [1, -1] * n
    frame = np.array(np.meshgrid(*base, copy=False)).T.reshape(-1, n)
    # transpose it to work properly with coupling values in np.matmul
    frame = frame.T
    halved = coupling_constants / 2
    # calculate list of coupled peaks' distances from base peak value
    # and add it to base value to find actual coupled peaks' values
    coup = np.matmul(halved, frame)
    # ensure proper shapes and return
    out = shieldings[..., np.newaxis] + coup[..., np.newaxis, :]
    new_shape = (*out.shape[:2], -1) if separate_peaks else (out.shape[0], -1)
    return out.reshape(*new_shape)
