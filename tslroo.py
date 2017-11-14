import os, sys, re
import math
import numpy as np
from time import clock
from datetime import datetime
from collections.abc import Mapping, MutableMapping
import win32gui

__author__ = "Michał Więcław"
__version__ = "0.3.0"


class Extractor(Mapping):
    
    def __init__(self):
        
        self.regexs = self.get_regexs()
        self._storage = {'command': self.get_command,
                         'stoich': self.get_stoich,
                         'energies': self.get_energies,
                         'vibra': self.get_vibra_dict(),
                         'eletcr': self.get_electr_dict()
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
                temp = re.compile(r'{}.*:\n.*\n((?:\s*-?\d+\.?\d*)*)'.format(pat1))
                return temp, re.compile(r'(-?\d+\.?\d*){}'.format(pat2))

        r = {}
        
        d = {'freq': ('nm',''),
             'energy': ('eV', ''),
             'vosc': ('velocity dipole', '\n'),
             'vrot': (r'R(velocity)', r'\s*\d+\.?\d*\n'),
             'lrot': ('electric dipole', '\n'),
             'losc': (r'R(length)', '\n')}
        r['electr'] = {k:electr_dict(*v) for k,v in d.items()}
        
        r['command'] = re.compile(r'\#(.*)\n')
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
        pats = 'Frequencies', 'Dip. str.', 'Rot. str.', 'IR Inten', 'E-M angle', 'Raman1', 'ROA1'
        r['vibra'] = {key: re.compile(r'{}\s*--\s+(.*)\n'.format(patt))
                      for key, patt in zip(keys, pats)}
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
            
        return {key:wrapper(patt) for key, patt in self.regexs['vibra'].items()}
        
        
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
        
        
class Soxhlet:
    
    def __init__(self):
        self.extractor = Extractor()
        self.settings = Settings()

    
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
            
            
    def get_type(self):
        f = self.filtered[0]
        with open(f) as f:
            f = f.read()
        command = self.extractor['command'](f).lower()
        if 'freq' in command:
            return 'vibra'
        elif 'nd=' in command:
            return 'electr'
        else:
            return 'none'
    
    
    def load_files(self, path=None):
        path = path if path else self.settings.work_dir
        self.files = os.listdir(path)
        
        
    def filter_files(self, ext, files=None):
        """Filters files from file names list.
        
        Positional parameter:
        files --    list of strings representing file names
        ext --      string representing file extention
        
        Function filters file names in provided list. It returns list of
        file names ending with prowided ext string, representing file
        extention and number of files in created list as tuple.
        """
        files = files if files else self.files
        filtered = [f for f in files if f.endswith(ext)]
        return filtered
         
         
    def log_or_out(self):
        """Checks list of file extentions in list of file names.
        
        Positional parameter:
        files --    list of strings representing file names
        
        Function checks for .log and .out files in passed list of file names.
        If both are present, it raises TypeError exception.
        If either is present, it raises ValueError exception.
        It returns string representing file extention present in files list.
        """
        logs, outs = (any(f.endswith(ext) for f in eslf.files) \
                      for ext in ('.log', '.out'))
        if outs and logs:
            raise TypeError(".log and .out files mixed in directory.")
        elif not outs and not logs:
            raise ValueError("Didn't found any .log or .out files.")
        else:
            return '.log' if logs else '.out'

            
    def get_data(self, to_get, settings=None):
        settings = self.settings if not settings else settings
        try:
            to_get = to_get.split(' ')
        except AttributeError:
            pass
        self.data = Data(settings)
        return self.data
        
        
    def load_bars(self):
        pass
        
        
        
class Data(MutableMapping):

    Boltzmann = 0.0019872041 #kcal/(mol*K)

    def __init__(self):
        energies = 'zpec tenc entc gibc zpe ten ent gib scf'.split(' ')
        vibra = 'freq dip rot ir e-m raman1 roa1'.split(' ')
        electr = 'freq energy vosc vrot lrot losc'.split(' ')
        self._data = dict.fromkeys(*energies, *vibra, *electr)
        
    
    def __getitem__(self, key):
        return self._data[key]
    
    
    def __setitem__(self, key, value):
        self._data[key] = value
    
    
    def __delitem__(self):
        del self._data[key]
    
    
    def __iter__(self):
        return iter(self._data)
    
    
    def __len__(self):
        return len(self._data)
    
    
    def calc_popul(self, t=298.15):
        for e in ('ent', 'gib', 'scf'):
            self._data['{}d'.format(e)], self._data['{}p'.format(e)] = \
                boltzmann_dist(data[e], t)
                
    
    def boltzmann_dist(energies, t):
        delta = (energies - energies.min()) * 627.5095
        x = np.exp(-delta/(t*self.Boltzmann))
        popul = x/x.sum()
        return delta, popul
    
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
            Tk().withdraw()
            path = askdirectory()
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