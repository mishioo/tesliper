# IMPORTS
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
def dip_to_ir(values, frequencies):
    """Calculates signal intensity of IR spectrum.

    Parameters
    ----------
    values: numpy.ndarray
        Dipol strength values extracted from gaussian output files.
    frequencies: numpy.ndarray
        Frequencies extracted from gaussian output files.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    return values * frequencies / 91.86108673


def rot_to_vcd(values, frequencies):
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
    return values * frequencies / 2.296e5


def osc_to_uv(values):
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


def rot_to_ecd(values, frequencies):
    """Calculates signal intensity of ECD spectrum.

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
    return values * frequencies / 22.96
