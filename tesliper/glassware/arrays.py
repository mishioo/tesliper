# IMPORTS
import logging as lgg
from abc import ABC, abstractmethod
from typing import Any, Sequence, Tuple, Union

import numpy as np

from .. import datawork as dw
from ..datawork import convert_band
from ..datawork.atoms import atomic_number
from .array_base import (
    ArrayBase,
    ArrayProperty,
    CollapsibleArrayProperty,
    JaggedArrayProperty,
)
from .spectra import Spectra

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


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

    full_name_ref = {}
    _units = {}

    @property
    def full_name(self):
        try:
            return self.full_name_ref[self.genre]
        except KeyError:
            return ""

    @property
    def units(self):
        try:
            return self._units[self.genre]
        except KeyError:
            return ""


class IntegerArray(DataArray):

    associated_genres = ("charge", "multiplicity")
    full_name_ref = {"charge": "Charge", "multiplicity": "Multiplicity"}
    values = ArrayProperty(dtype=int, check_against="filenames")


class FloatArray(DataArray):
    associated_genres = (
        "zpecorr",
        "tencorr",
        "entcorr",
        "gibcorr",
    )
    full_name_ref = dict(
        zpecorr="Zero-point Correction",
        tencorr="Correction to Energy",
        entcorr="Correction to Enthalpy",
        gibcorr="Correction to Free Energy",
    )
    _units = dict(
        zpecorr="Hartree",
        tencorr="Hartree",
        entcorr="Hartree",
        gibcorr="Hartree",
    )

    values = ArrayProperty(dtype=float, check_against="filenames")


class InfoArray(DataArray):
    full_name_ref = {
        "command": "Command",
        "cpu_time": "CPU Time",
        "stoichiometry": "Stoichiometry",
    }
    _units = {}
    associated_genres = (
        "command",
        "cpu_time",
        "stoichiometry",
    )
    values = ArrayProperty(dtype=str, check_against="filenames")


class FilenamesArray(DataArray):
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

    associated_genres = ("filenames",)
    full_name_ref = {"filenames": "Filenames"}
    _units = {}

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
        # ignore attempts at setting values
        pass


class BooleanArray(DataArray):
    full_name_ref = {
        "normal_termination": "Normal Termination",
        "optimization_completed": "Optimization Completed",
    }
    _units = {}
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

    full_name_ref = dict(
        zpe="Zero-point Energy",
        ten="Thermal Energy",
        ent="Thermal Enthalpy",
        gib="Thermal Free Energy",
        scf="SCF",
    )
    _units = dict(
        zpe="Hartree",
        ten="Hartree",
        ent="Hartree",
        gib="Hartree",
        scf="Hartree",
    )
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
    def as_kcal_per_mol(self):
        """Energy values converted to kcal/mol."""
        # convert hartree to kcal/mol by multiplying by 627.5095
        return self.values * dw.energies.HARTREE_TO_KCAL_PER_MOL

    @property
    def deltas(self):
        """Calculates energy difference between each conformer and lowest energy
        conformer. Converts energy to kcal/mol.

        Returns
        -------
        numpy.ndarray
            List of energy differences from lowest energy in kcal/mol."""
        return dw.calculate_deltas(self.as_kcal_per_mol)

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
        return dw.calculate_min_factors(self.as_kcal_per_mol, self.t)

    @property
    def populations(self):
        """Calculates Boltzmann distribution of conformers.

        Returns
        -------
        numpy.ndarary
            List of conformers populations calculated as Boltzmann
            distribution."""
        return dw.calculate_populations(self.as_kcal_per_mol, self.t)

    def calculate_populations(self, t):
        """Calculates conformers' Boltzmann distribution in given temperature.

        Parameters
        ----------
        t : int or float
            Temperature of calculated state in K."""
        return dw.calculate_populations(self.as_kcal_per_mol, t)


class Averagable:
    """Mix-in for DataArray subclasses, that may be averaged based on populations
    of conformers."""

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


class Bands(FloatArray):
    associated_genres = ("freq", "wavelen", "ex_en")
    full_name_ref = {
        "ex_en": "Excitation energy",
        "freq": "Frequency",
        "wavelen": "Wavelength",
    }
    _units = {"freq": "cm^(-1)", "wavelen": "nm", "ex_en": "eV"}

    def __init__(
        self,
        genre,
        filenames,
        values,
        allow_data_inconsistency=False,
    ):
        super().__init__(genre, filenames, values, allow_data_inconsistency)

    @property
    def freq(self):
        """Values converted to frequencies in cm^(-1).
        Same as `Bands.frequencies`
        """
        return convert_band(self.values, from_genre=self.genre, to_genre="freq")

    @property
    def frequencies(self):
        """Values converted to frequencies in cm^(-1).
        Same as `Bands.freq`
        """
        return self.freq

    @property
    def wavelen(self):
        """Values converted to wavelengths in nm.
        Same as `Bands.wavelengths`
        """
        return convert_band(self.values, from_genre=self.genre, to_genre="wavelen")

    @property
    def wavelengths(self):
        """Values converted to wavelengths in nm.
        Same as `Bands.wavelen`
        """
        return self.wavelen

    @property
    def ex_en(self):
        """Values converted to excitation_energy in eV.
        Same as `Bands.excitation_energy`
        """
        return convert_band(self.values, from_genre=self.genre, to_genre="ex_en")

    @property
    def excitation_energy(self):
        """Values converted to excitation_energy in eV.
        Same as `Bands.ex_en`
        """
        return self.ex_en

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


class SpectralData(FloatArray, ABC):
    """Base class for spectral data genres, that are not spectral activities."""

    # TODO: Supplement tests regarding this class' subclasses

    associated_genres = ()

    @property
    @abstractmethod
    def spectra_type(self):
        return NotImplemented

    @property
    @abstractmethod
    def freq(self):
        return convert_band(self.wavelen, from_genre="wavelen", to_genre="freq")

    @property
    def frequencies(self):
        return self.freq

    @property
    @abstractmethod
    def wavelen(self):
        return convert_band(self.wavelen, from_genre="freq", to_genre="wavelen")

    @property
    def wavelengths(self):
        return self.wavelen


class _VibData(SpectralData):
    freq = ArrayProperty(check_against="filenames")
    associated_genres = ()

    def __init__(
        self,
        genre,
        filenames,
        values,
        freq,
        allow_data_inconsistency=False,
    ):
        super().__init__(genre, filenames, values, allow_data_inconsistency)
        self.freq = freq

    @property
    def wavelen(self):
        return super().wavelen


class VibrationalData(_VibData):
    associated_genres = ("mass", "frc", "emang")
    full_name_ref = dict(
        mass="Reduced masses", frc="Force constants", emang="E-M Angle"
    )
    _units = dict(mass="AMU", frc="mDyne/A", emang="deg")

    @property
    def spectra_type(self):
        return "vibrational"


class ScatteringData(_VibData):
    associated_genres = (
        "depolarp",
        "depolaru",
        "depp",
        "depu",
        "alpha2",
        "beta2",
        "alphag",
        "gamma2",
        "delta2",
        "cid1",
        "cid2",
        "cid3",
        "rc180",
    )
    full_name_ref = {
        "depolarp": "Depolar-P Raman",
        "depolaru": "Depolar-U Raman",
        "depp": "Depolar-P ROA",
        "depu": "Depolar-U ROA",
        "alpha2": "Raman invariant Alpha2",
        "beta2": "Raman invariant Beta2",
        "alphag": "ROA invariant AlphaG",
        "gamma2": "ROA invariant Gamma2",
        "delta2": "ROA invariant Delta2",
        "cid1": "CID ICPu/SCPu(180)",
        "cid2": "CID ICPd/SCPd(90)",
        "cid3": "CID DCPI(180)",
        "rc180": "Degree of circularity",
    }
    _units = {
        "alpha2": "(A**4/AMU)",
        "beta2": "(A**4/AMU)",
        "alphag": "(10**4 A**5/AMU)",
        "gamma2": "(10**4 A**5/AMU)",
        "delta2": "(10**4 A**5/AMU)",
    }

    @property
    def spectra_type(self):
        return "scattering"

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
        super().__init__(genre, filenames, values, freq, allow_data_inconsistency)
        self.laser = laser  # in nm
        self.t = t  # temperature in K


class ElectronicData(SpectralData):
    wavelen = ArrayProperty(check_against="filenames")
    associated_genres = ("eemang",)
    full_name_ref = dict(eemang="E-M Angle")
    _units = dict(eemang="deg")

    @property
    def spectra_type(self):
        return "electronic"

    def __init__(
        self,
        genre,
        filenames,
        values,
        wavelen,
        allow_data_inconsistency=False,
    ):
        super().__init__(genre, filenames, values, allow_data_inconsistency)
        self.wavelen = wavelen  # in nm

    @property
    def freq(self):
        return super().freq


class SpectralActivities(SpectralData, Averagable, ABC):
    """Base class for spectral activities genres."""

    associated_genres = ()
    spectra_name_ref = dict(
        rot="vcd",
        dip="ir",
        iri="ir",
        ramact="raman",
        raman1="raman",
        roa1="roa",
        raman2="raman",
        roa2="roa",
        raman3="raman",
        roa3="roa",
        vrot="ecd",
        lrot="ecd",
        vosc="uv",
        losc="uv",
        vdip="uv",
        ldip="uv",
    )
    full_name_ref = dict()
    _units = dict()
    _intensities_converters = {}

    @property
    def spectra_name(self):
        if self.genre in self.spectra_name_ref:
            return self.spectra_name_ref[self.genre]

    @property
    def intensities(self):
        """Converts spectral activity calculated by quantum chemistry software
        to signal intensity.

        Returns
        -------
        numpy.ndarray
            Signal intensities for each conformer.

        Raises
        ------
        NotImplementedError
            if genre does not provide values conversion to intensities."""
        try:
            converter = self._intensities_converters[self.genre]
        except KeyError:
            raise NotImplementedError(
                f"Genre {self.genre} does not provide conversion to intensities."
            )
        return converter(self.values, self.frequencies)

    @abstractmethod
    def calculate_spectra(self, start, stop, step, width, fitting):
        return NotImplemented


def _as_is(values, *_args, **_kwargs):
    return values


class _VibAct(_VibData, SpectralActivities):
    def calculate_spectra(self, start, stop, step, width, fitting):
        """Calculates spectrum for each individual conformer.

        Parameters
        ----------
        start : int or float
            Number representing start of spectral range in relevant units.
        stop : int or float
            Number representing end of spectral range in relevant units.
        step : int or float
            Number representing step of spectral range in relevant units.
        width : int or float
            Number representing half width of maximum peak height.
        fitting : function
            Function, which takes spectral data, freqs, abscissa, width as parameters
            and returns numpy.array of calculated, non-corrected spectrum points.

        Returns
        -------
        SingleSpectrum
            Calculated spectrum.

        Raises
        ------
        ValueError
            If given `start`, `stop`, and `step` values would produce an empty
            or one-element sequence; i.e. if `start` is grater than `stop` or if
            `start - stop < step`, assuming `step` is a positive value.
        """
        abscissa = np.arange(start, stop, step)
        if abscissa.size <= 1:
            raise ValueError(
                f"Not enough data points between start = {start} and stop = {stop} "
                f"with step = {step}. Please provide start, stop, and step values "
                "that will produce at least two-element sequence."
            )
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


class VibrationalActivities(VibrationalData, _VibAct):
    associated_genres = (
        "iri",
        "dip",
        "rot",
    )
    _intensities_converters = {
        "dip": dw.dip_to_ir,
        "rot": dw.rot_to_vcd,
        "iri": _as_is,
    }
    full_name_ref = dict(
        rot="Rot. Strength",
        dip="Dip. Strength",
        iri="IR Intensity",
    )
    _units = dict(
        rot="10^(-44) esu^2 cm^2",
        dip="10^(-40) esu^2 cm^2",
        iri="KM/Mole",
    )


class ScatteringActivities(ScatteringData, _VibAct):
    associated_genres = (
        "ramanactiv",
        "ramact",
        "raman1",
        "roa1",
        "raman2",
        "roa2",
        "raman3",
        "roa3",
    )
    full_name_ref = dict(
        ramanactiv="Raman scatt. activities",
        ramact="Raman scatt. activities",
        roa1="ROA inten. ICPu/SCPu(180)",
        raman1="Raman inten. ICPu/SCPu(180)",
        roa2="ROA inten. ICPd/SCPd(90)",
        raman2="Raman inten. ICPd/SCPd(90)",
        roa3="ROA inten. DCPI(180)",
        raman3="Raman inten. DCPI(180)",
    )
    _units = dict(
        ramanactiv="A^4/AMU",
        ramact="A^4/AMU",
        roa1="10^4 K",
        raman1="K",
        roa2="10^4 K",
        raman2="K",
        roa3="10^4 K",
        raman3="K",
    )
    _intensities_converters = {
        "ramanactiv": _as_is,
        "ramact": _as_is,
        "raman1": _as_is,
        "roa1": _as_is,
        "raman2": _as_is,
        "roa2": _as_is,
        "raman3": _as_is,
        "roa3": _as_is,
    }

    @property
    def intensities(self):
        """Converts spectral activity calculated by quantum chemistry software
        to signal intensity.

        Returns
        -------
        numpy.ndarray
            Signal intensities for each conformer.

        Raises
        ------
        NotImplementedError
            if genre does not provide values conversion to intensities."""
        try:
            converter = self._intensities_converters[self.genre]
        except KeyError:
            return super().intensities
        return converter(self.values, self.frequencies, self.t, self.laser)


class ElectronicActivities(ElectronicData, SpectralActivities):
    associated_genres = (
        "vdip",
        "ldip",
        "vrot",
        "lrot",
        "vosc",
        "losc",
    )
    full_name_ref = dict(
        vrot="Rot. (velo)",
        lrot="Rot. (lenght)",
        vosc="Osc. (velo)",
        losc="Osc. (length)",
        vdip="Dip. (velo)",
        ldip="Dip. (length)",
    )
    _units = dict(
        vrot="10^(-40) erg*esu*cm/Gauss",
        lrot="10^(-40) erg*esu*cm/Gauss",
        vdip="10^(-44) esu^2 cm^2",
        ldip="10^(-44) esu^2 cm^2",
    )
    _intensities_converters = {
        # for "osc" ignore frequencies given by default by super().intensities
        "vosc": lambda v, _: dw.osc_to_uv(v),
        "losc": lambda v, _: dw.osc_to_uv(v),
        "vrot": dw.rot_to_ecd,
        "lrot": dw.rot_to_ecd,
        # TODO: add "ldip" and "vdip"
        "ldip": lambda *_: NotImplemented,
        "vdip": lambda *_: NotImplemented,
    }

    def calculate_spectra(self, start, stop, step, width, fitting):
        """Calculates spectrum for each individual conformer.

        Parameters
        ----------
        start : int or float
            Number representing start of spectral range in relevant units.
        stop : int or float
            Number representing end of spectral range in relevant units.
        step : int or float
            Number representing step of spectral range in relevant units.
        width : int or float
            Number representing half width of maximum peak height.
        fitting : function
            Function, which takes spectral data, freqs, abscissa, width as parameters
            and returns numpy.array of calculated, non-corrected spectrum points.

        Returns
        -------
        SingleSpectrum
            Calculated spectrum.

        Raises
        ------
        ValueError
            If given `start`, `stop`, and `step` values would produce an empty
            or one-element sequence; i.e. if `start` is grater than `stop` or if
            `start - stop < step`, assuming `step` is a positive value.
        """
        abscissa = np.arange(start, stop, step)
        if abscissa.size <= 1:
            raise ValueError(
                f"Not enough data points between start = {start} and stop = {stop} "
                f"with step = {step}. Please provide start, stop, and step values "
                "that will produce at least two-element sequence."
            )
        _width = convert_band(
            width, from_genre="ex_en", to_genre="freq"
        )  # from eV to cm-1
        _abscissa = convert_band(
            abscissa, from_genre="wavelen", to_genre="freq"
        )  # from nm to cm-1
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


class Transitions(DataArray):
    """DataArray that stores information about electronic transitions from ground
    to excited state contributing to each band.

    Data is stored in three attributes: `ground`, `excited`, and `values`, which are
    respectively: list of ground state electronic subshells, list of excited state
    electronic subshells, and list of coefficients of transitions from corresponding
    ground to excited subshell. Each of these arrays is of shape (conformers, bands,
    max_transitions), where 'max_transitions' is a highest number of transitions
    contributing to single band across all bands of all conformers.

    Attributes
    ----------
    filenames : numpy.ndarray(dtype=str)
        List of filenames of gaussian output files, from which data were extracted.
    values : numpy.ndarray(dtype=float)
        List of coefficients of each transition. It is a 3-dimensional of shape
        (conformers, bands, max_transitions).
    ground : numpy.ndarray(dtype=int)
        List of ground state electronic subshells, stored as integers assigned to them
        by used quantum computations program. It is a 3-dimensional of shape
        (conformers, bands, max_transitions).
    ground : numpy.ndarray(dtype=int)
        List of excited state electronic subshells, stored as integers assigned to them
        by used quantum computations program. It is a 3-dimensional of shape
        (conformers, bands, max_transitions).
    genre : str
        Genre of given data.
    allow_data_inconsistency : bool, optional
        Specifies if inconsistency of data should be allowed when creating instance
        of this class and setting it's attributes. Defaults to `True`, as different
        number of transitions may be contributing to each band.

    """

    associated_genres = ("transitions",)
    full_name_ref = dict(transitions="Transitions")
    _units = dict()
    ground = JaggedArrayProperty(dtype=int, check_against="filenames")
    excited = JaggedArrayProperty(dtype=int, check_against="filenames")
    values = JaggedArrayProperty(dtype=float, check_against="filenames")

    @staticmethod
    def unpack_values(values: Sequence[Sequence[Sequence[Tuple[int, int, float]]]]):
        """Unpack transitions data stored as list of tuples of (ground, excited,
        coefficient) to separate lists for each information pice, keeping original
        dimensionality (conformers, bands, transitions).

        Parameters
        ----------
        values : list of lists of lists of tuples of (int, int, float)
            Transitions data (ground and excited state electronic subshell and
            coefficient of transition from former to latter) for each transition
            of each band of each conformer.

        Returns
        -------
        list of lists of lists of int,
        list of lists of lists of int,
        list of lists of lists of float
            Transitions data separated to lists of ground, excited, and coefficients,
            for each transition of each band of each conformer.
        """
        outs = [[], [], []]  # ground, excited, coefs
        for conformer in values:
            [out.append(list()) for out in outs]
            curr_confs = [out[-1] for out in outs]
            for band in conformer:
                [c.append(list()) for c in curr_confs]
                curr_bands = [c[-1] for c in curr_confs]
                for transition in band:
                    for container, value in zip(curr_bands, transition):
                        container.append(value)
        return outs

    def __init__(
        self,
        genre: str,
        filenames: Sequence[str],
        values: Sequence[Sequence[Sequence[Tuple[int, int, float]]]],
        allow_data_inconsistency: bool = False,
    ):
        super().__init__(genre, filenames, values, allow_data_inconsistency)
        ground, excited, values = self.unpack_values(values)
        self.ground = ground
        self.excited = excited
        self.values = values

    @property
    def coefficients(self) -> np.ndarray:
        """Coefficients of each transition, alias for `values`."""
        return self.values

    @coefficients.setter
    def coefficients(self, values):
        self.values = values

    @property
    def contribution(self) -> np.ndarray:
        """Contribution of each transition to given band, calculated as 2 * coef^2.
        To get values in percent, multiply by 100."""
        return 2 * np.square(self.values)

    @property
    def indices_highest(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Indices of coefficients of highest contribution to band in form that
        can be used in numpy's advanced indexing mechanism."""
        contribution = self.contribution
        indices = contribution.argmax(axis=2)
        x, y, _ = contribution.shape
        # np.ogrid generates missing part of a slice tuple; i.e. creates
        # arrays of integers from 0 to n, with appropriate dimensionality,
        # where n is size of given dimension
        x, y = np.ogrid[:x, :y]
        # returned tuple can be used to slice original values array
        return x, y, indices

    @property
    def highest_contribution(
        self,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Electronic transitions data limited to transition of highest contribution
        to each band. Returns tuple with 4 arrays: ground and excited state electronic
        subshell, coefficient of transition from former to latter, and its contribution,
        for each band of each conformer."""
        indices = self.indices_highest
        # could be also achieved by the following:
        # np.take_along_axis(values, indices[..., np.newaxis], axis=2).squeeze(axis=2)
        # but indexing is much quicker, once `indices` is established
        return (
            self.ground[indices],
            self.excited[indices],
            self.values[indices],
            self.contribution[indices],
        )


class Geometry(FloatArray):
    """DataArray that stores information about geometry of conformers.

    Attributes
    ----------
    molecule_atoms : numpy.ndarray(dtype=int)
        List of atomic numbers representing atoms in conformer, one for each coordinate.

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

    associated_genres = ("geometry", "input_geom")
    full_name_ref = dict(geometry="Geometry", input_geom="Input Geometry")
    _units = dict(geometry="Angstrom")
    values = ArrayProperty(dtype=float, check_against="filenames")
    molecule_atoms = CollapsibleArrayProperty(
        dtype=int,
        check_against="values",
        check_depth=2,
        # TODO: make sanitizer, that accepts jagged nested sequences
        fsan=np.vectorize(atomic_number, otypes=[int]),
        strict=True,
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
