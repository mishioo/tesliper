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
__version__ = "0.4.0"


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
    Unify inner dict to only work as in example.
    """
    
    def __init__(self):
        self.regexs = self.get_regexs()
        self._storage = {'command': self.get_command,
                         'stoich': self.get_stoich,
                         'energies': self.get_energies,
                         'vibra': self.get_vibra_dict(),
                         'eletcr': self.get_electr_dict(),
                         'popul': self.get_popul
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
                temp = re.compile(r'{}.*:\n.*\n((?:\s*-?\d+\.?\d*)*)'\
                                  .format(pat1))
                return temp, re.compile(r'(-?\d+\.?\d*){}'.format(pat2))

        r = {}
        d = {'freq': ('nm',''),
             'energy': ('eV', ''),
             'vosc': ('velocity dipole', '\n'),
             'vrot': (r'R(velocity)', r'\s*\d+\.?\d*\n'),
             'lrot': ('electric dipole', '\n'),
             'losc': (r'R(length)', '\n')}
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
        keys = 'freq dip rot ir e-m raman1 roa1'.split(' ')
        pats = 'Frequencies', 'Dip. str.', 'Rot. str.', 'IR Inten',\
               'E-M angle', 'Raman1', 'ROA1'
        r['vibra'] = {key: re.compile(r'{}\s*--\s+(.*)\n'.format(patt))
                      for key, patt in zip(keys, pats)}
        r['popul'] = re.compile(r'(-?\w.*?)\s')
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
    Move/Remove unnececery methods.
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
        elif 'nd=' in self.command:
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
            dictionary with extracted data
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
        
    def load_bars(self):
        """Parses *.bar files associated with object and loads spectral data
        previously extracted from gaussian output files.
                
        Returns
        -------
        dict
            dictionary with extracted spectral data
        """
        no = len(self.bar_files)
        #Create empty dict with list of empty lists as default value.
        output = defaultdict(lambda: [[] for _ in range(no)])
        for num, bar in enumerate(self.bar_files):
            with open(os.path.join(self.path, bar), newline='') as handle:
                header = handle.readline()
                reader = csv.reader(handle, delimiter='\t')
                keys = next(reader)
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
            dictionary with extracted data
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
    
    def smart_extract(self, path=None):
        if path:
            self.settings.change_dir(path)
        else:
            path = self.settings.work_dir
        files = self.load_files(path)
        filtered = self.filtered = filter_files(log_or_out(path))
        spectra_type = self.set_type()
        # establish to_get
        data = self.get_data(to_get)
        if 'energies' in to_get:
            pass
        if 'vibra' in to_get:
            pass
        if 'electr' in to_get:
            pass
        if ('vibra' in to_get or 'electr' in to_get) and 'energies' in to_get:
            #do it better
            pass
        
    def set_type(self, spectra_type=None):
        if spectra_type:
            self.settings.set_type(spectra_type)
        else:
            self.settings.set_type(self.get_type())
        return self.settings.spectra_type

    def load_files(self, path=None):
        path = path if path else self.settings.work_dir
        self.files = os.listdir(path)
            
    def get_data(self, to_get, settings=None):
        settings = self.settings if not settings else settings
        try:
            to_get = to_get.split(' ')
        except AttributeError:
            pass
        self.data = Data(settings)
        return self.data

        
class Data(MutableMapping):

    Boltzmann = 0.0019872041 #kcal/(mol*K)

    def __init__(self):
        energies = 'zpec tenc entc gibc zpe ten ent gib scf'.split(' ')
        vibra = 'freq dip rot ir e-m raman1 roa1'.split(' ')
        electr = 'efreq energy vosc vrot lrot losc'.split(' ')
        self._data = dict.fromkeys([*energies, *vibra, *electr])
    
    def __getitem__(self, key):
        #TO DO: calculate value if not calculated yet
        return self._data[key]
    
    def __setitem__(self, key, value):
        if isinstance(value, list):
            try:
                value = np.array(value, dtype=float)
            except ValueError:
                pass
        self._data[key] = value
    
    def __delitem__(self):
        del self._data[key]
    
    def __iter__(self):
        return iter(self._data)
    
    def __len__(self):
        return len(self._data)
    
    def calc_popul(self, t=298.15):
        for e in ('ent', 'gib', 'scf'):
            self['{}d'.format(e)], self['{}p'.format(e)] = \
                self._boltzmann_dist(self[e], t)
                
    def _boltzmann_dist(self, energies, t):
        delta = (energies - energies.min()) * 627.5095
        x = np.exp(-delta/(t*self.Boltzmann))
        popul = x/x.sum()
        return delta, popul
        
    def find_imag(self):
        self['imag'] = self['freq'] < 0
        return self['imag'].sum(0)
        
    def average_spectra(self, spectra_type, popul_type):
        spectra, popul = self[spectra_type], self[popul_type]
        av = (spectra[0,1,:] * popul[:, np.newaxis]).sum(0)
        av_spec = np.array([spectra[0][0], av])
        self['av_{}'.format(spectra_type)] = av_spec
        return av_spec
        #av_spec = sum(s * p for s, p in zip(spectra[1], populations))
    
    def get_spectra(self, type, start, stop, step, hwhm, fitting):
        """
        Parameters
        ----------
        type: str
            Name of spectrum, which is to be calculated. Valid names are:
            vcd, ir, raman, roa, ecd, uv.
        start: int or float
            Number representing start of spectral range in relevant units.
        stop: int or float
            Number representing end of spectral range in relevant units.
        step: int or float
            Number representing step of spectral range in relevant units.
        hwhm: int or float
            Number representing half width of maximum peak hight.
        fitting: str
            String representing desired spectrum fitting. Valid values are
            gaussian and lorentzian.
        """
        base = np.arange(start, stop, step)
            #spectrum base, 1d numpy.array of wavelengths/wave numbers
        if fitting.lower() == 'gaussian':
            fitting = self._gaussian
        elif fitting.lower() == 'lorentzian':
            fitting = self._lorentzian
        else:
            raise NameError("Unknown fitting name: '{}'".format(fitting))
        bars, freqs, factor = self._spectr_type_ref[type]
        factor = factor(base) if callable(factor) else factor
        self[type] = np.zeros(base.shape)
        for bar, freq in zip(bars, freqs):
            spectrum = self.calculate_spectrum(bar, freq, base, hwhm, factor,
                                               fitting)
            self[type][num] = np.array([base, spectrum])
        return self[type]
        
    def calculate_spectrum(self, bar, freq, base, hwhm, factor, fitting):
        """
        Parameters
        ----------
        bars: numpy.array
            Appropiate values extracted from gaussian output files.
        freqs: numpy.array
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
        """
        spectrum = factor * fitting(bar, freq, base, hwhm)
        return spectrum
        
    def _gaussian(self, bar, freq, base, hwhm):
        sigm = hwhm / math.sqrt(2 * math.log(2))
        it = np.nditer([base, None], flags = ['buffered'],
                        op_flags = [['readonly'],
                            ['writeonly', 'allocate', 'no_broadcast']],
                        op_dtypes=[np.float64,np.float64]
                        )
        for lam, peaks in it:
            e = bar * exp(-0.5 * (lam - freq) ** 2 / sigm ** 2)
            peaks[...] = e.sum() / (sigm * (2 * math.pi)**0.5)
        return it.operands[1]
        
    def _lorentzian(self, bar, freq, base, hwhm):
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
    def _spectr_type_ref(self):
        def uv_factor(freqs):
            return freqs * 3.07441575e-12 
        r = dict(
            #type = (bars, freqs, factor)
            vcd = (self['rot'], self['freq'], 1.38607595e38),
            ir = (self['dip'], self['freq'], 3.46518986e37),
            raman = (self['raman1'], self['freq'], 0),
            roa = (self['roa1'], self['freq'], 0),
            ecd = (self['rot'], self['freq'], 3.07441575e+6),
            uv = (self['dip'], self['freq'], uv_factor)
                )
        return r
        
    def show_spectrum(self, spectrum):
        plt.plot(*spectrum)
        plt.show()

        
class Settings:

    def __init__(self):
    
        self._output_dir = ''
        self._work_dir = ''
        
        self.spectra_type = '' #'vibra', 'electr' or 'none'
        self.parameters = {}
        self.standard_parameters = {
            'vibra': {'HWHM': 6,
                      'START': 800,
                      'STOP': 2100,
                      'STEP': 2,
                      'FITTING': 'LORENTZIAN'},
            'electr': {'HWHM': 6,
                       'START': 800,
                       'STOP': 2100,
                       'STEP': 2,
                       'FITTING': 'GAUSSIAN'}
            }
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

    def set_standard_parameters(self, spectra_type=None):
        spectra_type = self.spectra_type if not spectra_type else spectra_type
        self.parameters = self.standard_parameters[spectra_type]
    
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
    
    def _ch_dir(self, dest, path):
        if not path:
            window = win32gui.GetForegroundWindow()
            Tk().withdraw()
            path = askdirectory()
            win32gui.SetForegroundWindow(window)
        if not path:
            print("Directory not choosen.")
        else:
            os.chdir(path)
            dest = path
            
    def change_dir(self, path=None):
        self._ch_dir(self.work_dir, path)
        self._ch_dir(self.output_dir, path)
        return self.work_dir
        
    def change_work_dir(self, path=None):
        self._ch_dir(self._work_dir, path)
        return self.work_dir
        
    def change_output_dir(self, path=None):
        self._ch_dir(self._output_dir, path)
        return self.output_dir
        
    def set_type(self, spectra_type):
        if spectra_type not in ('vibra', 'electr', 'none'):
            raise ValueError("Settings.spectra_type \
                cannot be set to {}.".format(spectra_type))
        else:
            self.spectra_type = spectra_type
            return self.spectra_type