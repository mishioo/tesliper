"""Paser for Gaussian output files."""
import logging as lgg
import re

from .parser_base import ParserBase

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.INFO)

# REGEXS
number_group = r"\s*(-?\d+\.?\d*)"
number = number_group.replace("(", "").replace(")", "")

TERMINATION_CRE = re.compile(r"Normal termination.*\n\Z")
SCF_CRE = re.compile(r"SCF Done.*?=" + number_group)  # use .search(line).group(1)
STOICH_CRE = re.compile(r"^ Stoichiometry\s*(\w*(?:\(\d+[+-]?,?\d*\))?)\n")

GEOM_LINE_CRE = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+)" + 3 * number_group)

# VIBRATIONAL
vibr_genre = {
    "Frequencies": "freq",
    "Red. masses": "mass",
    "Frc consts": "frc",
    "IR Inten": "iri",
    "Dip. str.": "dip",
    "Rot. str.": "rot",
    "E-M angle": "emang",
    "Depolar (P)": "depolarp",
    "Depolar (U)": "depolaru",
    "RamAct": "ramact",
    "Raman Activ": "ramanactiv",
    "Dep-P": "depp",
    "Dep-U": "depu",
    "Alpha2": "alpha2",
    "Beta2": "beta2",
    "AlphaG": "alphag",
    "Gamma2": "gamma2",
    "Delta2": "delta2",
    "Raman1": "raman1",
    "ROA1": "roa1",
    "CID1": "cid1",
    "Raman2": "raman2",
    "ROA2": "roa2",
    "CID2": "cid2",
    "Raman3": "raman3",
    "ROA3": "roa3",
    "CID3": "cid3",
    "RC180": "rc180",
}

VIBRATIONAL_CRE = re.compile(
    r"^\s\s?([a-zA-Z.\-]+[0-9]*(?:\s?[a-zA-Z.()]+)?)\s*(?:(?:Fr= \d+)?--)"
    + 3 * number_group
)

# ELECTRONIC
EXCITED_CRE = re.compile(
    r"^ Excited State\s+\d+:[a-zA-Z\-\s\'\"]*(-?\d+\.?\d*) eV\s+(-?\d+\.?\d*) nm"
)
TRANSITIONS_CRE = re.compile(r"(\d+)\s*->\s*(\d+)\s+(-?\d+\.\d+)")
numbers = 4 * number + 2 * number_group + r"?\n"
NUMBERS_CRE = re.compile(numbers)


# CLASSES
class GaussianParser(ParserBase):
    """Parser for extracting data from human-readable output files from Gaussian
    computational chemistry software (.log and .out files).

    This class implements methods for reading information about conducted calculations'
    parameters, molecule energy, structure optimization, and calculation of spectral
    properties. It's use is as straightforward as:

    >>> parser = GaussianParser()
    >>> with open('path/to/file.out') as file:
    >>>     data = parser.parse(file)

    Dictionary with data extracted is also stored as :attr:`.data` attribute of instance
    used for parsing. Each key in said dictionary is a name of its value data type,
    called from now on a 'data genre' (to avoid confusion with Python's data type).
    Below is a full list of data genres recognized by this parser, with their
    description:

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
    transitions : list of lists of lists of (int, int, float), available from td job
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
    charge : int, always available
        molecule's charge
    multiplicity : int, always available
        molecule's spin multiplicity
    input_atoms : list of str, always available
        input atoms as a list of atoms' symbols
    input_geom : list of lists of floats, always available
        input geometry as X, Y, Z coordinates of atoms
    stoichiometry : str, always available
        molecule's stoichiometry
    last_read_atoms : list of ints, always available
        molecule's atoms as atomic numbers
    last_read_geom : list of lists of floats, always available
        molecule's geometry (last one found in file) as X, Y, Z coordinates of atoms
    optimized_atoms : list of ints, available from successful opt job
        molecule's atoms read from optimized geometry as atomic numbers
    optimized_geom : list of lists of floats, available from successful opt job
        optimized geometry as X, Y, Z coordinates of atoms

    Attributes
    ----------
    data : dict
        Data extracted during last parsing."""

    purpose = "gaussian"

    def __init__(self):
        super().__init__()
        self._iterator = iter([])
        self.data = {}

    def parse(self, lines) -> dict:
        """Parses content of Gaussian output file and returns dictionary of found data.

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
        # TODO: supplement docstring
        self.workhorse = self.initial
        self.data = {}
        self._iterator = iter(lines)
        try:
            for line in self._iterator:
                self.workhorse(line)
        except StopIteration:
            filename = getattr(self._iterator, "name", None)
            filename = f'"{filename}" file' if filename else None
            logger.info(
                f"Unexpected stop of iteration occurred while parsing "
                f"{filename or self._iterator}. Job didn't finish or content may be "
                f"corrupted."
            )
            self.data["normal_termination"] = False
        return self.data

    @ParserBase.state
    def initial(self, line: str) -> None:
        """First step of parsing Gaussian output file. It populates parser.data
        dictionary with these data genes: 'normal_termination', 'version', 'command',
        'charge', 'multiplicity', 'input_geom'. Optionally, 'optimization_completed'
        genre is added if optimization was requested in calculation job.

        Parameters
        ----------
        line : str
            Line of text to parse."""
        data, iterator = self.data, self._iterator
        # assume error termination until output file says otherwise
        data["normal_termination"] = False
        while not line == " Cite this work as:\n":
            line = next(iterator)
        data["version"] = next(iterator).strip(" \n,")
        while not line.startswith(" #"):
            line = next(iterator)
        command = []
        while not line.startswith(" --"):
            command.append(line.strip("# \n"))
            line = next(iterator)
        command = data["command"] = " ".join(command)
        if "opt" in command:
            data["optimization_completed"] = False
        while not line == " Symbolic Z-matrix:\n":
            line = next(iterator)
        c_and_m = re.match(r" Charge =\s*(-?\d) Multiplicity = (\d)", next(iterator))
        data["charge"], data["multiplicity"] = map(int, c_and_m.groups())
        line = next(iterator).strip()
        input_geom = []
        pattern = r"(\w+)" + 3 * number_group
        while line:  # reads symbolic Z-matrix
            atom = re.match(pattern, line)
            label, *coordinates = atom.groups()
            input_geom.append([label, list(map(float, coordinates))])
            line = next(iterator).strip()
        data["input_atoms"], data["input_geom"] = map(list, zip(*input_geom))
        self.workhorse = self.wait

    @ParserBase.state
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
        elif "Normal termination" in line:
            self.data["normal_termination"] = True
        elif line.startswith(" SCF Done:"):
            self.data["scf"] = float(SCF_CRE.search(line).group(1))
        elif line.startswith(" Stoichiometry"):
            self.data["stoichiometry"] = STOICH_CRE.match(line).group(1)
        elif "Proceeding to internal job step number" in line:
            # last job determines if termination was normal
            self.data["normal_termination"] = False

    @ParserBase.state(trigger=re.compile(r"^\s+Standard orientation"))
    def geometry(self, line: str) -> None:
        """Function for extracting information about molecule standard orientation
        geometry from Gaussian output files. It updates parser.data dictionary with
        'last_read_atoms' and 'last_read_geom' data genres.

        Parameters
        ----------
        line : str
            Line of text to parse."""
        data, iterator = self.data, self._iterator
        match = GEOM_LINE_CRE.match(line)
        while not match:
            line = next(iterator)
            match = GEOM_LINE_CRE.match(line)
        geom = []
        while match:
            geom.append(match.groups())
            line = next(iterator)
            match = GEOM_LINE_CRE.match(line)
        geom = ((int(a), [float(x), float(y), float(z)]) for _, a, _, x, y, z in geom)
        # produce list and list of lists instead of tuple and tuple of lists
        data["last_read_atoms"], data["last_read_geom"] = map(list, zip(*geom))
        self.workhorse = self.wait

    @ParserBase.state(trigger=re.compile("^ Search for a local minimum."))
    def optimization(self, line: str) -> None:
        """This method scans optimization data in Gaussian output file, updating
        parser.data dictionary with 'stoichiometry', 'scf', 'optimization_completed',
        'optimized_atoms', and 'optimized_geom' data genres (last two via
        :meth:`.geometry` method).

        Parameters
        ----------
        line : str
            Line of text to parse.
        """
        # TODO: modify this to only run if optimization requested
        if self.triggers["geometry"].match(line):
            self.geometry(line)
            self.workhorse = self.optimization
        elif line.startswith(" Stoichiometry"):
            self.data["stoichiometry"] = STOICH_CRE.match(line).group(1)
        elif line.startswith(" SCF Done:"):
            self.data["scf"] = float(SCF_CRE.search(line).group(1))
        elif line.startswith(" Optimization completed."):
            self.data["optimization_completed"] = True
            if "optimized_geom" not in self.data:
                self.data["optimized_geom"] = self.data["last_read_geom"]
                self.data["optimized_atoms"] = self.data["last_read_atoms"]
        elif line.startswith(" Error termination"):
            self.data["normal_termination"] = False
        if line.startswith((" Error termination", " Job cpu time")):
            self.workhorse = self.wait

    @ParserBase.state(trigger=re.compile("^ Harmonic frequencies"))
    def frequencies(self, line: str) -> None:
        """Responsible for extracting harmonic vibrations-related data and information
        about molecule's energy.

        Parameters
        ----------
        line : str
            Line of text to parse."""
        data, iterator = self.data, self._iterator
        while not line == "\n":
            # while frequencies section is not over
            match = VIBRATIONAL_CRE.match(line)
            while match:
                # unpack values from current line to list of corresponding genre
                name, *values = match.groups()
                genre = vibr_genre[name]  # convert gaussian line name to genre
                data.setdefault(genre, list()).extend(float(x) for x in values)
                line = next(iterator)
                match = VIBRATIONAL_CRE.match(line)
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
        iterator = self._iterator
        while not line.startswith(" Excited State"):
            line = next(iterator)
        # map obj unpacked in calling method
        out = [map(float, EXCITED_CRE.match(line).groups())]
        while line.strip():
            line = next(iterator)
            match = TRANSITIONS_CRE.search(line)
            if match:
                out.append(match.groups())
        return out

    @ParserBase.state(trigger=re.compile("^ Excited states from"))
    def excited(self, line: str) -> None:
        """Responsible for extracting electronic transitions-related data from Gaussian
        output file. Updates parser.data dictionary with 'ldip', 'losc', 'vdip', 'vosc',
        'vrot', 'eemang', 'lrot', 'wavelen', 'ex_en', and 'transitions' data genres.

        Parameters
        ----------
        line : str
            Line of text to parse."""
        data, iterator = self.data, self._iterator
        for genres, header in (
            (("ldip", "losc"), "electric dipole"),
            (("vdip", "vosc"), "velocity dipole"),
            (("vrot", "eemang"), "Rotatory Strengths"),
            (("lrot", ""), "Rotatory Strengths"),
        ):
            while header not in line:
                line = next(iterator)
            next(iterator)  # skip column names
            match = NUMBERS_CRE.search(next(iterator))
            values = []
            while match:
                values.append(float(x) if x else None for x in match.groups())
                line = next(iterator)
                match = NUMBERS_CRE.search(line)
            for genre, values in zip(genres, zip(*values)):
                if genre:
                    data[genre] = values
        while not line.startswith(" **"):
            (energy, wavelen), *transitions = self._excited_states(line)
            data.setdefault("wavelen", []).append(wavelen)
            data.setdefault("ex_en", []).append(energy)
            data.setdefault("transitions", []).append(
                [[int(low), int(high), float(coef)] for low, high, coef in transitions]
            )
            line = next(iterator)
        self.workhorse = self.wait
