import logging as lgg
from .array_base import ArrayProperty
from .. import datawork as dw


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
    def units(self):
        return self._units[self.genre]

    @property
    def scaling(self):
        return self._scaling

    @scaling.setter
    def scaling(self, factor):
        self._scaling = factor
        self._y = self.values * factor

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, offset):
        self._offset = offset
        self._x = self.abscissa + offset

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    def __len__(self):
        return len(self.abscissa)

    def __bool__(self):
        return self.abscissa.size != 0


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

    def average(self, energies):
        """A method for averaging spectra by population of conformers.

        Parameters
        ----------
        energies : Energies object instance
            Object with populations and type attributes containing
            respectively: list of populations values as numpy.ndarray and
            string specifying energy type.

        Returns
        -------
        numpy.ndarray
            2d numpy array where arr[0] is list of wavelengths/wave numbers
            and arr[1] is list of corresponding averaged intensity values.
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
            self.scaling,
            self.offset,
            filenames=self.filenames,
            averaged_by=energy_type,
        )
        logger.debug(f"{self.genre} spectrum averaged by {energy_type}.")
        return av_spec
