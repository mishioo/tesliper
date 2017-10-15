import os
import re
import numpy as np
from time import clock
import cProfile
import mmap
from contextlib import closing
from collections import OrderedDict
from pprint import pprint
from itertools import chain, zip_longest

Boltzmann = 0.0019872041 #kcal/(mol*K)

def get_regexs():

    ens = re.compile(r''' Zero-point correction=\s*(-?\d+\.?\d*).*
 Thermal correction to Energy=\s*(-?\d+\.?\d*)
 Thermal correction to Enthalpy=\s*(-?\d+\.?\d*)
 Thermal correction to Gibbs Free Energy=\s*(-?\d+\.?\d*)
 Sum of electronic and zero-point Energies=\s*(-?\d+\.?\d*)
 Sum of electronic and thermal Energies=\s*(-?\d+\.?\d*)
 Sum of electronic and thermal Enthalpies=\s*(-?\d+\.?\d*)
 Sum of electronic and thermal Free Energies=\s*(-?\d+\.?\d*)''')
    scf = re.compile(r'SCF Done.*=\s+(-?\d+\.?\d*)')
    freq = re.compile(r'Frequencies --\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)?\s+(-?\d+\.?\d*)?')
    return ens, scf, freq

def filter_files(files):
    outs, logs = [], []
    for f in files:
        if f.endswith('.out'):
            outs.append(f)
        if f.endswith('.log'):
            logs.append(f)   
    if outs and logs:
        raise TypeError(".log and .out files mixed in directory.")
    elif not outs and not logs:
        raise ValueError("Didn't found any .log or .out files.")
    else:
        filtered = outs if outs else logs
        no = len(filtered)
        return filtered, no
        
def get_data(file, regexs):     
    ens, scf, freq = regexs
    found_ens = ens.search(file).groups()
    found_scf = scf.findall(file)[-1]
    found_freq = np.array(list(chain(*freq.findall(file))), dtype='float')
    return (*found_ens, found_scf, found_freq)

def read_file(file):
    with open(file, 'r') as f:
        return f.read()

def boltzmann_dist(energies, t=298.15):
    global Boltzmann
    delta = (energies - energies.min()) * 627.5095
    x = np.exp(-delta/(t*Boltzmann))
    popul = x/x.sum()
    return delta, popul

def save_output(data):
    with open('BoltzmannDistribution.txt', 'w') as output:
        output.write()
            
def main_func(path):
    os.chdir(os.path.abspath(os.path.join(os.sep, *path)))
    regexs = get_regexs()
    files = os.listdir()
    filtered, no = filter_files(files)
    keys = 'zpec tenc entc gibc zpe ten ent gib scf freq imag'.split(' ')
    data = OrderedDict((k,np.zeros(no)) for k in keys)
    data['freq'] = [0 for _ in range(no)]
    for curr_no, file in enumerate(filtered):
        print('Working on file {} of {}'.format(curr_no, no))
        file_cont = read_file(file)
        for arr, val in zip(data.values(), get_data(file_cont, regexs)):
            arr[curr_no] = val
        data['imag'][curr_no] = (data['freq'][curr_no] < 0).sum()
    for item in ('ent', 'gib', 'scf'):
        data['{}d'.format(item)], data['{}p'.format(item)] = \
            boltzmann_dist(data['{}'.format(item)])
    return data
        
        
c = clock() 
#cProfile.run("\
main_func(('Users','Lenon','pythonstuff','Asiowe','log_popr'))#")
print('Took: {}'.format(clock() - c))
