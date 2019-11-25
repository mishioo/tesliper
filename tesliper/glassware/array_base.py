# IMPORTS
import inspect
import logging as lgg
import numpy as np
from ..exceptions import InconsistentDataError


# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
class ArrayProperty(property):
    def __init__(
        self, fget=None, fset=None, fdel=None, doc=None, dtype=float, check_against=None
    ):
        super().__init__(fget=fget, fset=fset, fdel=fdel, doc=doc)
        self.dtype = dtype
        self.check_against = check_against

    def __set_name__(self, objtype, name):
        self.name = name

    def __set__(self, instance, values):
        values = self.check_input(instance, values)
        if self.fset is not None:
            self.fset(instance, values)
        else:
            vars(instance)[self.name] = values

    def __get__(self, instance, objtype=None):
        if instance is None:
            return self
        if self.fget is not None:
            return self.fget(instance)
        else:
            return vars(instance)[self.name]

    def __call__(self, fget):
        new = self.getter(fget)
        if self.__doc__ is None:
            new.__doc__ = fget.__doc__
        return new

    def getter(self, fget):
        return type(self)(
            fget, self.fset, self.fdel, self.__doc__, self.dtype, self.check_against
        )

    def setter(self, fset):
        return type(self)(
            self.fget, fset, self.fdel, self.__doc__, self.dtype, self.check_against
        )

    def deleter(self, fdel):
        return type(self)(
            self.fget, self.fset, fdel, self.__doc__, self.dtype, self.check_against
        )

    def check_input(self, instance, values):
        allow = getattr(instance, "allow_data_inconsistency", False)
        if self.check_against:
            length = len(getattr(instance, self.check_against))
            if not len(values) == length and not allow:
                raise ValueError(
                    f"{self.name} and {self.check_against} must be the same "
                    f"length. Arrays of length {len(values)} and {length} "
                    f"were given."
                )
        try:
            return np.array(values, dtype=self.dtype)
        except ValueError as error:
            genre = getattr(instance, "genre", "<unknown>")
            if "convert" in error.args[0]:
                raise
            elif not allow:
                error_msg = (
                    f"{instance.__class__.__name__} of genre "
                    f"{genre} with unequal number of values "
                    f"for molecule requested."
                )
                raise InconsistentDataError(error_msg) from error
            else:
                values = self._pad(values)
                logger.info(
                    f"{genre} values' lists were appended with zeros to "
                    f"match length of longest entry."
                )
                return values

    def _pad(self, values):
        lengths = [len(v) for v in values]
        longest = max(lengths)
        values = np.array(
            [
                np.pad(v, (0, longest - len_), "constant", constant_values=0)
                for v, len_ in zip(values, lengths)
            ],
            dtype=self.dtype,
        )
        return values


class ArrayBase:
    """Base class for data holding objects."""

    associated_genres = ()
    constructors = {}

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, "associated_genres"):
            raise AttributeError(
                "Class derived from ArrayBase should provide associated_genres"
                " attribute."
            )
        ArrayBase.constructors.update((genre, cls) for genre in cls.associated_genres)

    def __init__(self, genre, filenames, values, allow_data_inconsistency=False):
        self.genre = genre
        self.allow_data_inconsistency = allow_data_inconsistency
        self.filenames = filenames
        self.values = values

    @property
    def filenames(self):
        return self._filenames

    @filenames.setter
    def filenames(self, value):
        self._filenames = np.array(value, dtype=str)

    values = ArrayProperty(check_against="filenames")

    def get_repr_args(self):
        signature = inspect.signature(type(self))
        args = {
            name: getattr(self, name)
            if hasattr(self, name)
            else (param.default if param.default is not signature.empty else None)
            for name, param in signature.parameters.items()
        }
        return args

    @classmethod
    def get_init_params(cls):
        signature = inspect.signature(cls)
        return signature.parameters.copy()

    def __repr__(self):
        args = [
            f"{name}={repr(arg) if isinstance(arg, str) else arg}"
            for name, arg in self.get_repr_args().items()
        ]
        return f"{type(self).__name__}({', '.join(args)})"

    def __str__(self):
        return (
            f"[{type(self).__name__} of genre '{self.genre}', "
            f"{self.filenames.size} conformers]"
        )

    def __len__(self):
        return len(self.filenames)

    def __bool__(self):
        return self.filenames.size != 0
