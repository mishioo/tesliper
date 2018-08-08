import re
import logging as lgg

# from triex import Triex

logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)

number = r'\s*(-?\d+\.\d+)'

command = re.compile(r'(#.*?)\n\s--', flags=re.DOTALL)
error = re.compile(r'^[\w\s]+error')
termination = re.compile(r'Normal termination.*(?:\n.*\n.*)?\n\Z')
cpu_time = re.compile(
    r'Job cpu time:\s*(\d+)\s*days\s*(\d+)\s*hours\s*(\d+)\s*minutes'
    r'\s*(\d+\.\d)\s*seconds'
)  # use .findall(text)

# GEOMETRY
geom_part = re.compile(
    'Berny optimization.*?\n\n\n',
    flags=re.DOTALL
)
geom_line_pat = r'\s*(\d+)\s+(\d+)\s+(\d+)' + \
            3 * number + r'\s*\n'
geom_inp_pat = r'Input orientation:.*?-+\n(?:' + \
           geom_line_pat.replace('(', '(?:') + \
           r')+?\s-+\n'
geom_inp = re.compile(geom_inp_pat, flags=re.DOTALL)
geom_std_pat = r'Standard orientation:.*?-+\n(?:' + \
           geom_line_pat.replace('(', '(?:') + \
           r')+?\s-+\n'
geom_std = re.compile(geom_std_pat, flags=re.DOTALL)
geom_line = re.compile(geom_line_pat)
scf = re.compile(r'SCF Done.*=\s+(-?\d+\.?\d*)')  # use .findall(text)
stoich = re.compile(r'Stoichiometry\s*(\w*)\n')  # use .findall(text)


def geom_parse(text):
    """Function for extracting geometry data from output files.
    Needs refactoring and is not included in standard parsing procedure."""
    data = {}
    geom = text  # geom_part.search(text)  # takes long time if no match
    if not geom:
        logger.warning('No expected geom data found.')
        return {}
    # geom = geom.group()
    data['optimization_completed'] = 'Optimization completed.' in geom
    data['stoichometries'] = stoich.findall(geom)
    data['scfs'] = scf.findall(geom)
    data['scf'] = data['scfs'][-1]
    sg = geom_std.findall(geom)
    if sg:
        data['standard_geometries'] = [geom_line.findall(g) for g in sg]
        if data['optimization_completed']:
            data['optimized'] = data['standard_geometries'][-1]
    else:
        data['input_geometries'] = [
            geom_line.findall(g) for g in geom_inp.findall(geom)
        ]
        if data['optimization_completed']:
            data['optimized'] = data['input_geometries'][-1]
    return data


# VIBRATIONAL
freq_part = re.compile(
    r'Harmonic frequencies .+? and normal coordinates:\n(.*)\n\n',
    flags=re.DOTALL
)  # use .search(text).group(1)
energies = re.compile(
    r' Zero-point correction=\s*(?P<zpec>-?\d+\.?\d*).*\n'
    r' Thermal correction to Energy=\s*(?P<tenc>-?\d+\.?\d*)\n'
    r' Thermal correction to Enthalpy=\s*(?P<entc>-?\d+\.?\d*)\n'
    r' Thermal correction to Gibbs Free Energy=\s*(?P<gibc>-?\d+\.?\d*)\n'
    r' Sum of electronic and zero-point Energies=\s*(?P<zpe>-?\d+\.?\d*)\n'
    r' Sum of electronic and thermal Energies=\s*(?P<ten>-?\d+\.?\d*)\n'
    r' Sum of electronic and thermal Enthalpies=\s*(?P<ent>-?\d+\.?\d*)\n'
    r' Sum of electronic and thermal Free Energies=\s*(?P<gib>-?\d+\.?\d*)'
)  # use .search(text).groups()
freq_dict = dict(
    freq=r'Frequencies',
    mass=r'Red. masses',
    frc=r'Frc consts',
    iri=r'IR Inten',
    dip=r'Dip. str.',
    rot=r'Rot. str.',
    emang=r'E-M angle',
    raman=r'Raman Activ',
    depolarp=r'Depolar (P)',
    depolaru=r'Depolar (U)',
    ramact=r'RamAct',
    depp=r'Dep-P',
    depu=r'Dep-U',
    alpha2=r'Alpha2',
    beta2=r'Beta2',
    alphag=r'AlphaG',
    gamma2=r'Gamma2',
    delta2=r'Delta2',
    raman1=r'Raman1',
    roa1=r'ROA1',
    cid1=r'CID1',
    raman2=r'Raman2',
    roa2=r'ROA2',
    cid2=r'CID2',
    raman3=r'Raman3',
    roa3=r'ROA3',
    cid3=r'CID3',
    rc180=r'RC180'
)
vibr_dict = {k: re.compile(v+'(?:\s+(?:Fr= \d+)?--\s+)'+3*number) for k, v in freq_dict.items()}
# roa_dict = {k: re.compile(v+3*number) for k, v in roa_dict.items()}

# trie_regex = Triex([re.escape(v) for v in freq_dict.values()]).pattern
# vibr_regex = re.compile('('+trie_regex+')(?:\s+(?:Fr= \d+)?--\s+)'+3*number)
# vibr_keys = {v: k for k, v in freq_dict.items()}


def vibr_parse_old(text):
    data = {}
    freq = freq_part.search(text)
    if not freq:
        logger.warning('No expected freq data found.')
        return {}
    freq = freq.group()
    # ens = energies.search(freq)
    # if ens:
    #     data.update(ens.groupdict())
    for key, patt in vibr_dict.items():
        m = patt.findall(freq)
        if m:
            data[key] = [float(i) for t in m for i in t]
    return data

def vibr_parse(text):
    data = {}
    freq = text
    ens = energies.search(freq)
    if ens:
        data.update(ens.groupdict())
    for key, patt in vibr_dict.items():
        m = patt.findall(freq)
        if m:
            data[key] = [float(i) for t in m for i in t]
    if not data:
        logger.warning('No expected freq data found.')
        return {}
    return data

def vibr_parse_triex(text):
    data = {}
    # ens = energies.search(text)
    # if ens:
    #     data.update(ens.groupdict())
    freqiter = vibr_regex.findall(text)
    if freqiter:
        for key, *vals in freqiter:
            arr = data.setdefault(vibr_keys[key], [])
            arr.extend([float(i) for i in vals])
    return data

# ELECTRIC
electr_part = re.compile(
    r'Excitation energies and oscillator strengths:\n\s*\n(.*?)Leave Link.*?\n',
    flags=re.DOTALL
)  # use .search(text).group(1).split('\n \n')
exited_states = re.compile(
    r'Excited State\s+\d+.+\n(?:\s*\d+\s*->\s*\d+\s+-?\d+\.\d+)*'
)
electr_dict = dict(
    state_n=r'Excited State\s+(\d+)',
    efreq=r'(-?\d+\.?\d*) nm',
    ex_en=r'(-?\d+\.?\d*) eV',
    transition='\s*(\d+\s*->\s*\d+)\s+(-?\d+\.\d+)'
)
velo_dip_osc = re.compile(
    r'velocity dipole.*\n.*\n' + 6 * r'\s*?:-?\d+\.?\d*' + r'\n'
)
len_dip_osc = re.compile(
    r'electric dipole.*?:\n.*\n' + 6 * r'\s*?:-?\d+\.?\d*' + r'\n'
)
velo_rot_emang = re.compile(
    r'Rotatory Strengths.*\n.*\n' + 6 * r'\s*?:-?\d+\.?\d*' + r'\n'
)
len_rot = re.compile(
    r'Rotatory Strengths.*\n.*\n' + 5 * r'\s*?:-?\d+\.?\d*' + r'\n'
)


def electr_parse(text):
    data = {}
    return data


parts = dict(
    opt=geom_parse,
    freq=vibr_parse,
    td=electr_parse
)


def parse(text):
    extr = {}
    cmd = command.search(text)
    if not cmd:
        raise ValueError('No command found in text.')
    extr['cmd'] = cmd.group(1)
    cmdlow = extr['cmd'].lower()
    for key in 'freq td'.split(' '):
        if key in cmdlow:
            extr.update(parts[key](text))
    if not 'scf' in extr:
        extr['scf'] = scf.findall(text)[-1]
    trmntn = termination.search(text)
    extr['normal_termination'] = True if trmntn else False
    err = error.search(text)
    if err:
        extr['error'] = err.group()
    else:
        extr['error'] = None
    extr['cpu_time'] = cpu_time.findall(text)

    extr['geom'] = geom_line.findall(geom_std.findall(text)[-1])  # temporarly

    return extr

if __name__ == '__main__':
    pass
    # with open(r'D:\Code\python-projects\Tesliper\logi\opt only\c-t1_B6311.log', 'r') as f:
    #     cont = f.read()
    #
    # print(trie_regex)
    #
    # print(vibr_parse_old(cont) == vibr_parse(cont))
    # from timeit import timeit
    # import cProfile
    #
    # print(f'new: {timeit("vibr_parse(cont)", globals=globals(), number=100)}')
    # print(f'old: {timeit("vibr_parse_old(cont)", globals=globals(), number=100)}')
    # print(f'onp: {timeit("vibr_parse_old_no_preproc(cont)", globals=globals(), number=100)}')
    # cProfile.run('for _ in range(100): vibr_parse(cont)')
    # cProfile.run('for _ in range(100): vibr_parse_old(cont)')
    # cProfile.run('for _ in range(100): vibr_parse_old_no_preproc(cont)')
