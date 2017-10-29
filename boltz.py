import os
import re
import sys
import numpy as np
import math
from time import clock, sleep
import cProfile
from contextlib import closing
from pprint import pprint
from tkinter import Tk
from tkinter.filedialog import askdirectory
from tabulate import tabulate
from datetime import datetime
import win32gui


######################
#####   GLOBALS  #####
######################

__author__ = "Michał Więcław"
__date__ = "15.10.2017"
__version__ = "0.1"

#Constants
Boltzmann = 0.0019872041 #kcal/(mol*K)

#Global variables
PATH = ''
#uzupełnić
extractibles = {'POPUL':('ens', 'scf'), 'ECD':('freq', 'rot'), 'VCD':('freq', 'rot'),
                'IR':('freq', 'dip'), 'UV':('freq', 'dip'), 'RAMAN':'', 'E-M':'e-m'}

#Messages
welcome_message = 'Welcome to Tesliper: Teoretical Spectra Little Helper.'
help_text = "Sorry, no help available yet. You're on own, mate."
indiv_help_text = {}

#########################
#####   EXCEPTIONS  #####
#########################

class ParserError(Exception): pass


###############################
#####   FILES MANAGEMENT  #####
###############################
    
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
    logs, outs = (any(f.endswith(ext) for f in files) for ext in ('.log', '.out'))
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

        
def change_directory(path=None):
    if not path:
        window = win32gui.GetForegroundWindow()
        Tk().withdraw()
        path = askdirectory()
        win32gui.SetForegroundWindow(window)
    if not path:
        print("Directory not choosen. Tesliper will terminate in:", end=' ')
        for i in range(3,0,-1):
            print(i, end='')
            sys.stdout.flush()
            sleep(0.7)
            print('\b', end='')
        sys.exit()
    try:
        os.chdir(path)
        print('Working directory is now: {}'.format(path))
    except FileNotFoundError:
        print("Can't find directory: {}\n"
              "Try browsing mode by simply typing 'CD' "
              'with no additional arguments.'.format(path))
        return
    return path

    
def save_output(files, to_extract, data):
    headers = [item+end for end in ('p', 'd', '', 'c') for item in ('scf', 'ent', 'gib') if item+end != 'scfc']
    table = zip(files,*[data[item] for item in headers])
    with open('BoltzmannDistribution.txt', 'w') as output:
        output.write(tabulate(table, headers=headers))
    #TO DO: own output formatting, without tabulate
    #TO DO: better headers
    #TO DO: other output files

  
#################################
#####   DATA MANIPULATION   #####
#################################

def init_data_container():
    pass
        
def boltzmann_dist(energies, t=298.15):
    """
    """
    global Boltzmann
    delta = (energies - energies.min()) * 627.5095
    x = np.exp(-delta/(t*Boltzmann))
    popul = x/x.sum()
    return delta, popul
    

def average_spaecra(spectra, populations):
    return sum(s * p for s, p in zip(spectra, populations))
    
    
def calculate_spectrum(bars, freqs, factor, start, stop, step, fwhm, line_shape):
    line_shapes_functions = {'lorentzian':lorentzian, 'gaussian':gaussian}
    function = line_shapes_functions[line_shape]
    spectrum_base = np.arange(start, stop, step)
    spectrum = factor * function(bars, freqs, spectrum_base, fwhm)
    return spectrum
    
    
def lorentzian(bars, freqs, spectrum_base, fwhm):
    hwhm = fwhm/2
    it = np.nditer([spectrum_base, None])
    for lam, peaks in it:
        s = bars/((lam - freqs)**2 + hwhm**2)
        peaks[...] = s.sum() * lam * hwhm / math.pi
    return it.operands[1]
    
# ???    
def gaussian(bars, freqs, spectrum_base, fwhm):
    sigm = fwhm / (2 * math.sqrt(2 * math.log(2)))
    betha = fwhm * math.sqrt(math.pi / math.log(2)) / 2
    it = np.nditer([spectrum_base, None])
    for lam, peaks in it:
        e = exp(-math.pi * (lam - freqs) ** 2 / betha ** 2)
        
        
#def rot_spectra_point(freq, '''fr_max?,''' strght, '''step?,''' fwhm):
    #fwhm - full width at half maximum
    #strght - rotator/dipole strenght
#    pass

# change np.arange for custom iterator?
def old_uv_spectra(dip_str, freqs, spectrum_base, fwhm):
    spectra = np.zeros(spectrum_base.shape)
    A_UV = 2.29046299E+4 * 1.772453851
    B = -3.07441575E+6
    for no, lam in enumerate(spectrum_base):
        a = A_UV * dip_str * freqs / (fwhm * 2**0.5) / lam
        b = math.exp(B * ((lam - freqs) / (freqs * lam * fwhm * 2**0.5))**2)
        spectra[no] = (a*b).sum()
    return spectra
   
   
def old_ecd_spectra(rot_str, freqs, spectrum_base, fwhm):
    spectra = np.zeros(spectrum_base.shape)
    A_CD = 4.30767847E+41 * 1E-40
    B = -3.07441575E+6
    for no, lam in enumerate(spectrum_base):
        a = A_CD * rot_str / (fwhm * 2**0.5) / lam
        b = math.exp(B * ((lam - freqs) / (freqs * lam * fwhm * 2**0.5))**2)
        spectra[no] = (a*b).sum()
    return spectra

    
def old_vcd_spectra(rot_str, freqs, spectrum_base, fwhm):
    spectra = np.zeros(spectrum_base.shape)
    for no, lam in enumerate(spectrum_base):
        a = rot_str * freqs * fwhm * 1.38607595
        b = fwhm**2 + (freqs - lam)**2
        spectra[no] = (a / (b * 1000000)).sum()
    return spectra


def old_ir_spectra(dip_str, freqs, spectrum_base, fwhm):
    spectra = np.zeros(spectrum_base.shape)
    for no, lam in enumerate(spectrum_base):
        a = dip_str * freqs * fwhm * 3.46518986
        b = fwhm**2 + (freqs - lam)**2
        spectra[no] = (a / (b * 1000)).sum()
    return spectra
    
    
def new_vcd_spectra(rot_str, freqs, spectrum_base, fwhm):
    it = np.nditer([spectrum_base, None])
    hwhm = fwhm/2
    for lam, val in it:
        s = rot_str/((lam - freqs)**2 + hwhm**2)
        val[...] = lam * hwhm / (math.pi * 9.184e-39) * s.sum()
    return it.operands[1]

    
#########################
#####   WORKFLOW    #####
#########################    
      
def get_regexs():
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
    keys = 'freq dip rot ir e-m raman1 roa1'.split(' ')
    pats = 'Frequencies', 'Dip. str.', 'Rot. str.', 'E-M angle', 'Raman1', 'ROA1'
    for k, p in zip(keys, pats):
        regexs[k] = re.compile(r'{}.*--\s+(.*)\n'.format(p))
    return regexs

    
def parse_query(query):
    global PATH
    print()
    commands = [s.upper() for s in re.findall(r'\w*', query) if s]
    known_commands = 'EXIT CD HELP GET INFO'.split(' ')
    
    if commands[0] not in known_commands:
        print("No such command: {}.".format(commands[0]))
        return
        
    elif commands[0] == 'EXIT':
        if len(commands) == 1:
            print('It was nice. Thanks for stopping by!')
            sleep(0.7)
            sys.exit()
        else:
            print("'EXIT' doesn't take any additional paramiters.\n"
                  "Simply type 'EXIT' to close Tesliper.")
            return
            
    elif commands[0] == 'HELP':
        global help_text, indiv_help_text
        if len(commands) == 1:
            print(help_text)
        elif len(commands) == 2:
            try:
                print(indiv_help_text[commands[1]])
            except KeyError:
                print("No such command: '{}'.".format(commands[1]))
        else:
            print("'HELP' takes up to one additional parameter.")
        return
        
    elif commands[0] == 'CD':
        PATH = change_directory(query[3:])
        return
        
    elif commands[0] == 'INFO':
        #uzupełnić
        pass
        
    elif commands[0] == 'GET':
        global extractibles
        unknown = [s for s in commands[1:] if s not in extractibles]
        if unknown:
            sufix, delim = ('s', "', '") if len(unknown) > 1 else ('', '')
            print("Unknown parameter{}: '{}'".format(sufix, delim.join(unknown)))
            return
        if not PATH:
            PATH = change_directory()
        return set(item for com in commands[1:] for item in extractibles[com])
        
    else:
        with open("TesliperCrashLog.txt", 'a') as crashlog:
            crashlog.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S, "))
            crashlog.write('function: parse_query, parameters: {}\n'.format(query))
        raise ParserError("I'm sorry! I wasn't able parse your query.\n"
                          "Please notity Tesliper's author about that.")
    
    
def main_func(to_extract):
    regexs = get_regexs()
    files = os.listdir()
    filtered, no = filter_files(files, log_or_out(files))
    keys = 'zpec tenc entc gibc zpe ten ent gib scf freq imag'.split(' ')
    data = {k:np.zeros(no) for k in keys}
    data.update({k:[0 for _ in range(no)] for k in ['freq'] + to_extract})
    data.update({k:[] for k in ('vcd_spec', 'ir_spec')})
    #spectrum_base = np.arange(start, stop, step)
    spectrum_base = np.arange(800, 2100, 1.92867)
    for curr_no, file in enumerate(filtered):
        print('Working on file {} of {}'.format(curr_no+1, no))
        file_cont = read_file(file)
        for key, val in get_data(file_cont, regexs, to_extract).items():
            data[key][curr_no] = val
        data['imag'][curr_no] = (data['freq'][curr_no] < 0).sum()
        data['vcd_spec'].append(old_vcd_spectra(data['rot'][curr_no], data['freq'][curr_no], spectrum_base, 6))
        data['ir_spec'].append(old_ir_spectra(data['dip'][curr_no], data['freq'][curr_no], spectrum_base, 6))
    for item in ('ent', 'gib', 'scf'):
        data['{}d'.format(item)], data['{}p'.format(item)] = boltzmann_dist(data[item])
    for item in data:
        print(item, data[item][0])
    #save_output(filtered, to_extract, data)


#########################
#####   MAIN LOOP   #####
#########################
    
if __name__ == '__main__':
    print(welcome_message, '\n')
    try:
        PATH = sys.argv[1]
    except IndexError:
        print('Free hint: to specify working directory type "cd" and hit Enter. ;)')
    while True:
        query = parse_query(input('What can I do for you? '))
        if query:
            c = clock() 
            #cProfile.run("\
            main_func(query)#")
            print('Took: {}'.format(clock() - c))
