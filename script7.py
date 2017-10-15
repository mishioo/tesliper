import os
import re
import numpy as np
from time import clock
import cProfile
import mmap
from contextlib import closing

def get_regexs():

    ens = re.compile(b''' Zero-point correction=\s*(-?\d+\.?\d*).*
 Thermal correction to Energy=\s*(-?\d+\.?\d*)
 Thermal correction to Enthalpy=\s*(-?\d+\.?\d*)
 Thermal correction to Gibbs Free Energy=\s*(-?\d+\.?\d*)
 Sum of electronic and zero-point Energies=\s*(-?\d+\.?\d*)
 Sum of electronic and thermal Energies=\s*(-?\d+\.?\d*)
 Sum of electronic and thermal Enthalpies=\s*(-?\d+\.?\d*)
 Sum of electronic and thermal Free Energies=\s*(-?\d+\.?\d*)''')
    scf = re.compile(b'SCF Done.*=\s+(-?\d+\.?\d*)')
    return ens, scf

def get_data(path, file, regexs):     
    with open(os.path.join(path, file), 'r') as f:
        data = dict()
        with closing(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as m:
            ens, scf = regexs
            found_ens = ens.search(m).groups()
            found_scf = scf.findall(m)[-1]
        return found_ens, found_scf

def read_files(path):
    regexs = get_regexs()
    path = os.path.abspath(os.path.join(os.sep, *path))
    #corrs = dict.fromkeys()
    for file in os.listdir(path):
        if file.endswith('.out'):
            return get_data(path, file, regexs)
            
 
c = clock() 
print(read_files(('Users','Lenon','pythonstuff','Asiowe','vcd_raman')))
print('Took: {}'.format(clock() - c))
