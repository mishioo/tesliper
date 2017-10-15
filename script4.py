import os
import re
import numpy as np
from time import clock
import cProfile
import mmap
from contextlib import closing

def get_regexs():
    regexs = dict(
        SCF = b'SCF Done.*',
        corr_zero_point = b'Zero-point correction',
        corr_energy = b'Thermal correction to Energy',
        corr_enthalpy = b'Thermal correction to Enthalpy',
        corr_free_en = b'Thermal correction to Gibbs Free Energy',
        zero_point = b'Sum of electronic and zero-point Energies',
        energy = b'Sum of electronic and thermal Energies',
        enthalpy = b'Sum of electronic and thermal Enthalpies',
        free_en = b'Sum of electronic and thermal Free Energies')  
    return {k:re.compile(v + b'=\s+(-?\d+\.?\d*)')
            for k,v in regexs.items()}

def get_data(path, file, regexs):     
    with open(os.path.join(path, file), 'r') as f:
        data = dict()
        with closing(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as m:
            for key, regex in regexs.items():
                found = regex.findall(m)
                data[key] = found[-1]
        return data

def read_files(path):
    regexs = get_regexs()
    path = os.path.abspath(os.path.join(os.sep, *path))
    for file in os.listdir(path):
        if file.endswith('.out'):
            return get_data(path, file, regexs)
 
c = clock() 
read_files(('Users','Lenon','pythonstuff','Asiowe','vcd_raman'))
print('Took: {}'.format(clock() - c))
