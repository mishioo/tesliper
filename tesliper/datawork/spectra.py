# IMPORTS
import logging as lgg
import math
import numpy as np


# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


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
            f'Array with {frequencies.ndim} dimensions can\'t be interpreted '
            f'as a list of conformers\' frequencies.'
        )


def find_imaginary(frequencies):
    """Finds all molecules with imaginary frequency values.

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
        raise ValueError('Peak width must be a positive value!')
    if intensities.shape != frequencies.shape:
        raise ValueError(
            '`intensities` and `frequencies` must be of same shape!'
        )
    if abscissa.size == 0:
        return np.array([])
    sigm = width / 1.4142135623730951  # math.sqrt(2)
    denominator = sigm * 2.5066282746310002  # (2 * math.pi) ** 0.5
    it = np.nditer(
        [abscissa, None], flags=['buffered'],
        op_flags=[['readonly'], ['writeonly', 'allocate', 'no_broadcast']],
        op_dtypes=[np.float64, np.float64]
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
        raise ValueError('Peak width must be a positive value!')
    if intensities.shape != frequencies.shape:
        raise ValueError(
            '`intensities` and `frequencies` must be of same shape!'
        )
    if abscissa.size == 0:
        return np.array([])
    hwhmsqrd = width ** 2
    hwhmoverpi = width / math.pi
    it = np.nditer(
        [abscissa, None], flags=['buffered'],
        op_flags=[['readonly'], ['writeonly', 'allocate', 'no_broadcast']],
        op_dtypes=[np.float64, np.float64]
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
        raise ValueError(
            '`intensities` and `frequencies` must be of same shape!'
        )
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
    popsum = populations.sum()
    if not np.isclose(popsum, 1):
        # normalize population data, if needed
        populations = populations / popsum
    # populations must be of same shape as values array
    # so we expand populations with appropriate number of dimensions
    shape = (-1,) + (1,) * (values.ndim - 1)
    popul = populations.reshape(*shape)
    return (values * popul).sum(0)
