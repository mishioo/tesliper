# IMPORTS
import logging as lgg
from collections import Sequence, Iterable

import numpy as np
from .array_base import ArrayProperty
from .arrays import FloatArray, Spectra
from ..exceptions import InconsistentDataError
from ..datawork.helpers import (
    atomic_number, validate_atoms, take_atoms, drop_atoms, atoms_symbols,
    symbol_of_element
)
from ..datawork.nmr import unpack, couple, drop_diagonals
from ..datawork.spectra import calculate_spectra


# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
class Shieldings(FloatArray):
    """Container for list of lists of magnetic shielding tensor values for each
    conformer.

    Parameters
    ----------
    genre : str
        Name of DataArray genre.
    filenames : iterable of str
        List of filenames representing each conformer.
    values : iterable of iterables of floats
        List of magnetic shielding tensor values for each conformer. There
        should be the same number of values for each conformer, unless
        `allow_data_inconsistency` parameter is set to True.
    molecule : iterable of int
        List of atomic numbers representing atoms in molecule.
    intercept : int or float
        Intercept value for linear regression scaling of shielding tensor
        values.
    slope : int or float
        Slope value for linear regression scaling of shielding tensor values.
    allow_data_inconsistency : bool, optional
        Allows suppression of DataArray's mechanisms of checking data
        consistency (proper shapes of related data arrays); defaults to False.

    Attributes
    ----------
    genre : str
        Name of DataArray genre.
    filenames : numpy.ndarray of str
        List of filenames representing each conformer.
    values : numpy.ndarray of float
        Tree-dimensional numpy.ndarray of floats of shape (Conformers, Atoms,
        Coupling Constants), consisting of coupling constants' values for each
        atom for each conformer.
    intercept : int or float
        Intercept value for linear regression scaling of shielding tensor
        values.
    slope : int or float
        Slope value for linear regression scaling of shielding tensor values.
    allow_data_inconsistency : bool
        Specifies if DataArray's mechanisms of checking data should be
        suppressed."""

    associated_genres = [
        genre for atom in atoms_symbols.values()
        for genre in (f'{atom.lower()}_mst', f'{atom.lower()}_amst')
    ]

    def __init__(
            self, genre, filenames, values, molecule, intercept=0, slope=-1,
            allow_data_inconsistency=False
    ):
        super().__init__(genre, filenames, values, allow_data_inconsistency)
        self.molecule = molecule
        self.intercept = intercept
        self.slope = slope

    validate_atoms = staticmethod(validate_atoms)
    molecule = ArrayProperty(dtype=int, check_against=None)

    @molecule.getter
    def molecule(self):
        """numpy.ndarray of int: List of atomic numbers representing atoms in
        molecule. Given atoms' list is always validated using `validate_atoms`
        method of this class when assigning new value."""
        return vars(self)['molecule']

    molecule.__doc__ = molecule.getter.__doc__

    @molecule.setter
    def molecule(self, molecule):
        molecule = self.validate_atoms(molecule)
        if len(molecule) < self.values.shape[1]:
            raise ValueError(
                "Molecule must have at least same number of atoms, as number "
                "of values provided."
            )
        vars(self)['molecule'] = np.array(
            molecule, dtype=type(self).molecule.dtype
        )

    @property
    def spectra_name(self):
        """str: Genre of related spectra."""
        return f"{self.nucleus.lower()}_nmr"

    @property
    def nucleus(self):
        """str: Symbol of an atom, to which shielding values refer."""
        return self.genre.split('_')[0].capitalize()

    @property
    def atomic_number(self):
        """int: Atomic number of a nucleus, to which shielding values refer."""
        return atomic_number(self.nucleus)

    @property
    def atoms(self):
        """numpy.ndarray of int: positions in the molecule of atoms, to which
        shielding values refer."""
        return np.where(self.molecule == self.atomic_number)[0]

    @property
    def shielding_values(self):
        """numpy.ndarray: Magnetic shielding tensor values scaled by `intercept`
        and `slope` values associated with Shieldings instance, as
        two-dimensional array of shape (Conformers, Values). The equation used
        is: (values - intercept) / -slope."""
        values = self.values.reshape(self.values.shape[0], -1)
        return (values - self.intercept) / -self.slope

    def couple(self, coupling_constants, couple_with=None,
               exclude_self_couplings=True):
        """Returns new Shieldings instance, representing peaks coupled with
        given coupling constants values.

        This function will exclude atoms' self-coupling constants if given
        Couplings instance include those with the same nuclei, that Shieldings
        instance deal with. This can be suppressed by setting
        `exclude_self_couplings` parameter to False. Parameter `couple_with` is
        always validated with self.validate_atoms method.

        Parameters
        ----------
        coupling_constants : Couplings or iterable
            coupling constants used to couple shielding values; it can be
            a Couplings instance or list of coupling constants' values for each
            atom in molecule, for each molecule (list of lists of lists)
        couple_with : int, str iterable of int, or iterable of str, optional
            atom's symbol, atomic number or list of those; specifies by which
            coupling constants should shielding values be coupled; all coupling
            constants contained in given Couplings instance are used, if
            `couple_with` is not specified; `couple_with` should be
            None (default) if `coupling_constants` is not a Couplings instance
        exclude_self_couplings : bool, optional
            specifies if self-coupling constants should be discarded, if there
            are any; defaults to True

        Returns
        -------
        Shieldings
            new instance with coupled peaks as values"""
        try:
            couple_with = couple_with if couple_with else \
                list(set(coupling_constants.atomic_numbers_coupled))
            couple_with = np.array(self.validate_atoms(couple_with))
            coupling_constants = coupling_constants.take_atoms(
                self.atomic_number, couple_with
            )
        except AttributeError:
            if couple_with is not None:
                raise ValueError(
                    "Parameter 'couple_with' must be None when list of "
                    "coupling constants given instead of Couplings object."
                )
        if couple_with is not None and exclude_self_couplings and \
                self.atomic_number in couple_with:
            cc_values = coupling_constants.exclude_self_couplings()
        elif couple_with is not None:
            cc_values = coupling_constants.coupling_constants
        elif exclude_self_couplings:
            try:
                cc_values = drop_diagonals(coupling_constants)
            except ValueError as err:
                raise ValueError(
                    "Cannot exclude self-couplings from a list of "
                    "non-symmetric arrays of coupling constants' values. To "
                    "prevent this error set 'exclude_self_couplings' to False "
                    "or use a Couplings instance as 'coupling_constants'."
                ) from err
        else:
            cc_values = coupling_constants
        values = couple(self.values, cc_values, separate_peaks=True)
        return type(self)(
            genre=self.genre, filenames=self.filenames, values=values,
            molecule=self.molecule, intercept=self.intercept, slope=self.slope,
            allow_data_inconsistency=self.allow_data_inconsistency
        )

    def calculate_spectra(self, start, stop, step, width, fitting):
        abscissa = np.arange(start, stop, step)
        values = calculate_spectra(
            self.shielding_values, np.ones_like(self.shielding_values),
            abscissa, width, fitting
        )
        spectra = Spectra(
            self.spectra_name, self.filenames, values, abscissa, width,
            fitting.__name__
        )
        return spectra

    def average_positions(self, positions):
        """Average signals of atoms on given positions. Returns new instance
        of Shieldings object with new values.

        Parameters
        ----------
        positions : iterable of int or iterable of iterables of int
            List of lists of positions of signals, that should be averaged

        Returns
        -------
        Shieldings
            new Shieldings instance with desired signals averaged averaged."""
        values = self.values.copy()
        positions = list(positions)
        if not isinstance(positions[0], (Sequence, Iterable)):
            positions = [positions]  # make sure it's list of lists
        for pos in positions:
            pos = np.where(np.isin(self.atoms, pos))
            confs, _, *other = values.shape
            values[:, pos] = values[:, pos].mean(1)
            values = values.reshape(confs, 1, *other)
        return type(self)(
            genre=self.genre, filenames=self.filenames, values=values,
            molecule=self.molecule, intercept=self.intercept, slope=self.slope,
            allow_data_inconsistency=self.allow_data_inconsistency
        )


class Couplings(FloatArray):
    """Container for list of coupling constants' values matrices for each
    conformer.

    Parameters
    ----------
    genre : str
        Name of DataArray genre.
    filenames : iterable of str
        List of filenames representing each conformer.
    values : iterable of iterables of floats or iterable of iterables
             of iterables of floats
        List of coupling constant's values for each conformer; it may be a list
        of lists with values for each conformer or a list of lists of lists
        consisting of coupling constants' values for each atom for each
        conformer. In the first case values given will be unpacked into a list
        of symmetric matrices, so given lists must consist of triangular number
        of values; in the second case values are taken as they are.
        Nevertheless, there should be the same number of values for each atom
        and the same number of atoms for each conformer, unless
        `allow_data_inconsistency` parameter is set to True.
    molecule : iterable of int
        List of atomic numbers representing atoms in molecule.
    atoms : iterable of int, optional
        List of atoms' positions in `molecule`; should be of the same length
        as number of given atoms for conformer, unless
        `allow_data_inconsistency` parameter is set to True. If not specified,
        all atoms listed as `molecule` are used.
    atoms_coupled : iterable of int or iterable of str, optional
        List of atoms' positions in `molecule`; should be
        of the same length as number of given coupling constants' values for
        atom, unless `allow_data_inconsistency` parameter is set to True. If
        not specified, `atoms` value is used.
    frequency : int, optional
        Frequency of an NMR spectrometer. Defaults to 100.
    allow_data_inconsistency : bool, optional
        Allows suppression of DataArray's mechanisms of checking data
        consistency (proper shapes of related data arrays); defaults to False.

    Attributes
    ----------
    genre : str
        Name of DataArray genre.
    filenames : numpy.ndarray of str
        List of filenames representing each conformer.
    values : numpy.ndarray of float
        Tree-dimensional numpy.ndarray of floats of shape (Conformers, Atoms,
        Coupling Constants), consisting of coupling constants' values for each
        atom for each conformer.
    frequency : int
        Frequency of an NMR spectrometer.
    allow_data_inconsistency : bool
        Specifies if DataArray's mechanisms of checking data should be
        suppressed."""
    associated_genres = ['fermi']

    def __init__(
            self, genre, filenames, values, molecule, atoms=None,
            atoms_coupled=None, frequency=100, allow_data_inconsistency=False
    ):
        values = np.asarray(values)
        values = unpack(values) if values.ndim == 2 else values
        super().__init__(genre, filenames, values, allow_data_inconsistency)
        self.molecule = molecule
        self.atoms = atoms if atoms is not None else []
        self.atoms_coupled = atoms_coupled if atoms_coupled is not None else []
        self.frequency = frequency

    molecule = ArrayProperty(dtype=int, check_against=None)
    atoms = ArrayProperty(dtype=int, check_against=None)
    atoms_coupled = ArrayProperty(dtype=int, check_against=None)
    validate_atoms = staticmethod(validate_atoms)

    @molecule.getter
    def molecule(self):
        """numpy.ndarray of int: List of atomic numbers representing atoms in
        molecule. Given atoms' list is always validated using `validate_atoms`
        method of this class when assigning new value."""
        return vars(self)['molecule']

    molecule.__doc__ = molecule.getter.__doc__

    @molecule.setter
    def molecule(self, molecule):
        molecule = self.validate_atoms(molecule)
        if len(molecule) < self.values.shape[1]:
            raise ValueError(
                "Molecule must have at least same number of atoms, as number "
                "of values provided."
            )
        vars(self)['molecule'] = np.array(
            molecule, dtype=type(self).molecule.dtype
        )

    @atoms.getter
    def atoms(self) -> np.ndarray:
        """numpy.ndarray of int: List of atom's positions in molecule;
        should be of the same length as number of given atoms for conformer
        (i.e. size of the first dimension of `values` array), unless
        `allow_data_inconsistency` attribute is set to True."""
        return vars(self)['atoms']

    atoms.__doc__ = atoms.getter.__doc__

    @atoms.setter
    def atoms(self, atoms):
        if not atoms.size:
            atoms = np.arange(self.molecule.size)
        if not atoms.size == len(self.values[0]) \
                and not self.allow_data_inconsistency:
            raise InconsistentDataError(
                f'Number of atoms ({atoms.size}) does not match number of '
                f'coupling constants\' lists ({len(self.values[0])}).'
            )
        vars(self)['atoms'] = atoms

    @atoms_coupled.getter
    def atoms_coupled(self) -> np.ndarray:
        """numpy.ndarray of int: List of atom's positions in molecule. If empty
        list given, `atoms` attribute value will be assigned. Should be of the
        same length as number of given coupling constants' values for atom (i.e.
        size of the second dimension of `values` array), unless
        `allow_data_inconsistency` attribute is set to True."""
        return vars(self)['atoms_coupled']

    atoms_coupled.__doc__ = atoms_coupled.getter.__doc__

    @atoms_coupled.setter
    def atoms_coupled(self, atoms):
        if not atoms.size and (len(self.atoms) == len(self.values[0][0])
                               or self.allow_data_inconsistency):
            atoms = self.atoms
        elif not atoms.size:
            raise ValueError(
                f"'atoms_coupled' parameter must be specified when creating a "
                f"{type(self)} instance with values as list of unsymmetric "
                f"matrices."
            )
        elif not atoms.size == len(self.values[0][0]) \
                and not self.allow_data_inconsistency:
            raise InconsistentDataError(
                f"Number of atoms_coupled ({atoms.size}) does not match number "
                f"of coupling constants' values ({len(self.values[0][0])})."
            )
        vars(self)['atoms_coupled'] = atoms

    @property
    def atomic_numbers(self):
        """numpy.ndarray of int: list of atomic numbers of `atoms`."""
        return self.molecule[self.atoms]

    @property
    def atomic_numbers_coupled(self):
        """numpy.ndarray of int: list of atomic numbers of atoms with which
         `atoms` are coupled."""
        return self.molecule[self.atoms_coupled]

    @property
    def nuclei(self):
        """numpy.ndarray of str: list of symbols of `atoms`."""
        return np.vectorize(symbol_of_element)(self.molecule[self.atoms])

    @property
    def nuclei_coupled(self):
        """numpy.ndarray of str: list of symbols of atoms with which
         `atoms` are coupled."""
        return np.vectorize(symbol_of_element)(
            self.molecule[self.atoms_coupled]
        )

    @property
    def coupling_constants(self):
        """numpy.ndarray of float: `values` divided by `frequency`."""
        return self.values / self.frequency

    def take_atoms(self, atoms=None, coupled_with=None):
        """Returns new Couplings instance containing only coupling constants'
        values for atoms specified as `atoms` (first dimension) and
        `coupled_with` (second dimension).

        Parameters
        ----------
        atoms : int, str iterable of int, or iterable of str, optional
            atom's symbol, atomic number or list of those; specifies which atoms
            for each molecule should be included in new instance; all are used,
            if this parameter is not specified (default)
        coupled_with : int, str iterable of int, or iterable of str, optional
            atom's symbol, atomic number or list of those; specifies which
            coupling constants' values for each atom in molecule should be
            included in new instance; all are used, if this parameter is not
            specified (default)

        Returns
        -------
        Couplings
            new instance of Couplings class containing data for specified
            atoms and coupling constants only; other attributes' values
            (genre, filenames, frequency) are preserved"""
        atoms = self.validate_atoms(atoms) if atoms is not None else self.atomic_numbers
        coupled_with = self.validate_atoms(coupled_with) \
            if coupled_with is not None else self.atomic_numbers_coupled
        temp = take_atoms(self.values, self.atomic_numbers, atoms).swapaxes(2, 1)
        new_values = take_atoms(temp, self.atomic_numbers_coupled, coupled_with)
        new_values = new_values.swapaxes(2, 1)
        new_atoms = take_atoms(self.atoms, self.atomic_numbers, atoms)
        new_coupled = take_atoms(
            self.atoms_coupled, self.atomic_numbers_coupled, coupled_with
        )
        new_inst = type(self)(
            genre=self.genre, filenames=self.filenames, values=new_values,
            molecule=self.molecule, atoms=new_atoms, atoms_coupled=new_coupled,
            frequency=self.frequency,
            allow_data_inconsistency=self.allow_data_inconsistency
        )
        return new_inst

    def drop_atoms(self, atoms=None, coupled_with=None):
        """Returns new Couplings instance containing only coupling constants'
        values for atoms NOT specified as `atoms` (first dimension) and
        `coupled_with` (second dimension).

        Parameters
        ----------
        atoms : int, str iterable of int, or iterable of str, optional
            atom's symbol, atomic number or list of those; specifies which atoms
            for each molecule should be omitted in new instance; all are kept,
            if this parameter is not specified (default)
        coupled_with : int, str iterable of int, or iterable of str, optional
            atom's symbol, atomic number or list of those; specifies which
            coupling constants' values for each atom in molecule should be
            omitted in new instance; all are kept, if this parameter is not
            specified (default)

        Returns
        -------
        Couplings
            new instance of Couplings class containing data for NOT specified
            atoms and coupling constants only; other attributes' values
            (genre, filenames, frequency) are preserved"""
        atoms = self.validate_atoms(atoms) if atoms is not None else []
        coupled_with = self.validate_atoms(coupled_with) \
            if coupled_with is not None else []
        temp = drop_atoms(self.values, self.atomic_numbers, atoms).swapaxes(2, 1)
        new_values = drop_atoms(temp, self.atomic_numbers_coupled, coupled_with)
        new_values = new_values.swapaxes(2, 1)
        new_atoms = drop_atoms(self.atoms, self.atomic_numbers, atoms)
        new_coupled = drop_atoms(
            self.atoms_coupled, self.atomic_numbers_coupled, coupled_with
        )
        new_inst = type(self)(
            genre=self.genre, filenames=self.filenames, values=new_values,
            molecule=self.molecule, atoms=new_atoms, atoms_coupled=new_coupled,
            frequency=self.frequency,
            allow_data_inconsistency=self.allow_data_inconsistency
        )
        return new_inst

    def exclude_self_couplings(self):
        """Returns list of each atom's coupling constants values, excluding this
        atom's self-coupling constant.

        Output is an array of shape (Conformers, Atoms, Coupling Constants - 1),
        but coupling constants' values for each atom may be in different order
        than originally.

        Returns
        -------
        numpy.ndarray
            array of coupling constants' values scaled to instance's frequency,
            byt with atom's self-coupling constants' values removed

        Raises
        ------
        ValueError
            if self-coupling constants are not included for all atoms
        """
        atoms = set(self.atomic_numbers)
        atoms_coupled = set(self.atomic_numbers_coupled)
        overload = atoms - atoms_coupled
        if overload:
            raise ValueError(
                f"Cannot exclude self-coupling constants if they are not "
                f"included for all atoms. No such constants for these atoms "
                f"found: {', '.join(symbol_of_element(a) for a in overload)}."
            )
        excessive = atoms_coupled - atoms
        cc = self.take_atoms(coupled_with=atoms) if excessive else self
        values = drop_diagonals(cc.coupling_constants)
        if excessive:
            other_values = \
                self.take_atoms(coupled_with=excessive).coupling_constants
            values = np.concatenate((values, other_values), 2)
        return values

    @property
    def is_symmetric(self):
        confs, x, y, *other = self.values.shape
        return x == y

    def average_positions(self, positions):
        """Average signals of atoms on given positions. Returns new instance
        of Couplings object with new values.

        Parameters
        ----------
        positions : iterable of int or iterable of iterables of int
            List of positions of signals, that should be averaged

        Returns
        -------
        Couplings
            new Couplings instance with desired signals averaged."""
        values = self.values.copy()
        positions = list(positions)
        if not isinstance(positions[0], (Sequence, Iterable)):
            positions = [positions]  # make sure it's list of lists
        for pos in positions:
            pos = np.where(np.isin(self.atoms, pos))[0]
            pos_cop = np.where(np.isin(self.atoms_coupled, pos))[0]
            slc = values[:, pos, np.expand_dims(pos_cop, -1)]
            confs, x, *other = slc.shape
            dropped = drop_diagonals(slc)
            means = dropped.reshape(confs, -1).mean(1)
            means = means.repeat(x ** 2).reshape(confs, x, *other)
            means = means * np.invert(np.eye(x, dtype=bool))
            values[:, pos, np.expand_dims(pos_cop, -1)] = means
        return type(self)(self.genre, self.filenames, values, self.molecule,
                          self.atoms, self.atoms_coupled, self.frequency,
                          self.allow_data_inconsistency)

    def suppress_coupling(self, positions):
        """Suppress atoms' coupling by setting their coupling constants to zero.
        Returns new Couplings instance.

        Parameters
        ----------
        positions : iterable of int or iterable of iterables of int
            List of positions of atoms, which coupling should be suppressed.
            Multiple iterables can be given.

        Returns
        -------
        Couplings
            new Couplings instance with desired atoms coupling suppressed."""
        values = self.values.copy()
        positions = list(positions)
        if not isinstance(positions[0], (Sequence, Iterable)):
            positions = [positions]  # make sure it's list of lists
        for psns in positions:
            psns = np.asarray(psns)
            smaller_than_molecule = psns < self.molecule.size
            if not smaller_than_molecule.all():
                raise ValueError(
                    f"Atoms on positions {psns[~smaller_than_molecule]} "
                    f"requested, but only {self.molecule.size} atoms in "
                    f"molecule."
                )
            pos = np.where(np.isin(self.atoms, psns))[0]
            pos_cop = np.where(np.isin(self.atoms_coupled, psns))[0]
            values[:, pos, np.expand_dims(pos_cop, -1)] = 0
        return type(self)(
            genre=self.genre, filenames=self.filenames, values=values,
            molecule=self.molecule, atoms=self.atoms,
            atoms_coupled=self.atoms_coupled, frequency=self.frequency,
            allow_data_inconsistency=self.allow_data_inconsistency
        )

# To convert from index 'n' of 1d storage of symmetric array to 2d array indices
# row = get_triangular_base(n)
# col = n - get_triangular(r)
