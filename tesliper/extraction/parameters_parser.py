from configparser import ConfigParser, MissingSectionHeaderError, ParsingError
from pathlib import Path
from typing import Callable, Union
import re
import logging

from .. import datawork as dw


logger = logging.getLogger(__name__)

# from Python re docs
FLOATCRE = re.compile(r"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?")
FITTINGCRE = re.compile(r"lorentzian|gaussian")


def quantity(s: str) -> float:
    """Convert to float first occurrence of float-looking part of string `s`,
    ignoring anything else. Raise `configparser.ParsingError` if float cannot be found.

    Parameters
    ----------
    s : str
        string containing a float

    Returns
    -------
    float
        extracted float value
    """
    match = FLOATCRE.search(s)
    if match:
        return float(match.group())
    else:
        raise ParsingError("Cannot interpret any part of given string as float.")


def fitting(s: str) -> Callable:
    """Get fitting function mentioned in a given string `s`, ignoring anything else.
    Raise `configparser.ParsingError` if known function name cannot be found.

    Parameters
    ----------
    s : str
        string containing name of fitting function

    Returns
    -------
    callable
        an identified fitting function
    """
    match = FITTINGCRE.search(s.lower())
    try:
        return getattr(dw, match.group())
    except AttributeError:
        raise ParsingError(f"No such fitting function: {s}.")


class ParametersParser(ConfigParser):
    """Parser for configuration files containing spectra calculation parameters.

    Configuration file should be in format similar to .ini files: a list of key-value
    pairs, separated with "=" or ":", one pair for line. Standard parameters (width,
    start, stop, step, and fitting) will be converted to appropriate data type, i.e.
    float or function reference. If parameter value cannot be converted to its
    target type, it will be ignored and warning will be emitted. Any other (unexpected)
    parameters are included in the output and left as they are.

    The parser is case-insensitive and knows some alias names of expected parameters:
    for instance, "hwhm", "half width of band in half height", "half width at half
    maximum" will be all recognised as "width" parameter. If you wish to add custom
    aliases, update `ParametersParser.ALIASES` dictionary with appropriate
    "alias": "target" pair.

    Notes
    -----
    ParametersParser is based on Python's configparser, so it will parse files that
    contain a section header, enclosed in braces. However, the section name will be
    ignored and there may be only one such section header, otherwise an exception is
    raised.
    """

    ALIASES = {
        "half width of band in half height": "width",
        "half width at half maximum": "width",
        "hwhm": "width",
        "start range": "start",
        "stop range": "stop",
        "fitting function": "fitting",
    }

    def __init__(self):
        super().__init__(converters={"quantity": quantity, "fitting": fitting})
        self._transformers = {
            "width": self.getquantity,
            "start": self.getquantity,
            "stop": self.getquantity,
            "step": self.getquantity,
            "fitting": self.getfitting,
        }

    def optionxform(self, optionstr: str) -> str:
        """Translates option names to desired form - lowercase and standard wording,
        as defined in ALIASES.
        """
        optionstr = optionstr.lower()
        if optionstr in self.ALIASES:
            optionstr = self.ALIASES[optionstr]
        return optionstr

    @property
    def parameters(self) -> dict:
        """Dictionary of parameters for calculating spectra extracted from parsed file
        and converted to appropriate type."""
        if len(self.sections()) > 1:
            raise ParsingError(
                "Multiple sections in parameters setup file are not supported."
            )
        params = {}
        try:
            section = self.sections()[0]
        except IndexError:
            return params
        for option in self.options(section):
            try:
                params[option] = self._transformers[option](section, option)
            except ParsingError:
                logger.warning(
                    f"Cannot understand value for {option}, it will be ignored."
                )
            except KeyError:
                logger.warning(
                    f"Unknown parameter in settings: '{option}',"
                    f" it will not be converted."
                )
                params[option] = self.get(section, option)
        return params

    def parse(self, source: Union[str, Path]):
        """Parse given source file to get stored parameters.

        Parameters
        ----------
        source : str or Path
            Path to file with calculations' parameters.

        Returns
        -------
        dict
            Parsed parameters.
        """
        source = Path(source)
        with source.open() as handle:
            text = handle.read()
        try:
            self.read_string(text)
        except MissingSectionHeaderError:
            self.read_string(f"[PARAMETERS]\n{text}")
        return self.parameters
