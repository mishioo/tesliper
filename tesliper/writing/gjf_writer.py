"""Export of Gaussian input files (.gjf) for setting up new calculation step."""
import logging
from itertools import cycle
from pathlib import Path
from string import Template
from typing import Dict, Iterable, List, Optional, Sequence, TextIO, Union

from ..datawork.atoms import symbol_of_element
from ..glassware import Geometry, IntegerArray
from .writer_base import WriterBase

# LOGGER
logger = logging.getLogger(__name__)


# FUNCTIONS
def _format_coordinates(coords: Sequence[Sequence[float]], atoms: Sequence[int]):
    for a, (x, y, z) in zip(atoms, coords):
        a = symbol_of_element(a)
        yield f" {a: <2} {x: > 12.8f} {y: > 12.8f} {z: > 12.8f}"


# CLASSES
class GjfWriter(WriterBase):
    """Generates Gaussian input files for each conformer given."""

    extension = "gjf"
    _link0_commands = {
        "Mem",  # str specifying required memory
        "Chk",  # str with file path
        "OldChk",  # str with file path
        "SChk",  # str with file path
        "RWF",  # str with file path
        "OldMatrix",  # str with file path
        "OldRawMatrix",  # str with file path
        "Int",  # str with spec
        "D2E",  # str with spec
        "KJob",  # str with link number and, optionally, space-separated number
        "Save",  # boolean
        "ErrorSave",  # boolean
        "NoSave",  # boolean, same as ErrorSave
        "Subst",  # str with link number and space-separated file path
    }
    _link0_commands = {k.lower(): k for k in _link0_commands}
    _parametrized = {
        "chk",
        "oldchk",
        "schk",
        "rwf",
        "oldmatrix",
        "oldrawmatrix",
        "subst",
    }
    empty_lines_at_end = 2

    def __init__(
        self,
        destination: Union[str, Path],
        mode: str = "x",
        link0: Optional[Dict[str, Union[str, bool]]] = None,
        route: str = "",
        comment: str = "No information provided.",
        post_spec: str = "",
    ):
        """
        Parameters
        ----------
        destination: str or pathlib.Path
            Directory, to which generated files should be written.
        mode: str, optional
            Specifies how writing to file should be handled. Should be one of
            characters: "a" (append to existing file); "x" (only write if file doesn't
            exist yet); or "w" (overwrite file if it already exists). Defaults to "x".
        link0 : Dict[str, Union[str, bool]], optional
            Link0 commands that should be included in generated files, as a dictionary
            of {"command": "value"}. Refer to :attr:`link0` for more information. If
            omitted, no link0 commands are added.
        route : str
            Calculation directives for Gaussan, refer to the Gaussian documentation for
            information on how to construct the calculations route.
        comment : str, optional
            Additional text, describing the calculations, by default "No information
            provided."
        post_spec : str, optional
            Additional specification written after the molecule specification, written
            to generated files as provided by the user (you need to take care of line
            breaks). If omitted, no additional specification is added.
        """
        super().__init__(destination=destination, mode=mode)
        self.link0 = link0 or {}
        self.route = route
        self.comment = comment
        self.post_spec = post_spec

    def geometry(
        self,
        geometry: Geometry,
        charge: Union[IntegerArray, Sequence[int], int, None] = None,
        multiplicity: Union[IntegerArray, Sequence[int], int, None] = None,
        name_template: Union[str, Template] = "${conf}.${ext}",
    ):
        """Write given conformers' geometries to multiple Gaussian input files.

        Parameters
        ----------
        geometry : Geometry
            :class:`.Geometry` object containing data for each confomer that should be
            exported as Gaussian input file.
        charge : Union[IntegerArray, Sequence[int], int, None], optional
            Molecule's charge for each conformer. May be a sequence of values or one
            value that will be repeated for each conformer. By default 0 for each.
        multiplicity : Union[IntegerArray, Sequence[int], int, None], optional
            Molecule's multiplicity for each conformer. May be a sequence of values or
            one value that will be repeated for each conformer. By default 1 for each.
        name_template : Union[str, Template], optional
            Template that will be used to generate filenames, by default
            "${conf}.${ext}". Refer to :meth:`.make_name` documentation for details on
            supported placeholders.
        """
        geom = geometry.values
        atoms = cycle(geometry.molecule_atoms)
        try:
            char = charge.values
        except AttributeError:
            char = (0,) if charge is None else charge
            char = [char] if not isinstance(char, Iterable) else char
        char = cycle(char)
        try:
            mult = multiplicity.values
        except AttributeError:
            mult = (1,) if multiplicity is None else multiplicity
            mult = [mult] if not isinstance(mult, Iterable) else mult
        mult = cycle(mult)
        template_params = {"genre": geometry.genre, "cat": "geometry"}
        for *params, handle in zip(
            geom,
            atoms,
            char,
            mult,
            self._iter_handles(geometry.filenames, name_template, template_params),
        ):
            self._write_conformer(handle, *params, template_params)

    def _write_conformer(
        self,
        file: TextIO,
        g: Sequence[Sequence[float]],
        a: Sequence[int],
        c: int,
        m: int,
        template_params: dict,
    ):
        for key, value in self.link0.items():
            key = key.lower()
            if key in self._parametrized:
                # template_params are updated bt _iter_handles
                # so we can simply reuse it
                value = self.make_name(template=value, **template_params)
            if "save" in key and value:
                file.write(f"%{self._link0_commands[key]}\n")
            else:
                file.write(f"%{self._link0_commands[key]}={value}\n")
        file.write(self.route)
        file.write("\n" * 2)
        file.write(self.comment)
        file.write("\n" * 2)
        file.write(f"{c} {m}")
        for line in _format_coordinates(g, a):
            file.write("\n" + line)
        if self.post_spec:
            file.write("\n\n")
            file.write(self.post_spec)
        file.write("\n" * self.empty_lines_at_end)

    @property
    def link0(self) -> Dict[str, Union[str, bool]]:
        """
        Link0 commands, in a form of ``{"command": "value"}``, that will be placed in
        the beginning of each Gaussian input file created. If anny *command* is an
        unknown keword, an exception will be raised. Accepted *command* keywords are as
        follows:

        :Mem: str specifying required memory
        :Chk: str with file path
        :OldChk: str with file path
        :SChk: str with file path
        :RWF: str with file path
        :OldMatrix: str with file path
        :OldRawMatrix: str with file path
        :Int: str with spec
        :D2E: str with spec
        :KJob: str with link number and, optionally, space-separated number
        :Save: boolean
        :ErrorSave: boolean
        :NoSave: boolean, same as ErrorSave
        :Subst: str with link number and space-separated file path

        Commands that provide a file path as a value may be parametrized for each
        conformer. You can put a placeholder inside a given string path, that will be
        parametrized when writing to file. See :meth:`.make_name` to see available
        placeholders. You may use any of values listed there, however ``${conf}`` and
        ``${num}`` will probably be the most useful.
        """
        return self._link0

    @link0.setter
    def link0(self, commands: Dict[str, Union[str, bool]]):
        unknown = {k for k in commands if k.lower() not in self._link0_commands}
        if unknown:
            raise ValueError(f"Unknown link 0 commands provided: {', '.join(unknown)}.")
        self._link0 = {k: v for k, v in commands.items() if v}

    @property
    def route(self) -> str:
        """Also known as *# lines*, specifies desired calculation type, model chemistry,
        and other options for Gaussian. If pound sign is missing, it is added in the
        beginning. For supported keywords and syntax refer to the Gaussian's
        documentation.
        """
        return " ".join(self._route)

    @route.setter
    def route(self, commands: str):
        try:
            commands_ = commands.split()
        except AttributeError as error:
            raise TypeError("Expected object of type str.") from error
        length = len(commands_)
        if not length:
            commands_ = ["#"]
        else:
            first = commands_[0]
            if not first.startswith("#"):
                commands_ = ["#"] + commands_
        self._route = commands_
