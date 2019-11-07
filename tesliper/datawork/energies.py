# IMPORTS
import logging as lgg
import numpy as np


# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# GLOBAL VARIABLES
Boltzmann = 0.0019872041  # kcal/(mol*K)


# MODULE FUNCTIONS
def calculate_deltas(energies):
    """Calculates energy difference between each conformer and lowest energy
    conformer. Converts energy to kcal/mol.

    Parameters
    ----------
    energies : numpy.ndarray or iterable
        List of conformers energies in Hartree units.

    Returns
    -------
    numpy.ndarray
        List of energy differences from lowest energy in kcal/mol."""
    array = np.asanyarray(energies, dtype=float)
    if not array.shape:
        raise TypeError(f"Expected iterable, not '{type(energies)}'")
    # need to reshape if single value given instead of sequence
    try:
        return (array - array.min()) * 627.5095
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
    energies : numpy.ndarray or iterable
        List of conformers energies in Hartree units.
    t : float, optional
        Temperature of the system in K, defaults to 298,15 K.

    Returns
    -------
    numpy.ndarary
        List of conformers' Boltzmann factors respective to lowest
        energy conformer."""
    arr = -calculate_deltas(energies)
    return np.exp(arr / (t * Boltzmann))


def calculate_populations(energies, t=298.15):
    """Calculates Boltzmann distribution of conformers of given energies.

    Parameters
    ----------
    energies : numpy.ndarray or iterable
        List of conformers energies in Hartree units.
    t : float, optional
        Temperature of the system in K, defaults to 298,15 K.

    Returns
    -------
    numpy.ndarary
        List of conformers populations calculated as Boltzmann distribution."""
    arr = calculate_min_factors(energies, t)
    return arr / arr.sum()
