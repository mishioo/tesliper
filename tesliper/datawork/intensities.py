# IMPORTS
import logging as lgg

import numpy as np

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# GLOBAL VARIABLES
default_spectra_bars = {
    "ir": "dip",
    "vcd": "rot",
    "uv": "vosc",
    "ecd": "vrot",
    "raman": "raman1",
    "roa": "roa1",
}


# TODO: refactor this module:
#       - remove generic calculate_intensities function
#       - bind other functions more closely to corresponding `DataArray`s
#       - figure out how to handle intensities genres like "iri" and "raman"


# MODULE FUNCTIONS
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


def ramanx_to_raman(values, frequencies, t=289.15, laser=18797):
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
        18797 cm^(-1) = 532 nm.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    f = 1.6099098823816564e-8  # my math says e-35, but it gives wrong results
    # f = 9.695104081272649e-08
    e = 1 - np.exp(-1.438775 * frequencies / t)
    out = f * (laser - frequencies) ** 4 / (frequencies * e)
    return values * out


def roax_to_roa(values, frequencies, t=289.15, laser=18797):
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
        18797 cm^(-1) = 532 nm.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values."""
    return ramanx_to_raman(values, frequencies, t, laser)


def raman_and_roa(values, *args, **kwargs):
    """Returns values as passed, ignoring any other args and kwargs.
    Introduced for consistency of intensities calculation.

    Parameters
    ----------
    values: numpy.ndarray

    Returns
    -------
    numpy.ndarray
        Values passed to this function."""
    return values


intensities_reference = dict(
    dip=dip_to_ir,
    rot=rot_to_vcd,
    vosc=osc_to_uv,
    losc=osc_to_uv,
    vrot=rot_to_ecd,
    lrot=rot_to_ecd,
    ramact=raman_and_roa,
    raman1=raman_and_roa,
    raman2=raman_and_roa,
    raman3=raman_and_roa,
    roa1=raman_and_roa,
    roa2=raman_and_roa,
    roa3=raman_and_roa,
)


def calculate_intensities(genre, values, frequencies=None, t=289.15, laser=18797):
    """Calculates signal intensity of desired type.

    Notes
    -----
    It seems that Raman and ROA intensities are simply values extracted from
    Gaussian files. For now they are returned as they are.

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
        and ROA calculations (currently not used at all).
    laser: int, optional
        Frequency of laser used for excitation,, in cm^(-1), defaults to
        18797 cm^(-1) = 532 nm. Used only in Raman and ROA calculations
        (currently not used at all).

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
            f"Invalid genre: '{genre}'. Can't convert genre to signal " f"intensity."
        )
    return calculate(values, frequencies, t, laser)
