class TesliperError(Exception):
    """Base class for Exceptions used by tesliper library."""

    pass


class InconsistentDataError(TesliperError):
    """Raised to signalize problems with molecules' data consistency.
    Subclasses TesliperError."""

    pass


class InvalidStateError(TesliperError, ValueError):
    """Used by Parser class to signalize problems when handling states.
    Subclasses TesliperError and ValueError."""

    pass


class InvalidElementError(TesliperError, ValueError):
    """Used by tesliper to indicate, that value cannot be interpreted as an
     element. Subclasses TesliperError and ValueError."""

    pass
