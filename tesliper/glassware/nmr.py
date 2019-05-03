import numpy as np

from .array_base import ArrayProperty
from .arrays import DataArray, Spectra
from ..exceptions import InconsistentDataError
from ..datawork.helpers import (
    atomic_number, validate_atoms, take_atoms, drop_atoms, atoms_symbols,
    symbol_of_element
)
from ..datawork.nmr import unpack, couple, drop_diagonals
from ..datawork.spectra import calculate_spectra


class Shieldings(DataArray):

    associated_genres = [
        genre for atom in atoms_symbols.values()
        for genre in (f'{atom.lower()}_mst', f'{atom.lower()}_amst')
    ]

    def __init__(
            self, genre, filenames, values, intercept=0, slope=-1,
            allow_data_inconsistency=False
    ):
        super().__init__(genre, filenames, values, allow_data_inconsistency)
        self.intercept = intercept
        self.slope = slope

    @property
    def spectra_name(self):
        return f"{self.nucleus.lower()}_nmr"

    @property
    def nucleus(self):
        return self.genre.split('_')[0].capitalize()

    @property
    def atomic_number(self):
        return atomic_number(self.nucleus)

    @property
    def shielding_values(self):
        values = self.values.reshape(self.values.shape[0], -1)
        return (values - self.intercept) / -self.slope

    validate_atoms = staticmethod(validate_atoms)

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
                list(set(coupling_constants.atoms_coupled))
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
        return type(self)(self.genre, self.filenames, values, self.intercept,
                          self.slope, self.allow_data_inconsistency)

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


class Couplings(DataArray):

    associated_genres = ['fermi']

    def __init__(
            self, genre, filenames, values, atoms, atoms_coupled=None,
            frequency=100, allow_data_inconsistency=False
    ):
        values = np.asarray(values)
        values = unpack(values) if len(values.shape) == 2 else values
        super().__init__(genre, filenames, values, allow_data_inconsistency)
        self.atoms = atoms
        self.atoms_coupled = atoms_coupled if atoms_coupled is not None else []
        self.frequency = frequency

    atoms = ArrayProperty(dtype=int, check_against=None)
    atoms_coupled = ArrayProperty(dtype=int, check_against=None)
    validate_atoms = staticmethod(validate_atoms)

    @atoms.getter
    def atoms(self) -> np.ndarray:
        return vars(self)['atoms']

    @atoms.setter
    def atoms(self, atoms):
        atoms = validate_atoms(atoms)
        if not len(atoms) == len(self.values[0]) \
                and not self.allow_data_inconsistency:
            raise InconsistentDataError(
                f'Number of atoms ({len(atoms)}) does not match number of '
                f'coupling constants\' lists ({len(self.values[0])}).'
            )
        vars(self)['atoms'] = np.array(atoms)

    @atoms_coupled.getter
    def atoms_coupled(self) -> np.ndarray:
        return vars(self)['atoms_coupled']

    @atoms_coupled.setter
    def atoms_coupled(self, atoms):
        atoms = validate_atoms(atoms)
        if not atoms and (len(self.atoms) == len(self.values[0][0])
                          or self.allow_data_inconsistency):
            atoms = self.atoms
        elif not atoms:
            raise ValueError(
                f"'atoms_coupled' parameter must be specified when creating a "
                f"{type(self)} instance with values as list of unsymmetric "
                f"matrices."
            )
        elif not len(atoms) == len(self.values[0][0]) \
                and not self.allow_data_inconsistency:
            raise InconsistentDataError(
                f"Number of atoms_coupled ({len(atoms)}) does not match number "
                f"of coupling constants' values ({len(self.values[0][0])})."
            )
        vars(self)['atoms_coupled'] = np.array(atoms)

    @property
    def coupling_constants(self):
        return self.values / self.frequency

    def take_atoms(self, atoms=None, couple_with=None):
        atoms = self.validate_atoms(atoms) if atoms is not None else self.atoms
        couple_with = self.validate_atoms(couple_with) \
            if couple_with is not None else self.atoms_coupled
        temp = take_atoms(self.values, self.atoms, atoms).transpose(0, 2, 1)
        new_values = take_atoms(temp, self.atoms_coupled, couple_with)
        new_values = new_values.transpose(0, 2, 1)
        new_atoms = take_atoms(self.atoms, self.atoms, atoms)
        new_coupled = take_atoms(
            self.atoms_coupled, self.atoms_coupled, couple_with
        )
        new_inst = type(self)(
            genre=self.genre, filenames=self.filenames, values=new_values,
            atoms=new_atoms, atoms_coupled=new_coupled,
            frequency=self.frequency,
            allow_data_inconsistency=self.allow_data_inconsistency
        )
        return new_inst

    def drop_atoms(self, atoms=None, couple_with=None):
        # TODO: correct this according to take_atoms
        atoms = self.validate_atoms(atoms) if atoms is not None else self.atoms
        new_atoms = drop_atoms(self.atoms, self.atoms, atoms)
        couple_with = self.validate_atoms(couple_with) \
            if couple_with is not None else new_atoms
        temp = drop_atoms(self.values, self.atoms, atoms)
        new_values = take_atoms(temp.T, self.atoms_coupled, couple_with)
        new_coupled = take_atoms(self.atoms, self.atoms_coupled, couple_with)
        new_inst = type(self)(
            self.genre, self.filenames, new_values, self.frequency, new_atoms,
            new_coupled, self.allow_data_inconsistency
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
        atoms = set(self.atoms)
        atoms_coupled = set(self.atoms_coupled)
        overload = atoms - atoms_coupled
        if overload:
            raise ValueError(
                f"Cannot exclude self-coupling constants if they are not "
                f"included for all atoms. No such constants for these atoms "
                f"found: {', '.join(symbol_of_element(a) for a in overload)}."
            )
        excessive = atoms_coupled - atoms
        cc = self.take_atoms(couple_with=atoms) if excessive else self
        values = drop_diagonals(cc.coupling_constants)
        if excessive:
            other_values = \
                self.take_atoms(couple_with=excessive).coupling_constants
            values = np.concatenate((values, other_values), 2)
        return values

# To convert from index 'n' of 1d storage of symmetric array to 2d array indices
# row = get_triangular_base(n)
# col = n - get_triangular(r)
