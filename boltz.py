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
from tabulate import tabulate

__author__ = "Michał Więcław"
__date__ = "15.10.2017"
__version__ = "0.1"

#Boltzmann constant
Boltzmann = 0.0019872041 #kcal/(mol*K)

def get_regexs(to_extract):
#TO DO: remove func parameter and create all regexs explicitly.
    """Responsible for preparing regular expresions for parsing Gaussian files.
    Returns dictionary of re compiled objects.
    """
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

def filter_files(files, ext):
    """Filters files from file names list.
    
    Positional parameter:
    files --    list of strings representing file names
    ext --      string representing file extention
    
    Function filters file names in provided list. It returns list of
    file names ending with prowided ext string, representing file
    extention and number of files in created list as tuple.
    """
    filtered = [f for f in files if f.endswith(ext)]
    return filtered, len(filtered)
        
def log_or_out(files):
    """Checks list of file extentions in list of file names.
    
    Positional parameter:
    files --    list of strings representing file names
    
    Function checks for .log and .out files in passed list of file names.
    If both are present, it raises TypeError exception.
    If either is present, it raises ValueError exception.
    It returns string representing file extention present in files list.
    """
    logs, outs = (any(f.endswith(ext) for f in files) for ext in ('.log', '.out')
    if outs and logs:
        raise TypeError(".log and .out files mixed in directory.")
    elif not outs and not logs:
        raise ValueError("Didn't found any .log or .out files.")
    else:
        return '.log' if logs else '.out'
        
def get_data(file, regexs, to_extract):
    """Extracts demanded data from .out/.log file using regexs.
    
    Positional parameters:
    file        -- file handle
    regexs      -- dict of compiled re objects
    to_extract  -- list of strings
    
    Returns dictionary of data, demanded by passing to_extract list,
    containing strings - keys present in regexs dict. Returned dict
    contains single values or numpy arrays, depending on data type.
    """
    energies = 'zpec tenc entc gibc zpe ten ent gib'.split(' ')
    file_data = {k:v for k, v in zip(energies, regexs['ens'].search(file).groups())}
    file_data['scf'] = regexs['scf'].findall(file)[-1]
    for item in ['freq'] + to_extract:
        temp = [s for group in regexs[item].findall(file) for s in group.split(' ') if s]
        file_data[item] = np.array(temp, dtype='float')
    return file_data

def read_file(file):
    """Simple function to read file."""
    with open(file, 'r') as f:
        return f.read()

def boltzmann_dist(energies, t=298.15):
    """
    """
    global Boltzmann
    delta = (energies - energies.min()) * 627.5095
    x = np.exp(-delta/(t*Boltzmann))
    popul = x/x.sum()
    return delta, popul

def save_output(files, to_extract, data):
    headers = [item+end for end in ('p', 'd', '', 'c') for item in ('scf', 'ent', 'gib') if item+end != 'scfc']
    table = zip(files,*[data[item] for item in headers])
    with open('BoltzmannDistribution.txt', 'w') as output:
        output.write(tabulate(table, headers=headers))
    #TO DO: own output formatting, without tabulate
    #TO DO: better headers
    #TO DO: other output files
        
def get_things_to_extract():
    #TO DO: better valid_things
    #TO DO: shorscuts for Boltzman Distribution, bar substraction, Spectra creation, ect.
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
    filtered, no = filter_files(files, log_or_out(files))
    keys = 'zpec tenc entc gibc zpe ten ent gib scf freq imag'.split(' ')
    data = {k:np.zeros(no) for k in keys}
    data.update({k:[0 for _ in range(no)] for k in ['freq'] + to_extract})
    for curr_no, file in enumerate(filtered):
        print('Working on file {} of {}'.format(curr_no+1, no))
        file_cont = read_file(file)
        for key, val in get_data(file_cont, regexs, to_extract).items():
            data[key][curr_no] = val
        data['imag'][curr_no] = (data['freq'][curr_no] < 0).sum()
    for item in ('ent', 'gib', 'scf'):
        data['{}d'.format(item)], data['{}p'.format(item)] = boltzmann_dist(data[item])
    save_output(filtered, to_extract, data)
    
if __name__ == '__main__':
    os.chdir(get_directory())
    #TO DO: get_things_to_extract must ask for each thing (only energies by default)
    to_extract = get_things_to_extract()
    c = clock() 
    #cProfile.run("\
    main_func(to_extract)#")
    print('Took: {}'.format(clock() - c))
