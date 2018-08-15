###################
###   IMPORTS   ###
###################

import logging as lgg
import math
import numpy as np
from collections import Counter
from contextlib import contextmanager
from copy import copy
# from . import descriptors as dscr
import descriptors as dscr


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


def intensities(bars, type):
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
        if isinstance(other, Data):
            value = other.trimmer.blade
        elif isinstance(other, Trimmer):
            value = other.blade
        else:
            value = other
        other_blade = np.array(value, dtype=bool)
        try:
            self.blade = np.logical_and(self.blade, other_blade)
        except ValueError:
            logger.exception("Cannot update {}'s trimmer with object of "\
                "different size. Size should be {}, not {}.".format(
                    self.owner.type, self.blade.size, other_blade.size))
        
    def match(self, other):
        if not isinstance(other, Data): 
            raise TypeError('Cannot match with {}. Can match only with '\
                'objects of type Data.'.forma(type(other)))
        previous_trimming = self.owner.trimming
        self.owner.trimming = False
        if other.filenames.size > self.owner.filenames.size:
            raise ValueError("{} can't match bigger object: {}."\
                .format(self.owner.type, other.type))
        blade = np.isin(self.owner.filenames, other.filenames)
        #print(blade)
        if np.isin(other.filenames, self.owner.filenames).all():
            self.set(blade)
            self.owner.trimming = True
        else:
            self.owner.trimming = previous_trimming
            raise ValueError("Can't match object: {0} with {1}. {1} has "
                "entries absent in {0}.".format(self.owner.type, other.type))
    
    def unify(self, other, preserve_blade=True, overriding=False):
        if not isinstance(other, Data): 
            raise TypeError('Cannot match with {}. Can match only with '\
                'objects of type Data.'.forma(type(other)))
        if self.owner.filenames.shape == other.filenames.shape and \
                (self.owner.filenames == other.filenames).all():
            logger.debug('{} and {} already matching, no need to unify'\
                        .format(self.owner.type, other.type))
            return
        else:
            logger.debug('Will make an attempt to unify {} and {}'\
                        .format(self.owner.type, other.type))
        previous_trimming = self.owner.trimming
        other_trimming = other.trimming
        self.owner.trimming = False
        if overriding or not preserve_blade: other.trimming = False
        if not np.intersect1d(other.filenames, self.owner.filenames).size:
            self.owner.trimming = previous_trimming
            other.trimming = other_trimming
            raise ValueError("Can't unify objects without common entries.")
        blade = np.isin(self.owner.filenames, other.filenames)
        #print(blade)
        func = self.update if preserve_blade else self.set
        func(blade)
        self.owner.trimming = True
        other.trimmer.match(self.owner)
        
    def reset(self):
        self.blade = np.ones(self.owner.true_size, dtype=bool)
    
    
class Data:
    """Base class for data holding objects. It provides trimming functionality
    for filtering data based on other objects content or arbitrary choice.
    
    Parameters
    ----------
    filenames : numpy.ndarray(dtype=str)
        List of filenames of gaussian output files, from whitch data were
        extracted.
    stoich : numpy.ndarray(dtype=str)
        Stoichiometry of each conformer.
    values : numpy.ndarray(dtype=float)
        List of appropriate data values.
    true_size : int
        Number of files from which data was extracted.
    trimming : bool
        If set to True causes descriptors to return trimmed values.
    trimmer : Trimmer object instance
        Object providing trimming functionality.
    trimmed
        
    TO DO
    -----
    Create full_name_ref
    """
    
    #Descriptors:
    filenames = dscr.StrTypeArray('filenames')
    stoich = dscr.StrTypeArray('stoich')
    values = dscr.FloatTypeArray('values')

    full_name_ref = dict(
        rot = 'Rot. Strength',
        dip = 'Dip. Strength',
        roa1 = 'ROA1',
        raman1 = 'Raman1',
        vrot = 'Rot. (velo)',
        lrot = 'Rot. (lenght)',
        vosc = 'Osc. (velo)',
        losc = 'Osc. (length)',
        iri = 'IR Intensity',
        vemang = 'E-M Angle',
        eemang = 'E-M Angle',
        zpe = 'Zero-point Energy',
        ten = 'Thermal Energy',
        ent = 'Thermal Enthalpy',
        gib = 'Thermal Free Energy',
        scf = 'SCF',
        ex_en = 'Excitation energy',
        vfreq = 'Frequency',
        efreq = 'Wavelength',
        energies = 'Energies'
        )

    def __init__(self, type, filenames, stoich=None, values=None):
        self.type = type
        self.filenames = filenames
        self.true_size = self._full_filenames.size
            #self._full_filenames set by descriptor
        if stoich is not None: self.stoich = stoich
        if values is not None: self.values = values
        self.trimming = True
        self.trimmer = Trimmer(self)
        
    def __getitem__(self, key):
        #TO DO: figure out how to get rid of nested arrays
        #when single conformer is used
        single = self.full
        blade = single.filenames == key
        index, = np.where(blade)
        if index.size > 1:
            raise ValueError('No such conformer name found: {}.'.format(key))
        elif index.size < 1:
            raise ValueError('More than one such name: {}.'.format(key))
        else:
            single.trimmer.set(blade)
            single.trimming = True
            return single

    @property
    def trimmed(self):
        temp = copy(self)
        temp.trimmer = Trimmer(self)
        temp.trimmer.set(self.trimmer.blade)
        temp.trimming = True
        return temp
        
    @property
    def full(self):
        temp = copy(self)
        temp.trimmer = Trimmer(self)
        temp.trimming = False
        return temp
        
    @property
    def full_name(self):
        return self.full_name_ref[self.type]

    def trimm_by_stoich(self, stoich=None):
        if stoich:
            wanted = stoich
        else:
            counter = Counter(self.stoich)
            try:
                wanted = counter.most_common(1)[0][0]
            except IndexError:
                wanted = ''
        blade = self._full_stoich == wanted
        self.trimmer.update(blade)
        self.trimming = True
        return self
        
    @contextmanager    
    def temporarily_trimmed(self, blade=None):
        curr_trimm = self.trimming
        self.trimming = True
        if blade is not None:
            old_blade = self.trimmer.blade
            self.trimmer.set(blade)
        yield self
        if blade is not None:
            self.trimmer.set(old_blade)
        self.trimming = curr_trimm
    
                    
class Energies(Data):
    """
    Parameters
    ----------
    type : str
        Type of energy.
    filenames : numpy.ndarray(dtype=str)
        List of filenames of gaussian output files, from whitch data were
        extracted.
    stoich : numpy.ndarray(dtype=str)
        Stoichiometry of each conformer.
    values : numpy.ndarray(dtype=float)
        Energy value for each conformer.
    corrections : numpy.ndarray(dtype=float)
        Energy correction value for each conformer.
    populations : numpy.ndarray(dtype=float)
        Population value for each conformer.
    deltas : numpy.ndarray(dtype=float)
        Energy excess value for each conformer.
    t : int or float
        Temperature of calculated state in K.
    """
    
    #Descriptors:
    corrections = dscr.FloatTypeArray('corrections')

    Boltzmann = 0.0019872041 #kcal/(mol*K)
    
    def __init__(self, type, filenames, stoich, values, corrections=None,
                 t=None):
        super().__init__(type, filenames, stoich, values)
        if corrections:
            self.corrections = corrections
        self.t = t if t else 298.15
        
    @property
    def deltas(self):
        try:
            return (self.values - self.values.min()) * 627.5095
                #convert hartree to kcal/mol by multiplying by 627.5095
        except ValueError:
            #if no values, return empty array.
            return np.array([])
            
    @property
    def min_factor(self):
        # F(state_n)/F(state_min)
        return np.exp(-self.deltas / (self.t * self.Boltzmann))
        
    @property
    def populations(self):
        x = self.min_factor
        return x/x.sum()
        
    def calculate_populations(self, t=None):
        """Calculates populations and energy excesses for all tree types of
        energy (ent, gib, scf) in given temperature and bounds outcome to
        Data instance on which method was called.
        
        Notes
        -----
        If trimming functionality is used, populations should be recalculated
        after each change of trimming blade.
        
        Parameters
        ----------
        t : int or float, optional
            Temperature of calculated state in K. If omitted, value bounded to
            instance is used (298.15 K by default).
        """
        if t is not None:
            self.t = t
        else:
            t = self.t
        deltas, populations = self._boltzmann_dist(self.values, t)
        return populations
                
    def _boltzmann_dist(self, values, t):
        """Calculates populations and energy excesses of conformers, based on
        energy array and temperature passed to function.
        
        Parameters
        ----------
        values : numpy.ndarray
            List of conformers' energies.
        t : int or float
            Temperature of calculated state.
            
        Returns
        -------
        tuple of numpy.ndarray
            Tuple of arrays with energy excess for each conformer and population
            distribution in given temperature.
        """
        delta = (values - values.min()) * 627.5095
        x = np.exp(-delta/(t*self.Boltzmann))
        popul = x/x.sum()
        return delta, popul
        
        
class Bars(Data):

    #Descriptors:
    frequencies = dscr.FloatTypeArray('frequencies')
    excitation_energies = dscr.FloatTypeArray('excitation_energies')
    imag = dscr.IntTypeArray('imag')
    intensities = dscr.IntensityArray()

    spectra_name_ref = dict(
        rot = 'vcd',
        dip = 'ir',
        iri = 'ir',
        roa1 = 'roa',
        raman1 = 'raman',
        vrot = 'ecd',
        lrot = 'ecd',
        vosc = 'uv',
        losc = 'uv'
        )
    
    spectra_type_ref = dict(
        vcd = 'vibra',
        ir = 'vibra',
        roa = 'vibra',
        raman = 'vibra',
        ecd = 'electr',
        uv = 'electr'
        )
    
    def __init__(self, type, stoich, filenames, frequencies, values=None,
                 imag=None, t=None, laser=None, excitation_energies=None):
        super().__init__(type, filenames, stoich, values)
        self.frequencies = frequencies
        if values is None:
            self.values = self.frequencies
        if imag:
            self.imag = imag
        else:
            self.imag = self.frequencies < 0
        self.t = 298.15 if t is None else t #temperature in K
        if self.spectra_name in ('raman', 'roa'): #valid only for raman & roa
            self.laser = laser if laser is not None else 532 #in nm
        if self.spectra_name in ('uv', 'ecd'): #valid only for uv & ecd
            self.excitation_energies = excitation_energies
                        
    @property
    def spectra_name(self):
        if self.type in self.spectra_name_ref:
            return self.spectra_name_ref[self.type]
    
    @property
    def spectra_type(self):
        if self.type in self.spectra_name_ref:
            return self.spectra_type_ref[self.spectra_name]
        
    def find_imag(self):
        """Finds all freqs with imaginary values and creates 'imag' entry with
        list of indicants of imaginery values presence.
        
        Returns
        -------
        numpy.ndarray
            List of number of imaginary values in each file.
        """
        output = {}
        imag = self.imag.sum(1)
        indices = np.nonzero(imag)
        pairs = np.array([self.filenames, imag]).T
        # print(imag, indices, pairs)
        return {k: v for k, v in pairs[indices]}
        
    def calculate_spectra(self, start, stop, step, hwhm, fitting):
        """Calculates spectrum of desired type for each individual conformer.
        
        Parameters
        ----------
        type : str
            Name of spectrum, which is going to be calculated. Valid names
            are: vcd, ir, raman, roa, ecd, uv.
        start : int or float
            Number representing start of spectral range in relevant units.
        stop : int or float
            Number representing end of spectral range in relevant units.
        step : int or float
            Number representing step of spectral range in relevant units.
        hwhm : int or float
            Number representing half width of maximum peak hight.
        fitting : function
            Function, which takes bars, freqs, base, hwhm as parameters and
            returns numpy.array of calculated, non-corrected spectrum points.
            
        Returns
        -------
        numpy.ndarray
            Array of 2d arrays containing spectrum (arr[0] is list of
            wavelengths/wave numbers, arr[1] is list of corresponding
            intensity values).
        """
        base = np.arange(start, stop+step, step)
            #spectrum base, 1d numpy.array of wavelengths/wave numbers
        if self.spectra_type == 'electr':
            width = hwhm / 1.23984e-4 #from eV to cm-1
            w_nums = 1e7 / base #from nm to cm-1
            freqs = 1e7 / self.frequencies #from nm to cm-1
        else: 
            width = hwhm
            w_nums = base
            freqs = self.frequencies
        inten =  self.intensities
        spectra = np.zeros([len(freqs), base.shape[0]])
        for bar, freq, spr in zip(inten, freqs, spectra):
            spr[...] = fitting(bar, freq, w_nums, width)
        output = Spectra(self.spectra_name, self.filenames, base,
                          spectra, hwhm, fitting)
        if output: logger.info(
            "{} spectra calculated with HWHM = {} and {} fitting.".format(
                self.spectra_name, hwhm, fitting.__name__))
        return output


class Spectra(Data):
    
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
    
    def __init__(self, name, filenames, base, values, hwhm, fitting):
        super().__init__(Bars.spectra_type_ref[name],
                         filenames, values=values)
        self.trimming = False
        self.name = name
        self.base = base
        self.start = base[0]
        self.stop = base[-1]
        self.step = abs(base[0] - base[1])
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
        energy_type = energies.type
        try:
            old_popul = self._averaged[energy_type]['populations']
            if populations.shape == old_popul.shape:
                if (populations == old_popul).all():
                    logger.debug('Populations same as previously used. ' \
                                 'Returning cashed spectrum.') 
                    return self._averaged[energy_type]['spectrum']
                else:
                    logger.debug('Spectrum previously averaged with ' \
                                 'different populations.') 
            else:
                logger.debug('Spectrum previously averaged with ' \
                             'different populations.') 
        except KeyError:
            logger.debug('No previously averaged spectrum found.')
        with self.temporarily_trimmed():
            self.trimmer.match(energies)
            #populations must be of same shape as spectra
            #so we expand populations with np.newaxis
            av = (self.values * populations[:, np.newaxis]).sum(0)
            av_spec = np.array([self.base, av])
            self._averaged[energy_type] = dict(
                populations = populations,
                spectrum = av_spec,
                values = av,
                base = self.base)
        logger.info('{} spectrum averaged by {}.'.format(self.name,
                                                         energy_type))
        return av_spec
    
    @property
    def text_header(self):
        header = '{} spectrum, HWHM = {} {}, fitting = {}'
        header = header.format(
            self.name.upper(), self.hwhm, self.units[self.type]['hwhm'],
            self.fitting.__name__)
        return header
    
    @property
    def averaged_header(self):
        header = self.text_header + ', averaged by {}.'
        header.format(Data.full_name_ref[self.energy_type])
        return header

