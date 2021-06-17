from configparser import ConfigParser, MissingSectionHeaderError, ParsingError
from pathlib import Path


class ParametersParser(ConfigParser):

    ALIASES = {
        "half width of band in half height": "width",
        "hwhm": "width",
        "start range": "start",
        "stop range": "stop",
        "fitting function": "fitting",
    }

    DEFAULTS = {}

    def optionxform(self, optionstr: str) -> str:
        optionstr = optionstr.lower()
        if optionstr in self.ALIASES:
            optionstr = self.ALIASES[optionstr]
        return optionstr

    def parse(self, source):
        source = Path(source)
        with source.open() as handle:
            text = handle.read()
        try:
            self.read_string(text)
        except MissingSectionHeaderError:
            self.read_string("[PARAMETERS]\n")
        if len(self.sections()) > 1:
            raise ParsingError(
                "Multiple sections in parameters setup file are not supported."
            )
        params = self[self.sections()[0]]
        return {key: self.transformers[key](value) for key, value in params.items()}

    _transformers = {}

    @property
    def transformers(self):
        # TODO: modify converters and use it to implement functionality for converting
        #       to floats when not only number in value and to get lorentzian
        #       and gaussian functions instead of strings
        return self._transformers
