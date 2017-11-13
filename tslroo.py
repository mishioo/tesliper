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
        
        r['command'] = re.compile(r'\#(.*)\n\-+')
        r['stoich'] = re.compile(r'Stoichiometry\s*(\w*)$')
        
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
    
    def init(self, files):
        self.files = files
        self.extractor = Extractor()
     
     
    def filter_files(self, ext):
        """Filters files from file names list.
        
        Positional parameter:
        files --    list of strings representing file names
        ext --      string representing file extention
        
        Function filters file names in provided list. It returns list of
        file names ending with prowided ext string, representing file
        extention and number of files in created list as tuple.
        """
        filtered = [f for f in self.files if f.endswith(ext)]
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


    def load_bars(self):
        pass
        
class Data(MutableMapping):
    pass
    
class Settings:
    pass
    
        