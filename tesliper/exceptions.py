class TesliperError(Exception):
    """Base class for Exceptions used by tesliper library."""
    pass


class InconsistentDataError(TesliperError):
    """Raised to signalize problems with molecules' data consistency."""
    pass
