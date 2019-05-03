# IMPORTS
import logging as lgg
import numpy as np
from ..exceptions import InconsistentDataError


# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
class ArrayProperty(property):

    def __init__(
            self, fget=None, fset=None, fdel=None, doc=None, dtype=float,
            check_against=None
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
            fget, self.fset, self.fdel, self.__doc__, self.dtype,
            self.check_against
        )

    def setter(self, fset):
        return type(self)(
            self.fget, fset, self.fdel, self.__doc__, self.dtype,
            self.check_against
        )

    def deleter(self, fdel):
        return type(self)(
            self.fget, self.fset, fdel, self.__doc__, self.dtype,
            self.check_against
        )

    def check_input(self, instance, values):
        if self.check_against:
            length = len(getattr(instance, self.check_against))
            if not len(values) == length:
                raise ValueError(
                    f"Values and {self.check_against} must be the same length. "
                    f"Arrays of length {len(values)} and {length} were given."
                )
        try:
            return np.array(values, dtype=self.dtype)
        except ValueError:
            if not instance.allow_data_inconsistency:
                error_msg = f"{instance.__class__.__name__} of genre " \
                            f"{instance.genre} with unequal number of values " \
                            f"for molecule requested."
                raise InconsistentDataError(error_msg)
            lengths = [len(v) for v in values]
            longest = max(lengths)
            _values = np.array(
                [np.pad(v, (0, longest-len_), 'constant', constant_values=0)
                    for v, len_ in zip(values, lengths)], dtype=self.dtype
            )
            logger.info(
                f"{instance.genre} values' lists were appended with zeros to "
                f"match length of longest entry."
            )
            return _values


class ArrayBase:
    """Base class for data holding objects."""

    associated_genres = ()
    constructors = {}

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, 'associated_genres'):
            raise AttributeError(
                'Class derived from ArrayBase should provide associated_genres'
                ' attribute.'
            )
        ArrayBase.constructors.update(
            (genre, cls) for genre in cls.associated_genres
        )

    def __init__(
            self, genre, filenames, values, allow_data_inconsistency=False
    ):
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

    values = ArrayProperty(check_against='filenames')

    def __len__(self):
        return len(self.filenames)

    def __bool__(self):
        return self.filenames.size != 0
