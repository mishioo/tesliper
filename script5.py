import os
import re
import numpy as np
from time import clock
import cProfile

def get_regexs():
    regexs = dict(
        SCF = r'SCF Done.*',
        corr_zero_point = r'Zero-point correction',
        corr_energy = r'Thermal correction to Energy',
        corr_enthalpy = r'Thermal correction to Enthalpy',
        corr_free_en = r'Thermal correction to Gibbs Free Energy',
        zero_point = r'Sum of electronic and zero-point Energies',
        energy = r'Sum of electronic and thermal Energies',
        enthalpy = r'Sum of electronic and thermal Enthalpies',
        free_en = r'Sum of electronic and thermal Free Energies')  
    return {k:re.compile(v + r'=\s+(-?\d+\.?\d*)')
            for k,v in regexs.items()}

def get_data(path, file, regexs):     
    with open(os.path.join(path, file), 'r') as f:
        data = dict()
        for line in f:
            if line.startswith((' Sum', ' Thermal', ' Zero', ' SCF')):
                for key, regex in regexs.items():
                    m = regex.search(line)
                    if m:
                        data[key] = m.group(1)
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
