import os, sys, re
import math
import copy
import numpy as np
import csv
from collections.abc import Mapping, MutableMapping
from collections import Counter, defaultdict
from itertools import chain, cycle
import win32gui
from tkinter import Tk
from tkinter.filedialog import askdirectory, askopenfilename
import matplotlib.pyplot as plt
import descriptors as dscr


__author__ = "Michał Więcław"
__version__ = "0.4.1"


def gaussian(bar, freq, base, hwhm):
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
        e = bar * np.exp(-0.5 * ((lam - freq) / sigm) ** 2)
        peaks[...] = e.sum() / (sigm * (2 * math.pi)**0.5)
    return it.operands[1]
    
    
def lorentzian(bar, freq, base, hwhm):
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
        s = bar /((freq - lam)**2 + hwhm**2)
        s2 = hwhm / math.pi * s.sum()
        val[...] = s2
    return it.operands[1]

    
def from_dict(data):
    output = {}
    filenames = data.pop('filenames')
    stoich = data.pop('stoich')
    for key, value in data.items():
        if key in 'zpe ten ent gib scf'.split(' '):
            corr = None if not '{}c'.format(key) in data else \
                data['{}c'.format(key)]
            output[key] = Energies(type = key, filenames = filenames,
                                   stoich = stoich, values = value,
                                   corrections = corr
                                   )
        elif key in 'freq dip rot vosc vrot losc lrot raman1 roa1 e-m energy'\
                    .split(' '):
            output[key] = Bars(type = key, filenames = filenames,
                               stoich = stoich,
                               frequencies = data['freq'],
                               values = value
                               )
        elif key in 'uv ir ecd vcd roa raman'.split(' '):
            output[key] = Spectra(type = key,
                                  filenames = filenames, stoich = stoich,
                                  base = base, values = value, hwhm = hwhm,
                                  fitting = fitting)
    return output

        
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
        d = {'freq': ('nm',''),
             'energy': ('eV', ''),
             'vosc': ('velocity dipole.*:\n', '\n'),
             'vrot': (r'R\(velocity\)', r'\s*\d+\.?\d*\n'),
             'losc': ('electric dipole.*:\n', '\n'),
             'lrot': (r'R\(length\)', '\n'),
             'e-m': (r'E-M Angle', '\n')}
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
               'E-M angle', 'Raman1\s*Fr=\s*\d', 'ROA1\s*Fr=\s*\d'
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
            None is returned if nor vibrational neither electronic spectra was
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
            List of strings containing keywords for extracting.
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
        extracted = defaultdict(lambda: [None] * no)
        request = set(request)
        request.add('stoich')
        if spectra_type == 'electr':
            request.add('energy')
        extracted['filenames'] = self.gaussian_files
        for num, file in enumerate(self.gaussian_files):
            with open(os.path.join(self.path, file)) as handle:
                cont = handle.read()
            for thing in request:
                if thing == 'energies':
                    energies = self.extractor[thing](cont)
                    for k, e in zip(energies_keywords, energies):
                        extracted[k][num] = e
                elif thing == 'stoich':
                    extracted[thing][num] = self.extractor[thing](cont)
                elif spectra_type:
                    extracted[thing][num] = \
                        self.extractor[spectra_type][thing](cont)
        return from_dict(extracted)
        
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
        return from_dict(output)
        
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
        return from_dict(output)
        
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
        
    def load_spectra(self):
        #TO DO: do it
        pass
        
    def parse_command(self):
        """Parses gaussian command extracted from first output file
        in associated files list.
        
        Returns
        -------
        list
            List of key-words needed for data extraction.
        """
        cmd = self.command.lower()
        prsr = {'opt': 'energies',
                'freq=': 'freq',
                'freq=vcd': 'dip rot ir e-m',
                'freq=roa': 'raman1 roa1',
                'td=': 'freq energy vosc vrot lrot losc e-m'
                }
        args = ' '.join(v for k, v in prsr if k in cmd).split(' ')
        return args

class Trimmer:
    
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
        self.blade = np.logical_and(self.blade, other_blade)
        
    def match(self, other, preserve_blade=True):
        curr_trimm = self.owner.trimming
        if not preserve_blade:
            self.owner.trimming = False
        if other.filenames.size > self.owner.filenames.size:
            raise ValueError("{} can't match bigger object: {}."\
                .format(self.owner, other))
        func = self.update if preserve_blade else self.set
        blade = np.isin(self.owner.filenames, other.filenames)
        if np.isin(other.filenames, self.owner.filenames).all():
            func(blade)
            self.owner.trimming = True
        else:
            self.owner.trimming = curr_trimm
            raise ValueError("Can't match objects: {0} and {1}. {1} has "
                             "entries absent in {0}.".format(self.owner,
                                                             other)
                            )
    
    def unify(self, other, preserve_blade=True):
        if not preserve_blade: self.owner.trimming = other.trimming = False
        if not np.intersect1d(other.filenames, self.owner.filenames).size:
            raise ValueError("Can't unify objects without common entries.")
        func = self.update if preserve_blade else self.set
        blade = np.isin(other.filenames, self.owner.filenames)
        func(blade)
        self.owner.trimming = True
        other.trimmer.match(self, preserve_blade)
        
    def reset(self):
        self.blade = np.ones(self.owner.true_size, dtype=bool)
        
class Data:
    """Mix-in class used to force conversion of list to numpy.ndarray during
    attribute setting.
    
    TO DO
    -----
    Check calculations of ecd spectrum, on HWHM = 0.35 peaks should be much
    broader (close to as on HWHM = 7.0)
    """
    
    #######################
    ###   Descriptors   ###
    #######################
    
    filenames = dscr.StrTypeArray('filenames')
    stoich = dscr.StrTypeArray('stoich')
    values = dscr.FloatTypeArray('values')
    #Bars specific:
    frequencies = dscr.FloatTypeArray('frequencies')
    imag = dscr.IntTypeArray('imag')
    #Energies specific:
    corrections = dscr.FloatTypeArray('corrections')
    #populations = dscr.FloatTypeArray('populations')
    #deltas = dscr.FloatTypeArray('deltas')

    full_name_ref = dict(
        rot = 'vcd',
        dip = 'ir',
        roa1 = 'roa',
        raman1 = 'raman',
        vrot = 'ecd',
        lrot = 'ecd',
        vosc = 'uv',
        losc = 'uv'
        )

    def __init__(self, filenames, stoich=None, values=None):
        self.filenames = filenames
        self.stoich = stoich
        self.values = values
        self.true_size = len(filenames)
        self.trimming = False
        self.trimmer = Trimmer(self)

    @property
    def trimmed(self):
        temp = copy(self)
        temp.trimming = True
        return temp
        
    def trimm_by_stoich(self, stoich=None):
        if stoich:
            wanted = stoich
        else:
            counter = Counter(self.stoich)
            wanted = counter.most_common(1)[0][0]
        blade = self.stoich == wanted
        self.trimmer.update(blade)
        self.trimming = True
        return self
    
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

                    
class Energies(Data):
    """
    Parameters
    ----------
    type: str
        Type of energy.
    filenames: numpy.ndarray(dtype=str)
        List of filenames of gaussian output files, from whitch data were
        extracted.
    stoich: numpy.ndarray(dtype=str)
        Stoichiometry of each conformer.
    energies: numpy.ndarray(dtype=float)
        Energy value for each conformer.
    corrections: numpy.ndarray(dtype=float)
        Energy correction value for each conformer.
    populations: numpy.ndarray(dtype=float)
        Population value for each conformer.
    deltas: numpy.ndarray(dtype=float)
        Energy excess value for each conformer.
    t: int or float
        Temperature of calculated state in K.
    """
    
    Boltzmann = 0.0019872041 #kcal/(mol*K)
    
    def __init__(self, type, filenames, stoich, values, corrections=None,
                 populations=None, deltas=None, t=None):
        self.type = type
        super().__init__(filenames, stoich, values)
        if corrections:
            self.corrections = corrections
        if populations:
            self.populations = np.array(populations, dtype=float)
        if deltas:
            self.deltas = np.array(deltas, dtype=float)
        self.t = t if t else 298.15
    
    def calculate_populations(self, t=None):
        """Calculates populations and energy excesses for all tree types of
        energy (ent, gib, scf) in given temperature and bounds outcome to
        Data instance on which method was called.
        
        Parameters
        ----------
        t: int or float
            Temperature of calculated state in K.
        """
        if t is not None:
            self.t = t
        else:
            t = self.t
        self.deltas, self.populations = self._boltzmann_dist(self.values, t)
        return self.populations
                
    def _boltzmann_dist(self, values, t):
        """Calculates populations and energy excesses of conformers, based on
        energy array and temperature passed to function.
        
        Parameters
        ----------
        values: numpy.ndarray
            List of conformers' energies.
        t: int or float
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
    
    spectra_name_ref = dict(
        rot = 'vcd',
        dip = 'ir',
        roa1 = 'roa',
        raman1 = 'raman',
        vrot = 'ecd',
        lrot = 'ecd',
        vosc = 'uv',
        losc = 'uv',
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
                 imag=None, t=None, laser=None):
        self.type = type
        super().__init__(filenames, stoich, values)
        self.frequencies = frequencies
        if self.values is not None:
            self.values = self.frequencies
        if imag:
            self.imag = imag
        else:
            self.imag = self.frequencies < 0
        t = 298.15 if t is None else t #temperature in K
        if self.spectra_name in ('raman', 'roa'): #valid only for raman & roa
            self.laser = laser if laser is not None else 532 #in nm
    
    @property
    def spectra_name(self):
        if self.type in self.spectra_name_ref:
            return self.spectra_name_ref[self.type]
    
    @property
    def spectra_type(self):
        if self.type in self.spectra_name_ref:
            return self.spectra_type_ref[self.spectra_name]
        
    @property
    def _intensity_ref(self):
        def raman(v):
            f = 9.695104081272649e-08
            e = 1 - np.exp(-14387.751601679205 * v / self.t)
            return f * (self.laser - v) ** 4 / (v * e)
        r = dict(
            vcd = lambda v: v * 4.3535e-50,
            ir = lambda v: v * 1.0884e-42,
            raman = raman,
            roa = raman,
            ecd = lambda v: v * 4.3535e-46,
            uv = lambda v: v ** 2 * 23.1504
            )
        return r
            
    @property
    def intensities(self):
        #TO DO: fit to use of trimming
        inten = self._intensity_ref[self.spectra_name]
        self._inten = self.values * inten(self.frequencies)
        return self._inten

    def find_imag(self):
        """Finds all freqs with imaginary values and creates 'imag' entry with
        list of indicants of imaginery values presence.
        
        Returns
        -------
        numpy.ndarray
            List of number of imaginary values in each file.
        """
        output = {}
        imag = self.imag.sum(0)
        indices = np.nonzero(imag)
        pairs = np.array([self.filenames, imag]).T
        return {k: v for k, v in pairs[indices]}
        
    def calculate_spectra(self, start, stop, step, hwhm, fitting,
                          conformers=None):
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
        conformers: ndarray or list
            List used for indexing.
            
        Returns
        -------
        numpy.ndarray
            Array of 2d arrays containing spectrum (arr[0] is list of
            wavelengths/wave numbers, arr[1] is list of corresponding
            intensity values).
        """
        base = np.arange(start, stop+step, step)
            #spectrum base, 1d numpy.array of wavelengths/wave numbers
        if self.type in ('losc', 'rosc', 'lrot', 'vrot'):
            width = hwhm / 1.23984e-4 #from eV to cm-1
            w_nums = 1e7 / base #from nm to cm-1
            freqs = 1e7 / self.frequencies #from nm to cm-1
        else: 
            width = hwhm
            w_nums = base
            freqs = self.frequencies
        freqs = freqs[conformers] if conformers else freqs
        inten = self.intensities[conformers] \
            if conformers else self.intensities
        spectra = np.zeros([len(freqs), base.shape[0]])
        for bar, freq, spr in zip(inten, freqs, spectra):
            spr[...] = fitting(bar, freq, w_nums, width)
        output = Spectra(self.spectra_name, self.filenames, base,
                          spectra, hwhm, fitting)
        return output
        
        
class Spectra(Data):
    
    def __init__(self, type, filenames, base, values, hwhm, fitting):
        self.type = type
        super().__init__(filenames)
        self.base = base
        self.values = values
        self.start = base[0]
        self.stop = base[-1]
        self.step = abs(base[0] - base[1])
        self.hwhm = hwhm
        self.fitting = fitting
        
    def average(self, energies):
        """A method for averaging spectra by population of conformers.
        
        Parameters
        ----------
        energies: Energies object instance
            Object with populations and type attributes containing
            respectively: list of populations values as numpy.ndarray and
            string specifying energy type.
            
        Returns
        -------
        numpy.ndarray
            2d numpy array where arr[0] is list of wavelengths/wave numbers
            and arr[1] is list of corresponding averaged intensity values.
        """
        self.populations = populations = energies.populations
        self.energy_type = energies.type
        #populations must be of same shape as spectra
        #so we expand populations with np.newaxis
        av = (self.values * populations[:, np.newaxis]).sum(0)
        self.averaged = av
        av_spec = np.array([self.base, av])
        return av_spec
    
class DataHolder(MutableMapping):

    def __init__(self):
        self._storage = {}

    def __getitem__(self, key):
        return self._storage[key]
    
    def __setitem__(self, key, value):
        self._storage[key] = value
    
    def __delitem__(self, key):
        del self._storage[key]
    
    def __iter__(self):
        return iter(self._storage)
    
    def __len__(self):
        return len(self._storage)
        
    def __setattr__(self, name, value):
        if name == '_storage':
            return super().__setattr__(name, value)
        elif name in self._storage:
            self[name] = value
        else:
            super().__setattr__(name, value)

    def __getattribute__(self, name):
        if name == '_storage':
            return object.__getattribute__(self, name)
        elif name in self._storage:
            return self[name]
        else:
            return object.__getattribute__(self, name)

            
class Tesliper:
    """
    TO DO
    -----
    separate spectra types
    """
    
    def __init__(self, input_dir=None, output_dir=None):
        if input_dir or output_dir:
            self.change_dir(input_dir, output_dir)
        if input_dir:
            self.soxhlet = Soxhlet(self.input_dir)
        self.energies = DataHolder()
        self.bars = DataHolder()
        self.spectra = DataHolder()
        
        self.standard_parameters = {
            'vibra': {'hwhm': 6,
                      'start': 800,
                      'stop': 2900,
                      'step': 2,
                      'fitting': lorentzian},
            'electr': {'hwhm': 0.35,
                       'start': 150,
                       'stop': 800,
                       'step': 1,
                       'fitting': gaussian}
            }
        self.set_standard_parameters()
        self._units = {
            'vibra': {'hwhm': 'cm-1',
                      'start': 'cm-1',
                      'stop': 'cm-1',
                      'step': 'cm-1'},
            'electr': {'hwhm': 'ev',
                       'start': 'nm',
                       'stop': 'nm',
                       'step': 'nm'}
            }

    def set_standard_parameters(self):
        self.parameters = {
            'vibra': self.standard_parameters['vibra'].copy(),
            'electr': self.standard_parameters['electr'].copy()
            }
        
    def update(self, *args, **kwargs):
        pairs = chain(*(d.items() for d in args), kwargs.items())
        for key, value in pairs:
            if isinstance(value, Energies):
                self.energies[key] = value
            elif isinstance(value, Bars):
                self.bars[key] = value
            elif isinstance(value, Spectra):
                self.spectra[key] = value
            else:
                raise TypeError("Tesliper instance can not be updated with "
                                "type {}".format(type(value)))
                                
    def change_dir(self, input_dir=None, output_dir=None):
        if input_dir:
            if not os.path.isdir(input_dir):
                raise FileNotFoundError(
                    "Invalid path or directory not found: {}"\
                    .format(input_dir)
                    )
            else:
                self.input_dir = input_dir
                self.soxhlet = Soxhlet(input_dir)
        if output_dir:
            self.output_dir = output_dir
        elif input_dir:
            output_dir = os.path.join(input_dir, 'tesliper_output')
            os.makedirs(output_dir, exist_ok=True)
            self.output_dir = output_dir
        else:
            raise TypeError("Tesliper.change_dir() requires at least one "
                            "argument: input_dir or output_dir.")
        
    def load_files(self, path=None):
        if path:
            self.soxhlet = Soxhlet(path)
            self.change_dir(path)
        else:
            self.soxhlet = Soxhlet(self.input_dir)
        return self.soxhlet
        
    def extract(self, *args, spectra_type=None, path=None):
        soxhlet = Soxhlet(path) if path else self.soxhlet
        data = soxhlet.extract(args, spectra_type)
        self.update(data)
        return data
    
    def smart_extract(self, deep_search=True, calculations=True,
                      average=True, save=True, with_load=True):
        #TO DO: do it
        pass
                
    def load_bars(self, path=None, spectra_type=None):
        soxhlet = Soxhlet(path) if path else self.soxhlet
        data = soxhlet.load_bars(spectra_type)
        self.update(data)
        return data
        
    def load_populations(self, path=None):
        soxhlet = Soxhlet(path) if path else self.soxhlet
        data = soxhlet.load_popul()
        self.update(data)
        return self.data
        
    def load_spectra(self, path=None):
        soxhlet = Soxhlet(path) if path else self.soxhlet
        data = soxhlet.load_spectra()
        self.update(data)
        return data
    
    def load_settings(self, path=None, spectra_type=None):
        soxhlet = Soxhlet(path) if path else self.soxhlet
        spectra_type = spectra_type if spectra_type else \
            soxhlet.get_spectra_type()
        settings = soxhlet.load_settings()
        self.settings[spectra_type].update(settings)
        return self.settings

    def calculate_populations(self, *args, t=None):
        query = args if args else self.energies.keys()
        gen = (v for k, v in self.energies.items() if k in query)
        t = [t] if isinstance(t, (int, float, type(None))) else t
        for value, temp in zip(gen, cycle(t)):
            value.calculate_populations(t=temp)
        return {k: v.populations for k, v in self.energies.items() \
                if k in query}
        
    def calculate_spectra(self, *args, sett_from_dict=None, start=None,
                          stop=None, step=None, hwhm=None, fitting=None):
        bar_names = {v: k for k, v in Bars.spectra_name_ref.items() \
            if not k.startswith('l')} #take velo for ecd by default
        query = args if args else self.bars.keys()
        query = [bar_names[v] if v in bar_names else v for v in query]
        query = set(query) #ensure no duplicates
        unknown = query - set(self.bars.keys())
        if unknown: raise ValueError("Don't have those bar types: {}"\
                                     .format(unknown))
        #TO DO: bar.spectra_type sucks :(
        bars = (v for k, v in self.bars.items() if k in query and v.spectra_type is not None)
        sett_from_args = {
            k: v for k, v in zip(('start', 'stop', 'step', 'hwhm', 'fitting'),
                                 (start, stop, step, hwhm, fitting))
            if v is not None
            }
        for bar in bars:
            sett = self.parameters[bar.spectra_type].copy()
            try:
                if sett_from_dict:
                    sett.update(sett_from_dict[bar.type])
            except KeyError:
                sett.update(sett_from_args)
            self.spectra[bar.spectra_name] = bar.calculate_spectra(**sett)
        
    def get_averaged_spectrum(self, spectr, energies):
        output = self.spectra[spectr].average(energies)
        return output
        
    def __save_vibra(self, fnms):
        bars = (bar for bar in self.bars.items() if bar.type in \
                'ir vcd raman1 roa1'.split(' '))
        order = 'freq rot dip raman1 roa1 e-m'.split(' ')
        bars = [b for b in order if b in bars] #ensure wanted order
        header = [bar.full_name for bar in bars]
        values = [bar.value for bar in bars]
        for fnm, bars in zip(fnms, np.array(values).T):
            #transpose array of bar values to iterate over files
            path = os.path.join(output_dir,
                                '{}.v.bar'.format(fnm.split('.')[0]))
            f = open(path, 'r', newline='')
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(header)
            writerows(bars)
            f.close()
            
    def save_output(self, *args, output_dir=None):
        output_dir = output_dir if output_dir else self.output_dir
        pass
        #populations, bars (with e-m), spectra, averaged, settings
        if 'popul' in args:
            for en in self.energies.values():
                if not hasattr(en, 'populations'): continue
                path = os.path.join(output_dir,
                                    'Distribution.{}.txt'.format(en.type))
                f = open(path, 'w', newline='')
                writer = csv.writer(f, delimiter='\t')
                writer.writerow(['Gaussian output file', 'Population', 'DE',
                                 'Energy', 'Imag', 'Stoichiometry'])
                writer.writerows([[f, p, d, e, i, s] for f, p, d, e, i, s in \
                    zip(en.filenames, en.populations, en.deltas, en.values,
                        self.bars.freq.imag.sum(0), en.stoich)])
                f.close()
        if 'bars' in args:
            order = 'freq rot dip raman roa vrot vosc lrot losc energy '\
                    'e-m'.split(' ')
            fnms = set([fnm for bar in self.bars for fnm in bar.filenames])
            fnms = sorted(list(fnms))
            if 'freq' in self.bars:
                pass
                    
        if 'averaged' in args:
            pass
        if 'settings' in args:
            pass
