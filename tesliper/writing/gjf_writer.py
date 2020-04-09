# IMPORTS
import logging
from pathlib import Path
from string import Template
from typing import Iterable, Union, List

from ._writer import SerialWriter
from ..glassware import Geometry


# LOGGER
logger = logging.getLogger(__name__)


# CLASSES
class GjfWriter(SerialWriter):

    extension = "gjf"
    _link0_commands = {
        "Mem",  # str with file path
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
        link0: dict = {},
        route: Union[str, List[str]] = "",
        comment: str = "No information provided.",
        post_spec: str = "",
        filename_template: Union[str, Template] = "${filename}.${ext}",
    ):
        super().__init__(
            destination=destination, mode=mode, filename_template=filename_template
        )
        self.link0 = link0
        self.route = route
        self.comment = comment
        self.post_spec = post_spec

    def write(self, geometry, charge, multiplicity):
        for fname, coords, c, m in zip(geometry.filenames, geometry.values):
            pass

    def _write_conformer(self, filename, coords, c, m):
        path = self.destination.joinpath(filename)
        with path.open(self.mode) as file:
            for key, value in self.link0:
                if "save" in key:
                    file.write(f"%{self._link0_commands[key]}")
                else:
                    file.write(f"%{self._link0_commands[key]}={value}\n")
            file.write(self.route)
            file.write("\n")
            file.write(self.comment)
            file.write("\n")
            file.write(f"{c} {m}")
            for line in self._format_coords(coords):
                file.write(line)
            if self.post_spec:
                file.write("\n")
                file.write(self.post_spec)
            file.write("\n" * self.empty_lines_at_end)

    def _format_coords(self, coords):
        for a, x, y, z in coords:
            yield f" {a: <2} {x: > .7f} {y: > .7f} {z: > .7f}\n"

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
    def route(self):
        return " ".join(self._route)

    @route.setter
    def route(self, commands):
        try:
            commands = commands.split()
        except AttributeError:
            pass
        if commands[0] in "T N P".split():
            commands[0] = f"#{commands[0]}"
        elif commands[0] == "#" and commands[1] in "T N P".split():
            commands[:2] = f"#{commands[1]}"
        elif commands[0] != "#":
            commands = ["#"] + commands
        self._route = commands
