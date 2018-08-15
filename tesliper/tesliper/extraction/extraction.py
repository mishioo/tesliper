###################
###   IMPORTS   ###
###################

import csv
import os
import logging as lgg
import numpy as np

from collections import defaultdict
from collections.abc import Mapping
from . import gaussian_parser

#################
###   TO DO   ###
#################

# correct load_bars, load_popul, load_spectrs, load_settings, from_dict methods

##################
###   LOGGER   ###
##################

logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


###################
###   CLASSES   ###
###################

class Soxhlet:
    """A tool for data extraction from files in specific directory. Typical
    use:
    
    >>> s = Soxhlet('absolute\path_to\working\dir')
    >>> data = s.extract()
    
    Attributes
    ----------
    path : str
        Path of directory bounded to Soxhlet instance.
    files : list
        List of files present in directory bounded to Soxhlet instance.
    output_files
    bar_files
    
    TO DO
    -----
    correct load_bars, load_popul, load_spectrs, load_settings, from_dict methods
    """

    def __init__(self, path, wanted_files=None, ext=None):
        """Initialization of Soxhlet object.
        
        Parameters
        ----------
        path : str
            String representing absolute path to directory containing files, which
            will be the subject of data extraction.
        wanted_files : list, optional
            List of files, that should be loaded for further extraction. If
            omitted, all files present in directory will be taken.
        ext : str
            String representing file extension of output files, that are to be
            parsed. If omitted, Soxhlet will try to resolve it based on
            contents of directory pointed by path.
            
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
        self.ext = ext if ext is not None else self.log_or_out()
        self.parser = gaussian_parser
        self.data = None

    # @property
    # def wanted_files(self):
    #     return self._wanted_files
    #
    # @wanted_files.setter
    # def wanted_files(self, files):
    #     if files:
    #         wanted_files = tuple(map(
    #             lambda f: '.'.join(f.split('.')[:-1]) if '.' in f else f, files
    #             ))
    #     else:
    #         wanted_files = tuple()
    #     self._wanted_files = wanted_files
    #     return wanted_files

    @property
    def output_files(self):
        """List of (sorted by file name) gaussian output files from files
        list associated with Soxhlet instance.
        """
        try:
            ext = self.ext
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

    def filter_files(self, ext=None):
        """Filters files from filenames list.
        
        Function filters file names in list associated with Soxhlet object
        instance. It returns list of file names ending with provided ext
        string, representing file extension and starting with any of filenames
        associated with instance as wanted_files if those were provided.
        
        Parameters
        ----------
        ext : str
            Strings representing file extension.
                
        Returns
        -------
        list
            List of filtered filenames as strings.
        """
        ext = ext if ext is not None else self.ext
        files = self.wanted_files if self.wanted_files else self.files
        filtered = [f for f in files if f.endswith(ext)]
        return filtered

    def log_or_out(self):
        """Checks list of file extentions in list of file names.
        
        Function checks for .log and .out files in passed list of file names.
        If both are present, it raises TypeError exception.
        If either is present, it raises ValueError exception.
        It returns string representing file extention present in files list.

        Returns
        -------
        str
            '.log' if *.log files are present in filenames list or '.out' if
            *.out files are present in filenames list.
            
        Raises
        ------
        ValueError
            If both *.log and *.out files are present in list of filenames.
        TypeError
            If neither *.log nor *.out files are present in list of filenames.
            
        TO DO
        -----
        correct this to take in consideration wanted_files
        """
        files = self.wanted_files if self.wanted_files else self.files
        logs, outs = (any(f.endswith(ext) for f in files)
                      for ext in ('.log', '.out'))
        if outs and logs:
            raise ValueError(".log and .out files mixed in directory.")
        elif not outs and not logs:
            raise TypeError("Didn't found any .log or .out files.")
        else:
            return '.log' if logs else '.out'

    def extract(self):
        """Extracts data from gaussian files associated with Soxhlet instance.
                
        Returns
        -------
        dict
            Dictionary of dictionaries with extracted data for each file
            associated with Soxhlet instance.
        """
        # logger.warning('Will be extracting, bruh!')
        data = {}
        for num, file in enumerate(self.output_files):
            with open(os.path.join(self.path, file)) as handle:
                cont = handle.read()
            data[file] = self.parser.parse(cont)
        self.data = data
        return data

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
        remove self.spectra_type dependence
        """
        spectra_type = spectra_type if spectra_type else self.spectra_type
        no = len(self.bar_files)
        # Create empty dict with list of empty lists as default value.
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
                    # For each row in *.bar file copy value to corresponding
                    # position in prepared output dict
                    for k, v in zip(keys, row):
                        # output[value type][file position in sorted list]
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
        keys = 'filenames scfp entp gibp scfd entd gibd scf ent gib imag ' \
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
                            v = float(v[:-1]) / 100
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
                raise FileNotFoundError(
                    "No or multiple setup files in directory."
                )
            else:
                f = open(fls[0], "r")
        sett = self.extractor["settings"](f)
        f.close()
        return sett

    def load_spectra(self):
        # TO DO: do it
        pass
