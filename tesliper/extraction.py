###################
###   IMPORTS   ###
###################

import os, re
import logging as lgg
import numpy as np

from collections import defaultdict
from collections.abc import Mapping
from tesliper.datawork import Bars, Energies, Spectra, default_spectra_bars


##################
###   LOGGER   ###
##################

logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


##################
###   ERRORS   ###
##################

class PatternNotFound(Exception): pass


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
    
    instances = {}
    
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
        self._id = len(self.instances)
        self.instances[self._id] = self

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
            default_spectra_bars[kword] \
            if kword in default_spectra_bars
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
            new._soxhlet_id = self._id
            output[key] = new
            done.append(Bars.full_name_ref[key])
        if done:
            logger.info('Successfully extracted: {}.'.format(', '.join(done)))
        else:
            logger.warning('Nothing extracted.')
        return output