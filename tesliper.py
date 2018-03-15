import csv
import math
import os, sys, re
import numpy as np
from collections.abc import Mapping, MutableMapping
from collections import Counter, defaultdict
from copy import copy
from itertools import chain, cycle
from tkinter import Tk
from tkinter.filedialog import askdirectory, askopenfilename
import matplotlib.pyplot as plt
import descriptors as dscr
import logging as lgg


__author__ = "Michał M. Więcław"
__version__ = "0.5.3"


##################
###   ERRORS   ###
##################

class PatternNotFound(Exception): pass


##################
###   LOGGER   ###
##################

logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)

mainhandler = lgg.StreamHandler()
mainhandler.setLevel(lgg.DEBUG)

logger.addHandler(mainhandler)


############################
###   MODULE FUNCTIONS   ###
############################

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

        
###################
###   CLASSES   ###
###################

class Extractor(Mapping):
    """A tool for data extraction from gaussian output file.
    
    This object is a dict-like container with set of compiled regular
    expresion objects and set of methods which can be used to extract data
    from gaussian output files. Extracting methods can be acessed by getting
    value bound to keyword. Typical use:
    
    >>> e = Extractor()
    >>> extracted = e['keyword']('text to extract from')
    
    or, if spectra-type dependent data is to be extracted:
    
    >>> extracted = e['spectra_type']['keyword']('text to extract from')
    
    Extracted is then a list of strings or list of lists, depending on keyword.
    
    Notes
    -----
    Re objects can be get as dictionary under 'regexs' attribute if needed.
    
    Attributes
    ----------
    regexs: dict
        Dictionary of compiled regular expresion objects.
    
    TO DO
    -----
    ? Unify inner dict to only work as in example. ?
    Add handling of AttributeError when match not found (group() method
    called on None).
    """
    
    def __init__(self):
        self.regexs = self._get_regexs()
        self._storage = {'command': self._get_command,
                         'stoich': self._get_stoich,
                         'energies': self._get_energies,
                         'popul': self._get_popul,
                         'settings': self._get_settings
                        }
        self._storage.update(self._get_vibra_dict())
        self._storage.update(self._get_electr_dict())

    def __getitem__(self, key):
        return self._storage[key]
    
    def __iter__(self):
        return iter(self._storage)
    
    def __len__(self):
        return len(self._storage)
    
    def _get_regexs(self):
    
        def electr_dict(pat1, pat2):
            if not pat2:
                return re.compile(r'(\d*\.\d+) {}'.format(pat1)), ''
            else:
                temp = re.compile(r'{}.*?\n((?:\s*-?\d+\.?\d*\s*)*)'\
                                  .format(pat1))
                return temp, re.compile(r'(-?\d+\.?\d*){}'.format(pat2))

        r = {}
        d = {'efreq': ('nm',''),
             'ex_en': ('eV', ''),
             'vosc': ('velocity dipole.*:\n', '\n'),
             'vrot': (r'R\(velocity\)', r'\s*\d+\.?\d*\n'),
             'losc': ('electric dipole.*:\n', '\n'),
             'lrot': (r'R\(length\)', '\n'),
             'eemang': (r'E-M Angle', '\n')}
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
        keys = 'vfreq dip rot iri vemang raman1 roa1'.split(' ')
        pats = 'Frequencies', 'Dip. str.', 'Rot. str.', 'IR Inten',\
               'E-M angle', 'Raman1\s*Fr=\s*\d', 'ROA1\s*Fr=\s*\d'
        r['vibra'] = {key: re.compile(r'{}\s*--\s+(.*)\n'.format(patt))
                      for key, patt in zip(keys, pats)}
        r['popul'] = re.compile(r'(-?\w.*?)\s')
        r['settings'] = re.compile(r'(-?\d+.?d\*|lorentzian|gaussian)')
        return r
    
    def _get_command(self, text):
        try:
            return self.regexs['command'].search(text).group(1)
        except AttributeError:
            raise PatternNotFound("Could not extract command.")
            
    def _get_stoich(self, text):
        return self.regexs['stoich'].search(text).group(1)
    
    def _get_energies(self, text):
        ens = self.regexs['ens'].search(text).groups()
        scf = self.regexs['scf'].findall(text)[-1]
        return (*ens, scf)
        
    def _get_vibra_dict(self):
        def wrapper(patt):
            def inner(text):
                match = patt.findall(text)
                to_return = [s for g in match for s in g.split(' ') if s]
                if not to_return: raise PatternNotFound
                return to_return
            return inner
        return {key:wrapper(patt)
                for key, patt in self.regexs['vibra'].items()}
        
    def _get_electr_dict(self):
        def wrapper(pat1, pat2=None):
            def inner(text):
                if not pat2:
                    match = pat1.findall(text)
                    if not match: raise PatternNotFound
                    return match
                else:
                    try:
                        temp = pat1.search(text).group(1)
                    except AttributeError:
                        raise PatternNotFound
                    return pat2.findall(temp)
            return inner
        return {k:wrapper(*v) for k,v in self.regexs['electr'].items()}
        
    def _get_popul(self, text):
        return self.regexs['popul'].findall(text)
        
    def _get_settings(self, text):
        #TO DO: make it discriminate by keyword, not position
        sett = self.regexs['settings'].findall(text.lower()).groups()
        sett = {k: v for k, v in zip(('hwhm start stop step fitting'\
                                      .split(' '), sett))}
        return sett
        
class Soxhlet:
    """A tool for data extraction from files in specific directory. Typical
    use:
    
    >>> s = Soxhlet('absolute path to working dir')
    >>> data = s.extract('key', 'words', 'specifying', 'query')
    
    Attributes
    ----------
    path: str
        Path of directory bounded to Soxhlet instance.
    files: list
        List of files present in directory bounded to Soxhlet instance.
    extractor: Extractor object
        Extractor class instance used to extract data from files.
    command: str or None
        Initial command line extracted from first gaussian output file.
    spectra_type: str or None
        Type of spectra calculated. 'vibra' for vibrational spectra, 'electr'
        for electric spectra or None if only optimization was calculated.
    gaussian_files
    bar_files
    
    TO DO
    -----
    ? After Unifying Extractor class, do same with this class. ?
    """
    
    def __init__(self, path, wanted_files=None):
        """Initialization of Soxhlet object.
        
        Parameters
        ----------
        path : str
            String representing absolute path to directory containing files, which
            will be the subject of data extraction.
        files : list, optional
            List of files, that should be loaded for further extraction. If
            omitted, all files present in directory will be taken.
            
        Raises
        ------
        FileNotFoundError
            If path passed as argument to constructor doesn't exist.
        """
        if not os.path.isdir(path):
            raise FileNotFoundError("Path not found: {}".format(path))
        self.path = path
        self.files = os.listdir(path)
        self.wanted_files = wanted_files
        self.extractor = Extractor()
        self.command = self._get_command()
        self.spectra_type = self._get_spectra_type()

    @property
    def wanted_files(self):
        return self._wanted_files
        
    @wanted_files.setter
    def wanted_files(self, files):
        if files:
            wanted_files = tuple(map(
                lambda f: '.'.join(f.split('.')[:-1]) if '.' in f else f, files
                ))
        else:
            wanted_files = tuple()
        self._wanted_files = wanted_files
        return wanted_files
        
    @property
    def gaussian_files(self):
        """List of (sorted by file name) gaussian output files from files
        list associated with Soxhlet instance.
        """
        try:
            ext = self.log_or_out()
            gf = sorted(self.filter_files(ext))
        except ValueError:
            gf = None
        return gf
    
    @property
    def bar_files(self):
        """List of (sorted by file name) *.bar files from files list
        associated with Soxhlet instance.
        """
        try:
            ext = '.bar'
            bar = sorted(self.filter_files(ext))
        except ValueError:
            bar = None
        return bar
        
    def filter_files(self, ext):
        """Filters files from file names list.
        
        Function filters file names in list associated with Soxhlet object
        instance. It returns list of file names ending with provided ext
        string, representing file extension and starting with any of filenames
        associated with instance as wanted_files if those were provided.
        
        Parameters
        ----------
        ext : str
            List of strings containing keywords for extraction.
                
        Returns
        -------
        list
            List of filtered filenames as strings.
        """
        files = self.files
        wanted_files = self.wanted_files if self.wanted_files else ''
        filtered = [
            f for f in files if f.endswith(ext) and f.startswith(wanted_files)
            ]
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
        
    def _get_command(self):
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
        try:
            command = self.extractor['command'](cont).lower()
        except PatternNotFound:
            logger.critical("Gaussian command line could not be found in " \
                            "file {}. Please check if file is not corrupted." \
                            .format(self.gaussian_files[0]), exc_info=True)
            raise
        return command
 
    def _get_spectra_type(self):
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

    def parse_request(self, request):
        """Converts request to template dictionary used to place data during 
        extraction.
        
        Notes
        -----
        If any keyword passed will not be recognized, request will be reduced
        to contain known keywords only.
            
        Parameters
        ----------
        request: iterable
            List of keywords for extraction.
            
        Returns
        -------
        dict
            Template dictionary used to place extracted data.
            
        Raises
        ------
        ValueError
            If no recognized keywords was passed or request was empty.
        """
        request = map(str.lower, request)
        #convert spectra names to corresponding bar names
        request = [
            Tesliper.default_spectra_bars[kword] \
            if kword in Tesliper.default_spectra_bars
            else kword for kword in request
            ]
        query = set(request)
        emang = 'emang' in query
        if emang: query.remove('emang')
        unknown = [kword for kword in query if kword not in self.extractor]
        if unknown:
            unknown = set(unknown)
            msg = 'Unknown keywords in request: {}. Request will be reduced '\
                  'to known keywords.'.format(unknown)
            logger.warning(msg)
            query = query - unknown
        got_vibra = any(
            k in query for k in 'iri dip rot raman1 roa1 vemang'.split(' '))
        got_electr = any(
            k in query for k in 'vrot vosc lrot losc eemang'.split(' '))
        if got_vibra:
            query.add('vfreq')
            if emang: query.add('vemang')
        if got_electr:
            query.add('efreq')
            query.add('ex_en')
            if emang: query.add('eemang')
        if not query and not emang:
            logger.warning('No known keywords in request. '
                           'Extraction will not run.')
            raise ValueError('No known keywords in request or empty request.')
        elif not query and emang:
            query.add('eemang' if self.spectra_type == 'electr' else 'vemang')
            query.add('efreq' if self.spectra_type == 'electr' else 'vfreq')
        query.add('stoich')
        return query
            
    def extract(self, request):
        """From gaussian files associated with object extracts values related
        to keywords provided in arguments.
        
        Notes
        -----
        Uses Soxhlet.parse_request for determining keywords understandable
        by Extractor class.
        
        Parameters
        ----------
        request : list
            List of strings - keywords for extracting.
                
        Returns
        -------
        dict
            Dictionary with extracted data.
        """
        #logger.warning('Will be extracting, bruh!')
        query = self.parse_request(request)
        if not query: return {} 
        no = len(self.gaussian_files)
        extracted = defaultdict(lambda: [None] * no)
        extracted['filenames'] = self.gaussian_files
        energies_keys = 'zpec tenc entc gibc zpe ten ent gib scf'.split(' ')
        things_omitted = []
        for num, file in enumerate(self.gaussian_files):
            with open(os.path.join(self.path, file)) as handle:
                cont = handle.read()
            for thing in query:
                if thing in things_omitted: continue
                try:
                    if thing == 'energies':
                        energies = self.extractor[thing](cont)
                        for k, e in zip(energies_keys, energies):
                            extracted[k][num] = e
                    else:
                        
                        extracted[thing][num] = self.extractor[thing](cont)
                except PatternNotFound:
                    logger.warning("Could not extract: {}. This data won't be"\
                    " available. Problem occurred while processing file '{}'."\
                    " Please make sure file is not corrupted and contains " \
                    "desired informations.".format(Bars.full_name_ref[thing], 
                                                   file))
                    things_omitted.append(thing)
        return self.from_dict(**extracted)
        
    def load_bars(self, spectra_type=None):
        """Parses *.bar files associated with object and loads spectral data
        previously extracted from gaussian output files.
        
        Parameters
        ----------
        spectra_type : str, optional
            Type of spectra which is to extract; valid values are
            'vibra', 'electr' or '' (if spectrum is not present
            in gaussian output files); if omitted, spectra_type
            associated with object is used.
                
        Returns
        -------
        dict
            Dictionary with extracted spectral data.
            
        TO DO
        -----
        Make sure Transitions not needed.
        Rewrite to match current keys handling
        """
        spectra_type = spectra_type if spectra_type else self.spectra_type
        no = len(self.bar_files)
        #Create empty dict with list of empty lists as default value.
        output = defaultdict(lambda: [[] for _ in range(no)])
        keys = 'vfreq dip rot vemang'.split(' ') if spectra_type == 'vibra' else \
               'efreq vosc srot losc lrot energy eemang'.split(' ')
        for num, bar in enumerate(self.bar_files):
            with open(os.path.join(self.path, bar), newline='') as handle:
                header = handle.readline()
                col_names = handle.readline()
                if 'Transition' in col_names and 'eemang' in keys:
                    keys = keys[:-1]
                reader = csv.reader(handle, delimiter='\t')
                for row in reader:
                    #For each row in *.bar file copy value to corresponding
                    #position in prepared output dict
                    for k, v in zip(keys, row):
                        #output[value type][file position in sorted list]
                        output[k][num].append(float(v))
        return self.from_dict(output)
        
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
        return self.from_dict(output)
        
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
        prsr = {'opt': 'energies iri',
                'freq=': 'vfreq iri',
                'freq=vcd': 'dip rot vemang',
                'freq=roa': 'raman1 roa1',
                'td=': 'efreq ex_en vosc vrot lrot losc eemang'
                }
        args = set(
            arg for k, v in prsr.items() for arg in v.split(' ') if k in cmd)
        return args

    def from_dict(self, **data):
        """Creates dictionary of Data objects from dictionary containing
        appropriate key-word as keys and lists of extracted data as values.
        
        Parameters
        ----------
        data: dict
            Dictionary containing lists or numpy.ndarrays of data.
            
        Returns
        -------
        dict
            Dictionary with Data objects created from input data.
            
        Raises
        ------
        ValueError
            If any of input dictionary keys is not recognized.
        
        TO DO
        -----
        handling spectra
        """
        output = {}
        filenames = data.pop('filenames')
        stoich = data.pop('stoich')
        done = []
        for key, value in data.items():
            if key in 'zpec tenc entc gibc scfc ex_en vfreq efreq'.split(' '):
                continue
            if key in 'zpe ten ent gib scf'.split(' '):
                corr = None if not '{}c'.format(key) in data else \
                    data['{}c'.format(key)]
                new = Energies(
                    type = key, filenames = filenames, stoich = stoich,
                    values = value, corrections = corr)
            elif key in 'dip rot iri raman1 roa1 vemang'.split(' '):
                new = Bars(
                    type = key, filenames = filenames, stoich = stoich,
                    frequencies = data['vfreq'], values = value)
            elif key in 'vosc vrot losc lrot eemang'.split(' '):
                new = Bars(
                    type = key, filenames = filenames, stoich = stoich,
                    frequencies = data['efreq'], values = value,
                    excitation_energies = data['ex_en'])
            elif key in 'uv ir ecd vcd roa raman'.split(' '):
                output[key] = Spectra(
                    name = key, filenames = filenames, stoich = stoich,
                    base = base, values = value, hwhm = hwhm,
                    fitting = fitting)
            else:
                err_msg = "Unknown keyword: {}".format(key)
                #TO DO: supplement this log
                logger.error(err_msg)
                continue
            output[key] = new
            done.append(Bars.full_name_ref[key])
        if done:
            logger.info('Successfully extracted: {}.'.format(', '.join(done)))
        else:
            logger.warning('Nothing extracted.')
        return output
    
    
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
        vrot = 'Rot. (vibrational)',
        lrot = 'Rot. (lenght)',
        vosc = 'Osc. (vibrational)',
        losc = 'Osc. (length)',
        iri = 'IR Intensity',
        vemang = 'E-M Angle',
        eemang = 'E-M Angle',
        zpe = 'Zero-point Energy',
        ten = 'Thermal Energy',
        ent = 'Thermal Enthalpy',
        gib = 'Thermal Free Energy',
        scf = 'SCF',
        ex_en = 'Excitation energy'
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

    @property
    def trimmed(self):
        temp = copy(self)
        temp.trimming = True
        return temp
        
    @property
    def full(self):
        temp = copy(self)
        temp.trimming = False
        return temp

    def trimm_by_stoich(self, stoich=None):
        if stoich:
            wanted = stoich
        else:
            counter = Counter(self.stoich)
            wanted = counter.most_common(1)[0][0]
        blade = self._full_stoich == wanted
        self.trimmer.update(blade)
        self.trimming = True
        return self
    
                    
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
        except ValueError:
            return np.array([])
        
    @property
    def populations(self):
        x = np.exp(-self.deltas / (self.t * self.Boltzmann))
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
        if self.values is None:
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
        imag = self.imag.sum(0)
        indices = np.nonzero(imag)
        pairs = np.array([self.filenames, imag]).T
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
        return output
        
        
class Spectra:
    
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
        self.name = name
        self.type = Bars.spectra_type_ref[self.name]
        self.filenames = filenames
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
        self.populations = populations = energies.populations
        self.energy_type = energies.type
        #populations must be of same shape as spectra
        #so we expand populations with np.newaxis
        av = (self.values * populations[:, np.newaxis]).sum(0)
        self.averaged = av
        av_spec = np.array([self.base, av])
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
    
    @property
    def exported_filenames(self):
        make_new_names = lambda fnm: \
            '{}.{}.txt'.format('.'.join(fnm.split('.')[:-1]), self.name)
        names = map(make_new_names, self.filenames)
        return names
    
    @property
    def averaged_filename(self):
        return 'avg_{}_{}'.format(self.name, self.energy_type)
    
    def export_txts(self, path=''):
        for fname, spc in zip(self.exported_filenames, self.values):
            with open(os.path.join(path, fname), 'w') as file:
                file.write(self.text_header + '\n')
                file.write(
                    '\n'.join(
                    '{:>4d}\t{: .2f}'.format(int(b), s) \
                    for b, s in zip(self.base, spc))
                )
    
    
class DataHolder(MutableMapping):
    """Convenience dict-like holder for data objects. It enables accessing its
    values through standard dictionary syntax (holder['key']), as well as
    through attribute syntax (holder.key).
    """

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
    
    @property
    def spectral(self):
        return {k: v for k, v in self.items() if k in \
                'dip rot vosc vrot losc lrot raman1 roa1'.split(' ')}

            
class Tesliper:
    """
    TO DO
    -----
    Finish saving functionality.
    Add trimming support.
    Supplement docstrings.
    ? separate spectra types ?
    """
    
    standard_parameters = {
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
    units = Spectra.units
    default_spectra_bars = {
        'ir': 'dip',
        'vcd': 'rot',
        'uv': 'vosc',
        'ecd': 'vrot',
        'raman': 'raman1',
        'roa': 'roa1'
        }

    def __init__(self, input_dir=None, output_dir=None):
        if input_dir or output_dir:
            self.change_dir(input_dir, output_dir)
        if input_dir:
            self.soxhlet = Soxhlet(self.input_dir)
        self.energies = DataHolder()
        self.bars = DataHolder()
        self.spectra = DataHolder()
        self.set_standard_parameters()
        
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
        if not input_dir and not output_dir:
            raise TypeError("Tesliper.change_dir() requires at least one "
                            "argument: input_dir or output_dir.")
        input_dir, output_dir = map(
            lambda s: os.path.normpath(s) if s else None,
            (input_dir, output_dir)
            )
        print(input_dir)
        for dir in input_dir, output_dir:
            if dir and not os.path.isdir(dir):
                raise FileNotFoundError(
                    "Invalid path or directory not found: {}"\
                    .format(dir)
                    )
        if input_dir:
            self.input_dir = input_dir
            self.soxhlet = Soxhlet(input_dir)
            logger.info('Current working directory is: {}'.format(input_dir))
        if output_dir:
            self.output_dir = output_dir
            logger.info('Current output directory is: {}'.format(output_dir))
        elif input_dir and not hasattr(self, 'output_dir'):
            output_dir = os.path.join(input_dir, 'tesliper_output')
            os.makedirs(output_dir, exist_ok=True)
            self.output_dir = output_dir
            logger.info('Current output directory is: {}'.format(output_dir))
        else:
            return

        
    def load_files(self, path=None):
        if path:
            self.soxhlet = Soxhlet(path)
            self.change_dir(path)
        else:
            self.soxhlet = Soxhlet(self.input_dir)
        return self.soxhlet
        
    def extract(self, *args, path=None):
        soxhlet = Soxhlet(path) if path else self.soxhlet
        data = soxhlet.extract(args)
        self.update(data)
        return data
    
    def smart_extract(self, deep_search=True, with_load=True):
        #TO DO: add deep search and loading
        soxhlet = self.soxhlet
        args = soxhlet.parse_command()
        return self.extract(*args)
        pass
        
    def smart_calculate(self, average=True):
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
            soxhlet.spectra_type
        settings = soxhlet.load_settings()
        self.settings[spectra_type].update(settings)
        return self.settings
        
    def calculate_single_spectrum(self, spectra_name, conformer, start=None,
                                  stop=None, step=None, hwhm=None,
                                  fitting=None):
        bar = self.bars[self.default_spectra_bars[spectra_name]].full
        blade = [False if fname != conformer else True
                 for fname in bar.filenames]
        bar.trimmer.set(blade)
        bar.trimming = True
        sett_from_args = {
            k: v for k, v in zip(('start', 'stop', 'step', 'hwhm', 'fitting'),
                                 (start, stop, step, hwhm, fitting))
            if v is not None
            }
        sett = self.parameters[bar.spectra_type].copy()
        sett.update(sett_from_args)
        spc = bar.calculate_spectra(**sett)
        return spc
        
    def calculate_spectra(self, *args, start=None, stop=None,
                          step=None, hwhm=None, fitting=None):
        if not args:
            bars = self.bars.spectral.values()
        else:
            #convert to spectra name if bar name passed
            bar_names = self.default_spectra_bars
            query = [bar_names[v] if v in bar_names else v for v in args]
            query = set(query) #ensure no duplicates
            bar_names, bars = zip(
                *[(k, v) for k, v in self.bars.spectral.items() if k in query])
            unknown = query - set(self.bars.spectral.keys())
            if unknown:
                info = "No other requests provided." if not bar_names else \
                       "Will proceed using only those bars: {}".format(bar_names)
                msg = "Don't have those bar types: {}. {}".format(unknown, info)
                logger.warning(msg)
        sett_from_args = {
            k: v for k, v in zip(('start', 'stop', 'step', 'hwhm', 'fitting'),
                                 (start, stop, step, hwhm, fitting))
            if v is not None
            }
        output = {}
        for bar in bars:
            sett = self.parameters[bar.spectra_type].copy()
            sett.update(sett_from_args)
            spc = bar.calculate_spectra(**sett)
            self.spectra[bar.spectra_name] = spc
            output[bar.spectra_name] = spc
        return output
        
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

    def __unify_data(self, data, dummy, overriding):
        for dat in data.values():
            try:
                dummy.trimmer.unify(dat, overriding = overriding)
            except Exception:
                logger.warning(
                    'A problem occured during data unification. '\
                    'Make sure your file sets have any common filenames.',
                    exc_info=True)
                raise
        fnames = [dat.filenames for dat in data.values()]
        #for fnm in fnames: print(fnm)
        if not all(x.shape == y.shape and (x == y).all() for x, y \
                   in zip(fnames[:-1], fnames[1:])):
            #raise
            self.__unify_data(data, dummy, overriding)

    def unify_data(self, stencil=None):
        data = dict((k, v) for k, v in 
                    chain(self.bars.items(), self.energies.items()))
        if not stencil:
            dat = next(iter(data.values()))
            dummy = Data(type='dummy', filenames = dat.full.filenames)
        else:
            dummy = Data(type='dummy', filenames = stencil.full.filenames)
            dummy.trimmer.set(stencil.trimmer.blade)
        self.__unify_data(data, dummy,
            overriding = False if stencil is None else True)
