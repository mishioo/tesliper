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


class Atoms:

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
    def validate_atoms(atoms):
        if isinstance(atoms, str):
            atoms = atoms.split()
        elif isinstance(atoms, (int, float)):
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

    validate_atoms = Atoms.validate_atoms

    def couple(self, couplings, couple_with=None, exclude_self_couplings=True):
        """Returns new Shieldings instance, representing peaks coupled with
        given coupling constants values.

        This function will exclude atoms' self-coupling constants if given
        Couplings instance include those with the same nuclei, that Shieldings
        instance deal with. This can be suppressed by setting
        `exclude_self_couplings` parameter to False. Parameter `couple_with` is
        always validated with self.validate_atoms method.

        Parameters
        ----------
        couplings : Couplings
            coupling constants used to couple shielding values
        couple_with : int, str iterable of int, or iterable of str, optional
            atom's symbol, atomic number or list of those; specifies by which
            coupling constants should shielding values be coupled; all coupling
            constants contained in given Couplings instance are used, if
            `couple_with` is not specified
        exclude_self_couplings : bool, optional
            specifies if self-coupling constants should be discarded, if there
            are any; defaults to True

        Returns
        -------
        Shieldings
            new instance with coupled peaks as values"""
        couple_with = couple_with if couple_with else couplings.atoms_coupled
        couple_with = np.array(self.validate_atoms(couple_with))
        couplings = couplings.take_atoms(self.atomic_number, couple_with)
        if self.atomic_number in couple_with and exclude_self_couplings:
            cc_values = couplings.exclude_self_couplings()
        else:
            cc_values = couplings.coupling_constants
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


class Couplings(DataArray, Atoms):

    associated_genres = ['fermi']

    def __init__(
            self, genre, filenames, values, frequency, atoms,
            atoms_coupled=None, allow_data_inconsistency=False
    ):
        values = np.asarray(values)
        values = unpack(values) if len(values.shape) == 2 else values
        super().__init__(genre, filenames, values, allow_data_inconsistency)
        self.atoms = atoms
        self.atoms_coupled = atoms_coupled
        self.frequency = frequency

    atoms_coupled = ArrayProperty(dtype=int, check_against=None)

    @atoms_coupled.getter
    def atoms_coupled(self) -> np.ndarray:
        return vars(self)['atoms_coupled']

    @atoms_coupled.setter
    def atoms_coupled(self, atoms):
        if atoms is None and (len(self.atoms) == len(self.values[1])
                              or self.allow_data_inconsistency):
            atoms = self.atoms
        elif atoms is None:
            raise ValueError(
                f"'atoms_coupled' parameter must be specified when creating a "
                f"{type(self)} instance with values as list of unsymmetric "
                f"matrices."
            )
        elif not len(atoms) == len(self.values[1]) \
                and not self.allow_data_inconsistency:
            raise InconsistentDataError(
                f"Number of atoms_coupled ({len(atoms)}) does not match number "
                f"of coupling constants' values ({len(self.values[1])})."
            )
        vars(self)['atoms_coupled'] = atoms  # as np.ndarray via ArrayProperty

    @property
    def coupling_constants(self):
        return self.values / self.frequency

    def take_atoms(self, atoms=None, couple_with=None):
        atoms = self.validate_atoms(atoms) if atoms else self.atoms
        couple_with = \
            self.validate_atoms(couple_with) if couple_with else atoms
        temp = take_atoms(self.values, self.atoms, atoms)
        new_values = take_atoms(temp.T, self.atoms, couple_with)
        new_atoms = take_atoms(self.atoms, self.atoms, atoms)
        new_coupled = take_atoms(self.atoms, self.atoms_coupled, couple_with)
        new_inst = type(self)(
            self.genre, self.filenames, new_values, self.frequency, new_atoms,
            new_coupled, self.allow_data_inconsistency
        )
        return new_inst

    def drop_atoms(self, atoms=None, couple_with=None):
        atoms = self.validate_atoms(atoms) if atoms else self.atoms
        new_atoms = drop_atoms(self.atoms, self.atoms, atoms)
        couple_with = \
            self.validate_atoms(couple_with) if couple_with else new_atoms
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
        if atoms - atoms_coupled:
            raise ValueError(
                f"Cannot exclude self-coupling constants if they are not "
                f"included for all atoms. No such constants for these atoms "
                f"found: "
                f"{', '.join(atoms_symbols(a) for a in atoms - atoms_coupled)}."
            )
        excessive = atoms_coupled - atoms
        cc = self.take_atoms(couple_with=atoms) if excessive else self
        values = drop_diagonals(cc.coupling_constants)
        if excessive:
            values = np.concatenate(
                (values, self.take_atoms(couple_with=excessive)), 2
            )
        return values

# To convert from index 'n' of 1d storage of symmetric array to 2d array indices
# row = get_triangular_base(n)
# col = n - get_triangular(r)
