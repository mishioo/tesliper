import unittest as ut
from unittest.mock import Mock
from tesliper.glassware.nmr import Shieldings, Couplings, InconsistentDataError
import numpy as np


class TestShieldings(ut.TestCase):

    def setUp(self):
        self.shield = Shieldings(
            genre='h_mst', filenames=['file1.out', 'file2.out'],
            values=[[30, 40, 60], [40, 60, 70]], molecule_atoms=[1, 1, 1],
            intercept=10, slope=-10
        )
        self.coupl_h_mock = Mock(name="h_couplings_mock")
        self.coupl_h_mock.values = np.asarray(
            [[[.0, .2, .4],
              [.2, .0, .6],
              [.4, .6, .0]],
             [[.0, .2, .6],
              [.2, .0, .8],
              [.6, .8, .0]]]
        )
        self.coupl_h_mock.coupling_constants = self.coupl_h_mock.values
        self.coupl_h_mock.atoms_involved = np.asarray([0, 1, 2])
        self.coupl_h_mock.atoms_coupled = np.asarray([0, 1, 2])
        self.coupl_h_mock.atomic_numbers = np.asarray([1, 1, 1])
        self.coupl_h_mock.atomic_numbers_coupled = np.asarray([1, 1, 1])
        self.coupl_h_mock.exclude_self_couplings.return_value = np.asarray(
            [[[.2, .4], [.2, .6], [.4, .6]],
             [[.2, .6], [.2, .8], [.6, .8]]]
        )
        self.coupl_f_mock = Mock(name="f_couplings_mock")
        self.coupl_f_mock.values = np.asarray([[[2], [0], [0]],
                                               [[3], [0], [0]]])
        self.coupl_f_mock.coupling_constants = self.coupl_f_mock.values
        self.coupl_f_mock.atoms_involved = np.asarray([0, 1, 2])
        self.coupl_f_mock.atoms_coupled = np.asarray([3])
        self.coupl_f_mock.atomic_numbers = np.asarray([1, 1, 1])
        self.coupl_f_mock.atomic_numbers_coupled = np.asarray([9])
        self.coupl_f_mock.exclude_self_couplings.side_effect = ValueError
        self.coupl_mock = Mock(name="couplings_mock")
        self.coupl_mock.values = np.asarray(
            [[[.0, .2, .4, 2],
              [.2, .0, .6, 0],
              [.4, .6, .0, 0]],
             [[.0, .2, .6, 3],
              [.2, .0, .8, 0],
              [.6, .8, .0, 0]]]
        )
        self.coupl_mock.coupling_constants = self.coupl_mock.values
        self.coupl_mock.atoms_involved = np.asarray([0, 1, 2])
        self.coupl_mock.atoms_coupled = np.asarray([0, 1, 2, 3])
        self.coupl_mock.atomic_numbers = np.asarray([1, 1, 1])
        self.coupl_mock.atomic_numbers_coupled = np.asarray([1, 1, 1, 9])
        self.coupl_mock.exclude_self_couplings.return_value = np.asarray(
            [[[.2, .4, 2], [.2, .6, 0], [.4, .6, 0]],
             [[.2, .6, 3], [.2, .8, 0], [.6, .8, 0]]]
        )

        def take_atoms_side_effect(atoms=None, couple_with=np.array([1, 9])):
            couple_with = couple_with.tolist()
            if couple_with == [1]:
                return self.coupl_h_mock
            elif couple_with == [9]:
                return self.coupl_f_mock
            elif couple_with == [1, 9] or couple_with == [9, 1]:
                return self.coupl_mock
            else:
                raise ValueError("This shouldn't suppose to happen!")

        self.coupl_mock.take_atoms.side_effect = take_atoms_side_effect

    def test_molecule_atoms(self):
        self.assertSequenceEqual(self.shield.molecule_atoms.tolist(), [1, 1, 1])

    def test_molecule_atoms_two_dim(self):
        self.shield.molecule_atoms = [[2, 2, 2], [2, 2, 2]]
        self.assertSequenceEqual(self.shield.molecule_atoms.tolist(), [2, 2, 2])

    def test_molecule_atoms_two_dim_different(self):
        with self.assertRaises(InconsistentDataError):
            self.shield.molecule_atoms = [[2, 2, 2], [2, 1, 2]]

    def test_molecule_atoms_too_short(self):
        with self.assertRaises(ValueError):
            self.shield.molecule_atoms = [2, 2]

    def test_molecule_atoms_not_matching_conformers(self):
        with self.assertRaises(InconsistentDataError):
            self.shield.molecule_atoms = [[2, 2, 2]] * 3

    def test_nucleus(self):
        self.assertEqual(self.shield.nucleus, 'H')

    def test_spectra_name(self):
        self.assertEqual(self.shield.spectra_name, 'h_nmr')

    def test_atomic_number(self):
        self.assertEqual(self.shield.atomic_number, 1)

    def test_shielding_values(self):
        self.assertSequenceEqual(
            self.shield.shielding_values.tolist(),
            [[2, 3, 5], [3, 5, 6]]
        )

    def test_atoms(self):
        self.assertSequenceEqual(self.shield.atoms_involved.tolist(), [0, 1, 2])

    @ut.skip("to be created.")
    def test_couple_over_max_cc_num(self):
        out = self.shield.couple(self.coupl_mock)
        self.assertTrue(self.coupl_mock.take_atoms.called)

    def test_couple_all_exclude(self):
        out = self.shield.couple(self.coupl_mock)
        self.assertTrue(self.coupl_mock.take_atoms.called)
        self.assertSequenceEqual(
            [1, [1, 9]],
            [self.coupl_mock.take_atoms.call_args[0][0],
             self.coupl_mock.take_atoms.call_args[0][1].tolist()]
        )
        self.assertTrue(self.coupl_mock.exclude_self_couplings.called)
        self.assertSequenceEqual(
            out.values.tolist(),
            [[[31.3, 30.9, 31.1, 30.7, 29.3, 28.9, 29.1, 28.7],
              [40.4, 39.8, 40.2, 39.6, 40.4, 39.8, 40.2, 39.6],
              [60.5, 59.9, 60.1, 59.5, 60.5, 59.9, 60.1, 59.5]],
             [[41.9, 41.3, 41.7, 41.1, 38.9, 38.3, 38.7, 38.1],
              [60.5, 59.7, 60.3, 59.5, 60.5, 59.7, 60.3, 59.5],
              [70.7, 69.9, 70.1, 69.3, 70.7, 69.9, 70.1, 69.3]]]
        )

    def test_couple_all_no_exclude(self):
        out = self.shield.couple(self.coupl_mock, exclude_self_couplings=False)
        self.assertTrue(self.coupl_mock.take_atoms.called)
        self.assertSequenceEqual(
            [1, [1, 9]],
            [self.coupl_mock.take_atoms.call_args[0][0],
             self.coupl_mock.take_atoms.call_args[0][1].tolist()]
        )
        self.assertFalse(self.coupl_mock.exclude_self_couplings.called)
        self.assertSequenceEqual(
            out.values.tolist(),
            [[[31.3, 31.1, 31.3, 31.1, 30.9, 30.7, 30.9, 30.7, 29.3, 29.1,
               29.3, 29.1, 28.9, 28.7, 28.9, 28.7],
              [40.4, 40.4, 40.2, 40.2, 39.8, 39.8, 39.6, 39.6, 40.4, 40.4,
               40.2, 40.2, 39.8, 39.8, 39.6, 39.6],
              [60.5, 59.9, 60.1, 59.5, 60.5, 59.9, 60.1, 59.5, 60.5, 59.9,
               60.1, 59.5, 60.5, 59.9, 60.1, 59.5]],
             [[41.9, 41.7, 41.9, 41.7, 41.3, 41.1, 41.3, 41.1, 38.9, 38.7,
               38.9, 38.7, 38.3, 38.1, 38.3, 38.1],
              [60.5, 60.5, 60.3, 60.3, 59.7, 59.7, 59.5, 59.5, 60.5, 60.5,
               60.3, 60.3, 59.7, 59.7, 59.5, 59.5],
              [70.7, 69.9, 70.1, 69.3, 70.7, 69.9, 70.1, 69.3, 70.7, 69.9,
               70.1, 69.3, 70.7, 69.9, 70.1, 69.3]]]
        )

    def test_couple_bare_coupling_constants(self):
        out = self.shield.couple(
            [[[.2, .4], [.2, .6], [.4, .6]], [[.2, .6], [.2, .8], [.6, .8]]],
            exclude_self_couplings=False
        )
        self.assertFalse(self.coupl_mock.take_atoms.called)
        self.assertFalse(self.coupl_mock.exclude_self_couplings.called)
        self.assertSequenceEqual(
            out.values.tolist(),
            [[[30.3, 29.9, 30.1, 29.7],
              [40.4, 39.8, 40.2, 39.6],
              [60.5, 59.9, 60.1, 59.5]],
             [[40.4, 39.8, 40.2, 39.6],
              [60.5, 59.7, 60.3, 59.5],
              [70.7, 69.9, 70.1, 69.3]]]
        )

    def test_couple_bare_coupling_constants_with_dropping(self):
        out = self.shield.couple(
            [[[.0, .2, .4], [.2, .0, .6], [.4, .6, .0]],
             [[.0, .2, .6], [.2, .0, .8], [.6, .8, .0]]]
        )
        self.assertFalse(self.coupl_mock.take_atoms.called)
        self.assertFalse(self.coupl_mock.exclude_self_couplings.called)
        self.assertSequenceEqual(
            out.values.tolist(),
            [[[30.3, 29.9, 30.1, 29.7],
              [40.4, 39.8, 40.2, 39.6],
              [60.5, 59.9, 60.1, 59.5]],
             [[40.4, 39.8, 40.2, 39.6],
              [60.5, 59.7, 60.3, 59.5],
              [70.7, 69.9, 70.1, 69.3]]]
        )

    def test_couple_bare_coupling_constants_couple_with_given(self):
        self.assertRaises(
            ValueError, self.shield.couple, [[[2], [2], [4]], [[2], [2], [6]]],
            1, False
        )

    def test_couple_bare_coupling_constants_cant_drop_diag(self):
        self.assertRaises(
            ValueError, self.shield.couple,
            [[[2, 4], [2, 6], [4, 6]], [[2, 6], [2, 8], [6, 8]]], None, True
        )


class TestCouplings(ut.TestCase):
    # TODO: mock functions used by methods tested

    def setUp(self):
        self.std = dict(
            genre='fermi', filenames=['file1.out', 'file2.out'],
            molecule_atoms=[1, 1, 1, 9],
            values=[[[0, 2, 4, 20],
                     [2, 0, 6, 0],
                     [4, 6, 0, 0],
                     [20, 0, 0, 0]],
                    [[0, 2, 6, 24],
                     [2, 0, 8, 0],
                     [6, 8, 0, 0],
                     [24, 0, 0, 0]]]
        )
        self.cpl = Couplings(**self.std)

    def test_atoms(self):
        self.assertTrue(self.cpl.atoms_involved.dtype, int)
        self.assertSequenceEqual(self.cpl.atoms_involved.tolist(), [0, 1, 2, 3])

    def test_atoms_coupled(self):
        self.assertTrue(self.cpl.atoms_coupled.dtype, int)
        self.assertSequenceEqual(self.cpl.atoms_coupled.tolist(), [0, 1, 2, 3])

    def test_nuclei(self):
        self.assertTrue(self.cpl.nuclei.dtype, int)
        self.assertSequenceEqual(self.cpl.nuclei.tolist(), "H H H F".split())

    def test_nuclei_coupled(self):
        self.assertTrue(self.cpl.nuclei_coupled.dtype, int)
        self.assertSequenceEqual(
            self.cpl.nuclei_coupled.tolist(), "H H H F".split()
        )

    def test_atomic_numbers(self):
        self.assertTrue(self.cpl.atomic_numbers.dtype, int)
        self.assertSequenceEqual(self.cpl.atomic_numbers.tolist(), [1, 1, 1, 9])

    def test_atomic_numbers_coupled(self):
        self.assertTrue(self.cpl.atomic_numbers_coupled.dtype, int)
        self.assertSequenceEqual(
            self.cpl.atomic_numbers_coupled.tolist(), [1, 1, 1, 9]
        )

    def test_inconsistent_atoms(self):
        params = self.std.copy()
        params['atoms_coupled'] = [0, 1, 2]
        self.assertRaises(InconsistentDataError, Couplings, **params)

    def test_inst_with_unpack(self):
        params = self.std.copy()
        params['values'] = [[0, 2, 0, 4, 6, 0], [0, 2, 0, 6, 8, 0]]
        params['molecule_atoms'] = [1, 1, 1]
        cpl = Couplings(**params)
        self.assertSequenceEqual(
            cpl.values.tolist(),
            [[[0, 2, 4], [2, 0, 6], [4, 6, 0]],
             [[0, 2, 6], [2, 0, 8], [6, 8, 0]]]
        )

    def test_exclude_self_couplings_not_enough_values(self):
        params = self.std.copy()
        params['values'] = [[[0, 2, 4],
                             [2, 0, 6],
                             [4, 6, 0],
                             [20, 0, 0]],
                            [[0, 2, 6],
                             [2, 0, 8],
                             [6, 8, 0],
                             [24, 0, 0]]]
        params['atoms_coupled'] = [0, 1, 2]
        cpl = Couplings(**params)
        self.assertRaises(ValueError, cpl.exclude_self_couplings)

    def test_exclude_self_couplings_unsymmetrical(self):
        params = self.std.copy()
        params['values'] = [[[0, 2, 4, 20],
                             [2, 0, 6, 0],
                             [4, 6, 0, 0]],
                            [[0, 2, 6, 24],
                             [2, 0, 8, 0],
                             [6, 8, 0, 0]]]
        params['atoms_involved'] = [0, 1, 2]
        params['atoms_coupled'] = [0, 1, 2, 3]
        cpl = Couplings(**params)
        out = cpl.exclude_self_couplings().tolist()
        self.assertSequenceEqual(
            out,
            [[[0.02, 0.04, 0.2],
              [0.02, 0.06, 0],
              [0.04, 0.06, 0]],
             [[0.02, 0.06, 0.24],
              [0.02, 0.08, 0],
              [0.06, 0.08, 0]]]
        )

    def test_exclude_self_couplings(self):
        out = self.cpl.exclude_self_couplings().tolist()
        self.assertSequenceEqual(
            out,
            [[[0.02, 0.04, 0.2],
              [0.02, 0.06, 0],
              [0.04, 0.06, 0],
              [0.2, 0, 0]],
             [[0.02, 0.06, 0.24],
              [0.02, 0.08, 0],
              [0.06, 0.08, 0],
              [0.24, 0, 0]]]
        )

    def test_coupling_constants_values(self):
        self.assertSequenceEqual(self.cpl.coupling_constants.tolist(),
                                 [[[0, 0.02, 0.04, 0.2],
                                   [0.02, 0, 0.06, 0],
                                   [0.04, 0.06, 0, 0],
                                   [0.2, 0, 0, 0]],
                                  [[0, 0.02, 0.06, 0.24],
                                   [0.02, 0, 0.08, 0],
                                   [0.06, 0.08, 0.00, 0],
                                   [0.24, 0, 0, 0]]]
                                 )

    def test_take_atoms_all(self):
        new = self.cpl.take_atoms()
        self.assertSequenceEqual(new.atoms_involved.tolist(), [0, 1, 2, 3])
        self.assertSequenceEqual(new.atoms_coupled.tolist(), [0, 1, 2, 3])
        self.assertSequenceEqual(new.values.shape, (2, 4, 4))
        self.assertSequenceEqual(
            new.values.tolist(),
            [[[0, 2, 4, 20], [2, 0, 6, 0], [4, 6, 0, 0], [20, 0, 0, 0]],
             [[0, 2, 6, 24], [2, 0, 8, 0], [6, 8, 0, 0], [24, 0, 0, 0]]]
        )

    def test_take_atoms_h(self):
        new = self.cpl.take_atoms(atoms=1)
        self.assertSequenceEqual(new.atoms_involved.tolist(), [0, 1, 2])
        self.assertSequenceEqual(new.atoms_coupled.tolist(), [0, 1, 2, 3])
        self.assertSequenceEqual(new.values.shape, (2, 3, 4))
        self.assertSequenceEqual(
            new.values.tolist(),
            [[[0, 2, 4, 20], [2, 0, 6, 0], [4, 6, 0, 0]],
             [[0, 2, 6, 24], [2, 0, 8, 0], [6, 8, 0, 0]]]
        )

    def test_take_atoms_h_couple_h(self):
        new = self.cpl.take_atoms(atoms=1, coupled_with=1)
        self.assertSequenceEqual(new.atoms_involved.tolist(), [0, 1, 2])
        self.assertSequenceEqual(new.atoms_coupled.tolist(), [0, 1, 2])
        self.assertSequenceEqual(new.values.shape, (2, 3, 3))
        self.assertSequenceEqual(
            new.values.tolist(),
            [[[0, 2, 4], [2, 0, 6], [4, 6, 0]],
             [[0, 2, 6], [2, 0, 8], [6, 8, 0]]]
        )

    def test_take_couple_h(self):
        new = self.cpl.take_atoms(coupled_with=1)
        self.assertSequenceEqual(new.atoms_involved.tolist(), [0, 1, 2, 3])
        self.assertSequenceEqual(new.atoms_coupled.tolist(), [0, 1, 2])
        self.assertSequenceEqual(new.values.shape, (2, 4, 3))
        self.assertSequenceEqual(
            new.values.tolist(),
            [[[0, 2, 4], [2, 0, 6], [4, 6, 0], [20, 0, 0]],
             [[0, 2, 6], [2, 0, 8], [6, 8, 0], [24, 0, 0]]]
        )

    def test_take_atoms_couple_f(self):
        new = self.cpl.take_atoms(coupled_with=9)
        self.assertSequenceEqual(new.atoms_involved.tolist(), [0, 1, 2, 3])
        self.assertSequenceEqual(new.atoms_coupled.tolist(), [3])
        self.assertSequenceEqual(new.values.shape, (2, 4, 1))
        self.assertSequenceEqual(
            new.values.tolist(), [[[20], [0], [0], [0]], [[24], [0], [0], [0]]]
        )

    def test_take_atoms_h_couple_f(self):
        new = self.cpl.take_atoms(atoms=1, coupled_with=9)
        self.assertSequenceEqual(new.atoms_involved.tolist(), [0, 1, 2])
        self.assertSequenceEqual(new.atoms_coupled.tolist(), [3])
        self.assertSequenceEqual(new.values.shape, (2, 3, 1))
        self.assertSequenceEqual(
            new.values.tolist(), [[[20], [0], [0]], [[24], [0], [0]]]
        )

    def test_drop_atoms_no_parameters(self):
        new = self.cpl.drop_atoms()
        self.assertSequenceEqual(new.values.tolist(), self.cpl.values.tolist())

    def test_drop_atoms_h(self):
        new = self.cpl.drop_atoms(atoms=1)
        self.assertSequenceEqual(
            new.values.tolist(), [[[20, 0, 0, 0]], [[24, 0, 0, 0]]]
        )

    def test_drop_atoms_h_coupled_h(self):
        new = self.cpl.drop_atoms(atoms=1, coupled_with=1)
        self.assertSequenceEqual(
            new.values.tolist(), [[[0]], [[0]]]
        )

    def test_drop_atoms_h_coupled_f(self):
        new = self.cpl.drop_atoms(atoms=1, coupled_with=9)
        self.assertSequenceEqual(
            new.values.tolist(), [[[20, 0, 0]], [[24, 0, 0]]]
        )

    def test_drop_atoms_coupled_h(self):
        new = self.cpl.drop_atoms(coupled_with=1)
        self.assertSequenceEqual(
            new.values.tolist(), [[[20], [0], [0], [0]], [[24], [0], [0], [0]]]
        )

    def test_is_symmetric(self):
        self.assertTrue(self.cpl.is_symmetric)

    def test_not_is_symmetric(self):
        params = self.std.copy()
        params['values'] = [[[0, 2, 4, 20],
                             [2, 0, 6, 0],
                             [4, 6, 0, 0]],
                            [[0, 2, 6, 24],
                             [2, 0, 8, 0],
                             [6, 8, 0, 0]]]
        params['atoms_involved'] = [0, 1, 2]
        params['atoms_coupled'] = [0, 1, 2, 3]
        cpl = Couplings(**params)
        self.assertFalse(cpl.is_symmetric)

    def test_average_positions(self):
        cpl = self.cpl.average_positions((0, 1, 2))
        self.assertSequenceEqual(cpl.values.tolist(),
                                 [[[0, 4, 4, 20],
                                   [4, 0, 4, 0],
                                   [4, 4, 0, 0],
                                   [20, 0, 0, 0]],
                                  [[0, 16/3, 16/3, 24],
                                   [16/3, 0, 16/3, 0],
                                   [16/3, 16/3, 0, 0],
                                   [24, 0, 0, 0]]]
                                 )

    def test_suppress_coupling_pair(self):
        cpl = self.cpl.suppress_coupling([1, 2])
        self.assertSequenceEqual(
            cpl.values.tolist(),
            [[[0, 2, 4, 20],
              [2, 0, 0, 0],
              [4, 0, 0, 0],
              [20, 0, 0, 0]],
             [[0, 2, 6, 24],
              [2, 0, 0, 0],
              [6, 0, 0, 0],
              [24, 0, 0, 0]]]
        )

    def test_suppress_coupling_list_one_pair(self):
        cpl = self.cpl.suppress_coupling([[1, 2]])
        self.assertSequenceEqual(
            cpl.values.tolist(),
            [[[0, 2, 4, 20],
              [2, 0, 0, 0],
              [4, 0, 0, 0],
              [20, 0, 0, 0]],
             [[0, 2, 6, 24],
              [2, 0, 0, 0],
              [6, 0, 0, 0],
              [24, 0, 0, 0]]]
        )

    def test_suppress_coupling_list_two_pairs(self):
        cpl = self.cpl.suppress_coupling([[0, 1], [0, 3]])
        self.assertSequenceEqual(
            cpl.values.tolist(),
            [[[0, 0, 4, 0],
              [0, 0, 6, 0],
              [4, 6, 0, 0],
              [0, 0, 0, 0]],
             [[0, 0, 6, 0],
              [0, 0, 8, 0],
              [6, 8, 0, 0],
              [0, 0, 0, 0]]]
        )

    def test_suppress_coupling_unsymmetrical(self):
        params = self.std.copy()
        params['values'] = [[[0, 2, 4, 20],
                             [2, 0, 6, 0],
                             [4, 6, 0, 0]],
                            [[0, 2, 6, 24],
                             [2, 0, 8, 0],
                             [6, 8, 0, 0]]]
        params['atoms_involved'] = [0, 1, 2]
        params['atoms_coupled'] = [0, 1, 2, 3]
        cpl = Couplings(**params).suppress_coupling([0, 3])
        self.assertSequenceEqual(
            cpl.values.tolist(),
            [[[0, 2, 4, 0],
              [2, 0, 6, 0],
              [4, 6, 0, 0]],
             [[0, 2, 6, 0],
              [2, 0, 8, 0],
              [6, 8, 0, 0]]]
        )

    def test_suppress_coupling_unsymmetrical_other(self):
        params = self.std.copy()
        params['values'] = [[[0, 2, 4],
                             [2, 0, 6],
                             [4, 6, 0],
                             [20, 0, 0]],
                            [[0, 2, 6],
                             [2, 0, 8],
                             [6, 8, 0],
                             [24, 0, 0]]]
        params['atoms_coupled'] = [0, 1, 2]
        cpl = Couplings(**params).suppress_coupling([0, 3])
        self.assertSequenceEqual(
            cpl.values.tolist(),
            [[[0, 2, 4],
              [2, 0, 6],
              [4, 6, 0],
              [0, 0, 0]],
             [[0, 2, 6],
              [2, 0, 8],
              [6, 8, 0],
              [0, 0, 0]]]
        )

    def test_suppress_coupling_atom_out_of_range(self):
        self.assertRaises(ValueError, self.cpl.suppress_coupling, [1, 4])
