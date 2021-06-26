# IMPORTS
import logging as lgg
from collections import (
    OrderedDict,
    Counter,
    ItemsView,
    ValuesView,
    KeysView,
)
from contextlib import contextmanager
from itertools import chain
from typing import Sequence, Union, Iterable, Optional

import numpy as np

from tesliper.exceptions import TesliperError, InconsistentDataError
from . import arrays as ar
from .. import datawork as dw
from .array_base import _ARRAY_CONSTRUCTORS


# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# TYPE HINTS
AnyArray = Union[
    ar.DataArray,
    ar.Energies,
    ar.FloatArray,
    ar.FilenamesArray,
    ar.InfoArray,
    ar.BooleanArray,
    ar.IntegerArray,
    ar.GroundStateBars,
    ar.ExcitedStateBars,
    ar.Transitions,
    ar.Geometry,
]


# CLASSES
class _KeptItemsView(ItemsView):
    def __init__(self, mapping, indices=False):
        super().__init__(mapping)
        self.indices = indices

    def __contains__(self, item):
        key, value = item
        try:
            kept = self._mapping.kept[self._mapping.index_of(key)]
        except KeyError:
            return False
        else:
            if not kept:
                return False
            else:
                v = self._mapping[key]
                return v is value or v == value

    def __iter__(self):
        indices = self.indices
        for idx, (key, kept) in enumerate(zip(self._mapping, self._mapping.kept)):
            if kept:
                value = self._mapping[key]
                yield key, value if not indices else (idx, key, value)

    def __reversed__(self):
        yield from iter(reversed(list(self)))


class _KeptValuesView(ValuesView):
    def __init__(self, mapping, indices=False):
        super().__init__(mapping)
        self.indices = indices

    def __contains__(self, value):
        for key, kept in zip(self._mapping, self._mapping.kept):
            v = self._mapping[key]
            if (v is value or v == value) and kept:
                return True
        return False

    def __iter__(self):
        indices = self.indices
        for idx, (key, kept) in enumerate(zip(self._mapping, self._mapping.kept)):
            if kept:
                value = self._mapping[key]
                yield value if not indices else (idx, value)

    def __reversed__(self):
        yield from iter(reversed(list(self)))


class _KeptKeysView(KeysView):
    def __init__(self, mapping, indices=False):
        super().__init__(mapping)
        self.indices = indices

    def __contains__(self, key):
        try:
            return self._mapping.kept[self._mapping.index_of(key)]
        except KeyError:
            return False

    def __iter__(self):
        indices = self.indices
        for idx, (key, kept) in enumerate(zip(self._mapping, self._mapping.kept)):
            if kept:
                yield key if not indices else (idx, key)

    def __reversed__(self):
        yield from iter(reversed(list(self)))


class Conformers(OrderedDict):
    """Container for data extracted from quantum chemical software output files.

    Data for each file is stored in the underlying OrderedDict, under the key of
    said file's name. Its values are dictionaries with genres name (as key)
    and appropriate data pairs. Beside this, its essential functionality is
    transformation of stored data to corresponding DataArray objects with
    use of `arrayed` method. It provides some control over this transformation,
    especially in terms of including/excluding particular conformers' data
    on creation of new DataArray instance. This type of control is here called
    trimming. Trimming can be achieved by use of various `trim` methods defined
    in this class or by direct changes to `kept` attribute. See its
    documentation for more information.

    Parameters
    ----------
    *args
        list of arguments for creation of underlying dictionary
    allow_data_inconsistency : bool, optional
        specifies if data inconsistency should be allowed in created DataArray
        object instances, defaults to False
    **kwargs
        list of arbitrary keyword arguments for creation of underlying
        dictionary

    Class Attributes
    ----------------
    primary_genres
        Data genres considered most important, used as default when checking
        for conformers completeness (see `trim_incomplete` method).

    Notes
    -----
    Inherits from collections.OrderedDict.
    """

    primary_genres = tuple(
        "dip rot vosc vrot losc lrot raman1 roa1 scf zpe ent ten gib".split()
    )

    def __init__(self, *args, allow_data_inconsistency=False, **kwargs):
        self.allow_data_inconsistency = allow_data_inconsistency
        self.kept = []
        self.filenames = []
        self._indices = {}
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        try:
            value = dict(value)
        except TypeError as error:
            raise TypeError("Can't convert given value to dictionary.") from error
        except ValueError as error:
            raise ValueError("Can't convert given value to dictionary.") from error
        if key in self:
            index = self._indices[key]
        else:
            index = len(self.filenames)
            self.filenames.append(key)
            self.kept.append(True)
        super().__setitem__(key, value)
        self._indices[key] = index

    def __delitem__(self, key):
        index = self._indices[key]
        super().__delitem__(key)
        del self.filenames[index]
        del self.kept[index]
        del self._indices[key]
        for index, key in enumerate(self.keys()):
            self._indices[key] = index

    @property
    def kept(self):
        """List of booleans, one for each conformer stored, defining if
        particular conformers data should be included in corresponding DataArray
        instance, created by `arrayed` method. It may be changed by use of trim
        methods, by setting its value directly, or by modification of the
        underlying list. For the first option refer to those methods
        documentation, for rest see the Examples section.

        Returns
        -------
        list of bool
            List of booleans, one for each conformer stored, defining if
            particular conformers data should be included in corresponding
            DataArray instance.

        Raises
        ------
        TypeError
            If assigned values is not a sequence.
            If elements of given sequence are not one of types: bool, int, str.
        ValuesError
            If number of given boolean values doesn't match number of contained
            conformers.
        KeyError
            If any of given string values is not in underlying dictionary keys.
        IndexError
            If any of given integer values is not in range
            0 <= i < number of conformers.

        Examples
        --------

        New list of values can be set in a few ways. Firstly, it is the
        most straightforward to just assign a new list of boolean values to
        the `kept` attribute. This list should have the same number of elements
        as the number of conformers contained. A ValueError is raised if it
        doesn't.

        >>> c = Conformers(one={}, two={}, tree={})
        >>> c.kept
        [True, True, True]
        >>> c.kept = [False, True, False]
        >>> c.kept
        [False, True, False]
        >>> c.kept = [False, True, False, True]
        Traceback (most recent call last):
        ...
        ValueError: Must provide boolean value for each known conformer.
        4 values provided, 3 excepted.

        Secondly, list of filenames of conformers intended to be kept may be
        given. Only these conformers will be kept. If given filename is not in
        the underlying Conformers' dictionary, KeyError is raised.

        >>> c.kept = ['one']
        >>> c.kept
        [True, False, False]
        >>>  c.kept = ['two', 'other']
        Traceback (most recent call last):
        ...
        KeyError: Unknown conformers: other.

        Thirdly, list of integers representing conformers indices may br given.
        Only conformers with specified indices will be kept. If one of given integers
        cant be translated to conformer's index, IndexError is raised. Indexing with
        negative values is not supported currently.

        >>> c.kept = [1, 2]
        >>> c.kept
        [False, True, True]
        >>> c.kept = [2, 3]
        Traceback (most recent call last):
        ...
        IndexError: Indexes out of bounds: 3.

        Fourthly, assigning `True` or `False` to this attribute will mark all conformers
        as kept or not kept respectively.

        >>> c.kept = False
        >>> c.kept
        [False, False, False]
        >>> c.kept = True
        >>> c.kept
        [True, True, True]

        Lastly, list of kept values may be modified by setting its elements
        to True or False. It is advised against, however, as mistake such as
        `m.kept[:2] = [True, False, False]` will break some functionality by
        forcibly changing size of `kept` list.

        Notes
        -----
        Type of the first element of given sequence is used for dynamic
        dispatch.
        """
        # TODO: Consider making return value immutable.
        return self._kept

    @kept.setter
    def kept(self, blade: Union[Sequence[Union[bool, str, int]], bool]):
        if blade is True or blade is False:
            self._kept = [blade for _ in self.keys()]
            return
        try:
            first = blade[0]
        except (TypeError, KeyError):
            raise TypeError(f"Excepted sequence or boolean, got: {type(blade)}.")
        except IndexError:
            first = bool()
        if isinstance(first, str):
            blade = set(blade)
            if not blade.issubset(set(self.keys())):
                raise KeyError(
                    f"Unknown conformers: {', '.join(blade-set(self.keys()))}"
                )
            else:
                self._kept = [fnm in blade for fnm in self.keys()]
        elif isinstance(first, (bool, np.bool_)):
            if not len(blade) == len(self):
                raise ValueError(
                    f"Must provide boolean value for each known conformer. "
                    f"{len(blade)} values provided, {len(self)} excepted."
                )
            else:
                self._kept = [bool(b) for b in blade]  # convert from np.bool_
        elif isinstance(first, int):
            length = len(self)
            out_of_bounds = [b for b in blade if not 0 <= b < length]
            if out_of_bounds:
                raise IndexError(
                    f"Indexes out of bounds: "
                    f"{', '.join(str(n) for n in out_of_bounds)}."
                )
            else:
                blade = set(blade)
                self._kept = [num in blade for num in range(len(self))]
        else:
            raise TypeError(
                f"Expected sequence of strings, integers or booleans, got: "
                f"{type(first)} as first sequence's element."
            )

    def update(self, other=None, **kwargs):
        """Works like dict.update, but if key is already present, it updates
        dictionary associated with given key rather than changing its value.
        Please note, that values of status genres like 'optimization_completed'
        and 'normal_termination' will be updated as well for such key,
        if are present in given new values.
        """
        if other is not None:
            other = dict(other)
        else:
            other = dict()
        items = chain(other.items(), kwargs.items())
        for key, value in items:
            if key in self:
                self[key].update(value)
            else:
                self[key] = value

    def arrayed(self, genre: str, full: bool = False) -> AnyArray:
        """Lists requested data and returns as appropriate DataArray instance.

        Parameters
        ----------
        genre
            String representing data genre. Must be one of known genres.
        full
            Boolean indicating if full set of data should be taken, ignoring
            any trimming conducted earlier. Defaults to False.

        Returns
        -------
        DataArray
            Arrayed data of desired genre as appropriate DataArray object.
        """
        try:
            cls = _ARRAY_CONSTRUCTORS[genre]  # ArrayBase subclasses
        except KeyError:
            raise ValueError(f"Unknown genre '{genre}'.")
        if genre == "filenames":
            # return early if filenames requested
            return cls(
                genre=genre,
                filenames=list(self.kept_values() if not full else self.values()),
                allow_data_inconsistency=self.allow_data_inconsistency,
            )
        view = self.kept_items() if not full else self.items()
        array = ((fname, conf, conf[genre]) for fname, conf in view if genre in conf)
        try:
            filenames, confs, values = zip(*array)
        except ValueError:  # if no elements in `array`
            logger.debug(
                f"Array of gerne {genre} requested, but no such data available "
                f"or conformers providing this data were trimmed off. "
                f"Returning an empty array."
            )
            filenames, confs, values = [], [], []
        params = cls.get_init_params()
        parameter_type = type(params["genre"])
        params["genre"] = genre
        params["filenames"] = filenames
        params["values"] = values
        params["allow_data_inconsistency"] = self.allow_data_inconsistency
        for key in params:
            if not isinstance(params[key], parameter_type):
                # if value for parameter is already established, move on
                continue
            try:
                if not confs:
                    # this is a hack to invoke except clause
                    # also when conf is an empty sequence
                    raise KeyError
                params[key] = [conf[key] for conf in confs]
            except KeyError:
                # set param to its default value
                # or raise an error if it don't have one
                if params[key].default is not params[key].empty:
                    params[key] = params[key].default
                else:
                    raise TesliperError(
                        f"One or more conformers does not provide value for "
                        f"{key} genre, needed to instantiate {cls.__name__} "
                        f"object."
                    )
        return cls(**params)

    def by_index(self, index: int) -> dict:
        """Returns data for conformer on desired index."""
        return self[self.filenames[index]]

    def key_of(self, index: int) -> str:
        """Returns name of conformer associated with given index."""
        return self.filenames[index]

    def index_of(self, key: str) -> int:
        """Return index of given key."""
        try:
            return self._indices[key]
        except KeyError as error:
            raise KeyError(f"No such conformer: {key}.") from error

    def has_genre(self, genre: str, ignore_trimming: bool = False) -> bool:
        """Checks if any of stored conformers contains data of given genre.

        Parameters
        ----------
        genre : str
            Name of genre to test.
        ignore_trimming : bool
            If all known conformers should be considered (`ignore_trimming = True`)
            or only kept ones (`ignore_trimming = False`, default).

        Returns
        -------
        bool
            Boolean value indicating if any of stored conformers contains data
            of genre in question."""
        conformers = self.values() if ignore_trimming else self.kept_values()
        for conformer in conformers:
            if genre in conformer:
                return True
        return False

    def has_any_genre(
        self, genres: Iterable[str], ignore_trimming: bool = False
    ) -> bool:
        """Checks if any of stored conformers contains data of any of given
        genres.

        Parameters
        ----------
        genres : iterable of str
            List of names of genres to test.
        ignore_trimming : bool
            If all known conformers should be considered (`ignore_trimming = True`)
            or only kept ones (`ignore_trimming = False`, default).

        Returns
        -------
        bool
            Boolean value indicating if any of stored conformers contains data
            of any of genres in question."""
        conformers = self.values() if ignore_trimming else self.kept_values()
        for conformer in conformers:
            for genre in genres:
                if genre in conformer:
                    return True
        return False

    def trim_incomplete(
        self, wanted: Optional[Iterable[str]] = None, strict: bool = False
    ) -> None:
        """Mark incomplete conformers as "not kept".

        Conformers that does not contain one or more data genres specified as `wanted`
        will be marked as "not kept". If `wanted` parameter is not given, it evaluates
        to `conformers.primary_genres`. If no conformer contains all `wanted` genres,
        conformers that match the specification most closely are kept. The "closeness"
        is defined by number of conformer's genres matching `wanted` genres in the first
        place (the more, the better) and the position of particular genre in `wanted`
        list in the second place (the closer to the beginning, the better). This
        "match closest" behaviour may be turned off by setting parameter
        `strict` to `True`. In such case, only conformers containing all `wanted`
        genres will be kept.

        Parameters
        ----------
        wanted
            List of data genres used as completeness reference.
            If not given, evaluates to `conformers.primary_genres`.
        strict
            Indicates if all `wanted` genres must be present in the kept conformers
            (`strict=True`) or if "match closest" mechanism should be used
            as a fallback (`strict=False`, this is the default).

        Notes
        -----
        Conformers previously marked as "not kept" will not be affected.
        """
        # DONE: don't take optimization_completed and such into consideration
        # TODO: when above satisfied, change gui.tab_loader.Loader\
        #       .update_overview_values() and .set_overview_values()
        wanted = wanted if wanted is not None else self.primary_genres
        if not strict:
            count = [tuple(g in conf for g in wanted) for conf in self.values()]
            best_match = max(count)
            complete = (match == best_match for match in count)
        else:
            complete = (all(g in conf for g in wanted) for conf in self.values())
        blade = [kept and cmpl for kept, cmpl in zip(self.kept, complete)]
        self._kept = blade

    def trim_imaginary_frequencies(self) -> None:
        """Mark all conformers with imaginary frequencies as "not kept".

        Notes
        -----
        Conformers previously marked as "not kept" will not be affected.
        Conformers that doesn't contain "freq" genre will be treated as not having
        imaginary frequencies.
        """
        dummy = [1]
        for index, conf in enumerate(self.values()):
            freq = np.array(conf.get("freq", dummy))
            if (freq < 0).any():
                self._kept[index] = False

    def trim_non_matching_stoichiometry(self, wanted: Optional[str] = None) -> None:
        """Mark all conformers with stoichiometry other than `wanted` as "not kept".
        If not given, `wanted` evaluates to the most common stoichiometry.

        Parameters
        ----------
        wanted
            Only conformers with same stoichiometry will be kept. Evaluates to the most
            common stoichiometry if not given.

        Notes
        -----
        Conformers previously marked as "not kept" will not be affected.
        Conformers that doesn't contain stoichiometry data are always treated
        as non-matching.
        """
        if not wanted:
            counter = Counter(
                conf["stoichiometry"]
                for conf in self.values()
                if "stoichiometry" in conf
            )
            wanted = counter.most_common()[0][0]
        for index, conf in enumerate(self.values()):
            if "stoichiometry" not in conf or not conf["stoichiometry"] == wanted:
                self._kept[index] = False

    def trim_not_optimized(self) -> None:
        """Mark all conformers that failed structure optimization as "not kept".

        Notes
        -----
        Conformers previously marked as "not kept" will not be affected.
        Conformers that doesn't contain optimization data are always treated as
        optimized.
        """
        for index, conf in enumerate(self.values()):
            if not conf.get("optimization_completed", True):
                self._kept[index] = False

    def trim_non_normal_termination(self) -> None:
        """Mark all conformers, which calculation job did not terminate normally,
         as "not kept".

        Notes
        -----
        Conformers previously marked as "not kept" will not be affected.
        Conformers that doesn't contain data regarding their calculation job's
        termination are always treated as terminated abnormally.
        """
        for index, conf in enumerate(self.values()):
            if not conf.get("normal_termination", False):
                self._kept[index] = False

    def trim_inconsistent_sizes(self) -> None:
        """Mark as "not kept" all conformers that contain any iterable data genre,
        that is of different length, than in case of majority of conformers.

        Examples
        --------
        >>> c = Conformers(
        ...     one={'a': [1, 2, 3]},
        ...     two={'a': [1, 2, 3]},
        ...     three={'a': [1, 2, 3, 4]}
        ... )
        >>> c.kept
        [True, True, True]
        >>> c.trim_inconsistent_sizes()
        >>> c.kept
        [True, True, False]

        Notes
        -----
        Conformers previously marked as "not kept" will not be affected.
        """
        sizes = {}
        for fname, conf in self.items():
            for genre, value in conf.items():
                if isinstance(value, (np.ndarray, list, tuple)):
                    sizes.setdefault(genre, {})[fname] = len(value)
        maxes = {
            genre: Counter(v for v in values.values()).most_common()[0][0]
            for genre, values in sizes.items()
        }
        for index, fname in enumerate(self.keys()):
            for genre, most_common in maxes.items():
                confs = sizes[genre]
                if fname in confs and not confs[fname] == most_common:
                    self._kept[index] = False

    def trim_to_range(
        self,
        genre: str,
        minimum: Union[int, float] = float("-inf"),
        maximum: Union[int, float] = float("inf"),
        attribute: str = "values",
    ) -> None:
        """Marks as "not kept" all conformers, which numeric value of data
        of specified genre is outside of the range specified by `minimum`
        and `maximum` values.

        Parameters
        ----------
        genre
            Name of genre that should be compared to specified
            minimum and maximum values.
        minimum
            Minimal accepted value - every conformer, which genre value evaluates
            to less than `minimum` will be marked as "not kept".
            Defaults to `float(-inf)`.
        maximum
            Maximal accepted value - every conformer, which genre value evaluates
            to more than `maximum` will be marked as "not kept".
            Defaults to `float(inf)`.
        attribute
            Attribute of DataArray of specified `genre` that contains one-dimensional
            array of numeric values. defaults to `"values"`.

        Raises
        ------
        AttributeError
            If DataArray associated with `genre` genre has no attribute `attribute`.
        ValueError
            If data retrieved from specified genre's attribute is not in the form of
            one-dimensional array.
        TypeError
            If comparision cannot be made between elements of specified genre's
            attribute and `minimum` or `maximum` values.

        Notes
        -----
        Conformers previously marked as "not kept" will not be affected.
        """
        try:
            arr = self.arrayed(genre)
            atr = getattr(arr, attribute)
        except AttributeError as error:
            raise AttributeError(
                f"Invalid genre/attribute combination: {genre}/{attribute}. "
                f"Resulting DataArray object has no attribute {attribute}."
            ) from error
        values = np.asarray(atr)
        if values.ndim != 1:
            raise ValueError(
                f"Invalid genre/attribute combination: {genre}/{attribute}. "
                f"DataArray's attribute must contain one-dimensional array of values."
            )
        try:
            in_range = (minimum <= values) & (values <= maximum)
        except TypeError as error:
            raise TypeError(
                f"Cannot compare {type(minimum)} with {type(values[0])}."
            ) from error
        self.kept = arr.filenames[in_range]

    def trim_rmsd(
        self,
        threshold: Union[int, float],
        window_size: Union[int, float],
        geometry_genre: str = "geometry",
        energy_genre: str = "scf",
        ignore_hydrogen: bool = True,
    ) -> None:
        """Marks as "not kept" all conformers, that are not identical, according
        to provided RMSD threshold and energy difference. Conformers, which energy
        difference (dE) is higher than given `window_size` are always treated as
        different, while those with dE smaller than `window_size` and RMSD value
        smaller than given `threshold` are considered identical. From two identical
        conformers, the one with lower energy is "kept", and the other is discarded
        (marked as "not kept").

        Notes
        -----
        RMSD threshold and size of the energy window should be chosen depending on the
        parameters of conformers' set: number of conformers, size of the conformer,
        its lability, etc. However, `threshold` of 0.5 angstrom and `windoe_size`
        of 5 to 10 kcal/mol is a good place to start if in doubt.

        Parameters
        ----------
        threshold : int or float
            Maximum RMSD value to consider conformers identical.
        window_size : int or float
            Size of the energy window, in kcal/mol, inside which RMSD matrix is
            calculated. Essentially, a difference in conformers' energy, after which
            conformers are always considered different.
        geometry_genre : str
            Genre of geometry used to calculate RMSD matrix. "geometry" is default.
        energy_genre : str
            Genre of energy used to sort and group conformers into windows of given
            energy size. "scf" is used by default.
        ignore_hydrogen : bool
            If hydrogen atom should be discarded before RMSD calculation.
            Defaults to `True`.

        Raises
        ------
        InconsistentDataError
            If requested genres does not provide the same set of conformers.
        """
        energy = self.arrayed(energy_genre)
        geometry = self.arrayed(geometry_genre)
        if not energy.filenames.size == geometry.filenames.size:
            raise InconsistentDataError(
                "Unequal number of conformers in requested geometry and energy genres. "
                "Trim to incomplete entries before trimming with `trim_rmds`."
            )
        elif not np.array_equal(energy.filenames, geometry.filenames):
            raise InconsistentDataError(
                "Different conformers  in requested geometry and energy genres. "
                "Trim to incomplete entries before trimming with `trim_rmds`."
            )
        geom = (
            dw.drop_atoms(geometry.values, geometry.molecule_atoms, dw.atoms.Atom.H)
            if ignore_hydrogen
            else geometry.values
        )
        wanted = dw.rmsd_sieve(geom, energy.values, window_size, threshold)
        self.kept = geometry.filenames[wanted]

    def select_all(self) -> None:
        """Marks all conformers as 'kept'. Equivalent to `conformers.kept = True`."""
        self._kept = [True for _ in self._kept]

    def reject_all(self) -> None:
        """Marks all conformers as 'not kept'. Equivalent to
        `conformers.kept = False`.
        """
        self._kept = [False for _ in self._kept]

    def kept_keys(self, indices: bool = False) -> _KeptKeysView:
        """Equivalent of `dict.keys()` but gives view only on conformers marked
        as "kept". Returned view may also provide information on conformers index
        in its Conformers instance if requested with `indices=True`.

        >>> c = Conformers(c1={"g": 0.1}, c2={"g": 0.2}, c3={"g": 0.3}}
        >>> c.kept = [True, False, True]
        >>> list(c.kept_keys())
        ["c1", "c3"]
        >>> list(c.kept_keys(indices=True))
        [(0, "c1"}), (2, "c3")]

        Parameters
        ----------
        indices : bool
            If resulting Conformers view should also provide index of each conformer.
            Defaults to False.

        Returns
        -------09x
        _KeptKeysView
            View of kept conformers.
        """
        return _KeptKeysView(self, indices=indices)

    def kept_values(self, indices: bool = False) -> _KeptValuesView:
        """Equivalent of `dict.values()` but gives view only on conformers marked
        as "kept". Returned view may also provide information on conformers index
        in its Conformers instance if requested with `indices=True`.

        >>> c = Conformers(c1={"g": 0.1}, c2={"g": 0.2}, c3={"g": 0.3}}
        >>> c.kept = [True, False, True]
        >>> list(c.kept_values())
        [{"g": 0.1}, {"g": 0.3}]
        >>> list(c.kept_values(indices=True))
        [(0, {"g": 0.1}), (2,  {"g": 0.3})]

        Parameters
        ----------
        indices : bool
            If resulting Conformers view should also provide index of each conformer.
            Defaults to False.

        Returns
        -------
        _KeptValuesView
            View of kept conformers.
        """
        return _KeptValuesView(self, indices=indices)

    def kept_items(self, indices: bool = False) -> _KeptItemsView:
        """Equivalent of `dict.items()` but gives view only on conformers marked
        as "kept". Returned view may also provide information on conformers index
        in its Conformers instance if requested with `indices=True`.

        >>> c = Conformers(c1={"g": 0.1}, c2={"g": 0.2}, c3={"g": 0.3}}
        >>> c.kept = [True, False, True]
        >>> list(c.kept_items())
        [("c1", {"g": 0.1}), ("c3", {"g": 0.3})]
        >>> list(c.kept_items(indices=True))
        [(0, "c1", {"g": 0.1}), (2, "c3", {"g": 0.3})]

        Parameters
        ----------
        indices : bool
            If resulting Conformers view should also provide index of each conformer.
            Defaults to False.

        Returns
        -------
        _KeptItemsView
            View of kept conformers.
        """
        return _KeptItemsView(self, indices=indices)

    @property
    @contextmanager
    def untrimmed(self):
        blade = self._kept
        self.kept = True
        yield self
        self._kept = blade

    @contextmanager
    def trimmed_to(self, blade):
        old_blade = self._kept
        self.kept = blade
        yield self
        self._kept = old_blade

    @property
    @contextmanager
    def inconsistency_allowed(self):
        """Temporally sets Conformers' 'allow_data_inconsistency' attribute
        to true. Implemented as context manager to use with python 'with'
        keyword.

        Examples
        --------
        >>> c = Conformers()
        >>> with c.inconsistency_allowed:
        >>>     # do stuff here while c.allow_data_inconsistency is True
        >>>     c.allow_data_inconsistency
        True
        >>> c.allow_data_inconsistency
        False"""
        inconsistency = self.allow_data_inconsistency
        self.allow_data_inconsistency = True
        yield self
        self.allow_data_inconsistency = inconsistency
