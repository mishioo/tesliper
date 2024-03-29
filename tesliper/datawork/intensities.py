"""Optical activity to signal intensity converters."""

import logging as lgg

import numpy as np

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# GLOBAL VARIABLES
DEFAULT_ACTIVITIES = {
    "ir": "dip",
    "vcd": "rot",
    "uv": "vosc",
    "ecd": "vrot",
    "raman": "raman1",
    "roa": "roa1",
}


# MODULE FUNCTIONS
def dip_to_ir(values: np.ndarray, frequencies: np.ndarray) -> np.ndarray:
    """Calculates signal intensity of IR spectrum.

    Parameters
    ----------
    values: numpy.ndarray
        Dipole strength values extracted from gaussian output files.
    frequencies: numpy.ndarray
        Frequencies extracted from gaussian output files.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    return values * frequencies * 0.010886


def rot_to_vcd(values: np.ndarray, frequencies: np.ndarray) -> np.ndarray:
    """Calculates signal intensity of VCD spectrum.

    Parameters
    ----------
    values: numpy.ndarray
        Rotator strength values extracted from gaussian output files.
    frequencies: numpy.ndarray
        Frequencies extracted from gaussian output files.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    return values * frequencies * 0.0435441


def osc_to_uv(values: np.ndarray) -> np.ndarray:
    """Calculates signal intensity of UV spectrum.

    Parameters
    ----------
    values: numpy.ndarray
        Oscillator strength values extracted from gaussian output files.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    return values * 2.315351857e08


def rot_to_ecd(values: np.ndarray, wavelengths: np.ndarray) -> np.ndarray:
    """Calculates signal intensity of ECD spectrum.

    Parameters
    ----------
    values: numpy.ndarray
        Rotator strength values extracted from gaussian output files.
    wavelengths: numpy.ndarray
        Wavelengths extracted from gaussian output files.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    return values * wavelengths * 0.0435441


def dip_to_uv(values: np.ndarray, wavelengths: np.ndarray) -> np.ndarray:
    """Calculates signal intensity of UV spectrum.

    Parameters
    ----------
    values: numpy.ndarray
        Dipole strength values extracted from gaussian output files.
    wavelengths: numpy.ndarray
        Wavelengths extracted from gaussian output files.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    return values * wavelengths * 0.010886
