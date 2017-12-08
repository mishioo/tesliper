import os, sys, re
import math
import numpy as np
from time import clock
from datetime import datetime
from collections.abc import Mapping, MutableMapping
from collections import defaultdict
import win32gui
import csv
from tkinter import Tk
from tkinter.filedialog import askdirectory, askopenfilename
import matplotlib.pyplot as plt


__author__ = "Michał Więcław"
__version__ = "0.4.1"


class Extractor(Mapping):
    """A tool for data extraction from gaussian output file.
    
    This object is a dict-like container with set of compiled regular
    expresion objects and set of methods which can be used to extract data
    from gaussian output files. Extracting methods can be acessed by getting
    value bound to keyword. Typical use:
    
    >>> e = Extractor()
    >>> extracted = e['keyword']('text to extract from')
    
    extracted is then a string or list of strings, depending on keyword.
    Re objects can be get as dictionary under 'regexs' attribute if needed.
    
    Attributes
    ----------
    regexs: dict
        Dictionary of compiled regular expresion objects.
    
    TO DO
    -----
    Unify inner dict to only work as in example. ?
    Add handling of AttributeError when match not found (group() method
    called on None).
    """
    
    def __init__(self):
        self.regexs = self.get_regexs()
        self._storage = {'command': self.get_command,
                         'stoich': self.get_stoich,
                         'energies': self.get_energies,
                         'vibra': self.get_vibra_dict(),
                         'electr': self.get_electr_dict(),
                         'popul': self.get_popul,
                         'settings': self.get_settings
                        }

    def __getitem__(self, key):
        return self._storage[key]
    
    def __iter__(self):
        for item in self._storage: yield item
    
    def __len__(self):
        return len(self._storage)
    
    def get_regexs(self):
    
        def electr_dict(pat1, pat2):
            if not pat2:
                return re.compile(r'(\d*\.\d+) {}'.format(pat1)), ''
            else:
                temp = re.compile(r'{}.*?\n((?:\s*-?\d+\.?\d*\s*)*)'\
                                  .format(pat1))
                return temp, re.compile(r'(-?\d+\.?\d*){}'.format(pat2))

        r = {}
        d = {'efreq': ('nm',''),
             'energy': ('eV', ''),
             'vosc': ('velocity dipole.*:\n', '\n'),
             'vrot': (r'R\(velocity\)', r'\s*\d+\.?\d*\n'),
             'losc': ('electric dipole.*:\n', '\n'),
             'lrot': (r'R\(length\)', '\n'),
             'ee-m': (r'E-M Angle', '\n')}
        r['electr'] = {k:electr_dict(*v) for k,v in d.items()}
        r['command'] = re.compile(r'\#(.*?)\n\s-', flags=re.DOTALL)
        r['stoich'] = re.compile(r'Stoichiometry\s*(\w*)\n')
        ens_patt = (r' Zero-point correction=\s*(-?\d+\.?\d*).*\n'
            r' Thermal correction to Energy=\s*(-?\d+\.?\d*)\n'
            r' Thermal correction to Enthalpy=\s*(-?\d+\.?\d*)\n'
            r' Thermal correction to Gibbs Free Energy=\s*(-?\d+\.?\d*)\n'
            r' Sum of electronic and zero-point Energies=\s*(-?\d+\.?\d*)\n'
            r' Sum of electronic and thermal Energies=\s*(-?\d+\.?\d*)\n'
            r' Sum of electronic and thermal Enthalpies=\s*(-?\d+\.?\d*)\n'
            r' Sum of electronic and thermal Free Energies=\s*(-?\d+\.?\d*)')
        r['ens'] = re.compile(ens_patt)
        r['scf'] = re.compile(r'SCF Done.*=\s+(-?\d+\.?\d*)')
        keys = 'vfreq dip rot ir ve-m raman1 roa1'.split(' ')
        pats = 'Frequencies', 'Dip. str.', 'Rot. str.', 'IR Inten',\
               'E-M angle', 'Raman1', 'ROA1'
        r['vibra'] = {key: re.compile(r'{}\s*--\s+(.*)\n'.format(patt))
                      for key, patt in zip(keys, pats)}
        r['popul'] = re.compile(r'(-?\w.*?)\s')
        r['settings'] = re.compile(r'(-?\d+.?d\*|lorentzian|gaussian)')
        return r
    
    def get_command(self, text):
        return self.regexs['command'].search(text).group(1)
    
    def get_stoich(self, text):
        return self.regexs['stoich'].search(text).group(1)
    
    def get_energies(self, text):
        ens = self.regexs['ens'].search(text).groups()
        scf = self.regexs['scf'].findall(text)[-1]
        return (*ens, scf)
        
    def get_vibra_dict(self):
        def wrapper(patt):
            def inner(text):
                match = patt.findall(text)
                return [s for g in match for s in g.split(' ') if s]
            return inner
        return {key:wrapper(patt)
                for key, patt in self.regexs['vibra'].items()}
        
    def get_electr_dict(self):
        def wrapper(pat1, pat2=None):
            def inner(text):
                if not pat2:
                    return pat1.findall(text)
                else:
                    temp = pat1.search(text).group(1)
                    return pat2.findall(temp)
            return inner
        return {k:wrapper(*v) for k,v in self.regexs['electr'].items()}
        
    def get_popul(self, text):
        return self.regexs['popul'].findall(text)
        
    def get_settings(self, text):
        sett = self.regexs['settings'].findall(text.lower()).groups()
        sett = {k: v for k, v in zip(('hwhm start stop step fitting'\
                                      .split(' '), sett))}
        return sett
        
class Soxhlet:
    """A tool for data extraction from files in specific directory.
    
    Attributes
    ----------
    path: str
        Path of directory bounded to Soxhlet instance.
    files: list
        List of files present in directory bounded to Soxhlet instance.
    extractor: Extractor object
        Extractor class instance used to extract data from files.
    command: str or None
        
    spectra_type: str or None
    
    gaussian_files
    bar_files
    
    TO DO
    -----
    Supplement this docstring.
    After Unifying Extractor class, do same with this class.
    """
    
    @classmethod
    def from_pointer(cls):
        window = win32gui.GetForegroundWindow()
        Tk().withdraw()
        path = askdirectory()
        win32gui.SetForegroundWindow(window)
        return cls(path)
    
    def __init__(self, path):
        self.path = path
        self.files = os.listdir(path)
        self.extractor = Extractor()
        self.command = self.get_command()
        self.spectra_type = self.get_spectra_type()

    @property
    def gaussian_files(self):
        """List of (sorted by file name) gaussian output files from files
        list associated with Soxhlet instance.
        """
        try:
            return self.__gf
        except AttributeError:
            try:
                ext = self.log_or_out()
                gf = sorted(self.filter_files(ext))
            except ValueError:
                gf = None
            self.__gf = gf
            return self.__gf
    
    @property
    def bar_files(self):
        """List of (sorted by file name) *.bar files from files list
        associated with Soxhlet instance.
        """
        try:
            return self.__bar
        except AttributeError:
            try:
                ext = '.bar'
                bar = sorted(self.filter_files(ext))
            except ValueError:
                bar = None
            self.__bar = bar
            return self.__bar
        
    def filter_files(self, ext, files=None):
        """Filters files from file names list.
        
        Positional parameter:
        files --    list of strings representing file names
        ext --      string representing file extention
        
        Function filters file names in provided list. It returns list of
        file names ending with prowided ext string, representing file
        extention and number of files in created list as tuple.
        
        Parameters
        ----------
        ext : str
            List of strings containing keywords for extractiong.
        files : list, optional
            List of strings containing filenames to filter. If omitted,
            list of filenames associated with object is used.
                
        Returns
        -------
        list
            List of filtered filenames as strings.
        """
        files = files if files else self.files
        filtered = [f for f in files if f.endswith(ext)]
        return filtered
         
    def log_or_out(self, files=None):
        """Checks list of file extentions in list of file names.
        
        Function checks for .log and .out files in passed list of file names.
        If both are present, it raises TypeError exception.
        If either is present, it raises ValueError exception.
        It returns string representing file extention present in files list.
        
        Parameters
        ----------
        files : list, optional
            List of strings containing filenames to check. If omitted,
            list of filenames associated with object is used.
                
        Returns
        -------
        str
            '.log' if *.log files are present in filenames list or '.out' if
            *.out files are present in filenames list.
            
        Raises
        ------
        TypeError
            If both *.log and *.out files are present in list of filenames.
        ValueError
            If neither *.log nor *.out files are present in list of filenames.
        """
        files = files if files else self.files
        logs, outs = (any(f.endswith(ext) for f in files) \
                      for ext in ('.log', '.out'))
        if outs and logs:
            raise TypeError(".log and .out files mixed in directory.")
        elif not outs and not logs:
            raise ValueError("Didn't found any .log or .out files.")
        else:
            return '.log' if logs else '.out'        
        
    def get_command(self):
        """Parses first gaussian output file associated with Soxhlet instance
        and extracts gaussian command used to initialized calculations.
        
        Returns
        -------
        str:
            String representing extracted gaussian command.
        """
        if not self.gaussian_files:
            return None
        with open(os.path.join(self.path, self.gaussian_files[0])) as f:
            cont = f.read()
        command = self.extractor['command'](cont).lower()
        return command
 
    def get_spectra_type(self):
        """Parses gaussian command to determine spectra type.
        
        Returns
        -------
        str: {'vibra', 'electr'}
            'vibra' if vibrational or 'electr' if electronic spectra was
            calculated.
        None:
            None is returned if nor vibrational neitherelectronic spectra was
            calculated.
        """
        if not self.command:
            return None
        elif 'freq' in self.command:
            return 'vibra'
        elif 'td=' in self.command:
            return 'electr'
        else:
            return None
            
    def extract(self, request, spectra_type=None):
        """From gaussian files associated with object extracts values related
        to keywords provided in arguments. Assumes spectra_type associated
        with object if not specified.
        
        Parameters
        ----------
        request : list
            List of strings containing keywords for extractiong.
        spectra_type : str, optional
            Type of spectra which is to extract; valid values are
            'vibra', 'electr' or '' (if spectrum is not present
            in gaussian output files); if omitted, spectra_type
            associated with object is used.
                
        Returns
        -------
        dict
            Dictionary with extracted data.
        """
        spectra_type = spectra_type if spectra_type else self.spectra_type 
        no = len(self.gaussian_files)
        keys = [t for t in request if t != 'energies']
        energies_requested = 'energies' in request
        if energies_requested:
            energies_keywords = \
                'zpec tenc entc gibc zpe ten ent gib scf'.split(' ')
            keys[-1:-1] = energies_keywords
        output = defaultdict(lambda: [None] * no)
        output['filenames'] = self.gaussian_files
        for num, file in enumerate(self.gaussian_files):
            with open(os.path.join(self.path, file)) as handle:
                cont = handle.read()
            for thing in request:
                if thing == 'energies':
                    energies = self.extractor[thing](cont)
                    for k, e in zip(energies_keywords, energies):
                        output[k][num] = e
                elif thing == 'stoich':
                    output[thing][num] = self.extractor[thing](cont)
                elif spectra_type:
                    temp = self.extractor[spectra_type][thing](cont)
                    output[thing][num] = temp
        return output
        
    def load_bars(self, spectra_type=None):
        """Parses *.bar files associated with object and loads spectral data
        previously extracted from gaussian output files.
                
        Returns
        -------
        dict
            Dictionary with extracted spectral data.
            
        TO DO
        -----
        Make sure Transitions not needed.
        """
        spectra_type = spectra_type if spectra_type else self.spectra_type
        no = len(self.bar_files)
        #Create empty dict with list of empty lists as default value.
        output = defaultdict(lambda: [[] for _ in range(no)])
        keys = 'vfreq dip rot ve-m'.split(' ') if spectra_type == 'vibra' else \
               'efreq vosc srot losc lrot energy ee-m'.split(' ')
        for num, bar in enumerate(self.bar_files):
            with open(os.path.join(self.path, bar), newline='') as handle:
                header = handle.readline()
                col_names = handle.readline()
                if 'Transition' in col_names and 'ee-m' in keys:
                    keys = keys[:-1]
                reader = csv.reader(handle, delimiter='\t')
                for row in reader:
                    #For each row in *.bar file copy value to corresponding
                    #position in prepared output dict
                    for k, v in zip(keys, row):
                        #output[value type][file position in sorted list]
                        output[k][num].append(float(v))
        return output
        
    def load_popul(self):
        """Parses BoltzmanDistribution.txt file associated with object and
        loads conformers' energies previously extracted from gaussian output
        files and calculated populations.
                
        Returns
        -------
        dict
            Dictionary with extracted data.
        """
        keys = 'filenames scfp entp gibp scfd entd gibd scf ent gib imag '\
               'stoich'.split(' ')
        output = defaultdict(list)
        with open(os.path.join(self.path, 'BoltzmanDistribution.txt')) as blz:
            header1 = blz.readline()
            header2 = blz.readline()
            for row in blz.readlines():
                for k, v in zip(keys, self.extractor['popul'](row)):
                    try:
                        v = float(v)
                    except ValueError:
                        if '%' in v:
                            v = float(v[:-1])/100
                    output[k].append(v)
        return output
        
    def load_settings(self):
        """Parses Setup.txt file associated with object and returns dict with
        extracted values. Prefers Setup.txt file over *Setup.txt files.
        
        Returns
        -------
        dict
            Dictionary eith extracted settings data.
            
        Raises
        ------
        FileNotFoundError
            If no or multiple setup.txt files found.
        """
        try:
            f = open("Setup.txt", "r")
        except FileNotFoundError:
            fls = [file.endswith('Setup.txt') for file in self.files]
            if len(fls) != 1:
                raise FileNotFoundError("No or multiple setup files in "\
                                        "directory.")
            else:
                f = open(fls[0], "r")
        sett = self.extractor["settings"](f)
        f.close()
        return sett
        
    def parse_command(self):
        """Parses gaussian command extractet from first output file
        in associated files list.
        
        Returns
        -------
        list
            List of key-words needed for data extraction.
        """
        cmd = self.command.lower()
        prsr = {'opt': 'energies',
                'freq=': 'vfreq',
                'freq=vcd': 'dip rot ir ve-m',
                'freq=roa': 'raman1 roa1',
                'td=': 'efreq energy vosc vrot lrot losc ee-m'
                }
        args = ' '.join(v for k, v in prsr if k in cmd).split(' ')
        return args
            
        
class Data(MutableMapping):
    """Dict-like storage for all spectra-related data. Contains methods for
    calculating populations of conformers and theoretical spectra.
    
    Note
    ----
    Calculated values are automatically bounded to instance on which the 
    corresponding method was called. All data should be stored as
    numpy.ndarray. Below is the list of key-words used by this class:
    filenames
        List of filenames of gaussian output files, from whitch data were
        extracted.
    stoich
        Stoichiometry of each conformer.
    zpec
        Zero-point correction.
    tenc
        Thermal correction to Energy.
    entc
        Thermal correction to Enthalpy.
    gibc
        Thermal correction to Gibbs Free Energy.
    zpe
        Sum of electronic and zero-point Energies.
    ten
        Sum of electronic and thermal Energies.
    ent
        Sum of electronic and thermal Enthalpies.
    gib
        Sum of electronic and thermal Free Energies.
    scf
        Self-consistent field energy.
    entd
        Excess of energy of each conformer based on ent.
    gibd
        Excess of energy of each conformer based on gib.
    scfd
        Excess of energy of each conformer based on scf.
    entp
        Distribution of conformers' population based on ent.
    gibp
        Distribution of conformers' population based on gib.
    scfp
        Distribution of conformers' population based on scf.
    vfreq
        Frequencies (corresponding to vibrational spectra).
    dip
        Dip. Str. bars.
    rot
        Rot. Str. bars.
    raman1
        Raman 1 bars.
    roa1
        ROA1 bars.
    ve-m
        Values of E-M Angle (vibrational spectra).
    efreq
        Frequencies (corresponding to electronic spectra).
    vosc
        Velocity oscillator strength bars.
    vrot
        R(velocity) bars.
    losc
        Length oscillator strength bars.
    lrot
        R(length) bars.
    ee-m
        Values of E-M Angle (electronic spectra).
    
    Attributes
    ----------
    Boltzmann: float
        Value of Boltzmann constant in kcal/(mol*K).
        
    TO DO
    -----
    Check calculations of ecd spectrum, on HWHM = 0.35 peaks should be much
    broader (close to as on HWHM = 7.0)
    """

    Boltzmann = 0.0019872041 #kcal/(mol*K)

    def __init__(self):
        #energies = 'zpec tenc entc gibc zpe ten ent gib scf'.split(' ')
        #vibra = 'vfreq dip rot ir ve-m raman1 roa1'.split(' ')
        #electr = 'efreq energy vosc vrot lrot losc'.split(' ')
        #self._data = dict.fromkeys([*energies, *vibra, *electr])
        self._data = {}
        self._av_spectr = {}
    
    def __getitem__(self, key):
        #TO DO: calculate value if not calculated yet ?
        try:
            return self._av_spectr[key]
        except KeyError:
            return self._data[key]
    
    def __setitem__(self, key, value):
        if key.startswith(('gib_', 'ent_', 'scf_')):
            self._av_spectr[key] = value
            return
        if isinstance(value, list):
            try:
                value = np.array(value, dtype=float)
            except ValueError:
                pass
        self._validate(key, value)
        self._data[key] = value
    
    def __delitem__(self):
        del self._data[key]
    
    def __iter__(self):
        return iter(self._data)
    
    def __len__(self):
        return len(self._data)
        
    def _validate(self, key, value):
        """Method for validating data for inner compatibility during setting
        as value of this dict-like object.
        
        Raises
        ------
        ValueError
            If loded list/array is of different length than expected (does
            not match length of files' list stored under 'filenames' key).
        TypeError
            If stoichiometry of conformers which data is loaded does not match
            stoichioetry of conformers already associated with data object.
            
        TO DO
        -----
        In case of non-matchnig length check filenames and filter accordingly.
        """
        if not self:
            return
        files = self['filenames']
        #spectra = 'vcd ir raman1 roa1 ecd uv'
        if not (len(files) == len(value)): # or key in spectra):
            raise ValueError(
                "Loaded data must contain same number of entries (files "
                "of certain type in directory) as data already got."
                "Loaded data marked as {} has {} entries, shoud have {}."\
                .format(key, len(value), len(files))
                )
        if key == 'stoich' and 'stoich' in self:
            stoich = self['stoich']
            check = value != stoich
            if check.sum():
                raise TypeError(
                    "Stoichiometry from loaded files does not match in {}/{} "
                    "entries.".format(check,sum(), len(stoich)), check
                    )
    
    def calc_popul(self, t=298.15):
        """Calculates populations and energy excesses for all tree types of
        energy (ent, gib, scf) in given temperature and bounds outcome to
        Data instance on which method was called.
        
        Parameters
        ----------
        t: int or float
            Temperature of calculated state.
        """
        for e in ('ent', 'gib', 'scf'):
            self['{}d'.format(e)], self['{}p'.format(e)] = \
                self._boltzmann_dist(self[e], t)
                
    def _boltzmann_dist(self, energies, t):
        """Calculates populations and energy excesses of conformers, based on
        energy array and temperature passed to function.
        
        Parameters
        ----------
        energies: numpy.ndarray
            List of conformers' energies.
        t: int or float
            Temperature of calculated state.
            
        Returns
        -------
        tuple of numpy.ndarray
            Tuple of arrays with energy excess for each conformer and population
            distribution in given temperature.
        """
        delta = (energies - energies.min()) * 627.5095
        x = np.exp(-delta/(t*self.Boltzmann))
        popul = x/x.sum()
        return delta, popul
        
    def find_imag(self):
        """Finds all freqs with imaginary values and creates 'imag' entry with
        list of indicants of imaginery values presence.
        
        Returns
        -------
        numpy.ndarray
            List of number of imaginary values in each file.
        """
        self['imag'] = self['vfreq'] < 0
        return self['imag'].sum(0)
        
    def average_spectra(self, spectra_name, popul_type):
        """A method for averaging spectra by population of conformers.
        
        Parameters
        ----------
        spectra_name: str
            Key-word corresponding to spectra of certain type.
        popul_type: str
            Key-word corresponding to population distribution of certain type.
            
        Returns
        -------
        numpy.ndarray
            2d numpy array where arr[0] is list of wavelengths/wave numbers
            and arr[1] is list of corresponding averaged intensity values.
        """
        spectra, popul = self[spectra_name], self[popul_type]
        #popul must be of same shape as spectra
        #so we expand popul with np.newaxis
        av = (spectra[0,1,:] * popul[:, np.newaxis]).sum(0)
        av_spec = np.array([spectra[0][0], av])
        #self['av_{}'.format(spectra_name)] = av_spec
        self._av_spectr["{}_{}".format(popul_type[:3], spectra_name)] = av_spec
        return av_spec
        #av_spec = sum(s * p for s, p in zip(spectra[1], populations))
    
    def calculate_spectra(self, type, start, stop, step, hwhm, fitting):
        """Calculates spectrum of desider type for each individual conformer.
        
        Parameters
        ----------
        type: str
            Name of spectrum, which is going to be calculated. Valid names
            are: vcd, ir, raman, roa, ecd, uv.
        start: int or float
            Number representing start of spectral range in relevant units.
        stop: int or float
            Number representing end of spectral range in relevant units.
        step: int or float
            Number representing step of spectral range in relevant units.
        hwhm: int or float
            Number representing half width of maximum peak hight.
        fitting: function
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
        bars, freqs, factor = self.spectr_type_ref[type]
        factor = factor(base) if callable(factor) else factor
        #self[type] = np.zeros(base.shape) - unnececery
        #TO DO: do it numpy way
        temp = []
        for bar, freq in zip(self[bars], self[freqs]):
            spectrum = self._calc_spectr(bar, freq, base, hwhm, factor,
                                               fitting)
            temp.append(np.array([base, spectrum]))
        self[type] = temp
        return self[type]
        
    def calc_single_spectrum(self, type, start, stop, step, hwhm, fitting):
        """A method for calculating spectrum of single conformer.
        
        Note
        ----
        This method does not bound resultiong spectrum to its instance.
        
        Parameters
        ----------
        type: str
            Name of spectrum, which is going to be calculated. Valid names
            are: vcd, ir, raman, roa, ecd, uv.
        start: int or float
            Number representing start of spectral range in relevant units.
        stop: int or float
            Number representing end of spectral range in relevant units.
        step: int or float
            Number representing step of spectral range in relevant units.
        hwhm: int or float
            Number representing half width of maximum peak hight.
        fitting: function
            Function, which takes bars, freqs, base, hwhm as parameters and
            returns numpy.array of calculated, non-corrected spectrum points.
            
        Returns
        -------
        numpy.ndarray
            2d numpy array where arr[0] is list of wavelengths/wave numbers
            and arr[1] is list of corresponding intensity values.
        """
        base = np.arange(start, stop+step, step)
            #spectrum base, 1d numpy.array of wavelengths/wave numbers
        bars, freqs, factor = self.spectr_type_ref[type]
        factor = factor(base) if callable(factor) else factor
        self[type] = np.zeros(base.shape)
        spectrum = self._calc_spectr(bar, freq, base, hwhm, factor, fitting)
        return np.array([base, spectrum])
        
    def _calc_spectr(self, bar, freq, base, hwhm, factor, fitting):
        """A method used for calculating single spectra.
        
        Parameters
        ----------
        bar: numpy.array
            Appropiate values extracted from gaussian output files.
        freq: numpy.array
            Frequencies extracted from gaussian output files.
        base: numpy.array
            List of wavelength/wave number points on spectrum range.
        hwhm: int or float
            Number representing half width of maximum peak hight.
        factor: int or float or numpy.array
            Factor (or numpy.array of factors), which non-corrected spectrum
            points obtained from fitting function will be multiplied by.
        fitting: function
            Function, which takes bars, freqs, base, hwhm as parameters and
            returns numpy.array of calculated, non-corrected spectrum points.
            
        Returns
        -------
        numpy.ndarray
            List of calculated intensity values.
        """
        spectrum = factor * fitting(bar, freq, base, hwhm)
        return spectrum
        
    def gaussian(self, bar, freq, base, hwhm):
        """Gaussian fitting function for spectra calculation.
        
        Parameters
        ----------
        bar: numpy.array
            Appropiate values extracted from gaussian output files.
        freq: numpy.array
            Frequencies extracted from gaussian output files.
        base: numpy.array
            List of wavelength/wave number points on spectrum range.
        hwhm: int or float
            Number representing half width of maximum peak hight.
        
        Returns
        -------
        numpy.ndarray
            List of calculated intensity values.
        """
        sigm = hwhm / math.sqrt(2 * math.log(2))
        it = np.nditer([base, None], flags = ['buffered'],
                        op_flags = [['readonly'],
                            ['writeonly', 'allocate', 'no_broadcast']],
                        op_dtypes=[np.float64,np.float64]
                        )
        for lam, peaks in it:
            e = bar * np.exp(-0.5 * (lam - freq) ** 2 / sigm ** 2)
            peaks[...] = e.sum() / (sigm * (2 * math.pi)**0.5)
        return it.operands[1]
        
    def lorentzian(self, bar, freq, base, hwhm):
        """Lorentzian fitting function for spectra calculation.
        
        Parameters
        ----------
        bar: numpy.array
            Appropiate values extracted from gaussian output files.
        freq: numpy.array
            Frequencies extracted from gaussian output files.
        base: numpy.array
            List of wavelength/wave number points on spectrum range.
        hwhm: int or float
            Number representing half width of maximum peak hight.
        
        Returns
        -------
        numpy.ndarray
            List of calculated intensity values.
        """
        it = np.nditer([base, None], flags = ['buffered'],
                            op_flags = [['readonly'],
                                ['writeonly', 'allocate', 'no_broadcast']],
                            op_dtypes=[np.float64,np.float64])
        for lam, val in it:
            s = bar/((lam - freq)**2 + hwhm**2)
            s2 = lam * hwhm / (math.pi * 9.184e-39) * s.sum()
            val[...] = s2
        return it.operands[1]
    
    @property
    def spectr_type_ref(self):
        """Dictionary of bar key-words, frequency key-words anf values of
        factor needed for calculation of spectrum of certain type.
        """
        def uv_factor(freqs):
            return freqs * 3.07441575e-12 
        r = dict(
            #type = (bars, freqs, factor)
            vcd = ('rot', 'vfreq', 1.38607595e38),
            ir = ('dip', 'vfreq', 3.46518986e37),
            raman = ('raman1', 'vfreq', 0),
            roa = ('roa1', 'vfreq', 0),
            ecd = ('vrot', 'efreq', 3.07441575e+6),
            uv = ('vdip', 'efreq', uv_factor)
                )
        return r
        
    def show_spectrum(self, spectrum):
        """Simple method for ploting spectrum.
        
        Parameters
        ----------
        spectrum: iterable
            Two-element unpackable iterable of list of x and y coordinates.
        """
        plt.plot(*spectrum)
        plt.show()

        
class Settings:

    def __init__(self):
    
        self._output_dir = os.getcwd()
        self._work_dir = os.getcwd()
        
        self.spectra_type = None #'vibra', 'electr' or None
        self.standard_parameters = {
            'vibra': {'HWHM': 6,
                      'START': 800,
                      'STOP': 2900,
                      'STEP': 2,
                      'FITTING': 'lorentzian'},
            'electr': {'HWHM': 0.35,
                       'START': 150,
                       'STOP': 800,
                       'STEP': 1,
                       'FITTING': 'gaussian'}
            }
        self.set_standard_parameters()
        self._units = {
            'vibra': {'HWHM': 'cm-1',
                      'START': 'cm-1',
                      'STOP': 'cm-1',
                      'STEP': 'cm-1'},
            'electr': {'HWHM': 'eV',
                       'START': 'nm',
                       'STOP': 'nm',
                       'STEP': 'nm'}
            }

    def set_standard_parameters(self):
        self.parameters = {
            'vibra': self.standard_parameters['vibra'].copy(),
            'electr': self.standard_parameters['electr'].copy()
            }
    
    @property
    def work_dir(self):
        if not self._work_dir:
            self.change_work_dir
        return self._work_dir
    
    @property
    def output_dir(self):
        if not self._output_dir:
            self.change_output_dir
        return self._output_dir

    @property
    def units(self):
        return self._units[self.spectra_type]
    
    def change_dir(self, path=None, work=True, output=True):
        if not path:
            window = win32gui.GetForegroundWindow()
            Tk().withdraw()
            path = askdirectory()
            win32gui.SetForegroundWindow(window)
        if not path:
            print("Directory not choosen.")
        else:
            if work:
                os.chdir(path)
                self._work_dir = path
            if output:
                if not os.path.isdir(path):
                    os.makedirs(path)
                self._output_dir = path
            return path
            
    def set_type(self, spectra_type):
        if spectra_type not in ('vibra', 'electr') or \
                spectra_type is not None:
            raise ValueError("Settings.spectra_type \
                cannot be set to {}.".format(spectra_type))
        else:
            self.spectra_type = spectra_type
            return self.spectra_type
            
class Tesliper:
    """
    """
    
    def __init__(self):
        self.settings = Settings()
        self.data = Data()
        
    def load_files(self, path):
        self.soxhlet = Soxhlet(path)
        self.settings.set_type(self.soxhlet.spectra_type)
        self.settings.change_dir(path)
        
    def extract(self, *args, spectra_type=None, path=None):
        soxhlet = Soxhlet(path) if path else self.soxhlet
        data = soxhlet.extract(args, spectra_type)
        self.data.update(data)
        return self.data
    
    def smart_extract(self, deep_search=True, calculations=True,
                      average=True, save=True, with_load=True):
        #TO DO: do it
        pass
                
    def load_bars(self, spectra_type=None, path=None):
        soxhlet = Soxhlet(path) if path else self.soxhlet
        bars = soxhlet.load_bars(spectra_type)
        self.data.update(bars)
        return self.data
        
    def load_populations(self, path=None):
        soxhlet = Soxhlet(path) if path else self.soxhlet
        popul = soxhlet.load_popul()
        self.data.update(popul)
        return self.data
        
    def load_spectra(self, path=None):
        soxhlet = Soxhlet(path) if path else self.soxhlet
        spectra = soxhlet.load_spectra()
        self.data.update(spectra)
        return self.data
    
    def load_settings(self, path=None):
        soxhlet = Soxhlet(path) if path else self.soxhlet
        settings = soxhlet.load_settings()
        self.settings[self.settings.spectra_type].update(settings)
        return self.settings
            
    def change_dir(self, path=None):
        path = self.settings.change_dir(path)
        return path
        
    def change_work_dir(self, path=None):
        path = self.settings.change_dir(path, output=False)
        return path
        
    def change_output_dir(self, path=None):
        path = self.settings.change_dir(path, work=False)
        return path
                
    def calculate_populations(self, t=None):
        self.data.calc_popul(t)
        return self.data
        
    def calculate_spectra(*args, start=None, stop=None, step=None,
                          hwhm=None, fitting=None):
        if fitting == 'lorentzian':
            fit = self.data.lorentzian
        elif fitting == 'gaussian':
            fit = self.data.gaussian
        else:
            raise ValueError("Fitting style not recognized: {}"\
                             .format(fitting))
        settings = {k: v for k, v in
                    zip(('start', 'stop', 'step', 'hwhm', 'fitting'),
                        (start, stop, step, hwhm, fitting))
                    if v}
        for spectr in args:
            spectra_type = 'electr' if spectr in ('ecd', 'uv') else 'vibra'
            self.settings[spectra_type].update(settings)
            sett = self.settings[spectra_type]
            sett.update({'fitting': fit})
            self.data.calculate_spectra(spectr, **sett)
        
    def get_averaged_spectrum(self, spectr, popul_type):
        try:
            output = self.data.average_spectra(spectr, popul_type)
        except KeyError:
            self.smart_extract(average=False, save=False)
            output = data.average_spectra(spectr, popul_type)
        return output

    def save_output(self, *args):
        #TO DO: do it
        pass
        #populations, bars (with e-m), spectra, averaged, settings
        if 'popul' in args:
            pass
        if 'bars' in args:
            pass
        if 'averaged' in args:
            pass
        if 'settings' in args:
            pass
