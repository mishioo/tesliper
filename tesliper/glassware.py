###################
###   IMPORTS   ###
###################

import logging as lgg
from collections import OrderedDict, Counter
from contextlib import contextmanager

import numpy as np

##################
###   LOGGER   ###
##################

logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)

############################
###   GLOBAL VARIABLES   ###
############################

default_spectra_bars = {
    'ir': 'dip',
    'vcd': 'rot',
    'uv': 'vosc',
    'ecd': 'vrot',
    'raman': 'raman1',
    'roa': 'roa1'
}


###################
###   CLASSES   ###
###################


class DataArray:
    """Base class for data holding objects. It provides trimming functionality
    for filtering data based on other objects content or arbitrary choice.
    
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
        efreq='Wavelength',
        energies='Energies'
    )

    associated_genres = 'zpecorr tencorr entcorr gibcorr mass frc emang ' \
                        'depolarp depolaru depp depu alpha2 beta2 alphag ' \
                        'gamma2 delta2 cid1 cid2 cid3 rc180'.split(' ')

    @staticmethod
    def get_constructor(genre):
        constructors = {
            key: cls for cls in DataArray.__subclasses__()
            for key in cls.associated_genres
        }
        constructors.update({
            key: DataArray for key in DataArray.associated_genres
        })
        return constructors[genre]

    @staticmethod
    def make(genre, filenames, values, **kwargs):
        try:
            cls = DataArray.get_constructor(genre)
        except KeyError:
            raise ValueError(f"Unknown genre '{genre}'.")
        try:
            instance = cls(genre, filenames, values, **kwargs)
        except TypeError:
            print(genre, cls)
            print({
                key: cls for cls in DataArray.__subclasses__()
                for key in cls.associated_genres
        })
        return instance

    def __init__(self, genre, filenames, values, dtype=float, **kwargs):
        self.genre = genre
        self.dtype = dtype
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
        if not len(values) == len(self.filenames):
            raise ValueError(
                f"Values and filenames must be the same length. Arrays of"
                f"length {len(values)} and {len(self.filenames)} were given."
            )
        try:
            self.__values = np.array(values, dtype=self.dtype)
        except ValueError:
            lengths = [len(v) for v in values]
            longest = max(lengths)
            self.__values = np.array(
                [np.pad(v, (0, longest-len_), 'constant', constant_values=0)
                    for v, len_ in zip(values, lengths)], dtype=self.dtype
            )
            logger.warning(
                'DataArray with unequal number of elements for entry '
                'requested. Arrays were appended with zeros to match length '
                'of longest entry.'
            )

    def __len__(self):
        return self.filenames.size


class Info(DataArray):
    associated_genres = ['command', 'cpu_time', 'transitions', 'stoichiometry']

    def __init__(self, genre, filenames, values, dtype=str, **kwargs):
        super().__init__(genre, filenames, values, dtype=dtype)


class Booleans(DataArray):
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
        try:
            return (self.values - self.values.min()) * 627.5095
            # convert hartree to kcal/mol by multiplying by 627.5095
        except ValueError:
            # if no values, return empty array.
            return np.array([])

    @property
    def min_factor(self):
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
        return np.exp(-self.deltas / (self.t * self.Boltzmann))

    @property
    def populations(self):
        """Calculates Boltzmann distribution of conformers.

        Returns
        -------
        numpy.ndarary
            List of conformers populations calculated as Boltzmann
            distribution."""
        x = self.min_factor
        return x / x.sum()

    def calculate_populations(self, t):
        """Calculates conformers' Boltzmann distribution in given temperature.

        Parameters
        ----------
        t : int or float
            Temperature of calculated state in K."""
        x = np.exp(-self.deltas / (t * self.Boltzmann))
        return x / x.sum()


class Bars(DataArray):
    associated_genres = 'freq iri dip rot raman ramact raman1 roa1 raman2 ' \
                        'roa2 raman3 roa3 efreq ex_en eemang vdip ldip vrot ' \
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

    def __init__(self, genre, filenames, values, frequencies,
                 t=298.15, laser=532, **kwargs):
        super().__init__(genre, filenames, values, **kwargs)
        self.frequencies = frequencies
        self.t = t  # temperature in K
        self.laser = laser  # in nm
        # rename to raman_laser?

    @property
    def frequencies(self):
        return self.__frequencies

    @frequencies.setter
    def frequencies(self, frequencies):
        if not len(frequencies) == len(self.filenames):
            raise ValueError(
                f"Frequencies and filenames must be the same length. Arrays of"
                f"length {len(frequencies)} and {len(self.filenames)} "
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
    def spectra_name(self):
        if self.genre in self.spectra_name_ref:
            return self.spectra_name_ref[self.genre]

    @property
    def spectra_type(self):
        if self.genre in self.spectra_name_ref:
            return self.spectra_type_ref[self.spectra_name]

    @property
    def get_intensity_factor(self):
        def raman(obj):
            f = 9.695104081272649e-08
            e = 1 - np.exp(-14387.751601679205 * obj.frequencies / obj.t)
            out = f * (obj.laser - obj.frequencies) ** 4 / (obj.frequencies * e)
            return out

        reference = dict(
            raman=raman,
            roa=raman,
            ir=lambda obj: obj.frequencies / 91.48,
            vcd=lambda obj: obj.frequencies / 2.296e5,
            uv=lambda obj: obj.frequencies * 2.87e4,
            ecd=lambda obj: obj.frequencies / 22.96
        )
        return reference[self.spectra_name]

    @property
    def intensities(self):
        """Converts spectral activity calculated by quantum chemistry software
        to signal intensity.

        Returns
        -------
        numpy.ndarray
            Signal intensities for each conformer."""
        intensities = self.values * self.get_intensity_factor(self)
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

    def find_imag(self):
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

    def calculate_spectra(self, start, stop, step, hwhm, fitting):
        """Calculates spectrum of desired type for each individual conformer.
        
        Parameters
        ----------
        start : int or float
            Number representing start of spectral range in relevant units.
        stop : int or float
            Number representing end of spectral range in relevant units.
        step : int or float
            Number representing step of spectral range in relevant units.
        hwhm : int or float
            Number representing half width of maximum peak hight.
        fitting : function
            Function, which takes bars, freqs, abscissa, hwhm as parameters and
            returns numpy.array of calculated, non-corrected spectrum points.
            
        Returns
        -------
        numpy.ndarray
            Array of 2d arrays containing spectrum (arr[0] is list of
            wavelengths/wave numbers, arr[1] is list of corresponding
            intensity values).
        """
        abscissa = np.arange(start, stop + step, step)
        # spectrum abscissa, 1d numpy.array of wavelengths/wave numbers
        if self.spectra_type == 'electr':
            width = hwhm / 1.23984e-4  # from eV to cm-1
            w_nums = 1e7 / abscissa  # from nm to cm-1
            freqs = 1e7 / self.frequencies  # from nm to cm-1
        else:
            width = hwhm
            w_nums = abscissa
            freqs = self.frequencies
        inten = self.intensities
        spectra = np.zeros([len(freqs), abscissa.shape[0]])
        for bar, freq, spr in zip(inten, freqs, spectra):
            spr[...] = fitting(bar, freq, w_nums, width)
        output = Spectra(self.spectra_name, self.filenames, abscissa,
                         spectra, hwhm, fitting)
        if output:
            logger.info(
                "{} spectra calculated with HWHM = {} and {} fitting.".format(
                    self.spectra_name, hwhm, fitting.__name__
                )
            )
        return output


class Spectra(DataArray):
    units = {
        'vibra': {'hwhm': 'cm-1',
                  'start': 'cm-1',
                  'stop': 'cm-1',
                  'step': 'cm-1'},
        'electr': {'hwhm': 'eV',
                   'start': 'nm',
                   'stop': 'nm',
                   'step': 'nm'}
    }

    def __init__(self, name, filenames, abscissa, values, hwhm, fitting,
                 **kwargs):
        super().__init__(Bars.spectra_type_ref[name],
                         filenames, values=values, **kwargs)
        self.name = name
        self.abscissa = abscissa
        self.start = abscissa[0]
        self.stop = abscissa[-1]
        self.step = abs(abscissa[0] - abscissa[1])
        self.hwhm = hwhm
        self.fitting = fitting
        self._averaged = {}

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
        try:
            old_popul = self._averaged[energy_type]['populations']
            if populations.shape == old_popul.shape:
                if (populations == old_popul).all():
                    logger.debug('Populations same as previously used. '
                                 'Returning cashed spectrum.')
                    return self._averaged[energy_type]['spectrum']
                else:
                    logger.debug('Spectrum previously averaged with '
                                 'different populations.')
            else:
                logger.debug('Spectrum previously averaged with '
                             'different populations.')
        except KeyError:
            logger.debug('No previously averaged spectrum found.')
        # populations must be of same shape as spectra
        # so we expand populations with np.newaxis
        av = (self.values * populations[:, np.newaxis]).sum(0)
        av_spec = np.array([self.abscissa, av])
        self._averaged[energy_type] = dict(
            populations=populations,
            spectrum=av_spec,
            values=av,
            base=self.abscissa)
        logger.info('{} spectrum averaged by {}.'.format(self.name,
                                                         energy_type))
        return av_spec

    # @property
    # def text_header(self):
    #     header = '{} spectrum, HWHM = {} {}, fitting = {}'
    #     header = header.format(
    #         self.name.upper(), self.hwhm, self.units[self.genre]['hwhm'],
    #         self.fitting.__name__)
    #     return header
    #
    # @property
    # def averaged_header(self):
    #     header = self.text_header + ', averaged by {}.'
    #     header.format(DataArray.full_name_ref[self.energy_type])
    #     return header


class Molecules(OrderedDict):
    """Ordered mapping of dictionaries.

    Notes
    -----
    Inherits from collections.OrderedDict.

    TO DO
    -----
    Add type checks in update and setting methods."""

    vibrational_keys = (
        'freq mass frc iri dip rot emang raman depolarp depolaru '
        'ramact depp depu alpha2 beta2 alphag gamma2 delta2 raman1 '
        'roa1 cid1 raman2 roa2 cid2  raman3 roa3 cid3 rc180'.split(' ')
    )

    electronic_keys = (
        'efreq ex_en eemang vdip ldip vrot lrot vosc losc '
        'transitions'.split(' ')
    )

    def __init__(self, *args, **kwargs):
        self.__kept = []
        self.filenames = []
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value, **kwargs):
        # TO DO: enable other, convertible to dict, structures
        if not isinstance(value, dict):
            raise TypeError(f'Value should be dict-like object, '
                            f'not {type(value)}')
        super().__setitem__(key, value, **kwargs)
        self.kept.append(True)
        self.filenames.append(key)

    def __delitem__(self, key, **kwargs):
        super().__delitem__(key, **kwargs)
        index = self.filenames.index(key)
        del self.filenames[index]
        del self.kept[index]

    @property
    def kept(self):
        return self.__kept

    @kept.setter
    def kept(self, blade):
        try:
            first = blade[0]
        except (TypeError, KeyError):
            raise TypeError(f"Excepted sequence, got: {type(blade)}.")
        except IndexError:
            self.__kept = [False for __ in self.kept]
            return
        if isinstance(first, str):
            blade = set(blade)
            if not blade.issubset(set(self.keys())):
                raise KeyError(
                    f"Unknown conformers: {', '.join(blade-set(self.keys()))}"
                )
            else:
                self.__kept = [fnm in blade for fnm in self.keys()]
        elif isinstance(first, (bool, np.bool_)):
            if not len(blade) == len(self):
                raise ValueError(
                    f"When setting molecules.kept directly, must provide "
                    f"boolean value for each known conformer. {len(blade)} "
                    f"values provided, {len(self)} excepted."
                )
            else:
                self.__kept = [bool(b) for b in blade]  # convert from np.bool_
        elif isinstance(first, int):
            length = len(self.kept)
            out_of_bounds = [b for b in blade if not -length <= b < length]
            if out_of_bounds:
                raise IndexError(
                    f"Indexes out of bounds: "
                    f"{', '.join(str(n) for n in out_of_bounds)}."
                )
            else:
                blade = set(blade)
                self.__kept = [num in blade for num in range(len(self.kept))]
        else:
            raise TypeError(
                f"Expected sequence of strings, integers or booleans, got: "
                f"{type(first)} as first sequence's element."
            )


    def update(self, other=None, **kwargs):
        """Works like dict.update, but if key is already present, it updates
        dictionary associated with given key rather than changing its value.

        TO DO
        -----
        Add type checks."""
        molecules = dict()
        if other is not None:
            molecules.update(other)
        molecules.update(**kwargs)
        for key, value in molecules.items():
            if key in self:
                self[key].update(value)
            else:
                self[key] = value

    def arrayed(self, genre, full=False):
        """Lists requested data and returns as appropriate DataArray instance.

        Parameters
        ----------
        genre : str
            String representing data genre. Must be one of known genres.
        full : bool, optional
            Boolean indicating if full set of data should be taken, ignoring
            any trimming conducted earlier. Defaults to False.

        Returns
        -------
        DataArray
            Arrayed data of desired genre as appropriate DataArray object.

        TO DO
        -----
        Add some type checking and error handling."""
        if not (self.kept or self.items()):
            logger.debug(
                f'Array of gerne {genre} requested, but self.kept or '
                f'self.items() are empty. Returning empty array.'
            )
            return DataArray(genre, [], [])
        conarr = self.kept if not full else (True for __ in self.kept)
        array = [
            (fname, mol, mol[genre]) for (fname, mol), con
            in zip(self.items(), conarr) if con and genre in mol
        ]
        if array:
            filenames, mols, values = zip(*array)
        else:
            filenames, mols, values = [], [], []
        if genre in self.vibrational_keys:
            freqs = [mol['freq'] for mol in mols]
        elif genre in self.electronic_keys:
            freqs = [mol['efreq'] for mol in mols]
        else:
            freqs = [[] for __ in mols]
        arr = DataArray.make(genre, filenames, values, frequencies=freqs)
        return arr

    @property
    def _max_len(self):
        return max(len(m) for m in self.values())

    def trim_incomplete(self):
        longest = self._max_len
        for index, mol in enumerate(self.values()):
            if len(mol) < longest:
                self.kept[index] = False
        
    def trim_imaginary_frequencies(self):
        arr = self.arrayed('freq', full=True)
        imaginary = arr.imaginary
        for index, imag in enumerate(imaginary):
            if imag > 0:
                self.kept[index] = False

    def trim_non_matching_stoichiometry(self):
        counter = Counter((mol['stoichiometry'] for mol in self.values()))
        stoich = counter.most_common()[0][0]
        for index, mol in enumerate(self.values()):
            if not mol['stoichiometry'] == stoich:
                self.kept[index] = False

    def trim_not_optimized(self):
        for index, mol in enumerate(self.values()):
            if not mol.get('optimization_completed', True):
                self.kept[index] = False

    def trim_non_normal_termination(self):
        for index, mol in enumerate(self.values()):
            if not mol['normal_termination']:
                self.kept[index] = False

    def trim_to_range(self, genre, minimum=float("-inf"), maximum=float("inf"),
                      attribute='values'):
        try:
            arr = self.arrayed(genre)
            atr = getattr(arr, attribute)
        except AttributeError:
            raise ValueError(
                f"Invalid genre/attribute combination: {genre}/{attribute}. "
                f"Resulting DataArray object has no attribute {attribute}."
            )
        except TypeError:
            raise ValueError(
                f"Invalid genre/attribute combination: {genre}/{attribute}. "
                f"DataArray's attribute must be iterable."
            )
        if not isinstance(atr[0], (int, float)):
            raise ValueError(
                f"Invalid genre/attribute combination: {genre}/{attribute}. "
                f"Resulting DataArray must contain objects of type int or "
                f"float, not {type(atr[0])}"
            )
        blade = [
            fnm for v, fnm in zip(atr, arr.filenames) if minimum <= v <= maximum
        ]
        self.kept = blade

    def select_all(self):
        self.kept = [True for __ in self.kept]

    @property
    @contextmanager
    def untrimmed(self):
        blade = self.kept
        self.select_all()
        yield self
        self.kept = blade

    @contextmanager
    def trimmed_to(self, blade):
        old_blade = self.kept
        self.kept = blade
        yield self
        self.kept = old_blade

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
