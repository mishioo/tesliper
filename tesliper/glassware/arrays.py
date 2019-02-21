# IMPORTS
import logging as lgg

import numpy as np
from .. import datawork as dw
from ..exceptions import VariousMoleculesError


# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# GLOBAL VARIABLES
default_spectra_bars = {
    'ir': 'dip',
    'vcd': 'rot',
    'uv': 'vosc',
    'ecd': 'vrot',
    'raman': 'raman1',
    'roa': 'roa1'
}


# CLASSES
class BaseArray:
    """Base class for data holding objects."""

    associated_genres = ()
    constructors = {}

    def __init_subclass__(cls, **kwargs):
        if not cls.associated_genres or not hasattr(cls, 'associated_genres'):
            raise AttributeError(
                'Class derived from BaseArray should provide associated_genres'
                ' attribute.'
            )
        BaseArray.constructors.update(
            (genre, cls) for genre in cls.associated_genres
        )


class DataArray(BaseArray):
    """Base class for data holding objects. It provides trimming functionality
    for filtering data based on other objects content or arbitrary choice.
    ↑ this is no longer true, TO DO: correct this

    Parameters
    ----------
    filenames : numpy.ndarray(dtype=str)
        List of filenames of gaussian output files, from whitch data were
        extracted.
    values : numpy.ndarray(dtype=float)
        List of appropriate data values.

    TO DO
    -----
    Supplement full_name_ref
    """

    full_name_ref = dict(
        rot='Rot. Strength',
        dip='Dip. Strength',
        roa1='ROA1',
        raman1='Raman1',
        vrot='Rot. (velo)',
        lrot='Rot. (lenght)',
        vosc='Osc. (velo)',
        losc='Osc. (length)',
        iri='IR Intensity',
        vemang='E-M Angle',
        eemang='E-M Angle',
        zpe='Zero-point Energy',
        ten='Thermal Energy',
        ent='Thermal Enthalpy',
        gib='Thermal Free Energy',
        scf='SCF',
        ex_en='Excitation energy',
        vfreq='Frequency',
        wave='Wavelength',
        energies='Energies'
    )

    associated_genres = 'zpecorr tencorr entcorr gibcorr mass frc emang ' \
                        'depolarp depolaru depp depu alpha2 beta2 alphag ' \
                        'gamma2 delta2 cid1 cid2 cid3 rc180 eemang'.split(' ')

    def __init__(self, genre, filenames, values, dtype=float, check_sizes=True,
                 allow_various_molecules=False, **kwargs):
        self.genre = genre
        self.dtype = dtype
        self.check_sizes = check_sizes
        self.allow_various_molecules = allow_various_molecules
        self.filenames = filenames
        self.values = values

    @property
    def full_name(self):
        return self.full_name_ref[self.genre]

    @property
    def filenames(self):
        return self.__filenames

    @filenames.setter
    def filenames(self, value):
        self.__filenames = np.array(value, dtype=str)

    @property
    def values(self):
        return self.__values

    @values.setter
    def values(self, values):
        if self.check_sizes and not len(values) == len(self.filenames):
            raise ValueError(
                f"Values and filenames must be the same length. Arrays of"
                f"length {len(values)} and {len(self.filenames)} were given."
            )
        try:
            self.__values = np.array(values, dtype=self.dtype)
        except ValueError:
            if not self.allow_various_molecules:
                raise VariousMoleculesError(
                    f"{self.__class__.__name__} with unequal number of values "
                    f"for molecule requested."
                )
            lengths = [len(v) for v in values]
            longest = max(lengths)
            self.__values = np.array(
                [np.pad(v, (0, longest-len_), 'constant', constant_values=0)
                    for v, len_ in zip(values, lengths)], dtype=self.dtype
            )
            logger.info(
                "Values' lists were appended with zeros to match length "
                "of longest entry."
            )

    def __len__(self):
        return len(self.filenames)

    def __bool__(self):
        return self.filenames.size != 0


class InfoArray(DataArray):
    associated_genres = [
        'command', 'cpu_time', 'transitions', 'stoichiometry'  # , 'filenames'
    ]

    def __init__(self, genre, filenames, values, dtype=str, **kwargs):
        super().__init__(genre, filenames, values, dtype=dtype)


class BooleanArray(DataArray):
    associated_genres = ['normal_termination', 'optimization_completed']

    def __init__(self, genre, filenames, values, dtype=bool, **kwargs):
        super().__init__(genre, filenames, values, dtype=dtype)


class Energies(DataArray):
    """
    Parameters
    ----------
    genre : str
        genre of energy.
    filenames : numpy.ndarray(dtype=str)
        List of filenames of gaussian output files, from whitch data were
        extracted.
    values : numpy.ndarray(dtype=float)
        Energy value for each conformer.
    t : int or float
        Temperature of calculated state in K."""

    Boltzmann = 0.0019872041  # kcal/(mol*K)
    associated_genres = 'scf zpe ten ent gib'.split(' ')

    def __init__(self, genre, filenames, values, t=298.15, **kwargs):
        super().__init__(genre, filenames, values, **kwargs)
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


class Bars(DataArray):
    associated_genres = 'freq iri dip rot ramact raman1 roa1 raman2 ' \
                        'roa2 raman3 roa3 wave ex_en vdip ldip vrot '\
                        'lrot vosc losc'.split(' ')

    spectra_name_ref = dict(
        rot='vcd',
        dip='ir',
        iri='ir',
        roa1='roa',
        raman1='raman',
        vrot='ecd',
        lrot='ecd',
        vosc='uv',
        losc='uv'
    )
    spectra_type_ref = dict(
        vcd='vibra',
        ir='vibra',
        roa='vibra',
        raman='vibra',
        ecd='electr',
        uv='electr'
    )
    _units = dict(
        freq='Frequency / cm^(-1)',
        wave='Wavenlength / nm',
        ex_en='Excitation energy / eV',
        rot='R / 10^(-44) esu^2 cm^2',
        dip='D / 10^(-40) esu^2 cm^2',
        iri='KM/Mole',
        ramact='Raman scattering activities / A^4/AMU',
        roa1='ROA intensiy / 10^4 K',
        raman1='Raman intensity / K',
        roa2='ROA intensiy / 10^4 K',
        raman2='Raman intensity / K',
        roa3='ROA intensiy / 10^4 K',
        raman3='Raman intensity / K',
        vrot='R / 10^(-40) erg*esu*cm/Gauss',
        lrot='R / 10^(-40) erg*esu*cm/Gauss',
        vosc='Oscillator strength',
        losc='Oscillator strength',
        vdip='D / 10^(-44) esu^2 cm^2',
        ldip='D / 10^(-44) esu^2 cm^2'
    )

    def __init__(self, genre, filenames, values, frequencies=None,
                 wavelengths=None, t=298.15, laser=532, **kwargs):
        super().__init__(genre, filenames, values, **kwargs)
        self.frequencies = frequencies  # in cm-1
        self.wavelengths = wavelengths  # in nm
        self.t = t  # temperature in K
        self.laser = laser  # in nm
        # rename to raman_laser?

    @property
    def frequencies(self):
        if self.__frequencies is None:
            return 1e7 / self.wavelengths
        else:
            return self.__frequencies

    @frequencies.setter
    def frequencies(self, frequencies):
        if frequencies is None:
            self.__frequencies = None
            return
        if self.check_sizes and not len(frequencies) == len(self.values):
            raise ValueError(
                f"Frequencies and values must be the same length. Arrays of"
                f"length {len(frequencies)} and {len(self.values)} "
                f"were given."
            )
        try:
            self.__frequencies = np.array(frequencies, dtype=float)
        except ValueError:
            lengths = [len(v) for v in frequencies]
            longest = max(lengths)
            self.__frequencies = np.array(
                [np.pad(v, (0, longest-len_), 'constant', constant_values=0)
                    for v, len_ in zip(frequencies, lengths)], dtype=float
            )
            logger.warning(
                'DataArray with unequal number of frequency values for entry '
                'requested. Arrays were appended with zeros to match length '
                'of longest entry.'
            )

    @property
    def wavelengths(self):
        if self.__wavelengths is None:
            return 1e7 / self.frequencies
        else:
            return self.__wavelengths

    @wavelengths.setter
    def wavelengths(self, wavelengths):
        if wavelengths is None:
            if self.frequencies is None:
                raise TypeError(
                    "At least one: frequencies or wavelengths must not be None."
                )
            self.__wavelengths = None
            return
        if self.check_sizes and not len(wavelengths) == len(self.values):
            raise ValueError(
                f"Wavelengths and values must be the same length. Arrays of"
                f"length {len(wavelengths)} and {len(self.values)} "
                f"were given."
            )
        try:
            self.__wavelengths = np.array(wavelengths, dtype=float)
        except ValueError:
            lengths = [len(v) for v in wavelengths]
            longest = max(lengths)
            self.__wavelengths = np.array(
                [np.pad(v, (0, longest-len_), 'constant', constant_values=0)
                    for v, len_ in zip(wavelengths, lengths)], dtype=float
            )
            logger.warning(
                'DataArray with unequal number of wavelength values for entry '
                'requested. Arrays were appended with zeros to match length '
                'of longest entry.'
            )

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
            return ''

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
        if self.spectra_type == 'electr':
            _width = width / 1.23984e-4  # from eV to cm-1
            _abscissa = 1e7 / abscissa  # from nm to cm-1
        else:
            _width = width
            _abscissa = abscissa
        freqs = self.frequencies
        inten = self.intensities
        values = dw.calculate_spectra(
            freqs, inten, _abscissa, _width, fitting
        )
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


class Spectra(DataArray):
    associated_genres = 'ir uv vcd ecd raman roa'.split(' ')
    _vibra_units = {
        'width': 'cm-1',
        'start': 'cm-1',
        'stop': 'cm-1',
        'step': 'cm-1',
        'x': 'Frequency / cm^(-1)'
    }
    _electr_units = {
        'width': 'eV',
        'start': 'nm',
        'stop': 'nm',
        'step': 'nm',
        'x': 'Wavelength / nm'
    }
    _units = {
        'ir': {'y': 'Epsilon'},
        'uv': {'y': 'Epsilon'},
        'vcd': {'y': 'Delta Epsilon'},
        'ecd': {'y': 'Delta Epsilon'},
        'raman': {'y': 'I(R)+I(L)'},
        'roa': {'y': 'I(R)-I(L)'}
    }
    for u in 'ir vcd raman roa'.split(' '):
        _units[u].update(_vibra_units)
    for u in ('uv', 'ecd'):
        _units[u].update(_electr_units)

    def __init__(self, genre, filenames, values, abscissa, width=0.0,
                 fitting='n/a', scaling=1.0, offset=0.0, **kwargs):
        super().__init__(genre, filenames, values=values, **kwargs)
        self.abscissa = abscissa
        self.start = abscissa[0]
        self.stop = abscissa[-1]
        self.step = abs(abscissa[0] - abscissa[1])
        self.width = width
        self.fitting = fitting
        self.scaling = scaling
        self.offset = offset

    @property
    def units(self):
        return Spectra._units[self.genre]

    @property
    def scaling(self):
        return self.__scaling

    @scaling.setter
    def scaling(self, factor):
        self.__scaling = factor
        self.__y = self.values * factor

    @property
    def offset(self):
        return self.__offset

    @offset.setter
    def offset(self, offset):
        self.__offset = offset
        self.__x = self.abscissa + offset

    @property
    def x(self):
        return self.__x

    @property
    def y(self):
        return self.__y

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
            self.genre, av_spec, self.abscissa, self.width, self.fitting,
            self.scaling, self.offset, filenames=self.filenames,
            averaged_by=energy_type
        )
        logger.debug(f'{self.genre} spectrum averaged by {energy_type}.')
        return av_spec


class SingleSpectrum(Spectra):

    def __init__(self, genre, values, abscissa, width=0.0, fitting='n/a',
                 scaling=1.0, offset=0.0, filenames=None, averaged_by=None):
        filenames = [] if filenames is None else filenames
        super().__init__(genre, filenames, values=values, abscissa=abscissa,
                         width=width, fitting=fitting, scaling=scaling,
                         offset=offset, check_sizes=False)
        self.averaged_by = averaged_by


"""# performance test for making arrays
>>> from timeit import timeit
>>> import random
>>> dt = {n: chr(n) for n in range(100)}
>>> ls = list(range(100))
>>> kpt = random.choices(ls, k=80)
>>> skpt = set(kpt)
>>> timeit('[(k, v) for k, v in dt.items()]', globals=globals())
5.26354954301791
>>> timeit('[(n, dt[n]) for n in ls]', globals=globals())
6.790710222989297
>>> timeit('[(k,v) for k,v in dt.items() if k in skpt]', globals=globals())
7.0161151549953615
>>> timeit('[(n, dt[n]) for n in kpt]', globals=globals())
5.522729124628256
>>> timeit('[(n,dt[n]) for n,con in zip(ls,ls) if con]', globals=globals())
9.363086626095992
>>> timeit('[(k,v) for (k,v),con in zip(dt.items(),ls)]',globals=globals())
7.463483778659565"""
