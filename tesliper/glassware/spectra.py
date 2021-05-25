import logging as lgg
from typing import Optional, Union, Sequence, Dict

import numpy as np

from .array_base import ArrayProperty, CollapsibleArrayProperty
from .. import datawork as dw
import tesliper  # absolute import to solve problem of circular imports


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
        return self._units[self.genre]

    @property
    def scaling(self) -> Union[int, float]:
        return vars(self)["scaling"]

    @scaling.setter
    def scaling(self, factor: Union[int, float]):
        vars(self)["scaling"] = factor
        vars(self)["y"] = self.values * factor

    @property
    def offset(self) -> Union[int, float]:
        return vars(self)["offset"]

    @offset.setter
    def offset(self, offset: Union[int, float]):
        vars(self)["offset"] = offset
        vars(self)["x"] = self.abscissa + offset

    @property
    def x(self) -> np.ndarray:
        return vars(self)["x"]

    @property
    def y(self) -> np.ndarray:
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

    def __bool__(self):
        return self.abscissa.size != 0


class Spectra(SingleSpectrum):

    filenames = ArrayProperty(check_against=None, dtype=str)
    abscissa = ArrayProperty(check_against=None)
    values = ArrayProperty(check_against="filenames")
    scaling = CollapsibleArrayProperty(check_against="filenames", dtype=float)
    offset = CollapsibleArrayProperty(check_against="filenames", dtype=float)

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
        scaling = (
            self.scaling[0]
            if self.scaling.size == 1
            else np.average(self.scaling, weights=populations)
        )
        offset = (
            self.offset[0]
            if self.offset.size == 1
            else np.average(self.offset, weights=populations)
        )
        av_spec = SingleSpectrum(
            self.genre,
            av_spec,
            self.abscissa,
            self.width,
            self.fitting,
            scaling=scaling,
            offset=offset,
            filenames=self.filenames,
            averaged_by=energy_type,
        )
        logger.debug(f"{self.genre} spectrum averaged by {energy_type}.")
        return av_spec

    @scaling.setter
    def scaling(
        self, factor: Union[int, float, Sequence[int], Sequence[float], np.ndarray]
    ):
        if type(self).scaling.fsan is not None:
            factor = type(self).scaling.fsan(factor)
        factor = type(self).scaling.check_input(self, factor)
        vars(self)["scaling"] = factor
        vars(self)["y"] = self.values * factor

    @scaling.getter
    def scaling(self) -> np.ndarray:
        return vars(self)["scaling"]

    @offset.setter
    def offset(
        self, offset: Union[int, float, Sequence[int], Sequence[float], np.ndarray]
    ):
        if type(self).scaling.fsan is not None:
            offset = type(self).scaling.fsan(offset)
        offset = type(self).scaling.check_input(self, offset)
        vars(self)["offset"] = offset
        vars(self)["x"] = self.abscissa + offset

    @offset.getter
    def offset(self) -> np.ndarray:
        return vars(self)["offset"]

    def scale_to(
        self,
        spectrum: SingleSpectrum,
        average_by: Optional["tesliper.glassware.Energies"] = None,
    ) -> None:
        """Establishes a scaling factor to best match a scale of the `spectrum` values.
        If `average_by` is given, it is used to average the spectra prior to calculating
        the factor, and one factor is applied to each spectra. Otherwise spectra are
        treated separately, and resulting factor is an `np.ndarray` of values, different
        for each spectrum.

        Parameters
        ----------
        spectrum : SingleSpectrum
            This spectrum's y-axis values will be treated as a reference. If `spectrum`
            has its own scaling factor, it will be taken into account.
        average_by : Energies, optional
            Energies object, used to calculate average spectrum prior to calculating
            the factor. If not given, one factor for each spectrum will be calculated.
        """
        if average_by is not None:
            averaged = self.average(energies=average_by)
            self.scaling = super().scale_to(averaged)
        else:
            factor = np.array(
                [dw.find_scaling(spectrum.y, conformer) for conformer in self.values]
            )
            self.scaling = factor

    def shift_to(
        self,
        spectrum: SingleSpectrum,
        average_by: Optional["tesliper.glassware.Energies"] = None,
    ) -> None:
        """Establishes an offset factor to best match given `spectrum`.
        If `average_by` is given, it is used to average the spectra prior to calculating
        the factor, and one factor is applied to each spectra. Otherwise spectra are
        treated separately, and resulting factor is an `np.ndarray` of values, different
        for each spectrum.

        Parameters
        ----------
        spectrum : SingleSpectrum
            This spectrum will be treated as a reference. If `spectrum`
            has its own offset factor, it will be taken into account.
        average_by : Energies, optional
            Energies object, used to calculate average spectrum prior to calculating
            the factor. If not given, one factor for each spectrum will be calculated.
        """
        if average_by is not None:
            averaged = self.average(energies=average_by)
            self.offset = super().shift_to(averaged)
        else:
            offset = np.array(
                [
                    dw.find_offset(spectrum.x, spectrum.y, self.abscissa, conformer)
                    for conformer in self.values
                ]
            )
            self.offset = offset
