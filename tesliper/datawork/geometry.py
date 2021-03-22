import math
from typing import Sequence, Iterable, Union

import numpy as np


def take_atoms(
    values: Union[Sequence, np.ndarray],
    atoms: Union[Sequence[int], np.ndarray],
    wanted: Union[int, Iterable[int], np.ndarray],
) -> np.ndarray:
    """Filters given values, returning those corresponding to atoms specified
    as `wanted`. Roughly equivalent to:
    >>> numpy.take(values, numpy.where(numpy.equal(atoms, wanted))[0], 1)
    but returns empty array, if no atom in `atoms` matches `wanted` atom.
    If `wanted` is list of elements, numpy.isin is used instead of numpy.equal.

    Parameters
    ----------
    values: Sequence or numpy.ndarray
        array of values; it should be one-dimensional list of values or
        n-dimensional array of shape
        (conformers, values[, coordinates[, other]])
    atoms: Sequence of int or numpy.ndarray
        list of atoms in molecule, given as atomic numbers;
        order should be the same as corresponding values for each conformer
    wanted: int or Iterable of int or numpy.ndarray
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


def drop_atoms(
    values: Union[Sequence, np.ndarray],
    atoms: Union[Iterable[int], np.ndarray],
    discarded: Union[int, Iterable[int], np.ndarray],
) -> np.ndarray:
    """Filters given values, returning those corresponding to atoms not
    specified as discarded. Roughly equivalent to:
    >>> numpy.take(values, numpy.where(~numpy.equal(atoms, discarded))[0], 1)
    If `wanted` is list of elements, numpy.isin is used instead of numpy.equal.

    Parameters
    ----------
    values: Sequence or numpy.ndarray
        array of values; it should be one-dimensional list of values or
        n-dimensional array of shape
        (conformers, values[, coordinates[, other]])
    atoms: Iterable of int or numpy.ndarray
        list of atoms in molecule, given as atomic numbers;
        order should be the same as corresponding values for each conformer
    discarded: int or Iterable of int or numpy.ndarray
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


def is_triangular(n: int) -> bool:
    """Checks if number `n` is triangular.

    Notes
    -----
    If `n` is the mth triangular number, then n = m*(m+1)/2.
    Solving for m using the quadratic formula: m = (sqrt(8n+1) - 1) / 2,
    so `n` is triangular if and only if 8n+1 is a perfect square.

    Parameters
    ----------
    n: int
        number to check

    Returns
    -------
    bool
        True is number `n` is triangular, else False
    """
    if n < 0:
        return False
    check = math.sqrt(8 * n + 1)
    try:
        return check == int(check)
    except OverflowError:
        # check is float('inf')
        return False


def get_triangular_base(n: int) -> int:
    """Find which mth triangular number `n` is."""
    if not is_triangular(n):
        raise ValueError(f'"n" should be a triangular number. {n} is not triangular.')
    return int((math.sqrt(8 * n + 1) - 1) / 2)


def get_triangular(m: int) -> int:
    """Find `m`th triangular number."""
    if m < 0:
        raise ValueError('"m" should be non-negative number.')
    if not m // 1 == m:
        raise ValueError(f'"m" should be a whole number, {m} given.')
    return m * (m + 1) // 2


MoleculeOrList = Union[Sequence[Sequence[float]], Sequence[Sequence[Sequence[float]]]]


def center(a: MoleculeOrList) -> MoleculeOrList:
    """Zero-center all given molecules by subtracting their centroids.
    Accepts single molecule or list of molecules."""
    a = np.asanyarray(a)
    return a - np.expand_dims(a.mean(axis=-2), -2)


def kabsch_rotate(a: MoleculeOrList, b: MoleculeOrList) -> np.ndarray:
    """Minimize RMSD of molecules `a` and `b` by rotating molecule `a` onto `b`.
    Expects given representation of molecules to be zero-centered.
    Both `a` and `b` may be a single molecule or a set of molecules.

    Parameters
    ----------
    a : [Sequence of ]Sequence of Sequence of float
        Set of points representing atoms, that will be rotated to best match reference.
    b : [Sequence of ]Sequence of Sequence of float
        Set of points representing atoms of the reference molecule.

    Returns
    -------
    numpy.ndarray
        Rotated set of points `a`.

    Notes
    -----
    Uses Kabsch algorithm, also known as Wahba's problem. See:
    https://en.wikipedia.org/wiki/Kabsch_algorithm and
    https://en.wikipedia.org/wiki/Wahba%27s_problem
    """
    # this implementation uses Einstein summation convention, numpy.eisnum()
    # this approach is probably not the most efficient
    # but lets us easily perform a matrix multiplication on stacks of matrices
    a, b = np.asanyarray(a), np.asanyarray(b)
    # calculate covariance matrix for each stacked set of points
    # for each of stacked sets of points, equivalent of:
    # >>> cov = a.T @ b
    cov = np.einsum("...ji,...jk", a, b)
    u, s, vh = np.linalg.svd(cov)  # singular value decomposition
    # if determinant is negative, swap to ensure right-handed coordinate system
    det = np.linalg.det(vh @ u)  # works with stacked matrices
    # don't introduce new dimension if not necessary
    shape = (det.size, 3, 3) if det.size > 1 else (3, 3)
    swap = np.zeros(shape)
    swap[..., np.arange(2), np.arange(2)] = 1
    swap[..., -1, -1] = np.sign(det)
    # calculate optimally rotated set/s of points `a`
    # for each of stacked sets of points, equivalent of
    # >>> rotated = a @ u @ swap @ vh
    # where u @ swap @ vh is rotation matrix
    return np.einsum("...ij,...jk,...kl,...lm", a, u, swap, vh)


def rmsd(a: MoleculeOrList, b: MoleculeOrList) -> np.ndarray:
    """Compute RMSD (round-mean-square deviation) of two molecules (or sets of them).

    Parameters
    ----------
    a : [Sequence of ]Sequence of Sequence of float
        Set of points representing atoms or list thereof.
    b : [Sequence of ]Sequence of Sequence of float
        Set of points representing atoms  or list thereof.

    Returns
    -------
    float or numpy.ndarray
        Value of RMSD od two molecules or list of values, if list of molecules given.
    """
    deviation = np.asanyarray(a) - np.asanyarray(b)
    # get a mean of two last dimensions by using `axis=(-2, -1)`
    return np.sqrt(np.square(deviation).mean(axis=(-2, -1)))


def windowed(series: Sequence, size: int) -> np.ndarray:
    """Simple, vectorized implementation of basic sliding window.
    Produces a list of windows of given `size` from given `series`.

    Parameters
    ----------
    series : sequence
        Series of data, of which sliding window view is requested.
    size : int
        Number of data points in the window. Must be a positive integer.

    Returns
    -------
    numpy.ndarray
        Windowed view of the given sequence.

    Raises
    ------
    ValueError
        if non-positive integer given as window size
    TypeError
        if non-integer value given as window size

    Notes
    -----
    Implementation inspired by
    https://towardsdatascience.com/fast-and-robust-sliding-window-vectorization-with-numpy-3ad950ed62f5
    """
    if not isinstance(size, int):
        raise TypeError(f"`size` must be a positive integer, but {type(size)} given.")
    elif size <= 0:
        raise ValueError(f"`size` must be a positive integer, but {size} given.")
    series = np.asanyarray(series)
    # create indices for fancy indexing [[0, 1, ..., size], [1, 2, ..., size + 1], ...]
    windows = (
        np.arange(size)[np.newaxis, ...]
        + np.arange(series.size - size + 1)[np.newaxis, ...].T
    )
    return series[windows]


def energy_windows(
    values: Sequence[float], size: Union[int, float], keep_hermits: bool = False
) -> np.ndarray:
    """Implements a sliding window of a variable size, where values in each window are
    at most `size` bigger than the lowest value in given window. Values yielded
    are np.arrays of indices of sorted values, that constitute each window.

    A window is formed for each value in the original array, so a few last windows
    produced are subsequences of first window that includes the highest value in given
    `values` array. This "soft" right bound is also observed when distribution of values
    is uneven (ie. when gaps between some values are larger than given `size`).

    >>> list(energy_windows([1, 2, 3, 4], 3))
    [[0, 1, 2], [1, 2, 3], [2, 3]]
    >>> list(energy_windows([1, 2, 3, 7, 8], 3))
    [[0, 1, 2], [1, 2], [3, 4]]

    Windows of size 1, called hermits, are by default ignored.

    >>> list(energy_windows([1, 2, 10, 20, 22], 5))
    [[0, 1], [3, 4]]

    If such behavior is not desired, it may be turnd off with `keep_hermits = True`.
    One must remember that, due to the "soft" bound, the last window is always a hermit,
    if `keep_hermits`.

    >>> list(energy_windows([1, 2, 10, 20, 22], 5, keep_hermits=True))
    [[0, 1], [1], [2], [3, 4], [4]]

    Parameters
    ----------
    values : Sequence of float
        List of values, on which sliding window view is requested.
    size : int or float
        Maximum difference of smallest and largest values inside each window.
    keep_hermits : bool
        If windows of size one should be yielded (True) or omitted (False).
        False by default.

    Yields
    ------
    np.array of int
        List of indices, corresponding to sorted values in the original array,
        that form a window.

    Raises
    ------
    ValueError
        If given `size` is not a positive number.
    """
    if size <= 0:
        raise ValueError("Size of the energy window must be a positive number.")
    order = np.argsort(values)
    ordered = np.asanyarray(values)[order]
    # side="right" is ie. "or equal to" part of "include lower on equal to value+size"
    indices = np.searchsorted(ordered, ordered + size, side="right")
    for start, stop in enumerate(indices):
        if stop - start > 1 or keep_hermits:
            yield order[start : (stop if stop <= indices.size else None)]
