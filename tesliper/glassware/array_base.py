# IMPORTS
import inspect
import logging as lgg
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import numpy as np

from ..exceptions import InconsistentDataError

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# FUNCTIONS
NestedSequence = Sequence[Union[Any, "NestedSequence"]]


def longest_subsequences(sequences: NestedSequence) -> Tuple[int, ...]:
    """Finds lengths of longest subsequences on each level of given nested sequence.
    Each subsequence should have same number of nesting levels.

    Parameters
    ----------
    sequences : sequence [of sequences [of...]]
        Arbitrarily deep, nested sequence of sequences.

    Returns
    -------
    tuple of ints
        Length of the longest subsequence for each nesting level as a tuple.

    Notes
    -----
    If nesting level in not identical in all subsequences, lengths are reported
    up to first level of non-iterable elements.

    >>> longest_subsequences([[[1, 2]], [[1], 2]])
    (2,)

    Examples
    --------
    >>> longest_subsequences([[[1, 2]], [[1]]])
    (1, 2)
    >>> longest_subsequences([[[1, 2]], [[1], [1], [1]]])
    (3, 2)
    """
    try:
        if any(isinstance(v, str) for v in sequences):
            raise TypeError
        lenghts = [len(v) for v in sequences]
        longest = max(lenghts)
    except (TypeError, ValueError):
        return ()
    try:
        other = longest_subsequences([i for v in sequences for i in v])
    except TypeError:
        return (longest,)  # tuple
    return (longest, *other)


def find_best_shape(jagged: NestedSequence) -> Tuple[int, ...]:
    """Find shape of an array, that could fit arbitrarily deep, jagged, nested sequence
    of sequences. Reported size for each level of nesting is the length of the longest
    subsequence on this level.

    Parameters
    ----------
    jagged : sequence [of sequences [of...]]
        Arbitrarily deep, nested sequence of sequences.

    Returns
    -------
    tuple of ints
        Length of the longest subsequence for each nesting level as a tuple.

    Notes
    -----
    If nesting level in not identical in all subsequences, size is reported
    up to first level of non-iterable elements.

    >>> find_best_shape([[[1, 2]], [[1], 2]])
    (2, 2)

    Examples
    --------
    >>> find_best_shape([[[1, 2]], [[1]]])
    (2, 1, 2)
    >>> find_best_shape([[[1, 2]], [[1], [1], [1]]])
    (2, 3, 2)
    """
    return (len(jagged), *longest_subsequences(jagged))


def flatten(items: NestedSequence, depth: Optional[int] = None) -> Iterator:
    """Yield items from any nested iterable as chain of values up to given `depth`.
    If `depth` is `None`, yielded sequence is completely flat.

    Parameters
    ----------
    items : NestedSequence
        Arbitrarily deep, nested sequence of sequences.
    depth : int, optional
        How deep should fattening be.

    Yields
    ------
    Any
        Values from `items` as flatted sequence."""
    depth = float("inf") if depth is None else depth
    for x in items:
        should_iter = isinstance(x, Iterable) and not isinstance(x, (str, bytes))
        if should_iter and depth > 1:
            yield from flatten(x, depth - 1)
        else:
            yield x


def _mask(jagged: NestedSequence, shape: tuple) -> np.ndarray:
    """A workhorse of `mask` function, see there.

    Parameters
    ----------
    jagged : sequence [of sequences [of...]]
        Arbitrarily deep, nested sequence of sequences.
    shape : tuple of int
        Shape of an array that would fit `jagged`.

    Returns
    -------
    numpy.array
    Array of booleans, of given shape, indicating if value of same index exist
    in `jagged`.

    Notes
    -----
    Current implementation does not support shapes other than best fitting
    (see `find_best_shape`).
    """
    if len(shape) == 0:
        mask = np.array([])
    elif len(shape) == 1:
        mask = np.arange(shape[0]) < len(jagged)
    else:
        jagged = [_mask(v, shape[1:]) for v in jagged]
        padding = ((0, shape[0] - len(jagged)),) + ((0, 0),) * (len(shape) - 1)
        mask = np.pad(jagged, padding, "constant", constant_values=False)
    return mask


def mask(jagged: NestedSequence) -> np.ndarray:
    """Returns a numpy.array of booleans, of shape that best fits given jagged nested
    sequence `jagged`. Each boolean value of the output indicates if corresponding value
    exists in `jagged`.

    Parameters
    ----------
    jagged : sequence [of sequences [of...]]
        Arbitrarily deep, nested sequence of sequences.

    Returns
    -------
    numpy.array of bool
        Array of booleans, of shape that best fits `jagged`, indicating if value of
        same index exist in `jagged`.

    Notes
    -----
    To use output as a mask of numpy.ma.masked_array, it should be inverted.
    >>> np.ma.array(values, mask=~mask(jagged))

    Examples
    --------
    >>> mask([[1, 2], [1]])
    array([[True, True], [True, False]])
    >>> mask([[1, 2], []])
    array([[True, True], [False, False]])
    >>> mask([[[1], []], [[2, 3]]])
    array([[[True, False], [False, False]], [[True, True], [False, False]]])

    """
    return _mask(jagged, find_best_shape(jagged))


def to_masked(
    jagged: NestedSequence,
    dtype: Optional[type] = None,
    fill_value: Optional[Any] = None,
) -> np.ma.core.MaskedArray:
    """Convert jagged, arbitrarily deep, nested sequence to numpy.ma.masked_array
    with missing entries masked.

    Parameters
    ----------
    jagged : sequence [of sequences [of...]]
        Arbitrarily deep, nested sequence of sequences.
    dtype : type, optional
        Data type of the output. If `dtype` is `None`, the type of the data is figured
        out by numpy machinery.
    fill_value : scalar, optional
        Value used to fill in the masked values when necessary. If `None`, a default
        based on the data-type is used.

    Returns
    -------
    numpy.ma.core.MaskedArray
        Given `jagged` converted to numpy.ma.masked_array with missing entries masked.

    Raises
    ------
    ValueError
        If jagged sequence has inconsistent number of dimensions.

    Examples
    --------
    >>> to_masked([[1, 2], [1]])
    array(data=[[1, 2], [1, --]], mask=[[True, True], [True, False]])
    >>> to_masked([1, [1]])
    Traceback (most recent call last):
    ValueError: Cannot convert to masked array: jagged sequence has inconsistent
    number of dimensions.
    """
    if not jagged:
        return np.ma.array([])
    array, shape, done, lengths = jagged, (len(jagged),), False, []
    while not done:
        # iterate over each level of nesting, accumulating partially flatted array
        each_is_vector = all(
            isinstance(x, Iterable) and not isinstance(x, (str, bytes)) for x in array
        )
        each_is_scalar = all(
            not isinstance(x, Iterable) or isinstance(x, (str, bytes)) for x in array
        )
        if each_is_vector:
            # if each entry is vector, find these vectors' length
            lengths = [len(x) for x in array]
            # longest vector defines current dimension's shape
            shape = shape + (max(lengths),)
            # flatten one level
            array = [v for x in array for v in x]
        elif each_is_scalar:
            # if each entry is scalar, we're done
            done = True
        else:
            # if scalar and vector entries mixed, we raise an error
            raise ValueError(
                "Cannot convert to masked array: jagged sequence has inconsistent "
                "number of dimensions."
            )
    mask = _mask(jagged, shape)
    output = np.ma.zeros(shape, dtype=dtype)
    # fill output with values
    output[mask] = array
    # mask for numpy.ma.masked_array must be inverted (`True` masks value)
    return np.ma.array(output, mask=~mask, dtype=dtype, fill_value=fill_value)


# CLASSES
class ArrayProperty(property):
    """
    Property, that validates value given to its setter and stores it as a numpy.ndarray.
    """

    # TODO: supplement documentation with in-depth explanation
    def __init__(
        self,
        fget: Optional[Callable[[Any], np.ndarray]] = None,
        fset: Optional[Callable[[Any, Sequence], None]] = None,
        fdel: Optional[Callable[[Any], None]] = None,
        doc: str = None,
        dtype: type = float,
        check_against: Optional[str] = None,
        check_depth: int = 1,
        fill_value: Any = 0,
        fsan: Optional[Callable[[Sequence], Sequence]] = None,
    ):
        super().__init__(fget=fget, fset=fset, fdel=fdel, doc=doc)
        self.dtype = dtype
        self.check_against = check_against
        self.check_depth = check_depth
        self.fill_value = fill_value
        self.fsan = fsan

    def __set_name__(self, objtype, name):
        self.name = name

    def __set__(self, instance, values):
        if self.fsan is not None:
            values = self.fsan(values)
        values = self.check_input(instance, values)
        if self.fset is not None:
            super().__set__(instance, values)
        else:
            vars(instance)[self.name] = values

    def __get__(self, instance, objtype=None):
        if instance is None:
            return self
        if self.fget is not None:
            return super().__get__(instance)
        else:
            return vars(instance)[self.name]

    def __call__(self, fget):
        new = self.getter(fget)
        if self.__doc__ is None:
            new.__doc__ = fget.__doc__
        return new

    def getter(self, fget: Optional[Callable[[Any], Sequence]]):
        """Descriptor to change the getter on an ArrayProperty."""
        return type(self)(
            fget,
            self.fset,
            self.fdel,
            self.__doc__,
            self.dtype,
            self.check_against,
            self.fill_value,
            self.fsan,
        )

    def setter(self, fset: Optional[Callable[[Any, Sequence], None]]):
        """Descriptor to change the setter on an ArrayProperty."""
        return type(self)(
            self.fget,
            fset,
            self.fdel,
            self.__doc__,
            self.dtype,
            self.check_against,
            self.fill_value,
            self.fsan,
        )

    def deleter(self, fdel: Optional[Callable[[Any], None]]):
        """Descriptor to change the deleter on an ArrayProperty."""
        return type(self)(
            self.fget,
            self.fset,
            fdel,
            self.__doc__,
            self.dtype,
            self.check_against,
            self.fill_value,
            self.fsan,
        )

    def sanitizer(self, fsan: Optional[Callable[[Sequence], Sequence]]):
        """Descriptor to change the sanitizer on an ArrayProperty. Function given as
        parameter should take one positional argument and return sanitized values.
        If any sanitizer is provided, it is always called with `values` given to
        ArrayProperty setter. Sanitation is performed before `.check_input()`
        is called."""
        return type(self)(
            self.fget,
            self.fset,
            self.fdel,
            self.__doc__,
            self.dtype,
            self.check_against,
            self.fill_value,
            fsan,
        )

    def check_shape(self, instance: Any, values: Sequence):
        """Raises an error if `values` have different shape than attribute specified
        as`check_against`.
        """
        allow = getattr(instance, "allow_data_inconsistency", False)
        if self.check_against:
            attr_value = getattr(instance, self.check_against)
            try:
                ref_shape = attr_value.shape
            except AttributeError:
                ref_shape = find_best_shape(attr_value)
            best_shape = find_best_shape(values)
            shapes_same = (
                ref_shape[: self.check_depth] == best_shape[: self.check_depth]
            )
            if not shapes_same and not allow:
                raise ValueError(
                    f"{self.name} and {self.check_against} must have the same shape "
                    f"up to {self.check_depth} dimensions. Arrays of shape "
                    f"{best_shape} and {ref_shape} were given."
                )

    def check_input(self, instance: Any, values: Sequence) -> np.ndarray:
        """Checks if `values` given to setter have same length as attribute specified
        with `check_against`.

        Parameters
        ----------
        instance
            Instance of owner class.
        values
            Values to validate.

        Returns
        -------
        numpy.ndarray
            Validated values.

        Raises
        ------
        ValueError
            If `array_property.check_against` is not None and list of given values
            have different length than getattr(`instance`,
            `array_property.check_against`).
            If given list of values cannot be converted to `array_property.dtype` type.
        InconsistentDataError
            If `values` is list of lists of varying size and instance doesn't allow
            data inconsistency.
        """
        self.check_shape(instance, values)
        allow = getattr(instance, "allow_data_inconsistency", False)
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
                values = to_masked(values, dtype=self.dtype)
                logger.info(
                    f"{genre} values' lists were appended with zeros to "
                    f"match length of longest entry."
                )
                return values


class JaggedArrayProperty(ArrayProperty):
    """ArrayProperty for storing intentionally jagged arrays of data.
    InconsistentDataError is only raised if `check_shape()` fails. Given values are
    converted to masked array and expanded as needed, regardless value of
    `allow_data_inconsistency` attribute."""

    def check_input(self, instance: Any, values: Sequence) -> np.ndarray:
        self.check_shape(instance, values)
        return to_masked(values, dtype=self.dtype, fill_value=self.fill_value)


class CollapsibleArrayProperty(ArrayProperty):
    """ArrayProperty that stores only one value, if all entries are identical."""

    def __init__(
        self,
        fget: Optional[Callable[[Any], np.ndarray]] = None,
        fset: Optional[Callable[[Any, Sequence], None]] = None,
        fdel: Optional[Callable[[Any], None]] = None,
        doc: str = None,
        dtype: type = float,
        check_against: Optional[str] = None,
        check_depth: int = 1,
        fill_value: Any = 0,
        fsan: Optional[Callable[[Sequence], Sequence]] = None,
        strict: bool = False,
    ):
        self.strict = strict
        super().__init__(
            fget=fget,
            fset=fset,
            fdel=fdel,
            doc=doc,
            dtype=dtype,
            check_against=check_against,
            check_depth=check_depth,
            fill_value=fill_value,
            fsan=fsan,
        )

    def check_shape(self, instance: Any, values: Sequence):
        """Raises an error if `values` have different shape than attribute specified
        as`check_against`. Accepts values with size of first dimension equal to 1, even
        if it is not identical to the size of the first dimension of said attribute.
        """
        allow = getattr(instance, "allow_data_inconsistency", False)
        if self.check_against:
            attr_value = getattr(instance, self.check_against)
            try:
                ref_shape = attr_value.shape
            except AttributeError:
                ref_shape = find_best_shape(attr_value)
            best_shape = find_best_shape(values)
            first_important = int(best_shape[0] == 1)
            shapes_same = (
                ref_shape[first_important : self.check_depth]
                == best_shape[first_important : self.check_depth]
            )
            if not shapes_same and not allow:
                raise ValueError(
                    f"{self.name} and {self.check_against} must have the same shape "
                    f"up to {self.check_depth} dimensions. Arrays of shape "
                    f"{best_shape} and {ref_shape} were given."
                )

    def check_input(self, instance: Any, values: Union[Sequence, Any]) -> np.ndarray:
        """If given `values` is not iterable or is of type `str` it is returned
        without change. Otherwise it is validated using `ArrayProperty.check_input()`,
        and collapsed to single value if all values are identical.
        If values are non-uniform and instance doesn't allow data inconsistency,
        InconsistentDataError is raised.

        Parameters
        ----------
        instance
        values

        Returns
        -------
        numpy.ndarray or any
            Validated array or single value.

        Raises
        ------
        ValueError
            If `array_property.check_against` is not None and list of given values
            have different length than getattr(`instance`,
            `array_property.check_against`).
            If given list of values cannot be converted to `array_property.dtype` type.
        InconsistentDataError
            If `values` is list of lists of varying size and instance doesn't allow
            data inconsistency.
            If property is declared as strict, given `values` are non-uniform
            and instance doesn't allow data inconsistency.
        """
        if not isinstance(values, Iterable) or isinstance(values, str):
            return np.array([values], dtype=self.dtype)
        values = super().check_input(instance, values)
        allow = getattr(instance, "allow_data_inconsistency", False)
        try:
            all_same = (values == values[0]).all()
        except IndexError:
            return np.array([], dtype=self.dtype)
        if all_same:
            # return only first element, but keep dimensionality
            return values[np.newaxis, 0]
        elif self.strict and not allow:
            raise InconsistentDataError(
                "List of non-uniform values given to CollapsibleArrayProperty setter."
            )
        else:
            return values


_ARRAY_CONSTRUCTORS = {}


class ArrayBase:
    """Base class for data holding objects."""

    # TODO: signalize that this should be overridden in subclass
    #       consider implementing stronger protection ?
    associated_genres: Tuple[str, ...] = NotImplemented

    def __init_subclass__(cls, **kwargs):
        global _ARRAY_CONSTRUCTORS
        if cls.associated_genres is not NotImplemented:
            _ARRAY_CONSTRUCTORS.update((genre, cls) for genre in cls.associated_genres)

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
