# IMPORTS
import logging as lgg
import math
from typing import Sequence, Tuple, Union

import numpy as np

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# TYPES
Numbers = Sequence[Union[int, float]]


# MODULE FUNCTIONS
def count_imaginary(frequencies):
    """Finds number of imaginary frequencies of each conformer.

    Parameters
    ----------
    frequencies : numpy.ndarray
        List of conformers' frequencies. Array with one dimension is interpreted
        as list of frequencies for single conformer.

    Returns
    -------
    numpy.ndarray
        Number of imaginary frequencies of each conformer.

    Raises
    ------
    ValueError
        If input array has more than 2 dimensions."""
    if frequencies.size == 0:
        return np.array([])
    elif frequencies.ndim < 2:
        return np.asarray((frequencies < 0).sum())
    elif frequencies.ndim == 2:
        return (frequencies < 0).sum(1)
    else:
        raise ValueError(
            f"Array with {frequencies.ndim} dimensions can't be interpreted "
            f"as a list of conformers' frequencies."
        )


def find_imaginary(frequencies):
    """Finds all conformers with imaginary frequency values.

    Parameters
    ----------
    frequencies : numpy.ndarray
        List of conformers' frequencies.

    Returns
    -------
    numpy.ndarray
        List of the indices of conformers with imaginary frequency values.

    Raises
    ------
    ValueError
        If input array has more than 2 dimensions."""
    try:
        imag = count_imaginary(frequencies)
    except ValueError as err:
        raise ValueError(err) from err
    return np.nonzero(imag)[0]


def gaussian(intensities, frequencies, abscissa, width):
    """Gaussian fitting function for spectra calculation.

    Parameters
    ----------
    intensities: numpy.ndarray
        Appropriate values extracted from gaussian output files.
    frequencies: numpy.ndarray
        Frequencies extracted from gaussian output files.
    abscissa: numpy.ndarray
        List of wavelength/wave number points on spectrum x axis.
    width: int or float
        Number representing half width of peak at 1/e its maximum height.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values.

    Raises
    ------
    ValueError
        If given width is not greater than zero.
        If `intensities` and `frequencies` are not of the sane shape."""
    if width <= 0:
        raise ValueError("Peak width must be a positive value!")
    if intensities.shape != frequencies.shape:
        raise ValueError("`intensities` and `frequencies` must be of same shape!")
    if abscissa.size == 0:
        return np.array([])
    sigm = width / 1.4142135623730951  # math.sqrt(2)
    denominator = sigm * 2.5066282746310002  # (2 * math.pi) ** 0.5
    it = np.nditer(
        [abscissa, None],
        flags=["buffered"],
        op_flags=[["readonly"], ["writeonly", "allocate", "no_broadcast"]],
        op_dtypes=[np.float64, np.float64],
    )
    for x, peaks in it:
        e = intensities * np.exp(-0.5 * ((x - frequencies) / sigm) ** 2)
        peaks[...] = (e / denominator).sum()
    return it.operands[1]


def lorentzian(intensities, frequencies, abscissa, width):
    """Lorentzian fitting function for spectra calculation.

    Parameters
    ----------
    intensities: numpy.ndarray
        Appropriate values extracted from gaussian output files.
    frequencies: numpy.ndarray
        Frequencies extracted from gaussian output files.
    abscissa: numpy.ndarray
        List of wavelength/wave number points on spectrum x axis.
    width: int or float
        Number representing half width of peak at half its maximum height.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values.

    Raises
    ------
    ValueError
        If given width is not greater than zero.
        If `intensities` and `frequencies` are not of the same shape."""
    if width <= 0:
        raise ValueError("Peak width must be a positive value!")
    if intensities.shape != frequencies.shape:
        raise ValueError("`intensities` and `frequencies` must be of same shape!")
    if abscissa.size == 0:
        return np.array([])
    hwhmsqrd = width ** 2
    hwhmoverpi = width / math.pi
    it = np.nditer(
        [abscissa, None],
        flags=["buffered"],
        op_flags=[["readonly"], ["writeonly", "allocate", "no_broadcast"]],
        op_dtypes=[np.float64, np.float64],
    )
    for x, val in it:
        s = intensities / ((frequencies - x) ** 2 + hwhmsqrd)
        s2 = (hwhmoverpi * s).sum()
        val[...] = s2
    return it.operands[1]


def calculate_spectra(frequencies, intensities, abscissa, width, fitting):
    """Calculates spectrum for each individual conformer.

    Parameters
    ----------
    frequencies : numpy.ndarray
        List of conformers' frequencies in cm^(-1). Should be of shape
        (number _of_conformers, number_of_frequencies).
    intensities : numpy.ndarray
        List of calculated signal intensities for each conformer. Should be
        of same shape as frequencies.
    abscissa : numpy.ndarray
        List of points on x axis in output spectrum in cm^(-1).
    width : int or float
        Number representing peak width in cm^(-1), used by fitting function.
    fitting : function
        Function, which takes intensities, frequencies, abscissa, hwhm as
        parameters and returns numpy.array of calculated spectrum points.

    Returns
    -------
    numpy.ndarray
        Array of intensity values for each conformer.

    Raises
    ------
    ValueError
        If given width is not greater than zero.
        If `intensities` and `frequencies` are not of the same shape."""
    if intensities.shape != frequencies.shape:
        raise ValueError("`intensities` and `frequencies` must be of same shape!")
    if not intensities.size:
        return np.zeros(0)  # return early to avoid (0, N) shape of output array
    spectra = np.zeros([len(frequencies), abscissa.shape[0]])  # template
    for inten, freq, spr in zip(intensities, frequencies, spectra):
        spr[...] = fitting(inten, freq, abscissa, width)
    return spectra


def calculate_average(values, populations):
    """Calculates weighted average of `values`, where `populations` are used as
    weights.

    Parameters
    ----------
    values : numpy.ndarray or iterable
        List of values for each conformer, should be of shape (N, M), where N is
        number of conformers and M is number of values.
    populations : numpy.ndarray or iterable
        List of conformers' populations, should be of shape (N,) where N is
        number of conformers. Should add up to 1.

    Returns
    -------
    numpy.ndarray
        weighted arithmetic mean of values given.

    Raises
    ------
    ValueError
        If parameters of non-matching shape were given."""
    values = np.asanyarray(values)
    populations = np.asanyarray(populations)
    if not populations.size == values.shape[0]:
        raise ValueError(
            "Exactly one population value for each conformer must be provided."
        )
    if not values.size:
        return np.zeros([0])  # just return an empty array if `values` is empty
    popsum = populations.sum()
    if not np.isclose(popsum, 1):
        # normalize population data, if needed
        populations = populations / popsum
    # populations must be of same shape as values array
    # so we expand populations with appropriate number of dimensions
    shape = (-1,) + (1,) * (values.ndim - 1)
    popul = populations.reshape(*shape)
    return (values * popul).sum(0)


def idx_offset(a: Numbers, b: Numbers) -> int:
    """Calculate offset by which `b` should be shifted to best overlap with `a`.
    Both `a` and `b` should be sets of points, interpreted as spectral data. Returned
    offset is a number of data points, by which `b` should be moved relative to `a`,
    to get the best overlap of given spectra.

    Parameters
    ----------
    a : sequence of ints or floats
        `x` values` of the first spectrum.
    b : sequence of ints or floats
        `x` values` of the second spectrum.

    Returns
    -------
    int
        Offset, in number of data points, by which spectrum `b` should be shifted
        to best match spectrum `a`. Positive value means it should be shifted to the
        right and negative value means it should be shifted to the left of `a`.

    Notes
    -----
    The best overlap is found by means of cross-correlation of given spectra.
    """
    a, b = np.asanyarray(a), np.asanyarray(b)
    # normalize values to be zero centered to prevent influence of padding with zeros
    a = (a - a.mean()) / a.std()
    b = (b - b.mean()) / b.std()
    # calculate cross correlation array and find best overlap
    cross = np.correlate(a, b, mode="full")
    best = cross.argmax()
    return best - b.size + 1


def unify_abscissa(
    ax: Numbers, ay: Numbers, bx: Numbers, by: Numbers, upscale: bool = True
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Interpolate one of the given spectra to have the same points density as the
    other given spectrum.

    Which spectra should be interpolated is determined based on the density of points
    of both spectra, by default more loosely spaced spectrum is interpolated to match
    spacing of the other spectrum. This may be changed by passing `upscale=False`
    to the function call.

    Parameters
    ----------
    ax : sequence of ints or floats
        Abscissa of the first spectrum.
    ay : sequence of ints or floats
        Values of the first spectrum.
    bx : sequence of ints or floats
        Abscissa of the second spectrum.
    by : sequence of ints or floats
        Values of the second spectrum.
    upscale : bool
        If interpolation should be done on more loosely spaced spectrum (default).
        When set to False, spectrum with lower resolution will be treated as reference.

    Returns
    -------
    tuple of np.arrays of numbers
        Spectra, one unchanged and one interpolated, as a tuple of numpy arrays
        of x and y values. I.e. `tuple(ax, ay, new_bx, new_by)` or
        `tuple(new_ax, new_ay, bx, by)`, depending on values of `upscale` parameter.
    """
    ax, ay, bx, by = (
        np.asanyarray(ax),
        np.asanyarray(ay),
        np.asanyarray(bx),
        np.asanyarray(by),
    )
    ad, bd = ax[1] - ax[0], bx[1] - bx[0]  # we assume both have steady step
    if ad == bd:
        return ax, ay, bx, by  # no need to do anything
    elif (np.abs(ad) < np.abs(bd)) ^ upscale:  # xor on booleans
        # `ad` is smaller than `bd`, but we don't want to upscale or vice-versa
        nbx, nby, nax, nay = unify_abscissa(bx, by, ax, ay, upscale)  # swap spectra
        # but return in the same order as given in parameters
    else:
        step = np.abs(ad) * np.sign(bd)  # ad is new step, but sign from bd
        nbx = np.arange(bx[0], bx[-1], step)  # new abscissa
        nby = np.interp(nbx, bx, by)  # interpolate values on new abscissa
        nax, nay = ax, ay  # the other spectrum stays unchanged
    return nax, nay, nbx, nby


def find_offset(
    ax: Numbers, ay: Numbers, bx: Numbers, by: Numbers, upscale: bool = True
) -> float:
    """Finds value, by which the spectrum should be shifted along x-axis to best
    overlap with the first spectrum. If resolution of spectra is not identical,
    one of them will be interpolated to match resolution of the other one. By default
    interpolation is done on the lower-resolution spectra. This can be changed
    by passing `upscale = False` to function call.

    Parameters
    ----------
    ax : sequence of ints or floats
        Abscissa of the first spectrum.
    ay : sequence of ints or floats
        Values of the first spectrum.
    bx : sequence of ints or floats
        Abscissa of the second spectrum.
    by : sequence of ints or floats
        Values of the second spectrum.
    upscale : bool
        If interpolation should be done on more loosely spaced spectrum (default).
        When set to False, spectrum with lower resolution will be treated as reference
        for density of data points.

    Returns
    -------
    float
        Value, by which second spectrum should be shifted, in appropriate units.
    """
    ax, ay, bx, by = unify_abscissa(ax, ay, bx, by, upscale=upscale)
    shift = idx_offset(ay, by)
    if shift < 0:
        offset = ax[0] - bx[abs(shift)]
    else:
        offset = ax[shift] - bx[0]
    return offset


def find_scaling(a: Numbers, b: Numbers) -> float:
    """Find factor by which values `b` should be scaled to best match values `a`.

    Parameters
    ----------
    a : sequence of ints or floats
        `x` values` of the first spectrum.
    b : sequence of ints or floats
        `x` values` of the second spectrum.

    Returns
    -------
    float
        Scaling factor for `b` values.

    Notes
    -----
    If scaling factor cannot be reasonably given, i.e. when `b` is an empty list
    or list of zeros or NaNs, `1.0` is returned.
    """
    scaling = np.mean(np.abs(a)) / np.mean(np.abs(b))
    scaling = 1.0 if np.isnan(scaling) else scaling
    return scaling


# genre: {target: converter}
_converters = {
    "freq": {"wavelen": lambda v: 1e7 / v, "ex_en": lambda v: v / 8065.544},
    "wavelen": {"freq": lambda v: 1e7 / v, "ex_en": lambda v: 1239.8 / v},
    "ex_en": {"freq": lambda v: v * 8065.544, "wavelen": lambda v: 1239.8 / v},
}


def convert_band(
    value: Union[float, np.ndarray], from_genre: str, to_genre: str
) -> Union[float, np.ndarray]:
    """Convert one representation of band to another.

    Parameters
    ----------
    value : float or np.ndarray
        Value(s) to convert.
    from_genre : str
        Genre specifying a representation of band of input data.
        Should be one of: 'freq', 'wavelen', 'ex_en'.
    to_genre : str
        Genre specifying a representation of band, to which you want to convert.
        Should be one of: 'freq', 'wavelen', 'ex_en'.

    Returns
    -------
    float or np.ndarray
        Requested representation of bands. If `from_genre` is same as `to_genre`,
        then simply `value` is returned.
    """
    if from_genre == to_genre:
        return value
    try:
        converter = _converters[from_genre][to_genre]
    except KeyError as error:
        raise ValueError(
            f"Unsupported conversion: from '{from_genre}' to '{to_genre}'. "
            "Genres available for conversion are: 'freq', 'wavelen', 'ex_en'."
        ) from error
    return converter(value)
