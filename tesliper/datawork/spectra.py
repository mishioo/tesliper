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
        List of conformers' frequencies.

    Returns
    -------
    numpy.ndarray
        Number of imaginary frequencies of each conformer."""
    if frequencies.size > 0:
        return (frequencies < 0).sum(1)
    else:
        return np.array([])


def find_imaginary(frequencies):
    """Finds all molecules with imaginary frequency values.

    Parameters
    ----------
    frequencies : numpy.ndarray
        List of conformers' frequencies.

    Returns
    -------
    numpy.ndarray
        List of the indices of conformers with imaginary frequency values."""
    imag = count_imaginary(frequencies)
    return np.nonzero(imag)


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
        List of calculated intensity values."""
    sigm = width / 1.4142  # math.sqrt(2), half width at 1/e peak height
    denominator = sigm * 2.5066  # (2 * math.pi) ** 0.5
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
        List of calculated intensity values."""
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
        Array of intensity values for each conformer."""
    # spectrum abscissa, 1d numpy.array of wavenumbers
    spectra = np.zeros([len(frequencies), abscissa.shape[0]])  # template
    for inten, freq, spr in zip(intensities, frequencies, spectra):
        spr[...] = fitting(inten, freq, abscissa, width)
    return spectra


def calculate_average(spectra, populations):
    """Calculates weighted average of spectra, where populations are used as
    weights.

    Parameters
    ----------
    spectra : numpy.ndarray
        List of conformers' spectra, should be of shape (N, M), where N is
        number of conformers and M is number of spectral points.
    populations : numpy.ndarray
        List of conformers' populations, should be of shape (N,) where N is
        number of conformers. Should add up to 1.

    Returns
    -------
    numpy.ndarray
        Averaged spectrum.

    Raises
    ------
    ValueError
        If parameters of non-matching shape were passed.

    TO DO
    -----
    Add checking if populations add up to 1"""
    # populations must be of same shape as spectra
    # so we expand populations with np.newaxis
    popul = populations[:, np.newaxis]
    try:
        return (spectra * popul).sum(0)
    except ValueError:
        raise ValueError(
            f"Cannot broadcast populations of shape {populations.shape} with "
            f"spectra of shape {spectra.shape}."
        )

