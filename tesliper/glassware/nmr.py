import numpy as np

from .array_base import ArrayProperty
from .arrays import DataArray, Spectra
from ..exceptions import InconsistentDataError
from ..datawork.helpers import (
    atomic_number, is_triangular, get_triangular, get_triangular_base,
    take_atoms, drop_atoms, _symbol as atoms_symbols
)
from ..datawork.nmr import unpack, couple, drop_diagonals
from ..datawork.spectra import calculate_spectra


class _Atoms:

    atoms = ArrayProperty(dtype=int, check_against=None)

    @atoms.getter
    def atoms(self) -> np.ndarray:
        return vars(self)['atoms']

    @atoms.setter
    def atoms(self,  # type: Shieldings or Couplings
              atoms):
        if not len(atoms) == len(self.values[0]) \
                and not self.allow_data_inconsistency:
            raise InconsistentDataError(
                f'Number of atoms ({len(atoms)}) does not match number of '
                f'shielding values ({len(self.values[0])}).'
            )
        vars(self)['atoms'] = atoms  # as np.ndarray via ArrayProperty

    def take_atoms(self,  # type: Shieldings or Couplings
                   atoms):
        new_values = take_atoms(self.values, self.atoms, atoms)
        new_atoms = take_atoms(self.atoms, self.atoms, atoms)
        new_inst = type(self)(self.genre, self.filenames, new_values, new_atoms,
                              self.allow_data_inconsistency)
        return new_inst

    def drop_atoms(self,  # type: Shieldings or Couplings
                   atoms):
        new_values = drop_atoms(self.values, self.atoms, atoms)
        new_atoms = drop_atoms(self.atoms, self.atoms, atoms)
        new_inst = type(self)(self.genre, self.filenames, new_values, new_atoms,
                              self.allow_data_inconsistency)
        return new_inst

    @staticmethod
    def _validate_atoms(atoms):
        if isinstance(atoms, str):
            atoms = atoms.split()
        elif isinstance(atoms, int):
            atoms = [atoms]
        return [atomic_number(a) for a in atoms]


class Shieldings(DataArray):

    associated_genres = [
        genre for atom in atoms_symbols.values()
        for genre in (f'{atom.lower()}_mst', f'{atom.lower()}_mst_aniso')
    ]

    def __init__(
            self, genre, filenames, values, intercept=0, slope=-1,
            allow_data_inconsistency=False
    ):
        super().__init__(genre, filenames, values, allow_data_inconsistency)
        self.intercept = intercept
        self.slope = slope

    @property
    def nucleus(self):
        return self.genre.split('_')[0].capitalize()

    @property
    def atoms(self):
        return atomic_number(self.nucleus)

    @property
    def shielding_values(self):
        values = self.values.reshape(self.values.shape[0], -1)
        return (values - self.intercept) / -self.slope

    def couple(self, couplings, frequency, couple_with=None):
        couple_with = couple_with if couple_with else couplings.atoms_coupled
        couplings.take_atoms(self.atoms)
        couplings = Couplings(
            couplings.genre, couplings.filenames, couplings.values / frequency,
            couplings.atoms, couplings.atoms_coupled,
            couplings.allow_data_inconsistency, unpack_values=False
        )  # use constants scaled to requested frequency
        if self.atoms in couple_with:
            couplings_ = couplings.take_atoms(couple_with=self.atoms)
            couplings_ = couplings_.drop_diagonals()
            values = couple(self.shielding_values, couplings_)
            couple_with = couple_with[couple_with != self.atoms]
        else:
            values = self.shielding_values
        if couple_with.size:
            couplings_ = couplings.take_atoms(couple_with=couple_with).values
            values = couple(values, couplings_)
        return values

    def calculate_spectrum(self, start, stop, step, width, fitting):
        abscissa = np.arange(start, stop, step)
        values = calculate_spectra(
            self.shielding_values, np.ones_like(self.shielding_values),
            abscissa, width, fitting
        )
        spectra_name = self.spectra_name  # implement this
        fitting_name = fitting.__name__
        spectra = Spectra(
            spectra_name, self.filenames, values, abscissa, width, fitting_name
        )
        return spectra


class Couplings(DataArray, _Atoms):

    def __init__(
            self, genre, filenames, values, atoms, atoms_coupled=None,
            allow_data_inconsistency=False, unpack_values=True
    ):
        values = unpack(values) if unpack_values else values
        super().__init__(genre, filenames, values, allow_data_inconsistency)
        self.atoms = atoms
        self.atoms_coupled = atoms_coupled if not unpack_values else atoms

    atoms_coupled = ArrayProperty(dtype=int, check_against=None)

    @atoms_coupled.getter
    def atoms_coupled(self) -> np.ndarray:
        return vars(self)['atoms_coupled']

    @atoms_coupled.setter
    def atoms_coupled(self, atoms):
        if not len(atoms) == len(self.values[1]) \
                and not self.allow_data_inconsistency:
            raise InconsistentDataError(
                f"Number of atoms_coupled ({len(atoms)}) does not match number "
                f"of coupling constants' values ({len(self.values[1])})."
            )
        vars(self)['atoms_coupled'] = atoms  # as np.ndarray via ArrayProperty

    def take_atoms(self, atoms=None, couple_with=None):
        atoms = self._validate_atoms(atoms) if atoms else self.atoms
        couple_with = \
            self._validate_atoms(couple_with) if couple_with else atoms
        temp = take_atoms(self.values, self.atoms, atoms)
        new_values = take_atoms(temp.T, self.atoms, couple_with)
        new_atoms = take_atoms(self.atoms, self.atoms, atoms)
        new_coupled = take_atoms(self.atoms, self.atoms_coupled, couple_with)
        new_inst = type(self)(
            self.genre, self.filenames, new_values, new_atoms, new_coupled,
            self.allow_data_inconsistency, unpack_values=False
        )
        return new_inst

    def drop_atoms(self, atoms=None, couple_with=None):
        atoms = self._validate_atoms(atoms) if atoms else self.atoms
        new_atoms = drop_atoms(self.atoms, self.atoms, atoms)
        couple_with = \
            self._validate_atoms(couple_with) if couple_with else new_atoms
        temp = drop_atoms(self.values, self.atoms, atoms)
        new_values = take_atoms(temp.T, self.atoms_coupled, couple_with)
        new_coupled = take_atoms(self.atoms, self.atoms_coupled, couple_with)
        new_inst = type(self)(
            self.genre, self.filenames, new_values, new_atoms, new_coupled,
            self.allow_data_inconsistency, unpack_values=False)
        return new_inst

    def drop_diagonals(self):
        if not self.atoms.shape == self.atoms_coupled.shape:
            raise InconsistentDataError(
                'Cannot drop a diagonal of a non-symmetric matrix.'
            )
        return drop_diagonals(self.values)

# To convert from index 'n' of 1d storage of symmetric array to 2d array indices
# row = get_triangular_base(n)
# col = n - get_triangular(r)
