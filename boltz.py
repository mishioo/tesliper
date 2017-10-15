import os
import re
import sys
import numpy as np
from time import clock, sleep
import cProfile
from contextlib import closing
from pprint import pprint
from tkinter import Tk
from tkinter.filedialog import askdirectory

Boltzmann = 0.0019872041 #kcal/(mol*K)

def get_regexs(to_extract):
    regexs = {}
    regexs['ens'] = re.compile(r''' Zero-point correction=\s*(-?\d+\.?\d*).*
 Thermal correction to Energy=\s*(-?\d+\.?\d*)
 Thermal correction to Enthalpy=\s*(-?\d+\.?\d*)
 Thermal correction to Gibbs Free Energy=\s*(-?\d+\.?\d*)
 Sum of electronic and zero-point Energies=\s*(-?\d+\.?\d*)
 Sum of electronic and thermal Energies=\s*(-?\d+\.?\d*)
 Sum of electronic and thermal Enthalpies=\s*(-?\d+\.?\d*)
 Sum of electronic and thermal Free Energies=\s*(-?\d+\.?\d*)''')
    regexs['scf'] = re.compile(r'SCF Done.*=\s+(-?\d+\.?\d*)')
    regexs['freq'] = re.compile(r'Frequencies --\s+(.*)\n')
    for item in to_extract:
        regexs[item] = re.compile(r'{}.*--\s+(.*)\n'.format(item))
    return regexs

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
        
def get_data(file, regexs, to_extract):
    """Extract data from file using regexs."""
    energies = 'zpec tenc entc gibc zpe ten ent gib'.split(' ')
    file_data = {k:v for k, v in zip(energies, regexs['ens'].search(file).groups())}
    file_data['scf'] = regexs['scf'].findall(file)[-1]
    for item in ['freq'] + to_extract:
        temp = [s for group in regexs[item].findall(file) for s in group.split(' ') if s]
        file_data[item] = np.array(temp, dtype='float')
    return file_data

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
        
def get_things_to_extract():
    inp = input('What to extract?')
    valid_things = 'Red. masses,Frc consts,IR Inten,Dip. str.,Rot. str.,E-M angle,\
        RamAct,Dep-P,Dep-U,Alpha2,Beta2,AlphaG,Gamma2,Delta2,Raman1,ROA1,CID1,\
        Raman2,ROA2,CID2,Raman3,ROA3,CID3,RC180'
    inp = inp.split(' ') if inp else []
    for item in inp:
        if item not in ('Dip Rot '.split(' ')):
            raise ValueError('{} is not valid input.'.format(item))
    return inp

def get_directory():
    Tk().withdraw()
    path = askdirectory()
    if not path:
        print("Directory not choosen. Script will terminate in:", end=' ')
        for i in range(3,0,-1):
            print(i, end='')
            sys.stdout.flush()
            sleep(1)
            print('\b', end='')
        sys.exit()
    return path
    
def main_func(to_extract):
    regexs = get_regexs(to_extract)
    files = os.listdir()
    filtered, no = filter_files(files)
    keys = 'zpec tenc entc gibc zpe ten ent gib scf freq imag'.split(' ')
    data = {k:np.zeros(no) for k in keys}
    data.update({k:[0 for _ in range(no)] for k in ['freq'] + to_extract})
    for curr_no, file in enumerate(filtered):
        #print('Working on file {} of {}'.format(curr_no+1, no))
        file_cont = read_file(file)
        for key, val in get_data(file_cont, regexs, to_extract).items():
            data[key][curr_no] = val
        data['imag'][curr_no] = (data['freq'][curr_no] < 0).sum()
    for item in ('ent', 'gib', 'scf'):
        data['{}d'.format(item)], data['{}p'.format(item)] = \
            boltzmann_dist(data['{}'.format(item)])
    return data
        
if __name__ == '__main__':
    os.chdir(get_directory())
    to_extract = get_things_to_extract()
    c = clock() 
    #cProfile.run("\
    main_func(to_extract)#")
    print('Took: {}'.format(clock() - c))
