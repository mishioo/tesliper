import re
import logging as lgg

# from triex import Triex

logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)

number_group = r'\s*(-?\d+\.?\d*)'
number = r'\s*-?\d+\.?\d*'

command = re.compile(r'#(?:.*\n)+?(?=\s-)')
termination = re.compile(r'Normal termination.*\n\Z')
cpu_time = re.compile(
    r'Job cpu time:\s*(\d+)\s*days\s*(\d+)\s*hours\s*(\d+)\s*minutes'
    r'\s*(\d+\.\d)\s*seconds'
)  # use .findall(text)
scf = re.compile(r'SCF Done.*=\s+(-?\d+\.?\d*)')  # use .findall(text)
stoich = re.compile(r'Stoichiometry\s*(\w*)\n')  # use .findall(text)

# GEOMETRY
# not used currently
# needs optimizations
geom_part = re.compile(
    'Berny optimization.*?\n\n\n',
    flags=re.DOTALL
)
geom_line_pat = r'\s*(\d+)\s+(\d+)\s+(\d+)' + \
            3 * number_group + r'\s*\n'
geom_inp_pat = r'Input orientation:.*?-+\n(?:' + \
           geom_line_pat.replace('(', '(?:') + \
           r')+?\s-+\n'
geom_inp = re.compile(geom_inp_pat, flags=re.DOTALL)
geom_std_pat = r'Standard orientation:.*?-+\n(?:' + \
           geom_line_pat.replace('(', '(?:') + \
           r')+?\s-+\n'
geom_std = re.compile(geom_std_pat, flags=re.DOTALL)
geom_line = re.compile(geom_line_pat)


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
vibr_dict = dict(
    freq=r'Frequencies',
    mass=r'Red. masses',
    frc=r'Frc consts',
    iri=r'IR Inten',
    dip=r'Dip. str.',
    rot=r'Rot. str.',
    emang=r'E-M angle',
    raman=r'Raman Activ',
    depolarp=r'Depolar \(P\)',
    depolaru=r'Depolar \(U\)',
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
vibr_regs = {k: re.compile(v + '(?:\s+(?:Fr= \d+)?--\s+)' + 3 * number_group)
             for k, v in vibr_dict.items()}


def vibr_parse(text):
    data = {}
    freq = text
    ens = energies.search(freq)
    if ens:
        data.update(ens.groupdict())
    for key, patt in vibr_regs.items():
        m = patt.findall(freq)
        if m:
            data[key] = [float(i) for t in m for i in t]
    if not data:
        logger.warning('No expected freq data found.')
        return {}
    return data


# ELECTRIC
exited_grouped = re.compile(
    r'Excited State\s+(\d+).*\s+'  # beginning of pattern and state's number
    r'(-?\d+\.?\d*) eV\s+'   # state's energy, key = ex_en
    r'(-?\d+\.?\d*) nm.*\n'  # state's frequency, key = efreq
    r'((?:\s*\d+\s*->\s*\d+\s+-?\d+\.\d+)+)'  # state's transitions
    # with use of \s* in the beginning of repeating transitions pattern
    # this regex will match until first blank line
)
excited_states = re.compile(
    r'Excited State\s+\d+.+\n(?:\s*\d+\s*->\s*\d+\s+-?\d+\.\d+)*'
)
excit_dict = dict(
    state_n=r'Excited State\s+(\d+)',
    efreq=r'(-?\d+\.?\d*) nm',
    ex_en=r'(-?\d+\.?\d*) eV',
    transition='\s*(\d+\s*->\s*\d+)\s+(-?\d+\.\d+)'
)
excit_regs = {
    k: re.compile(v) for k, v in excit_dict.items()
}
numbers = 4 * number + 2 * number_group + r'?\n'
numbers_reg = re.compile(numbers)
electr_dict = dict(
    vdip_vosc=r'velocity dipole.*\n.*\n',
    ldip_losc=r'electric dipole.*?:\n.*\n',
    vrot_eemang=r'Rotatory Strengths.*\n.*velocity.*\n',
    lrot_=r'Rotatory Strengths.*\n.*length.*\n'
)
electr_regs = {
    k: re.compile(
        v + r'(?:' +  # core pattern and start of non-capturing group
        numbers.replace(r'(', r'(?:') +  # make all groups non-capturing
        r')+\n'  # match all lines of numbers to blank line
    ) for k, v in electr_dict.items()
}


def electr_parse(text):
    data = {}
    for key, patt in electr_regs.items():
        key1, key2 = key.split('_')
        found = patt.search(text)
        if found:
            nums = numbers_reg.findall(found.group())
            vals1, vals2 = zip(*nums)
            data[key1] = [float(v) for v in vals1]
            if key2:    # second key is '' when key == 'lrot_'
                        # in such case vals2 will be list of empty strings
                data[key2] = [float(v) for v in vals2]

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
    extr['command'] = cmd.group(1)
    extr.update(vibr_parse(text))
    extr.update(electr_parse(text))
    if 'scf' not in extr:
        extr['scf'] = scf.findall(text)[-1]
    trmntn = termination.search(text)
    extr['normal_termination'] = True if trmntn else False
    extr['cpu_time'] = cpu_time.findall(text)

    return extr


if __name__ == '__main__':
    def with_groups(text):
        data = {}
        for n, e, f, t in exited_grouped.findall(text):
            data.setdefault('ex_en', []).append(float(e))
            data.setdefault('efreq', []).append(float(f))
            data.setdefault('transition', []).append(
                excit_regs['transition'].findall(t)
            )
        return data

    def no_groups(text):
        data = {}
        for match in excited_states.findall(text):
            for k, v in excit_regs.items():
                if k == 'transition':
                    data.setdefault(k, []).append(
                        v.findall(match)
                    )
                elif k == 'state_n':
                    pass
                else:
                    data.setdefault(k, []).append(float(v.search(match).group(1)))
        return data

    with open(r'D:\Code\python-projects\Tesliper\logi\Tolbutamid\gjf\LOGI\ECD do 5kcal\ecd gjf\LOGI\Tolbutamid_c1.log', 'r') as f:
        cont = f.read()
    w = with_groups(cont)
    n = no_groups(cont)
    print(w==n)

    for k in w.keys():
        print(k, w[k] == n[k])

    from timeit import timeit
    print(timeit('with_groups(cont)', globals=globals(), number=1000))  # 0.8390080543772318
    print(timeit('no_groups(cont)', globals=globals(), number=1000))    # 1.6335766830799694

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
