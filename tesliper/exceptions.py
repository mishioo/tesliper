class TesliperError(Exception):
    """Base class for Exceptions used by tesliper library."""
    pass


class VariousMoleculesError(TesliperError):
    """Raised to signalize problems with molecules consistency."""
    pass
