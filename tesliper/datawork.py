###################
###   IMPORTS   ###
###################

import logging as lgg
import math
import numpy as np


##################
###   LOGGER   ###
##################

logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


############################
###   GLOBAL VARIABLES   ###
############################

default_spectra_bars = {
    'ir': 'dip',
    'vcd': 'rot',
    'uv': 'vosc',
    'ecd': 'vrot',
    'raman': 'raman1',
    'roa': 'roa1'
}

Boltzmann = 0.0019872041  # kcal/(mol*K)


############################
###   MODULE FUNCTIONS   ###
############################

def calculate_deltas(energies):
    """Calculates energy difference between each conformer and lowest energy
    conformer. Converts energy to kcal/mol.

    Parameters
    ----------
    energies : numpy.ndarray
        List of conformers energies in Hartree units.

    Returns
    -------
    numpy.ndarray
        List of energy differences from lowest energy in kcal/mol."""
    try:
        return (energies - energies.min()) * 627.5095
        # convert hartree to kcal/mol by multiplying by 627.5095
    except ValueError:
        # if no values, return empty array.
        return np.array([])


def calculate_min_factors(energies, t=298.15):
    """Calculates list of conformers' Boltzmann factors respective to lowest
    energy conformer in system of given temperature.

    Notes
    -----
    Boltzmann factor of two states is defined as:
    F(state_1)/F(state_2) = exp((E_1 - E_2)/kt)
    where E_1 and E_2 are energies of states 1 and 2,
    k is Boltzmann constant, k = 0.0019872041 kcal/(mol*K),
    and t is temperature of the system.

    Parameters
    ----------
    energies : numpy.ndarray
        List of conformers energies in Hartree units.
    t : float, optional
        Temperature of the system in K, defaults to 298,15 K.

    Returns
    -------
    numpy.ndarary
        List of conformers' Boltzmann factors respective to lowest
        energy conformer."""
    arr = calculate_deltas(energies)
    return np.exp(arr / (t * Boltzmann))


def calculate_populations(energies, t=298.15):
    """Calculates Boltzmann distribution of conformers of given energies.

    Parameters
    ----------
    energies : numpy.ndarray
        List of conformers energies in Hartree units.
    t : float, optional
        Temperature of the system in K, defaults to 298,15 K.

    Returns
    -------
    numpy.ndarary
        List of conformers populations calculated as Boltzmann distribution."""
    arr = calculate_min_factors(energies, t)
    return arr / arr.sum()


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


def dip_to_ir(values, frequencies, *args, **kwargs):
    """Calculates signal intensity of IR spectrum.

    Parameters
    ----------
    values: numpy.ndarray
        Dipol strength values extracted from gaussian output files.
    frequencies: numpy.ndarray
        Frequencies extracted from gaussian output files.

    Notes
    -----
    Any additional args and kwargs will be ignored.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    return values * frequencies / 91.86108673


def rot_to_vcd(values, frequencies, *args, **kwargs):
    """Calculates signal intensity of VCD spectrum.

    Parameters
    ----------
    values: numpy.ndarray
        Rotator strength values extracted from gaussian output files.
    frequencies: numpy.ndarray
        Frequencies extracted from gaussian output files.

    Notes
    -----
    Any additional args and kwargs will be ignored.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    return values * frequencies / 2.296e5


def osc_to_uv(values, *args, **kwargs):
    """Calculates signal intensity of UV spectrum.

    Parameters
    ----------
    values: numpy.ndarray
        Oscillator strength values extracted from gaussian output files.

    Notes
    -----
    Any additional args and kwargs will be ignored.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    return values * 2.315351857e08


def rot_to_ecd(values, frequencies, *args, **kwargs):
    """Calculates signal intensity of ECD spectrum.

    Parameters
    ----------
    values: numpy.ndarray
        Rotator strength values extracted from gaussian output files.
    frequencies: numpy.ndarray
        Frequencies extracted from gaussian output files.

    Notes
    -----
    Any additional args and kwargs will be ignored.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    return values * frequencies / 22.96


def ramanx_to_raman(values, frequencies, t=289.15, laser=18796.99):
    """Calculates signal intensity of Raman spectrum.

    Parameters
    ----------
    values: numpy.ndarray
        RamanX values extracted from gaussian output files.
    frequencies: numpy.ndarray
        Frequencies extracted from gaussian output files, in cm^(-1).
    t: float, optional
        Temperature of the system in K, defaults to 298,15 K.
    laser: int, optional
        Frequency of laser used for excitation, in cm^(-1), defaults to
        18796.99 cm^(-1) = 532 nm.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    f = 9.695104081272649e-08
    e = 1 - np.exp(-14387.751601679205 * frequencies / t)
    out = f * (laser - frequencies) ** 4 / (frequencies * e)
    return values * out


def roax_to_roa(values, frequencies, t=289.15, laser=18796.99):
    """Calculates signal intensity of ROA spectrum.

    TO DO
    -----
    Figure out correct calculations (for now calculated as raman)

    Parameters
    ----------
    values: numpy.ndarray
        ROAX values extracted from gaussian output files.
    frequencies: numpy.ndarray
        Frequencies extracted from gaussian output files, in cm^(-1).
    t: float, optional
        Temperature of the system in K, defaults to 298,15 K.
    laser: int, optional
        Frequency of laser used for excitation, in cm^(-1), defaults to
        18796.99 cm^(-1) = 532 nm.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    return ramanx_to_raman(values, frequencies, t, laser)


intensities_reference = dict(
    dip=dip_to_ir,
    rot=rot_to_vcd,
    vosc=osc_to_uv,
    losc=osc_to_uv,
    vrot=rot_to_ecd,
    lrot=rot_to_ecd,
    raman1=ramanx_to_raman,
    raman2=ramanx_to_raman,
    raman3=ramanx_to_raman,
    roa1=roax_to_roa,
    roa2=roax_to_roa,
    roa3=roax_to_roa
)


def calculate_intensities(genre, values, frequencies=None, t=289.15,
                          laser=18796.99):
    """Calculates signal intensity of desired type.

    Parameters
    ----------
    genre: str
        Genre of passed values, that are to be converted to intensities
    values: numpy.ndarray
        Values extracted from gaussian output files.
    frequencies: numpy.ndarray
        Frequencies extracted from gaussian output files in cm^(-1).
    t: float, optional
        Temperature of the system in K, defaults to 298,15 K. Used only in Raman
        and Roa calculations.
    laser: int, optional
        Frequency of laser used for excitation,, in cm^(-1), defaults to
        18796.99 cm^(-1) = 532 nm. Used only in Raman and Roa calculations.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values.

    Raises
    ------
    ValueError if unsupported or unknown genre passed."""
    try:
        calculate = intensities_reference[genre]
    except KeyError:
        raise ValueError(
            f"Invalid genre: '{genre}'. Can't convert genre to signal "
            f"intensity."
        )
    return calculate(values, frequencies, t, laser)


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

