# IMPORTS
import logging
from itertools import cycle
from pathlib import Path
from typing import Iterable, List, Sequence, TextIO, Union

from ..datawork.atoms import symbol_of_element
from ..glassware import Geometry, IntegerArray
from ._writer import Writer

# LOGGER
logger = logging.getLogger(__name__)


# FUNCTIONS
def _format_coordinates(coords: Sequence[Sequence[float]], atoms: Sequence[int]):
    for a, (x, y, z) in zip(atoms, coords):
        a = symbol_of_element(a)
        yield f" {a: <2} {x: > 12.8f} {y: > 12.8f} {z: > 12.8f}\n"


# CLASSES
class GjfWriter(Writer):
    """"""

    # TODO: Add per-file parametrization of link0 commands

    extension = "gjf"
    default_template = "${conf}.${ext}"
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
    empty_lines_at_end = 2

    def __init__(
        self,
        destination: Union[str, Path],
        mode: str = "x",
        link0: dict = None,
        route: Union[str, List[str]] = "",
        comment: str = "No information provided.",
        post_spec: str = "",
    ):
        super().__init__(destination=destination, mode=mode)
        self.link0 = link0 or {}
        self.route = route
        self.comment = comment
        self.post_spec = post_spec

    def geometry(
        self,
        geometry: Geometry,
        charge: Union[IntegerArray, Sequence[int], int] = (0,),
        multiplicity: Union[IntegerArray, Sequence[int], int] = (1,),
    ):
        geom = geometry.values
        atoms = cycle(geometry.molecule_atoms)
        try:
            char = charge.values
        except AttributeError:
            char = [charge] if not isinstance(charge, Iterable) else charge
        char = cycle(char)
        try:
            mult = multiplicity.values
        except AttributeError:
            mult = (
                [multiplicity]
                if not isinstance(multiplicity, Iterable)
                else multiplicity
            )
        mult = cycle(mult)
        for handle, *params in zip(
            self._iter_handles(geometry.filenames, geometry.genre),
            geom,
            atoms,
            char,
            mult,
        ):
            self._write_conformer(handle, *params)

    def _write_conformer(
        self,
        file: TextIO,
        g: Sequence[Sequence[float]],
        a: Sequence[int],
        c: int,
        m: int,
    ):
        for key, value in self.link0.items():
            if "save" in key:
                file.write(f"%{self._link0_commands[key]}\n")
            else:
                file.write(f"%{self._link0_commands[key]}={value}\n")
        file.write(self.route)
        file.write("\n" * 2)
        file.write(self.comment)
        file.write("\n" * 2)
        file.write(f"{c} {m}\n")
        for line in _format_coordinates(g, a):
            file.write(line)
        if self.post_spec:
            file.write("\n")
            file.write(self.post_spec)
            file.write("\n")
        file.write("\n" * (self.empty_lines_at_end - 1))

    @property
    def link0(self):
        return self._link0

    @link0.setter
    def link0(self, commands):
        unknown = {k for k in commands if k.lower() not in self._link0_commands}
        if unknown:
            raise ValueError(f"Unknown link 0 commands provided: {', '.join(unknown)}.")
        self._link0 = {k: v for k, v in commands.items() if v}

    @property
    def route(self) -> str:
        return " ".join(self._route)

    @route.setter
    def route(self, commands: Union[Sequence[str], str]):
        try:
            commands = commands.split()
        except AttributeError:
            logger.debug(
                "Given object has no `split` method - "
                "I'm asssuming it is of type Sequence other than str."
            )
        try:
            length = len(commands)
        except AttributeError as error:
            raise TypeError(
                "Expected object of type str or Sequence of str."
            ) from error
        if not length:
            commands = ["#"]
        else:
            try:
                first = commands[0]
            except (KeyError, TypeError) as error:
                raise TypeError(
                    "Expected object of type str or Sequence of str."
                ) from error
            try:
                if not first.startswith("#"):
                    commands = ["#"] + commands
            except AttributeError as error:
                raise TypeError(
                    "Expected object of type str or Sequence of str."
                ) from error
        self._route = commands
