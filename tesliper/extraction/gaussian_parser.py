import re
import logging as lgg
import numpy as np

from .base_parser import Parser

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.INFO)

# REGEXS
number_group = r"\s*(-?\d+\.?\d*)"
number = number_group.replace("(", "").replace(")", "")

command = re.compile(r"#(?:.*\n)+?(?=\s-)")
termination = re.compile(r"Normal termination.*\n\Z")
cpu_time_reg = re.compile(
    r"Job cpu time:\s*(\d+)\s*days\s*(\d+)\s*hours\s*(\d+)\s*minutes"
    r"\s*(\d+\.\d)\s*seconds"
)  # use .findall(text)
scf = re.compile(r"SCF Done.*=\s+(-?\d+\.?\d*)")  # use .findall(text)
stoich = re.compile(r"Stoichiometry\s*(\w*)\n")  # use .findall(text)
stoich_ = re.compile(r"^ Stoichiometry\s*(\w*)\n")  # use .findall(text)

# GEOMETRY
# not used currently
# needs optimizations
geom_part = re.compile("Berny optimization.*?\n\n\n", flags=re.DOTALL)
geom_line_pat = r"\s*(\d+)\s+(\d+)\s+(\d+)" + 3 * number_group + r"\s*\n"
geom_inp_pat = (
    r"Input orientation:.*?-+\n(?:" + geom_line_pat.replace("(", "(?:") + r")+?\s-+\n"
)
geom_inp = re.compile(geom_inp_pat, flags=re.DOTALL)
geom_std_pat = (
    r"Standard orientation:.*?-+\n(?:"
    + geom_line_pat.replace("(", "(?:")
    + r")+?\s-+\n"
)
geom_std = re.compile(geom_std_pat, flags=re.DOTALL)
geom_line = re.compile(geom_line_pat)
geom_line_ = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+)" + 3 * number_group)

# VIBRATIONAL
energies = re.compile(
    r" Zero-point correction=\s*(?P<zpecorr>-?\d+\.?\d*).*\n"
    r" Thermal correction to Energy=\s*(?P<tencorr>-?\d+\.?\d*)\n"
    r" Thermal correction to Enthalpy=\s*(?P<entcorr>-?\d+\.?\d*)\n"
    r" Thermal correction to Gibbs Free Energy=\s*(?P<gibcorr>-?\d+\.?\d*)\n"
    r" Sum of electronic and zero-point Energies=\s*(?P<zpe>-?\d+\.?\d*)\n"
    r" Sum of electronic and thermal Energies=\s*(?P<ten>-?\d+\.?\d*)\n"
    r" Sum of electronic and thermal Enthalpies=\s*(?P<ent>-?\d+\.?\d*)\n"
    r" Sum of electronic and thermal Free Energies=\s*(?P<gib>-?\d+\.?\d*)"
)  # use .search(text).groups()
vibr_dict = dict(
    freq=r"Frequencies",
    mass=r"Red. masses",
    frc=r"Frc consts",
    iri=r"IR Inten",
    dip=r"Dip. str.",
    rot=r"Rot. str.",
    emang=r"E-M angle",
    depolarp=r"Depolar \(P\)",
    depolaru=r"Depolar \(U\)",
    ramact=r"RamAct",
    ramanactiv=r"Raman Activ",
    depp=r"Dep-P",
    depu=r"Dep-U",
    alpha2=r"Alpha2",
    beta2=r"Beta2",
    alphag=r"AlphaG",
    gamma2=r"Gamma2",
    delta2=r"Delta2",
    raman1=r"Raman1",
    roa1=r"ROA1",
    cid1=r"CID1",
    raman2=r"Raman2",
    roa2=r"ROA2",
    cid2=r"CID2",
    raman3=r"Raman3",
    roa3=r"ROA3",
    cid3=r"CID3",
    rc180=r"RC180",
)
vibr_dict_ = vibr_dict.copy()
vibr_dict_["depolarp"] = r"Depolar (P)"
vibr_dict_["depolaru"] = r"Depolar (U)"
vibr_dict_ = {value: key for key, value in vibr_dict_.items()}
vibrational_reg = re.compile(
    r"^\s\s?([a-zA-Z.\-]+[0-9]*(?:\s?[a-zA-Z.()]+)?)\s*(?:(?:Fr= \d+)?--)"
    + 3 * number_group
)
vibr_regs = {
    k: re.compile(v + r"(?:\s+(?:Fr= \d+)?--\s+)" + 3 * number_group)
    for k, v in vibr_dict.items()
}

# ELECTRIC
excited_grouped = re.compile(
    r"Excited State\s+(\d+).*\s+"  # beginning of pattern and state's number
    r"(-?\d+\.?\d*) eV\s+"  # state's energy, key = ex_en
    r"(-?\d+\.?\d*) nm.*\n"  # state's frequency, key = wavelen
    r"((?:\s*\d+\s*->\s*\d+\s+-?\d+\.\d+)+)"  # state's transitions
    # with use of \s* in the beginning of repeating transitions pattern
    # this regex will match until first blank line
)
excited_reg = re.compile(
    r"^ Excited State\s+\d+:[a-zA-Z\-\s\'\"]*(-?\d+\.?\d*) eV\s+(-?\d+\.?\d*) nm"
)
transitions = r"\s*(\d+\s*->\s*\d+)\s+(-?\d+\.\d+)"
transitions_reg = re.compile(transitions)
transitions_ = r"(\d+)\s*->\s*(\d+)\s+(-?\d+\.\d+)"
transitions_reg_ = re.compile(transitions_)
numbers = 4 * number + 2 * number_group + r"?\n"
numbers_reg = re.compile(numbers)
electr_dict = dict(
    vdip_vosc=r"velocity dipole.*\n.*\n",
    ldip_losc=r"electric dipole.*?:\n.*\n",
    vrot_eemang=r"Rotatory Strengths.*\n.*velocity.*\n",
    lrot_=r"Rotatory Strengths.*\n.*length.*\n",
)
electr_regs = {
    k: re.compile(
        v  # core pattern
        + r"(?:"  # start of non-capturing group
        + numbers.replace(r"(", r"(?:")  # make all groups non-capturing
        + r")+"  # find all consecutive lines with numbers and terminate
    )
    for k, v in electr_dict.items()
}
shielding_reg = re.compile(
    r"(\w+)\s+Isotropic =" + number_group + r"\s+Anisotropy =" + number_group
)
fc_sci_not = r"(-?\d\.\d+D[+-]\d\d)"
fc_reg = re.compile(r"(\d+)\s+" + fc_sci_not + (r"\s*" + fc_sci_not + "?") * 4)


# CLASSES
class GaussianParser(Parser):
    """Parser for extracting data from human-readable output files from Gaussian
    computational chemistry software (.log and .out files).

    This class implements methods for reading information about conducted calculations'
    parameters, molecule energy, structure optimization, and calculation of spectral
    properties. It's use is as straightforward as:

    >>> parser = GaussianParser()
    >>> with open('path/to/file.out') as file:
    >>>     data = parser.parse(file)

    Dictionary with data extracted is also stored as `data` attribute of instance used
    for parsing. Each key in said dictionary is a name of its value data type, called
    from now on a 'data genre' (to avoid confusion with Python's data type). Below is
    a full list of data genres recognised by this parser, with their description:

    freq : list of floats, available from freq job
        harmonic vibrational frequencies (cm^-1)
    mass : list of floats, available from freq job
        reduced masses (AMU)
    frc : list of floats, available from freq job
        force constants (mDyne/A)
    iri : list of floats, available from freq job
        IR intensities (KM/mole)
    dip : list of floats, available from freq=VCD job
        dipole strengths (10**-40 esu**2-cm**2)
    rot : list of floats, available from freq=VCD job
        rotational strengths (10**-44 esu**2-cm**2)
    emang : list of floats, available from freq=VCD job
        E-M angle = Angle between electric and magnetic dipole transition moments (deg)
    depolarp : list of floats, available from freq=Raman job
        depolarization ratios for plane incident light
    depolaru : list of floats, available from freq=Raman job
        depolarization ratios for unpolarized incident light
    ramanactiv : list of floats, available from freq=Raman job
        Raman scattering activities (A**4/AMU)
    ramact : list of floats, available from freq=ROA job
        Raman scattering activities (A**4/AMU)
    depp : list of floats, available from freq=ROA job
        depolarization ratios for plane incident light
    depu : list of floats, available from freq=ROA job
        depolarization ratios for unpolarized incident light
    alpha2 : list of floats, available from freq=ROA job
        Raman invariants Alpha2 = alpha**2 (A**4/AMU)
    beta2 : list of floats, available from freq=ROA job
        Raman invariants Beta2 = beta(alpha)**2 (A**4/AMU)
    alphag : list of floats, available from freq=ROA job
        ROA invariants AlphaG = alphaG'(10**4 A**5/AMU)
    gamma2 : list of floats, available from freq=ROA job
        ROA invariants Gamma2 = beta(G')**2 (10**4 A**5/AMU)
    delta2 : list of floats, available from freq=ROA job
        ROA invariants Delta2 = beta(A)**2, (10**4 A**5/AMU)
    raman1 : list of floats, available from freq=ROA job
        Far-From-Resonance Raman intensities =ICPu/SCPu(180) (K)
    roa1 : list of floats, available from freq=ROA job
        ROA intensities =ICPu/SCPu(180) (10**4 K)
    cid1 : list of floats, available from freq=ROA job
        CID=(ROA/Raman)*10**4 =ICPu/SCPu(180)
    raman2 : list of floats, available from freq=ROA job
        Far-From-Resonance Raman intensities =ICPd/SCPd(90) (K)
    roa2 : list of floats, available from freq=ROA job
        ROA intensities =ICPd/SCPd(90) (10**4 K)
    cid2 : list of floats, available from freq=ROA job
        CID=(ROA/Raman)*10**4 =ICPd/SCPd(90)
    raman3 : list of floats, available from freq=ROA job
        Far-From-Resonance Raman intensities =DCPI(180) (K)
    roa3 : list of floats, available from freq=ROA job
        ROA intensities =DCPI(180) (10**4 K)
    cid3 : list of floats, available from freq=ROA job
        CID=(ROA/Raman)*10**4 =DCPI(180)
    rc180 : list of floats, available from freq=ROA job
        RC180 = degree of circularity
    wavelen : list of floats, available from td job
        excitation energies (nm)
    ex_en : list of floats, available from td job
        excitation energies (eV)
    eemang : list of floats, available from td job
        E-M angle = Angle between electric and magnetic dipole transition moments (deg)
    vdip : list of floats, available from td job
        dipole strengths (velocity)
    ldip : list of floats, available from td job
        dipole strengths (length)
    vrot : list of floats, available from td job
        rotatory strengths (velocity) in cgs (10**-40 erg-esu-cm/Gauss)
    lrot : list of floats, available from td job
        rotatory strengths (length) in cgs (10**-40 erg-esu-cm/Gauss)
    vosc : list of floats, available from td job
        oscillator strengths
    losc : list of floats, available from td job
        oscillator strengths
    transitions : list of tuples of tuples of (int, int, float), available from td job
        transitions (first to second) and their coefficients (third)
    scf : float, always available
        SCF energy
    zpe : float, available from freq job
        Sum of electronic and zero-point Energies (Hartree/Particle)
    ten : float, available from freq job
        Sum of electronic and thermal Energies (Hartree/Particle)
    ent : float, available from freq job
        Sum of electronic and thermal Enthalpies (Hartree/Particle)
    gib : float, available from freq job
        Sum of electronic and thermal Free Energies (Hartree/Particle)
    zpecorr : float, available from freq job
        Zero-point correction (Hartree/Particle)
    tencorr : float, available from freq job
        Thermal correction to Energy (Hartree/Particle)
    entcorr : float, available from freq job
        Thermal correction to Enthalpy (Hartree/Particle)
    gibcorr : float, available from freq job
        Thermal correction to Gibbs Free Energy (Hartree/Particle)
    command : str, always available
        command used for calculations
    normal_termination : bool, always available
        true if Gaussian job seem to exit normally, false otherwise
    optimization_completed : bool, available from opt job
        true if structure optimization was performed successfully
    version : str, always available
        version of Gaussian software used
    charge : float, always available
        molecule's charge
    multiplicity : float, always available
        molecule's spin multiplicity
    input_geom : list of tuples of (str, float, float, float), always available
        input orientation, starting with atom symbol
    stoichiometry : str, always available
        molecule's stoichiometry
    molecule_atoms : tuple of ints, always available
        molecule's atoms as atomic numbers
    geometry : tuple of tuples of floats, always available
        molecule's geometry (last one found in file) as X, Y, Z coordinates of atoms

    Attributes
    ----------
    data : dict
        Data extracted during last parsing."""

    purpose = "gaussian"

    def __init__(self):
        super().__init__()
        self.iterator = iter([])
        self.data = {}

    def parse(self, lines) -> dict:
        """Parses content of Gaussian output file and returns dictionary of found
        data. TODO: elaborate

        Parameters
        ----------
        lines : iterator
            Gaussian output file in a form iterable by lines of text. It may be a file
            handle, a list of strings, an io.StringIO instance, or similar. Please note
            that it should not be just a string instance, as it is normally iterated
            by a character, not by a line.

        Returns
        -------
        dict
            Dictionary of extracted data."""
        self.workhorse = self.initial
        self.data = {}
        self.iterator = iter(lines)
        for line in self.iterator:
            self.workhorse(line)
        return self.data

    @Parser.state
    def initial(self, line: str) -> None:
        """First step of parsing Gaussian output file. It populates parser.data
        dictionary with these data genes: 'normal_termination', 'version', 'command',
        'charge', 'multiplicity', 'input_geom'. Optionally, 'optimization_completed'
        genre is added if optimization was requested in calculation job.

        Parameters
        ----------
        line : str
            Line of text to parse."""
        data, iterator = self.data, self.iterator
        data["normal_termination"] = True
        while not line == " Cite this work as:\n":
            line = next(iterator)
        data["version"] = next(iterator).strip(" \n,")
        while not line.startswith(" #"):
            line = next(iterator)
        command = []
        while not line.startswith(" --"):
            command.append(line.strip())
            line = next(iterator)
        command = data["command"] = " ".join(command)
        if "opt" in command:
            data["optimization_completed"] = False
        while not line == " Symbolic Z-matrix:\n":
            line = next(iterator)
        c_and_m = re.match(r" Charge =\s*(-?\d) Multiplicity = (\d)", next(iterator))
        data["charge"], data["multiplicity"] = map(float, c_and_m.groups())
        line = next(iterator).strip()
        input_geom = []
        pattern = r"(\w+)" + 3 * number_group
        while line:
            atom = re.match(pattern, line)
            label, *coordinates = atom.groups()
            input_geom.append((label, *map(float, coordinates)))
            line = next(iterator).strip()
        data["input_geom"] = input_geom
        self.workhorse = self.wait

    @Parser.state
    def wait(self, line: str) -> None:
        """This function searches for lines of text triggering other parsing states.
        It also updates a parser.data dictionary with 'normal_termination', 'scf',
        'stoichiometry' data genres.

        Parameters
        ----------
        line : str
            Line of text to parse."""
        for name, reg in self.triggers.items():
            match = reg.match(line)
            if match:
                self.workhorse = name
                return
        if "Error termination" in line:
            self.data["normal_termination"] = False
        elif line.startswith(" SCF Done:"):
            self.data["scf"] = float(re.search(number, line).group())
        elif line.startswith(" Stoichiometry"):
            self.data["stoichiometry"] = stoich_.match(line).group(1)

    @Parser.state(trigger=re.compile(r"^\s+Standard orientation"))
    def geometry(self, line: str) -> None:
        """Function for extracting information about molecule standard orientation
        geometry from Gaussian output files. It updates parser.data dictionary with
        'molecule_atoms' and 'geometry' data genres.

        Parameters
        ----------
        line : str
            Line of text to parse."""
        data, iterator = self.data, self.iterator
        match = geom_line_.match(line)
        while not match:
            line = next(iterator)
            match = geom_line_.match(line)
        geom = []
        while match:
            geom.append(match.groups())
            line = next(iterator)
            match = geom_line_.match(line)
        geom = ((int(a), (float(x), float(y), float(z))) for _, a, _, x, y, z in geom)
        data["molecule_atoms"], data["geometry"] = zip(*geom)
        self.workhorse = self.wait

    @Parser.state(trigger=re.compile("^ Berny optimization"))
    def optimization(self, line: str) -> None:
        """This method scans optimization data in Gaussian output file, updating
        parser.data dictionary with 'stoichiometry', 'scf', 'optimization_completed',
        'molecule_atoms', and 'geometry' data genres (last two via `geometry()` method).

        Parameters
        ----------
        line : str
            Line of text to parse."""
        if self.triggers["geometry"].match(line):
            self.geometry(line)
            self.workhorse = self.optimization
        elif line.startswith(" Stoichiometry"):
            self.data["stoichiometry"] = stoich_.match(line).group(1)
        elif line.startswith(" SCF Done:"):
            self.data["scf"] = float(re.search(number, line).group())
        elif line.startswith(" Optimization completed."):
            self.data["optimization_completed"] = True
        elif line == "\n":
            self.workhorse = self.wait

    @Parser.state(trigger=re.compile("^ Harmonic frequencies"))
    def frequencies(self, line: str) -> None:
        """Responsible for extracting harmonic vibrations-related data and information
        about molecule's energy.

        Parameters
        ----------
        line : str
            Line of text to parse."""
        data, iterator = self.data, self.iterator
        while not line == "\n":
            # while frequencies section is not over
            match = vibrational_reg.match(line)
            while match:
                # unpack values from current line to list of corresponding genre
                name, *values = match.groups()
                genre = vibr_dict_[name]  # convert gaussian line name to genre
                data.setdefault(genre, list()).extend(float(x) for x in values)
                line = next(iterator)
                match = vibrational_reg.match(line)
            line = next(iterator)
        while not line.startswith(" Zero-point correction="):
            line = next(iterator)
        # parse energies values
        for genre in "zpecorr tencorr entcorr gibcorr zpe ten ent gib".split():
            data[genre] = float(re.search(number, line).group())
            line = next(iterator)
        self.workhorse = self.wait

    def _excited_states(self, line: str) -> list:
        """Helper function for extracting electronic transitions-related data
        from content of Gaussian output file.

        Parameters
        ----------
        line : str
            Line of text to parse.

        Returns
        -------
        list
            List of floats with data extracted from input string."""
        iterator = self.iterator
        while not line.startswith(" Excited State"):
            line = next(iterator)
        out = [map(float, excited_reg.match(line).groups())]
        while line.strip():
            line = next(iterator)
            match = transitions_reg_.search(line)
            if match:
                out.append(match.groups())
        return out

    @Parser.state(trigger=re.compile("^ Excited states from"))
    def excited(self, line: str) -> None:
        """Responsible for extracting electronic transitions-related data from Gaussian
        output file. Updates parser.data dictionary with 'ldip', 'losc', 'vdip', 'vosc',
        'vrot', 'eemang', 'lrot', 'wavelen', 'ex_en', and 'transitions' data genres.

        Parameters
        ----------
        line : str
            Line of text to parse."""
        data, iterator = self.data, self.iterator
        for genres, header in (
            (("ldip", "losc"), "electric dipole"),
            (("vdip", "vosc"), "velocity dipole"),
            (("vrot", "eemang"), "Rotatory Strengths"),
            (("lrot", ""), "Rotatory Strengths"),
        ):
            while header not in line:
                line = next(iterator)
            next(iterator)  # skip column names
            match = numbers_reg.search(next(iterator))
            values = []
            while match:
                values.append(float(x) if x else None for x in match.groups())
                line = next(iterator)
                match = numbers_reg.search(line)
            for genre, values in zip(genres, zip(*values)):
                if genre:
                    data[genre] = values
        while not line.startswith(" **"):
            (energy, wavelen), *transitions = self._excited_states(line)
            data.setdefault("wavelen", []).append(wavelen)
            data.setdefault("ex_en", []).append(energy)
            data.setdefault("transitions", []).append(
                tuple(
                    (int(low), int(high), float(coef))
                    for low, high, coef in transitions
                )
            )
            line = next(iterator)
        self.workhorse = self.wait


# FUNCTIONS
def _geom_parse(text):
    """Function for extracting geometry data from output files.
    Needs refactoring and is not included in standard parsing procedure."""
    data = {}
    geom = text  # geom_part.search(text)  # takes long time if no match
    if not geom:
        logger.warning("No expected geom data found.")
        return {}
    # geom = geom.group()
    data["optimization_completed"] = "Optimization completed." in geom
    data["stoichometries"] = stoich.findall(geom)
    data["scfs"] = scf.findall(geom)
    data["scf"] = data["scfs"][-1]
    sg = geom_std.findall(geom)
    if sg:
        data["standard_geometries"] = [geom_line.findall(g) for g in sg]
        if data["optimization_completed"]:
            data["optimized"] = data["standard_geometries"][-1]
    else:
        data["input_geometries"] = [
            geom_line.findall(g) for g in geom_inp.findall(geom)
        ]
        if data["optimization_completed"]:
            data["optimized"] = data["input_geometries"][-1]
    return data


def _vibr_parse(text):
    """Helper function for extracting electronic transitions-related data
    from content of Gaussian output file.

    Parameters
    ----------
    text : str
        Content of gaussian output file as string.

    Returns
    -------
    dict
        Dictionary of data extracted from input string."""

    logger.debug("entering _vibr_parse")
    data = {}
    ens = energies.search(text)
    if ens:
        data.update({k: float(v) for k, v in ens.groupdict().items()})
    else:
        logger.debug("No energies found!")
    for key, patt in vibr_regs.items():
        m = patt.findall(text)
        if m:
            data[key] = np.array([i for t in m for i in t], dtype=float)
    # if not data:
    #     logger.warning('No expected freq data found.')
    #     return {}
    return data


def _electr_parse(text):
    """Helper function for extracting electronic transitions-related data
    from content of Gaussian output file.

    Parameters
    ----------
    text : str
        Content of gaussian output file as string.

    Returns
    -------
    dict
        Dictionary of data extracted from input string."""

    logger.debug("entering _electr_parse")
    data = {}
    for key, patt in electr_regs.items():
        key1, key2 = key.split("_")
        found = patt.search(text)
        if found:
            nums = numbers_reg.findall(found.group())
            vals1, vals2 = zip(*nums)
            data[key1] = np.array(vals1, dtype=float)
            if key2 and vals2[0]:
                # key2 is '' when key == 'lrot_'
                # and eemang is not available in g.09B
                # in such cases vals2 will be list of empty strings
                data[key2] = np.array(vals2, dtype=float)
    excited = excited_grouped.findall(text)
    if excited:
        n, e, f, t = zip(*excited)
        data["ex_en"] = np.array(e, dtype=float)
        data["wavelen"] = np.array(f, dtype=float)
        data["transition"] = [transitions_reg.findall(x) for x in t]
    return data


def parse(text):
    """Parses content of Gaussian output file and returns dictionary of found
    data.

    Parameters
    ----------
    text : str
        Content of gaussian output file as string.

    Returns
    -------
    dict
        Dictionary of data extracted from input string. Keys present in
        returned dict depends on data found in input file and may be any from:
        freq, mass, frc, iri, dip, rot, emang, depolarp, depolaru,
        ramact, depp, depu, alpha2, beta2, alphag, gamma2, delta2, raman1,
        roa1, cid1, raman2, roa2, cid2,  raman3, roa3, cid3, rc180,
        wavelen, ex_en, eemang, vdip, ldip, vrot, lrot, vosc, losc, transitions,
        scf, zpe, ten, ent, gib, zpecorr, tencorr, entcorr, gibcorr, command,
        normal_termination, cpu_time, optimization_completed.

    Raises
    ------
    ValueError
        If no command line is found in input string.

    TO DO
    -----
    Add parsing of geometry-related data."""

    extr = {}
    cmd = command.search(text)
    if not cmd:
        raise ValueError("No command found in text.")
    extr["command"] = cmd.group()
    extr.update(_vibr_parse(text))
    extr.update(_electr_parse(text))
    logger.debug("final searches")
    scf_match = scf.findall(text)
    if scf_match:
        extr["scf"] = float(scf_match[-1])
    trmntn = termination.search(text)
    extr["normal_termination"] = True if trmntn else False
    # depreciated, as it is not important for tesliper to know this
    # and causes problems with Molecules.trim_inconsistent_sizes()
    # cpu_time = cpu_time_reg.findall(text)
    # if cpu_time:
    #     extr['cpu_time'] = cpu_time
    if "opt" in extr["command"].lower():
        extr["optimization_completed"] = "Optimization completed." in text
    stoichiometries = stoich.findall(text)
    if stoichiometries:
        extr["stoichiometry"] = stoichiometries[-1]
    return extr
