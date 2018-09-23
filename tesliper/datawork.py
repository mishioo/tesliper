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

def delta(energies):
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


def min_factor(energies, t=298.15):
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
    arr = delta(energies)
    return np.exp(arr / (t * Boltzmann))


def population(energies, t=298.15):
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
    arr = min_factor(energies, t)
    return arr / arr.sum()


def count_imaginary(frequencies):
    imag = frequencies < 0
    return imag.sum(1)


def find_imaginary(frequencies):
    """Finds all molecules with imaginary frequency values.

    Parameters
    ----------
    frequencies : numpy.ndarray
        List of conformers' frequencies.

    Returns
    -------
    numpy.ndarray
        List of number of imaginary values in each file."""
    imag = (frequencies < 0).sum(1)
    return np.nonzero(imag)


def gaussian(bar, freq, base, hwhm):
    """Gaussian fitting function for spectra calculation.

    Parameters
    ----------
    bar: numpy.ndarray
        Appropriate values extracted from gaussian output files.
    freq: numpy.ndarray
        Frequencies extracted from gaussian output files.
    base: numpy.ndarray
        List of wavelength/wave number points on spectrum range.
    hwhm: int or float
        Number representing half width of maximum peak hight.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values.
    """
    sigm = hwhm / math.sqrt(2 * math.log(2))
    it = np.nditer(
        [base, None], flags=['buffered'],
        op_flags=[['readonly'], ['writeonly', 'allocate', 'no_broadcast']],
        op_dtypes=[np.float64, np.float64]
    )
    for lam, peaks in it:
        e = bar * np.exp(-0.5 * ((lam - freq) / sigm) ** 2)
        peaks[...] = e.sum() / (sigm * (2 * math.pi) ** 0.5)
    return it.operands[1]


def lorentzian(bar, freq, base, hwhm):
    """Lorentzian fitting function for spectra calculation.

    Parameters
    ----------
    bar: numpy.ndarray
        Appropriate values extracted from gaussian output files.
    freq: numpy.ndarray
        Frequencies extracted from gaussian output files.
    base: numpy.ndarray
        List of wavelength/wave number points on spectrum range.
    hwhm: int or float
        Number representing half width of maximum peak hight.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values.
    """
    it = np.nditer(
        [base, None], flags=['buffered'],
        op_flags=[['readonly'], ['writeonly', 'allocate', 'no_broadcast']],
        op_dtypes=[np.float64, np.float64]
    )
    for lam, val in it:
        s = bar / ((freq - lam) ** 2 + hwhm ** 2)
        s2 = hwhm / math.pi * s.sum()
        val[...] = s2
    return it.operands[1]


def intensities(bars, frequencies, genre, t=289.15, laser=532):
    pass


def calculate_spectra(frequencies, intensities, start, stop, step, hwhm,
                      fitting):
    """Calculates spectrum for each individual conformer.

    Parameters
    ----------
    frequencies : numpy.ndarray
        List of conformers' frequencies. Should be of shape
        (number _of_conformers, number_of_frequencies).
    intensities : numpy.ndarray
        List of calculated signal intensities for each conformer. Should be
        of same shape as frequencies.
    start : int or float
        Number representing begining of spectral range in cm^(-1).
    stop : int or float
        Number representing end of spectral range in cm^(-1).
    step : int or float
        Number representing step of spectral range in cm^(-1).
    hwhm : int or float
        Number representing half width of maximum peak height in cm^(-1).
    fitting : function
        Function, which takes bars, freqs, base, hwhm as parameters and
        returns numpy.array of calculated, non-corrected spectrum points.

    Returns
    -------
    numpy.ndarray
        Array of intensity values for each conformer.
    """
    abscissa = np.arange(start, stop + step, step)
    spectra = np.zeros([len(frequencies), abscissa.shape[0]])  # template
    for bar, freq, spr in zip(intensities, frequencies, spectra):
        spr[...] = fitting(bar, freq, abscissa, hwhm)
    return spectra  # , base ?


def average(spectra, populations):
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
    if not spectra.shape == popul.shape:
        raise ValueError(
            f"Cannot broadcast populations of shape {populations.shape} with"
            f"spectra of shape {spectra.shape}."
        )
    return (spectra * popul).sum(0)
