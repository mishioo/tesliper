import logging as lgg
from typing import Dict, Optional, Union

import numpy as np

import tesliper  # absolute import to solve problem of circular imports

from .. import datawork as dw
from .array_base import ArrayProperty

# LOGGER
logger = lgg.getLogger(__name__)


class SingleSpectrum:

    _vibra_units = {
        "width": "cm-1",
        "start": "cm-1",
        "stop": "cm-1",
        "step": "cm-1",
        "x": "Frequency / cm^(-1)",
    }
    _electr_units = {
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
        _units[u].update(_vibra_units)
    for u in ("uv", "ecd"):
        _units[u].update(_electr_units)

    def __init__(
        self,
        genre,
        values,
        abscissa,
        width=0.0,
        fitting="n/a",
        scaling=1.0,
        offset=0.0,
        filenames=None,
        averaged_by=None,
    ):
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
    def units(self) -> Dict[str, str]:
        """Units in which spectral data is stored. It provides a unit for `.width`,
        `.start`, `.stop`, `.step`, `.x`, and `.y`. `.abscissa` and `.values` are
        stored in the same units as `.x` and `.y` respectively.
        """
        return self._units[self.genre]

    @property
    def scaling(self) -> Union[int, float]:
        """A factor for correcting the scale of spectra. Setting it to new value changes
        the `y` attribute as well. It should be an `int` or `float`.
        """
        return vars(self)["scaling"]

    @scaling.setter
    def scaling(self, factor: Union[int, float]):
        vars(self)["scaling"] = factor
        vars(self)["y"] = self.values * factor

    @property
    def offset(self) -> Union[int, float]:
        """A factor for correcting the shift of spectra. Setting it to new value changes
        the `x` attribute as well. It should be an `int` or `float`.
        """
        return vars(self)["offset"]

    @offset.setter
    def offset(self, offset: Union[int, float]):
        vars(self)["offset"] = offset
        vars(self)["x"] = self.abscissa + offset

    @property
    def x(self) -> np.ndarray:
        """Spectra's x-values corrected by adding its `.offset` to `.abscissa`."""
        return vars(self)["x"]

    @property
    def y(self) -> np.ndarray:
        """Spectra's y-values corrected by multiplying its `.values` by `.scaling`."""
        return vars(self)["y"]

    def scale_to(self, spectrum: "SingleSpectrum") -> None:
        """Establishes a scaling factor to best match a scale of the `spectrum` values.

        Parameters
        ----------
        spectrum : SingleSpectrum
            This spectrum's y-axis values will be treated as a reference. If `spectrum`
            has its own scaling factor, it will be taken into account.
        """
        self.scaling = dw.find_scaling(spectrum.y, self.values)

    def shift_to(self, spectrum: "SingleSpectrum") -> None:
        """Establishes an offset factor to best match given `spectrum`.

        Parameters
        ----------
        spectrum : SingleSpectrum
            This spectrum will be treated as a reference. If `spectrum`
            has its own offset factor, it will be taken into account.
        """
        self.offset = dw.find_offset(spectrum.x, spectrum.y, self.abscissa, self.values)

    def __len__(self):
        return len(self.abscissa)


class Spectra(SingleSpectrum):

    filenames = ArrayProperty(check_against=None, dtype=str)
    abscissa = ArrayProperty(check_against=None)
    values = ArrayProperty(check_against="filenames")

    def __init__(
        self,
        genre,
        filenames,
        values,
        abscissa,
        width=0.0,
        fitting="n/a",
        scaling=1.0,
        offset=0.0,
        allow_data_inconsistency=False,
    ):
        self.allow_data_inconsistency = allow_data_inconsistency
        SingleSpectrum.__init__(
            self, genre, values, abscissa, width, fitting, scaling, offset, filenames
        )

    def average(self, energies: "tesliper.glassware.Energies") -> SingleSpectrum:
        """A method for averaging spectra by population of conformers. If `scaling`
        or `offset` attributes are `np.ndarray`s, they are averaged as well.


        Parameters
        ----------
        energies : Energies object instance
            Object with populations and type attributes containing
            respectively: list of populations values as numpy.ndarray and
            string specifying energy type.

        Returns
        -------
        SingleSpectrum
            Averaged spectrum.
        """
        populations = energies.populations
        energy_type = energies.genre
        av_spec = dw.calculate_average(self.values, populations)
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
        """Establishes a scaling factor to best match a scale of the `spectrum` values.
        An average spectrum is calculated prior to calculating the factor.
        If `average_by` is given, it is used to average by population of each conformer.
        Otherwise an arithmetic average of spectra is calculated, which may lead
        to inaccurate results.

        Parameters
        ----------
        spectrum : SingleSpectrum
            This spectrum's y-axis values will be treated as a reference. If `spectrum`
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
        """Establishes an offset factor to best match given `spectrum`.
        An average spectrum is calculated prior to calculating the factor.
        If `average_by` is given, it is used to average by population of each conformer.
        Otherwise an arithmetic average of spectra is calculated, which may lead
        to inaccurate results.

        Parameters
        ----------
        spectrum : SingleSpectrum
            This spectrum will be treated as a reference. If `spectrum`
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
