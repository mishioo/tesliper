# IMPORTS
import logging as lgg
from collections import (
    OrderedDict, Counter,
    _OrderedDictKeysView, _OrderedDictItemsView, _OrderedDictValuesView
)
from contextlib import contextmanager

import numpy as np

from tesliper.exceptions import TesliperError
from .arrays import ArrayBase, DataArray

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
class _TrimmedItemsView(_OrderedDictItemsView):
    def __init__(self, mapping, indices=False):
        super().__init__(mapping)
        self.indices = indices

    def __contains__(self, item):
        key, value = item
        try:
            kept = self._mapping.kept[self._mapping[key]['_index']]
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
        for idx, (key, kept) in enumerate(
                zip(self._mapping, self._mapping.kept)
        ):
            if kept:
                value = self._mapping[key]
                yield key, value if not indices else (idx, key, value)


class _TrimmedValuesView(_OrderedDictValuesView):
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
        for idx, (key, kept) in enumerate(
                zip(self._mapping, self._mapping.kept)
        ):
            if kept:
                value = self._mapping[key]
                yield value if not indices else (idx, value)


class _TrimmedKeysView(_OrderedDictKeysView):
    def __init__(self, mapping, indices=False):
        super().__init__(mapping)
        self.indices = indices

    def __contains__(self, key):
        try:
            return self._mapping.kept[self._mapping[key]['_index']]
        except KeyError:
            return False

    def __iter__(self):
        indices = self.indices
        for idx, (key, kept) in enumerate(
                zip(self._mapping, self._mapping.kept)
        ):
            if kept:
                yield key if not indices else (idx, key)


class Molecules(OrderedDict):
    """Ordered mapping of dictionaries.

    Notes
    -----
    Inherits from collections.OrderedDict.

    TO DO
    -----
    Add type checks in update and setting methods."""

    def __init__(self, *args, allow_data_inconsistency=False, **kwargs):
        self.allow_data_inconsistency = allow_data_inconsistency
        self.kept = []
        self.filenames = []
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value, **kwargs):
        # TO DO: enable other, convertible to dict, structures
        # TO DO: make sure setting same key does not append kept and filenames
        if not isinstance(value, dict):
            raise TypeError(f'Value should be dict-like object, '
                            f'not {type(value)}')
        if key in self:
            index = self[key]['_index']
            self.kept[index] = True
        else:
            index = len(self.filenames)
            self.filenames.append(key)
            self.kept.append(True)
        super().__setitem__(key, value, **kwargs)
        self[key]['_index'] = index

    def __delitem__(self, key, **kwargs):
        index = self[key]['_index']
        super().__delitem__(key, **kwargs)
        del self.filenames[index]
        del self.kept[index]
        for index, mol in enumerate(self.values()):
            mol['_index'] = index

    @property
    def kept(self):
        return self.__kept

    @kept.setter
    def kept(self, blade):
        try:
            first = blade[0]
        except (TypeError, KeyError):
            raise TypeError(f"Excepted sequence, got: {type(blade)}.")
        except IndexError:
            try:
                self.__kept = [False for __ in self.kept]
            except AttributeError:
                self.__kept = []
            return
        if isinstance(first, str):
            blade = set(blade)
            if not blade.issubset(set(self.keys())):
                raise KeyError(
                    f"Unknown conformers: {', '.join(blade-set(self.keys()))}"
                )
            else:
                self.__kept = [fnm in blade for fnm in self.keys()]
        elif isinstance(first, (bool, np.bool_)):
            if not len(blade) == len(self):
                raise ValueError(
                    f"When setting molecules.kept directly, must provide "
                    f"boolean value for each known conformer. {len(blade)} "
                    f"values provided, {len(self)} excepted."
                )
            else:
                self.__kept = [bool(b) for b in blade]  # convert from np.bool_
        elif isinstance(first, int):
            length = len(self.kept)
            out_of_bounds = [b for b in blade if not -length <= b < length]
            if out_of_bounds:
                raise IndexError(
                    f"Indexes out of bounds: "
                    f"{', '.join(str(n) for n in out_of_bounds)}."
                )
            else:
                blade = set(blade)
                self.__kept = [num in blade for num in range(len(self.kept))]
        else:
            raise TypeError(
                f"Expected sequence of strings, integers or booleans, got: "
                f"{type(first)} as first sequence's element."
            )

    def update(self, other=None, **kwargs):
        """Works like dict.update, but if key is already present, it updates
        dictionary associated with given key rather than changing its value.

        TO DO
        -----
        Add type checks.
        Figure out what to do with values like optimization_completed
        and normal_termination."""
        molecules = dict()
        if other is not None:
            molecules.update(other)
        molecules.update(**kwargs)
        for key, value in molecules.items():
            if key in self:
                self[key].update(value)
            else:
                self[key] = value

    def arrayed(self, genre, full=False):
        """Lists requested data and returns as appropriate DataArray instance.

        Parameters
        ----------
        genre : str
            String representing data genre. Must be one of known genres.
        full : bool, optional
            Boolean indicating if full set of data should be taken, ignoring
            any trimming conducted earlier. Defaults to False.

        Returns
        -------
        DataArray
            Arrayed data of desired genre as appropriate DataArray object.

        TO DO
        -----
        Add support for 'filenames'"""
        try:
            cls = ArrayBase.constructors[genre]  # DataArray subclass
        except KeyError:
            raise ValueError(f"Unknown genre '{genre}'.")
        conarr = self.kept if not full else (True for __ in self.kept)
        array = (
            (fname, mol, mol[genre]) for (fname, mol), con
            in zip(self.items(), conarr) if con and genre in mol
        )
        try:
            filenames, mols, values = zip(*array)
        except ValueError:  # if no elements in `array`
            logger.debug(
                f'Array of gerne {genre} requested, but no such data available '
                f'or conformers providing this data where trimmed off. '
                f'Returning empty array.'
            )
            filenames, mols, values = [], [], []
        params = cls.get_init_params()
        parameter_type = type(params['genre'])
        params['genre'] = genre
        params['filenames'] = filenames
        params['values'] = values
        params['allow_data_inconsistency'] = self.allow_data_inconsistency
        for key in params:
            if not isinstance(params[key], parameter_type):
                continue
            try:
                params[key] = [mol[key] for mol in mols]
            except KeyError:
                if params[key].default is not params[key].empty:
                    params[key] = params[key].default
                else:
                    raise TesliperError(
                        f"One or more conformers does not provide value for "
                        f"{key} genre, needed to instantiate {cls.__name__} "
                        f"object."
                    )
        return cls(**params)

    def by_index(self, index):
        """Returns data for conformer on desired index."""
        return self[self.filenames[index]]

    def index(self, key):
        try:
            return self[key]['_index']
        except KeyError:
            raise ValueError(f"No such molecule: {key}.")

    @property
    def _max_len(self):
        return max(len(m) for m in self.values())

    def trim_incomplete(self, wanted=None):
        # TODO: don't take optimization_completed and such into consideration
        # TODO: when above satisfied, change gui.tab_loader.Loader\
        #       .update_overview_values() and .set_overview_values()
        # TODO: maybe use all as default but keep current `wanted` as Molecules'
        #       attribute or module level variable
        if wanted is None:
            wanted = 'dip rot vosc vrot losc lrot raman1 roa1 scf zpe ent ' \
                     'ten gib h_mst c_mst fermi'.split()
        elif isinstance(wanted, str):
            wanted = wanted.split()
        elif not isinstance(wanted, (list, tuple)):
            raise TypeError(
                f"Expected list, tuple or string, got {type(wanted)}."
            )
        count = [[g in mol for g in wanted] for mol in self.values()]
        best_match = max(count)
        for index, match in enumerate(count):
            if not match == best_match:
                self.kept[index] = False

    def trim_imaginary_frequencies(self):
        dummy = [1]
        for index, mol in enumerate(self.values()):
            freq = np.array(mol.get('freq', dummy))
            if (freq < 0).any():
                self.kept[index] = False

    def trim_non_matching_stoichiometry(self):
        counter = Counter(
            mol['stoichiometry'] for mol in self.values()
            if 'stoichiometry' in mol
        )
        stoich = counter.most_common()[0][0]
        for index, mol in enumerate(self.values()):
            if 'stoichiometry' not in mol or not mol['stoichiometry'] == stoich:
                self.kept[index] = False

    def trim_not_optimized(self):
        for index, mol in enumerate(self.values()):
            if not mol.get('optimization_completed', True):
                self.kept[index] = False

    def trim_non_normal_termination(self):
        # TODO: ensure its working properly
        for index, mol in enumerate(self.values()):
            if not mol.get('normal_termination', False):
                self.kept[index] = False

    def trim_inconsistent_sizes(self):
        sizes = {}
        for fname, mol in self.items():
            for genre, value in mol.items():
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
                    self.kept[index] = False

    def trim_to_range(self, genre, minimum=float("-inf"), maximum=float("inf"),
                      attribute='values'):
        try:
            arr = self.arrayed(genre)
            atr = getattr(arr, attribute)
        except AttributeError:
            raise ValueError(
                f"Invalid genre/attribute combination: {genre}/{attribute}. "
                f"Resulting DataArray object has no attribute {attribute}."
            )
        except TypeError:
            raise ValueError(
                f"Invalid genre/attribute combination: {genre}/{attribute}. "
                f"DataArray's attribute must be iterable."
            )
        if not isinstance(atr[0], (int, float)):
            raise ValueError(
                f"Invalid genre/attribute combination: {genre}/{attribute}. "
                f"Resulting DataArray must contain objects of type int or "
                f"float, not {type(atr[0])}"
            )
        blade = [
            fnm for v, fnm in zip(atr, arr.filenames) if minimum <= v <= maximum
        ]
        self.kept = blade

    def select_all(self):
        self.kept = [True for __ in self.kept]

    def trimmed_keys(self, indices=False):
        return _TrimmedKeysView(self, indices=indices)

    def trimmed_values(self, indices=False):
        return _TrimmedValuesView(self, indices=indices)

    def trimmed_items(self, indices=False):
        return _TrimmedItemsView(self, indices=indices)

    @property
    @contextmanager
    def untrimmed(self):
        blade = self.kept
        self.select_all()
        yield self
        self.kept = blade

    @contextmanager
    def trimmed_to(self, blade):
        old_blade = self.kept
        self.kept = blade
        yield self
        self.kept = old_blade

    """# performance test for making arrays
    >>> from timeit import timeit
    >>> import random
    >>> dt = {n: chr(n) for n in range(100)}
    >>> ls = list(range(100))
    >>> kpt = random.choices(ls, k=80)
    >>> skpt = set(kpt)
    >>> timeit('[(k, v) for k, v in dt.items()]', globals=globals())
    5.26354954301791
    >>> timeit('[(n, dt[n]) for n in ls]', globals=globals())
    6.790710222989297
    >>> timeit('[(k,v) for k,v in dt.items() if k in skpt]', globals=globals())
    7.0161151549953615
    >>> timeit('[(n, dt[n]) for n in kpt]', globals=globals())
    5.522729124628256
    >>> timeit('[(n,dt[n]) for n,con in zip(ls,ls) if con]', globals=globals())
    9.363086626095992
    >>> timeit('[(k,v) for (k,v),con in zip(dt.items(),ls)]',globals=globals())
    7.463483778659565"""
