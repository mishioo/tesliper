###################
###   IMPORTS   ###
###################

import logging as lgg
import math
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

############################
###   MODULE FUNCTIONS   ###
############################

Boltzmann = 0.0019872041  # kcal/(mol*K)


def delta(energies):
    """Calculates energy difference between each conformer and lowest energy
    conformer. Converts energy to kcal/mol.

    Parameters
    ----------
    energies : numpy.ndarray
        List of conformers energies in Hartree units.

    Returns
    -------
    numpy.ndarray
        List of energy differences from lowest energy in kcal/mol."""
    try:
        return (energies - energies.min()) * 627.5095
        # convert hartree to kcal/mol by multiplying by 627.5095
    except ValueError:
        # if no values, return empty array.
        return np.array([])


def min_factor(energies, t=298.15):
    """Calculates list of conformers' Boltzmann factors respective to lowest
    energy conformer in system of given temperature.

    Notes
    -----
    Boltzmann factor of two states is defined as:
    F(state_1)/F(state_2) = exp((E_1 - E_2)/kt)
    where E_1 and E_2 are energies of states 1 and 2,
    k is Boltzmann constant, k = 0.0019872041 kcal/(mol*K),
    and t is temperature of the system.

    Parameters
    ----------
    energies : numpy.ndarray
        List of conformers energies in Hartree units.
    t : float, optional
        Temperature of the system in K, defaults to 298,15 K.

    Returns
    -------
    numpy.ndarary
        List of conformers' Boltzmann factors respective to lowest
        energy conformer."""
    arr = delta(energies)
    return np.exp(arr / (t * Boltzmann))


def population(energies, t=298.15):
    """Calculates Boltzmann distribution of conformers of given energies.

    Parameters
    ----------
    energies : numpy.ndarray
        List of conformers energies in Hartree units.
    t : float, optional
        Temperature of the system in K, defaults to 298,15 K.

    Returns
    -------
    numpy.ndarary
        List of conformers populations calculated as Boltzmann distribution."""
    arr = min_factor(energies, t)
    return arr / arr.sum()


def count_imaginary(frequencies):
    imag = frequencies < 0
    return imag.sum(1)


def find_imaginary(frequencies):
    """Finds all molecules with imaginary frequency values.

    Parameters
    ----------
    frequencies : numpy.ndarray
        List of conformers' frequencies.

    Returns
    -------
    numpy.ndarray
        List of number of imaginary values in each file."""
    imag = (frequencies < 0).sum(1)
    return np.nonzero(imag)


def gaussian(bar, freq, base, hwhm):
    """Gaussian fitting function for spectra calculation.

    Parameters
    ----------
    bar: numpy.ndarray
        Appropriate values extracted from gaussian output files.
    freq: numpy.ndarray
        Frequencies extracted from gaussian output files.
    base: numpy.ndarray
        List of wavelength/wave number points on spectrum range.
    hwhm: int or float
        Number representing half width of maximum peak hight.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values.
    """
    sigm = hwhm / math.sqrt(2 * math.log(2))
    it = np.nditer(
        [base, None], flags=['buffered'],
        op_flags=[['readonly'], ['writeonly', 'allocate', 'no_broadcast']],
        op_dtypes=[np.float64, np.float64]
    )
    for lam, peaks in it:
        e = bar * np.exp(-0.5 * ((lam - freq) / sigm) ** 2)
        peaks[...] = e.sum() / (sigm * (2 * math.pi) ** 0.5)
    return it.operands[1]


def lorentzian(bar, freq, base, hwhm):
    """Lorentzian fitting function for spectra calculation.

    Parameters
    ----------
    bar: numpy.ndarray
        Appropriate values extracted from gaussian output files.
    freq: numpy.ndarray
        Frequencies extracted from gaussian output files.
    base: numpy.ndarray
        List of wavelength/wave number points on spectrum range.
    hwhm: int or float
        Number representing half width of maximum peak hight.

    Returns
    -------
    numpy.ndarray
        List of calculated intensity values.
    """
    it = np.nditer(
        [base, None], flags=['buffered'],
        op_flags=[['readonly'], ['writeonly', 'allocate', 'no_broadcast']],
        op_dtypes=[np.float64, np.float64]
    )
    for lam, val in it:
        s = bar / ((freq - lam) ** 2 + hwhm ** 2)
        s2 = hwhm / math.pi * s.sum()
        val[...] = s2
    return it.operands[1]


def intensities(bars, frequencies, genre, t=289.15, laser=532):
    pass


def calculate_spectra(frequencies, intensities, start, stop, step, hwhm, fitting):
    """Calculates spectrum for each individual conformer.

    Parameters
    ----------
    frequencies : numpy.ndarray
        List of conformers' frequencies. Should be of shape
        (number _of_conformers, number_of_frequencies).
    intensities : numpy.ndarray
        List of calculated signal intensities for each conformer. Should be
        of same shape as frequencies.
    start : int or float
        Number representing begining of spectral range in cm^(-1).
    stop : int or float
        Number representing end of spectral range in cm^(-1).
    step : int or float
        Number representing step of spectral range in cm^(-1).
    hwhm : int or float
        Number representing half width of maximum peak height in cm^(-1).
    fitting : function
        Function, which takes bars, freqs, base, hwhm as parameters and
        returns numpy.array of calculated, non-corrected spectrum points.

    Returns
    -------
    numpy.ndarray
        Array of intensity values for each conformer.
    """
    base = np.arange(start, stop + step, step)
    # spectrum base, 1d numpy.array of wavelengths/wave numbers
    # electronic : bool, optional
    #     Name of spectrum, which is going to be calculated. Valid names
    #     are: vcd, ir, raman, roa, ecd, uv.
    # if electronic:
    #     width = hwhm / 1.23984e-4  # from eV to cm-1
    #     w_nums = 1e7 / base  # from nm to cm-1
    #     freqs = 1e7 / self.frequencies  # from nm to cm-1
    # else:
    #     width = hwhm
    #     w_nums = base
    #     freqs = self.frequencies
    spectra = np.zeros([len(frequencies), base.shape[0]])  # template
    for bar, freq, spr in zip(intensities, frequencies, spectra):
        spr[...] = fitting(bar, freq, base, hwhm)
    return spectra  # , base ?


def average(spectra, populations):
    """Calculates weighted average of spectra, where populations are used as
    weights.

    Parameters
    ----------
    spectra : numpy.ndarray
        List of conformers' spectra, should be of shape (N, M), where N is
        number of conformers and M is number of spectral points.
    populations : numpy.ndarray
        List of conformers' populations, should be of shape (N,) where N is
        number of conformers. Should add up to 1.

    Returns
    -------
    numpy.ndarray
        Averaged spectrum.

    Raises
    ------
    ValueError
        If parameters of non-matching shape were passed.

    TO DO
    -----
    Add checking if populations add up to 1"""
    # populations must be of same shape as spectra
    # so we expand populations with np.newaxis
    popul = populations[:, np.newaxis]
    if not spectra.shape == popul.shape:
        raise ValueError(
            f"Cannot broadcast populations of shape {populations.shape} with"
            f"spectra of shape {spectra.shape}."
        )
    return (spectra * popul).sum(0)


###################
###   CLASSES   ###
###################

class Trimmer:
    """
    """

    blade = dscr.BladeDescr()

    def __init__(self, owner):
        self.owner = owner
        self.blade = np.ones(self.owner.true_size, dtype=bool)

    def set(self, value):
        self.blade = value

    def update(self, other):
        if isinstance(other, DataArray):
            value = other.trimmer.blade
        elif isinstance(other, Trimmer):
            value = other.blade
        else:
            value = other
        other_blade = np.array(value, dtype=bool)
        try:
            self.blade = np.logical_and(self.blade, other_blade)
        except ValueError:
            logger.exception("Cannot update {}'s trimmer with object of "
                             "different size. Size should be {}, not {}.".format(
                self.owner.genre, self.blade.size, other_blade.size))

    def match(self, other):
        if not isinstance(other, DataArray):
            raise TypeError('Cannot match with {}. Can match only with '
                            'objects of type Data.'.format(type(other)))
        previous_trimming = self.owner.trimming
        self.owner.trimming = False
        if other.filenames.size > self.owner.filenames.size:
            raise ValueError("{} can't match bigger object: {}."
                             .format(self.owner.genre, other.genre))
        blade = np.isin(self.owner.filenames, other.filenames)
        # print(blade)
        if np.isin(other.filenames, self.owner.filenames).all():
            self.set(blade)
            self.owner.trimming = True
        else:
            self.owner.trimming = previous_trimming
            raise ValueError("Can't match object: {0} with {1}. {1} has "
                             "entries absent in {0}.".format(self.owner.genre, other.genre))

    def unify(self, other, preserve_blade=True, overriding=False):
        if not isinstance(other, DataArray):
            raise TypeError('Cannot match with {}. Can match only with '
                            'objects of type Data.'.format(type(other)))
        if self.owner.filenames.shape == other.filenames.shape and \
                (self.owner.filenames == other.filenames).all():
            logger.debug('{} and {} already matching, no need to unify'
                         .format(self.owner.genre, other.genre))
            return
        else:
            logger.debug('Will make an attempt to unify {} and {}'
                         .format(self.owner.genre, other.genre))
        previous_trimming = self.owner.trimming
        other_trimming = other.trimming
        self.owner.trimming = False
        if overriding or not preserve_blade:
            other.trimming = False
        if not np.intersect1d(other.filenames, self.owner.filenames).size:
            self.owner.trimming = previous_trimming
            other.trimming = other_trimming
            raise ValueError("Can't unify objects without common entries.")
        blade = np.isin(self.owner.filenames, other.filenames)
        # print(blade)
        func = self.update if preserve_blade else self.set
        func(blade)
        self.owner.trimming = True
        other.trimmer.match(self.owner)

    def reset(self):
        self.blade = np.ones(self.owner.true_size, dtype=bool)

    # from DataArray class

    # @property
    # def trimmed(self):
    #     temp = copy(self)
    #     temp.trimmer = Trimmer(self)
    #     temp.trimmer.set(self.trimmer.blade)
    #     temp.trimming = True
    #     return temp
    #
    # @property
    # def full(self):
    #     temp = copy(self)
    #     temp.trimmer = Trimmer(self)
    #     temp.trimming = False
    #     return temp

    # def trimm_by_stoich(self, stoich=None):
    #     if stoich:
    #         wanted = stoich
    #     else:
    #         counter = Counter(self.stoich)
    #         try:
    #             wanted = counter.most_common(1)[0][0]
    #         except IndexError:
    #             wanted = ''
    #     blade = self._full_stoich == wanted
    #     self.trimmer.update(blade)
    #     self.trimming = True
    #     return self
    #
    # @contextmanager
    # def temporarily_trimmed(self, blade=None):
    #     curr_trimm = self.trimming
    #     self.trimming = True
    #     if blade is not None:
    #         old_blade = self.trimmer.blade
    #         self.trimmer.set(blade)
    #     yield self
    #     if blade is not None:
    #         self.trimmer.set(old_blade)
    #     self.trimming = curr_trimm


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

    associated_genres = 'zpec tenc entc gibc mass frc emang depolarp ' \
                        'depolaru depp depu alpha2 beta2 alphag gamma2 ' \
                        'delta2 cid1 cid2 cid3 rc180'.split(' ')

    @staticmethod
    def get_constructor(genre):
        constructors = {
            key: cls for cls in DataArray.__subclasses__()
            for key in cls.associated_genres
        }
        return constructors[genre]

    @staticmethod
    def make(genre, filenames, values, dtype=float, **kwargs):
        try:
            cls = DataArray.get_constructor(genre)
        except KeyError:
            cls = DataArray
        instance = cls(genre, filenames, values, dtype=dtype, **kwargs)
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
    def values(self, value):
        if not len(value) == len(self.filenames):
            raise ValueError(
                f"Values and filenames must be the same length. Arrays of"
                f"length {len(value)} and {len(self.filenames)} were given."
            )
        self.__values = np.array(value, dtype=self.dtype)


class Info(DataArray):

    associated_genres = ['command cpu_time', 'transitions']

    def __init__(self, genre, filenames, values, dtype=str):
        super().__init__(genre, filenames, values, dtype=dtype)


class Booleans(DataArray):

    associated_genres = ['normal_termination', 'optimization_completed']

    def __init__(self, genre, filenames, values, dtype=bool):
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

    def __init__(self, genre, filenames, values, t=298.15):
        super().__init__(genre, filenames, values)
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
                 t=298.15, laser=532):
        super().__init__(genre, filenames, values)
        self.frequencies = frequencies
        self.t = t  # temperature in K
        self.laser = laser  # in nm
        # rename to raman_laser?

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
            raman = raman,
            roa = raman,
            ir = lambda obj: obj.frequencies / 91.48,
            vcd = lambda obj: obj.frequencies / 2.296e5,
            uv = lambda obj: obj.frequencies * 2.87e4,
            ecd = lambda obj: obj.frequencies / 22.96
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
        intensities = self.values * get_intensity_factor(self)
        return intensities

    @property
    def imaginary(self):
        """Finds number of imaginary frequencies of each conformer.

        Returns
        -------
        numpy.ndarray
            Number of imaginary frequencies of each conformer."""
        return (self.frequencies < 0).sum(1)

    def find_imag(self):
        """Finds all freqs with imaginary values and creates 'imag' entry with
        list of indicants of imaginery values presence.
        
        Returns
        -------
        numpy.ndarray
            List of number of imaginary values in each file.
        """
        imag = self.imag.sum(1)
        indices = np.nonzero(imag)
        pairs = np.array([self.filenames, imag]).T
        # print(imag, indices, pairs)
        return {k: v for k, v in pairs[indices]}

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
        if output: logger.info(
            "{} spectra calculated with HWHM = {} and {} fitting.".format(
                self.spectra_name, hwhm, fitting.__name__))
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

    def __init__(self, name, filenames, abscissa, values, hwhm, fitting):
        super().__init__(Bars.spectra_type_ref[name],
                         filenames, values=values)
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
