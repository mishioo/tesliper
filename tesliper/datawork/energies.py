"""Functions for calculating populations of conformers based on their relative energies
using Boltzmann distribution.
"""

# IMPORTS
import logging as lgg

import numpy as np

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# GLOBAL VARIABLES
BOLTZMANN = 0.0019872041
"""Value of Boltzmann constant in kcal/(mol*K)."""

HARTREE_TO_KCAL_PER_MOL = 627.5095
"""Multiply by this factor to convert from Hartree/mol to kcal/mol."""


# MODULE FUNCTIONS
def calculate_deltas(energies):
    """Calculates energy difference between each conformer and lowest energy conformer.

    Parameters
    ----------
    energies : numpy.ndarray or iterable of float
        List of conformers energies.

    Returns
    -------
    numpy.ndarray
        List of energy differences from lowest energy."""
    array = np.asanyarray(energies, dtype=float)
    if not array.shape:
        raise TypeError(f"Expected iterable, not '{type(energies)}'")
    # need to reshape if single value given instead of sequence
    try:
        return array - array.min()
    except ValueError:
        # if no values, return empty array.
        return np.array([])


def calculate_min_factors(energies, t=298.15):
    """Calculates list of conformers' Boltzmann factors respective to lowest
    energy conformer in system of given temperature.

    Notes
    -----
    Boltzmann factor of two states is defined as:

    .. math::

        \frac{F(state_1)}{F(state_2)} = e^{(E_2 - E_1)/kt}

    where :math:`E_1` and :math:`E_2` are energies of states 1 and 2,
    :math:`k` is Boltzmann constant, :math:`k = 0.0019872041 kcal/(mol*K)`,
    and :math:`t` is temperature of the system.

    Parameters
    ----------
    energies : numpy.ndarray or iterable
        List of conformers energies in kcal/mol units.
    t : float, optional
        Temperature of the system in K, defaults to 298,15 K.

    Returns
    -------
    numpy.ndarary
        List of conformers' Boltzmann factors respective to lowest
        energy conformer."""
    arr = -calculate_deltas(energies)
    return np.exp(arr / (t * BOLTZMANN))


def calculate_populations(energies, t=298.15):
    """Calculates Boltzmann distribution of conformers of given energies.

    Parameters
    ----------
    energies : numpy.ndarray or iterable
        List of conformers energies in kcal/mol units.
    t : float, optional
        Temperature of the system in K, defaults to 298,15 K.

    Returns
    -------
    numpy.ndarary
        List of conformers populations calculated as Boltzmann distribution."""
    arr = calculate_min_factors(energies, t)
    return arr / arr.sum()
