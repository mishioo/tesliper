"""Objects representing spectra."""

import logging as lgg
from typing import Dict, Optional, Sequence, Union

import numpy as np

import tesliper  # absolute import to solve problem of circular imports

from .. import datawork as dw
from .array_base import ArrayProperty

# LOGGER
logger = lgg.getLogger(__name__)


class SingleSpectrum:
    """Represents a single spectrum: experimental, averaged from set of conformers, or
    calculated for only one conformer.

    Notes
    -----
    Calling ``len()`` on this class' instance will show a number of data points
    in the spectrum.
    """

    _vibrational_units = {
        "width": "cm-1",
        "start": "cm-1",
        "stop": "cm-1",
        "step": "cm-1",
        "x": "Frequency / cm^(-1)",
    }
    _electronic_units = {
        "width": "eV",
        "start": "nm",
        "stop": "nm",
        "step": "nm",
        "x": "Wavelength / nm",
    }
    _units = {
        "ir": {"y": "Epsilon"},
        "uv": {"y": "Epsilon"},
        "vcd": {"y": "Delta Epsilon"},
        "ecd": {"y": "Delta Epsilon"},
        "raman": {"y": "I(R)+I(L)"},
        "roa": {"y": "I(R)-I(L)"},
    }
    for u in "ir vcd raman roa".split(" "):
        _units[u].update(_vibrational_units)
    for u in ("uv", "ecd"):
        _units[u].update(_electronic_units)
    _spectra_type_ref = dict(
        vcd="vibrational",
        ir="vibrational",
        roa="scattering",
        raman="scattering",
        ecd="electronic",
        uv="electronic",
    )

    def __init__(
        self,
        genre: str,
        values: Sequence[float],
        abscissa: Sequence[float],
        width: float = 0.0,
        fitting: str = "n/a",
        scaling: float = 1.0,
        offset: float = 0.0,
        filenames: Optional[Sequence[str]] = None,
        averaged_by: Optional[str] = None,
    ):
        """
        Parameters
        ----------
        genre : str
            Name of data genre that this object represents.
        values : Sequence[float]
            List of intensity values for each point on the x-axis.
        abscissa : Sequence[float]
            List of x-axis values.
        width : float, optional
            Full width at half maximum used to calculate spectrum, if applies. Provided
            for the record only, by default 0.0.
        fitting : str, optional
            Name of the fitting function used to calculate spectrum, if applies.
            Provided for the record only, by default "n/a".
        scaling : float, optional
            Multiplyier for correction of signal intensity, by default 1.0.
        offset : float, optional
            Correction of the spectrum's shift. Positive value indicates a bathochromic
            shift, negative value indicates a hypsochromic shift. By default 0.0.
        filenames : Optional[Sequence[str]], optional
            List of identifiers of conformers that were used to calculate average
            spectrum, if applies.
        averaged_by : Optional[str], optional
            Energies genre used to calculate average spectrum, if applies.
        """
        self.genre = genre
        self.filenames = [] if filenames is None else filenames
        self.averaged_by = averaged_by
        self.abscissa = abscissa
        self.values = values
        self.start = abscissa[0]
        self.stop = abscissa[-1]
        self.step = abs(abscissa[0] - abscissa[1])
        self.width = width
        self.fitting = fitting
        self.scaling = scaling
        self.offset = offset

    filenames = ArrayProperty(check_against=None, dtype=str)
    abscissa = ArrayProperty(check_against=None)
    values = ArrayProperty(check_against="abscissa")

    @property
    def spectra_type(self):
        """Returns type of spectra: 'vibrational', 'electronic', or 'scattering'."""
        return self._spectra_type_ref[self.genre]

    @property
    def units(self) -> Dict[str, str]:
        """Units in which spectral data is stored. It provides a unit for
        :attr:`.width`, :attr:`.start`, :attr:`.stop`, :attr:`.step`, :attr:`.x`, and
        :attr:`.y`. :attr:`.abscissa` and :attr:`~.SingleSpectrum.values` are stored in
        the same units as :attr:`.x` and :attr:`.y` respectively.
        """
        return self._units[self.genre]

    @property
    def scaling(self) -> Union[int, float]:
        """A factor for correcting the scale of spectra. Setting it to new value changes
        the :attr:`.y` attribute as well. It should be an ``int`` or ``float``.
        """
        return vars(self)["scaling"]

    @scaling.setter
    def scaling(self, factor: Union[int, float]):
        vars(self)["scaling"] = factor
        vars(self)["y"] = self.values * factor

    @property
    def offset(self) -> Union[int, float]:
        """A factor for correcting the shift of spectra. Positive value indicates a
        bathochromic shift, negative value indicates a hypsochromic shift. Setting
        it to new value changes the :attr:`.x` attribute as well. It should be an
        ``int`` or ``float``.
        """
        return vars(self)["offset"]

    @offset.setter
    def offset(self, offset: Union[int, float]):
        vars(self)["offset"] = offset
        vars(self)["x"] = self.abscissa + offset

    @property
    def x(self) -> np.ndarray:
        """Spectra's x-values corrected by adding its :attr:`.offset` to
        :attr:`.abscissa`."""
        return vars(self)["x"]

    @property
    def y(self) -> np.ndarray:
        """Spectra's y-values corrected by multiplying its
        :attr:`~.SingleSpectrum.values` by :attr:`.scaling`."""
        return vars(self)["y"]

    def scale_to(self, spectrum: "SingleSpectrum") -> None:
        """Establishes a scaling factor to best match a scale of the *spectrum* values.

        Parameters
        ----------
        spectrum : SingleSpectrum
            This spectrum's y-axis values will be treated as a reference. If *spectrum*
            has its own scaling factor, it will be taken into account.
        """
        self.scaling = dw.find_scaling(spectrum.y, self.values)

    def shift_to(self, spectrum: "SingleSpectrum") -> None:
        """Establishes an offset factor to best match given *spectrum*.

        Parameters
        ----------
        spectrum : SingleSpectrum
            This spectrum will be treated as a reference. If *spectrum*
            has its own offset factor, it will be taken into account.
        """
        self.offset = dw.find_offset(spectrum.x, spectrum.y, self.abscissa, self.values)

    def __len__(self):
        return len(self.abscissa)


class Spectra(SingleSpectrum):
    """Represents a collection of spectra calculated for a number of conformers.

    .. versionchanged:: 0.9.1
        Corrected ``len()`` behavior.

    Notes
    -----
    Calling ``len()`` on this class' instance will show how many conformers'
    spectra it contains.
    """

    filenames = ArrayProperty(check_against=None, dtype=str)
    abscissa = ArrayProperty(check_against=None)
    values = ArrayProperty(check_against="filenames")

    def __init__(
        self,
        genre: str,
        filenames: Sequence[str],
        values: Sequence[Sequence[float]],
        abscissa: Sequence[float],
        width: float = 0.0,
        fitting: str = "n/a",
        scaling: float = 1.0,
        offset: float = 0.0,
        allow_data_inconsistency: bool = False,
    ):
        """
        Parameters
        ----------
        genre : str
            Name of data genre that this object represents.
        filenames : Optional[Sequence[str]], optional
            List of conformers' identifiers that were used to calculate spectra.
        values : Sequence[float]
            List of intensity values for each point on the x-axis.
        abscissa : Sequence[float]
            List of x-axis values.
        width : float, optional
            Full width at half maximum used to calculate spectra. Provided
            for the record only, by default 0.0.
        fitting : str, optional
            Name of the fitting function used to calculate spectra.
            Provided for the record only, by default "n/a".
        scaling : float, optional
            Multiplyier for correction of signal intensity, by default 1.0.
        offset : float, optional
            Correction of the spectra's shift. Positive value indicates a bathochromic
            shift, negative value indicates a hypsochromic shift. By default 0.0.
        allow_data_inconsistency : bool, optional
            Flag signalizing if instance should allow data inconsistency (see
            :class:`.ArrayPropety` for details).
        """

        self.allow_data_inconsistency = allow_data_inconsistency
        SingleSpectrum.__init__(
            self, genre, values, abscissa, width, fitting, scaling, offset, filenames
        )

    def average(self, energies: "tesliper.glassware.Energies") -> SingleSpectrum:
        """A method for averaging spectra by population of conformers. If this object
        is empty, averaged spectrum will be a flat line at 0.0 intensity.

        Parameters
        ----------
        energies : Energies
            Object with ``populations`` and ``genre`` attributes containing
            respectively: list of populations values as ``numpy.ndarray`` and
            string specifying energy genre.

        Returns
        -------
        SingleSpectrum
            Averaged spectrum.
        """
        populations = energies.populations
        energy_type = energies.genre
        av_spec = dw.calculate_average(self.values, populations)
        if not av_spec.size:
            av_spec = np.zeros(self.abscissa.shape)
        av_spec = SingleSpectrum(
            self.genre,
            av_spec,
            self.abscissa,
            self.width,
            self.fitting,
            scaling=self.scaling,
            offset=self.offset,
            filenames=self.filenames,
            averaged_by=energy_type,
        )
        logger.debug(f"{self.genre} spectrum averaged by {energy_type}.")
        return av_spec

    def scale_to(
        self,
        spectrum: SingleSpectrum,
        average_by: Optional["tesliper.glassware.Energies"] = None,
    ) -> None:
        """Establishes a scaling factor to best match a scale of the *spectrum* values.
        An average spectrum is calculated prior to calculating the factor.
        If *average_by* is given, it is used to average by population of each conformer.
        Otherwise an arithmetic average of spectra is calculated, which may lead
        to inaccurate results.

        Parameters
        ----------
        spectrum : SingleSpectrum
            This spectrum's y-axis values will be treated as a reference. If *spectrum*
            has its own scaling factor, it will be taken into account.
        average_by : Energies, optional
            Energies object, used to calculate average spectrum prior to calculating
            the factor. If not given, a simple arithmetic average of the spectra will
            be calculated.
        """
        if average_by is not None:
            averaged = self.average(energies=average_by)
            averaged.scale_to(spectrum)
            factor = averaged.scaling
        else:
            logger.warning(
                "Trying to find optimal scaling factor for spectra, but no Energies "
                "object given for averaging by population. Results may be inaccurate."
            )
            averaged = np.average(self.values, axis=0)
            factor = dw.find_scaling(spectrum.y, averaged)
        self.scaling = factor

    def shift_to(
        self,
        spectrum: SingleSpectrum,
        average_by: Optional["tesliper.glassware.Energies"] = None,
    ) -> None:
        """Establishes an offset factor to best match given *spectrum*.
        An average spectrum is calculated prior to calculating the factor.
        If *average_by* is given, it is used to average by population of each conformer.
        Otherwise an arithmetic average of spectra is calculated, which may lead
        to inaccurate results.

        Parameters
        ----------
        spectrum : SingleSpectrum
            This spectrum will be treated as a reference. If *spectrum*
            has its own offset factor, it will be taken into account.
        average_by : Energies, optional
            Energies object, used to calculate average spectrum prior to calculating
            the factor. If not given, a simple arithmetic average of the spectra will
            be calculated.
        """
        if average_by is not None:
            averaged = self.average(energies=average_by)
            averaged.shift_to(spectrum)
            factor = averaged.offset
        else:
            logger.warning(
                "Trying to find optimal offset factor for spectra, but no Energies "
                "object given for averaging by population. Results may be inaccurate."
            )
            averaged = np.average(self.values, axis=0)
            factor = dw.find_offset(spectrum.x, spectrum.y, self.abscissa, averaged)
        self.offset = factor

    def __len__(self):
        # must override SingleSpecrum's implementation, because it may have an abscisa
        # but contain no data for conformers
        # e.g. when created in calculations of spectra from an empty activities array
        return len(self.filenames)
