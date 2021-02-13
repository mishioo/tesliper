# IMPORTS
import logging as lgg
from typing import Sequence, Union, Any

import numpy as np
from .. import datawork as dw
from .array_base import ArrayBase, ArrayProperty, CollapsibleArrayProperty
from .spectra import Spectra

# LOGGER
from ..datawork.atoms import atomic_number
from ..exceptions import InconsistentDataError

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


# CLASSES
class DataArray(ArrayBase):
    """Base class for data holding objects. It provides trimming functionality
    for filtering data based on other objects content or arbitrary choice.
    ^ this is no longer true, TODO: correct this

    Parameters
    ----------
    filenames : numpy.ndarray(dtype=str)
        List of filenames of gaussian output files, from whitch data were
        extracted.
    values : numpy.ndarray(dtype=float)
        List of appropriate data values.
    """

    # TODO: Supplement full_name_ref

    full_name_ref = dict(
        rot="Rot. Strength",
        dip="Dip. Strength",
        roa1="ROA1",
        raman1="Raman1",
        vrot="Rot. (velo)",
        lrot="Rot. (lenght)",
        vosc="Osc. (velo)",
        losc="Osc. (length)",
        iri="IR Intensity",
        vemang="E-M Angle",
        eemang="E-M Angle",
        zpe="Zero-point Energy",
        ten="Thermal Energy",
        ent="Thermal Enthalpy",
        gib="Thermal Free Energy",
        scf="SCF",
        ex_en="Excitation energy",
        freq="Frequency",
        wave="Wavelength",
        energies="Energies",
    )

    @property
    def full_name(self):
        return self.full_name_ref[self.genre]


class IntegerArray(DataArray):

    associated_genres = ("charge", "multiplicity")
    values = ArrayProperty(dtype=int, check_against="filenames")


class FloatArray(DataArray):

    associated_genres = (
        "zpecorr",
        "tencorr",
        "entcorr",
        "gibcorr",
        "mass",
        "frc",
        "emang",
        "depolarp",
        "depolaru",
        "depp",
        "depu",
        "alpha2",
        "beta2",
        "alphag ",
        "gamma2",
        "delta2",
        "cid1",
        "cid2",
        "cid3",
        "rc180",
        "eemang",
    )
    values = ArrayProperty(dtype=float, check_against="filenames")


class InfoArray(DataArray):
    associated_genres = (
        "command",
        "cpu_time",
        "transitions",
        "stoichiometry",
    )
    values = ArrayProperty(dtype=str, check_against="filenames")


class FilenamesArray(DataArray):
    associated_genres = ("filenames",)
    """Special case of DataArray, holds only filenames. `values` property returns
    same as `filenames` and ignores any value given to its setter.

    Parameters
    ----------
    genre : str
        Name of genre, should be 'filenames'.
    filenames : numpy.ndarray(dtype=str)
        List of filenames of gaussian output files, from which data were extracted.
    values : numpy.ndarray(dtype=str)
        Always returns same as `filenames`.
    """

    def __init__(
        self,
        genre: str = "filenames",
        filenames: Union[Sequence, np.ndarray] = (),
        values: Any = None,
        allow_data_inconsistency: bool = False,
    ):
        super().__init__(genre, filenames, values, allow_data_inconsistency)

    @property
    def values(self):
        return self.filenames

    @values.setter
    def values(self, values):
        pass


class BooleanArray(DataArray):
    associated_genres = ("normal_termination", "optimization_completed")
    values = ArrayProperty(dtype=bool, check_against="filenames")


class Energies(FloatArray):
    """
    Parameters
    ----------
    genre : str
        genre of energy.
    filenames : numpy.ndarray(dtype=str)
        List of filenames of gaussian output files, from which data were
        extracted.
    values : numpy.ndarray(dtype=float)
        Energy value for each conformer.
    t : int or float
        Temperature of calculated state in K."""

    associated_genres = (
        "scf",
        "zpe",
        "ten",
        "ent",
        "gib",
    )

    def __init__(
        self, genre, filenames, values, t=298.15, allow_data_inconsistency=False
    ):
        super().__init__(genre, filenames, values, allow_data_inconsistency)
        self.t = t  # temperature in K

    @property
    def deltas(self):
        """Calculates energy difference between each conformer and lowest energy
        conformer. Converts energy to kcal/mol.

        Returns
        -------
        numpy.ndarray
            List of energy differences from lowest energy in kcal/mol."""
        return dw.calculate_deltas(self.values)

    @property
    def min_factors(self):
        """Calculates list of conformers' Boltzmann factors respective to lowest
        energy conformer in system.

        Notes
        -----
        Boltzmann factor of two states is defined as:
        F(state_1)/F(state_2) = exp((E_1 - E_2)/kt)
        where E_1 and E_2 are energies of states 1 and 2,
        k is Boltzmann constant, k = 0.0019872041 kcal/(mol*K),
        and t is temperature of the system.

        Returns
        -------
        numpy.ndarary
            List of conformers' Boltzmann factors respective to lowest
            energy conformer."""
        # F(state_n)/F(state_min)
        return dw.calculate_min_factors(self.values, self.t)

    @property
    def populations(self):
        """Calculates Boltzmann distribution of conformers.

        Returns
        -------
        numpy.ndarary
            List of conformers populations calculated as Boltzmann
            distribution."""
        return dw.calculate_populations(self.values, self.t)

    def calculate_populations(self, t):
        """Calculates conformers' Boltzmann distribution in given temperature.

        Parameters
        ----------
        t : int or float
            Temperature of calculated state in K."""
        return dw.calculate_populations(self.values, t)


class Averagable:
    """Mix-in for DataArrays, that may be averaged based on populations of conformers."""

    def average_conformers(self: DataArray, energies) -> DataArray:
        """A method for averaging values by population of conformers.

        Parameters
        ----------
        energies : Energies object instance or iterable
            Object with `populations` and `genre` attributes, containing
            respectively: list of populations values as numpy.ndarray and
            string specifying energy type. Alternatively, list of weights
            for each conformer.

        Returns
        -------
        DataArray
            New instance of DataArray's subclass, on which `average` method was
            called, containing averaged values.

        Raises
        ------
            If creation of an instance based on its' __init__ signature is
            impossible.
        """
        # TODO: make sure returning DataArray is necessary and beneficial
        #       maybe it should return just averaged value
        try:
            populations = energies.populations
            energy_type = energies.genre
        except AttributeError:
            populations = np.asanyarray(energies, dtype=float)
            energy_type = "unknown"
        averaged_values = dw.calculate_average(self.values, populations)
        args = self.get_repr_args()
        args["values"] = [averaged_values]
        args["allow_data_inconsistency"] = True
        try:
            averaged = type(self)(**args)
        except (TypeError, ValueError) as err:
            raise TypeError(
                f"Could not create an instance of {type(self)} from its "
                f"signature. Use tesliper.datawork.calculate_average instead."
            ) from err
        logger.debug(f"{self.genre} averaged by {energy_type}.")
        return averaged


class Bars(FloatArray, Averagable):

    associated_genres = ()
    spectra_name_ref = dict(
        rot="vcd",
        dip="ir",
        iri="ir",
        roa1="roa",
        raman1="raman",
        vrot="ecd",
        lrot="ecd",
        vosc="uv",
        losc="uv",
    )
    spectra_type_ref = dict(
        vcd="vibra", ir="vibra", roa="vibra", raman="vibra", ecd="electr", uv="electr"
    )
    _units = dict(
        freq="Frequency / cm^(-1)",
        wave="Wavenlength / nm",
        ex_en="Excitation energy / eV",
        rot="R / 10^(-44) esu^2 cm^2",
        dip="D / 10^(-40) esu^2 cm^2",
        iri="KM/Mole",
        ramact="Raman scattering activities / A^4/AMU",
        roa1="ROA intensiy / 10^4 K",
        raman1="Raman intensity / K",
        roa2="ROA intensiy / 10^4 K",
        raman2="Raman intensity / K",
        roa3="ROA intensiy / 10^4 K",
        raman3="Raman intensity / K",
        vrot="R / 10^(-40) erg*esu*cm/Gauss",
        lrot="R / 10^(-40) erg*esu*cm/Gauss",
        vosc="Oscillator strength",
        losc="Oscillator strength",
        vdip="D / 10^(-44) esu^2 cm^2",
        ldip="D / 10^(-44) esu^2 cm^2",
    )

    def __init__(
        self,
        genre,
        filenames,
        values,
        t=298.15,
        laser=532,
        allow_data_inconsistency=False,
    ):
        super().__init__(genre, filenames, values, allow_data_inconsistency)
        self.t = t  # temperature in K
        self.laser = laser  # in nm
        # rename to raman_laser?

    # TODO: at least one, freq or wave, must be defined by subclass;
    #       include that in docstring
    @property
    def freq(self):
        return 1e7 / self.wavelen

    @property
    def wavelen(self):
        return 1e7 / self.freq

    @property
    def frequencies(self):
        return self.freq

    @property
    def wavelengths(self):
        return self.wavelen

    @property
    def spectra_name(self):
        if self.genre in self.spectra_name_ref:
            return self.spectra_name_ref[self.genre]

    @property
    def spectra_type(self):
        if self.genre in self.spectra_name_ref:
            return self.spectra_type_ref[self.spectra_name]

    @property
    def units(self):
        try:
            return self._units[self.genre]
        except KeyError:
            return ""

    @property
    def intensities(self):
        """Converts spectral activity calculated by quantum chemistry software
        to signal intensity.

        Returns
        -------
        numpy.ndarray
            Signal intensities for each conformer."""
        intensities = dw.calculate_intensities(
            self.genre, self.values, self.frequencies, self.t, self.laser
        )
        return intensities


class GroundStateBars(Bars):
    associated_genres = (
        "freq",
        "iri",
        "dip",
        "rot",
        "ramact",
        "raman1",
        "roa1",
        "raman2 ",
        "roa2",
        "raman3",
        "roa3",
    )

    def __init__(
        self,
        genre,
        filenames,
        values,
        freq,
        t=298.15,
        laser=532,
        allow_data_inconsistency=False,
    ):
        super().__init__(genre, filenames, values, t, laser, allow_data_inconsistency)
        self.freq = freq

    freq = ArrayProperty(check_against="filenames")

    @property
    def imaginary(self):
        """Finds number of imaginary frequencies of each conformer.

        Returns
        -------
        numpy.ndarray
            Number of imaginary frequencies of each conformer."""
        if self.frequencies.size > 0:
            return (self.frequencies < 0).sum(1)
        else:
            return np.array([])

    def find_imaginary(self):
        """Finds all freqs with imaginary values and creates 'imag' entry with
        list of indicants of imaginery values presence.

        Returns
        -------
        dict
            Dictionary of {filename: number-of-imaginary-frequencies} for each
            conformer with at least one imaginary frequency.
        """
        imag = self.imaginary
        return {k: v for k, v in zip(self.filenames, imag) if v}

    def calculate_spectra(self, start, stop, step, width, fitting):
        """Calculates spectrum of desired type for each individual conformer.

        Parameters
        ----------
        start : int or float
            Number representing start of spectral range in relevant units.
        stop : int or float
            Number representing end of spectral range in relevant units.
        step : int or float
            Number representing step of spectral range in relevant units.
        width : int or float
            Number representing half width of maximum peak hight.
        fitting : function
            Function, which takes bars, freqs, abscissa, width as parameters and
            returns numpy.array of calculated, non-corrected spectrum points.

        Returns
        -------
        numpy.ndarray
            Array of 2d arrays containing spectrum (arr[0] is list of
            wavelengths/wave numbers, arr[1] is list of corresponding
            intensity values).
        """
        abscissa = np.arange(start, stop, step)
        freqs = self.frequencies
        inten = self.intensities
        values = dw.calculate_spectra(freqs, inten, abscissa, width, fitting)
        spectra_name = self.spectra_name
        fitting_name = fitting.__name__
        if values.size:
            logger.debug(
                f"Bar {self.genre}: {spectra_name} spectra calculated with "
                f"width = {width} and {fitting_name} fitting."
            )
        spectra = Spectra(
            spectra_name, self.filenames, values, abscissa, width, fitting_name
        )
        return spectra


class ExcitedStateBars(Bars):
    associated_genres = (
        "wave",
        "ex_en",
        "vdip",
        "ldip",
        "vrot",
        "lrot",
        "vosc",
        "losc",
    )

    def __init__(
        self,
        genre,
        filenames,
        values,
        wavelen,
        t=298.15,
        allow_data_inconsistency=False,
    ):
        super().__init__(genre, filenames, values, t, allow_data_inconsistency)
        self.wavelen = wavelen  # in nm

    wavelen = ArrayProperty(check_against="filenames")

    def calculate_spectra(self, start, stop, step, width, fitting):
        """Calculates spectrum of desired type for each individual conformer.

        Parameters
        ----------
        start : int or float
            Number representing start of spectral range in relevant units.
        stop : int or float
            Number representing end of spectral range in relevant units.
        step : int or float
            Number representing step of spectral range in relevant units.
        width : int or float
            Number representing half width of maximum peak hight.
        fitting : function
            Function, which takes bars, freqs, abscissa, width as parameters and
            returns numpy.array of calculated, non-corrected spectrum points.

        Returns
        -------
        numpy.ndarray
            Array of 2d arrays containing spectrum (arr[0] is list of
            wavelengths/wave numbers, arr[1] is list of corresponding
            intensity values).
        """
        abscissa = np.arange(start, stop, step)
        _width = width / 1.23984e-4  # from eV to cm-1
        _abscissa = 1e7 / abscissa  # from nm to cm-1
        freqs = self.frequencies
        inten = self.intensities
        values = dw.calculate_spectra(freqs, inten, _abscissa, _width, fitting)
        spectra_name = self.spectra_name
        fitting_name = fitting.__name__
        if values.size:
            logger.debug(
                f"Bar {self.genre}: {spectra_name} spectra calculated with "
                f"width = {width} and {fitting_name} fitting."
            )
        spectra = Spectra(
            spectra_name, self.filenames, values, abscissa, width, fitting_name
        )
        return spectra


class Geometry(FloatArray):
    """DataArray that stores information about geometry of conformers.

    Attributes
    ----------
    molecule_atoms : numpy.ndarray(dtype=int)
        List of atomic numbers representing atoms in molecule, one for each coordinate.

        Value given to setter should be a list of integers or list of strings, that
        can be interpreted as integers or symbols of atoms. Setter can be given a list
        of lists - one list of atoms for each conformer. All those lists should be
        identical in such case, otherwise InconsistentDataError is raised.
        Only one list of atoms is stored in either case.
    filenames : numpy.ndarray(dtype=str)
        List of filenames of gaussian output files, from which data were extracted.
    values : numpy.ndarray(dtype=float)
        List of x, y, z coordinated for each conformer, for each atom.
    genre : str
        Genre of given data.
    allow_data_inconsistency : bool, optional
        Specifies if inconsistency of data should be allowed when creating instance
        of this class and setting it's attributes. Defaults to `False`.
    """

    associated_genres = ("geometry",)
    values = ArrayProperty(dtype=float, check_against="filenames")
    molecule_atoms = CollapsibleArrayProperty(
        dtype=int,
        check_against="values",
        check_depth=2,
        # TODO: make sanitizer, that accepts jagged nested sequences
        fsan=np.vectorize(atomic_number),
    )

    def __init__(
        self,
        genre: str,
        filenames: Sequence[str],
        values: Sequence[Sequence[Sequence[float]]],
        molecule_atoms: Union[
            Sequence[Union[int, str]], Sequence[Sequence[Union[int, str]]]
        ],
        allow_data_inconsistency: bool = False,
    ):
        super().__init__(genre, filenames, values, allow_data_inconsistency)
        self.molecule_atoms = molecule_atoms
