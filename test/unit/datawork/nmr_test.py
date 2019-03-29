from unittest import TestCase
import numpy as np
from tesliper.datawork.nmr import drop_diagonals, couple, unpack


class TestUnpack(TestCase):
    def test_two_dimensional(self):
        out = unpack([[1, 2, 3], [4, 5, 6]]).tolist()
        self.assertSequenceEqual(out, [[[1, 2], [2, 3]], [[4, 5], [5, 6]]])

    def test_not_triangular_lenght(self):
        self.assertRaises(ValueError, unpack, [list(range(4))] * 2)

    def test_one_dimensional(self):
        out = unpack([1, 2, 3]).tolist()
        self.assertSequenceEqual(out, [[1, 2], [2, 3]])


class TestDropDiagonals(TestCase):
    def test_one_dim(self):
        arr = np.array([0])
        out = drop_diagonals(arr).tolist()
        self.assertSequenceEqual(out, [])

    def test_two_dim(self):
        arr = np.arange(9).reshape(3, 3)
        out = drop_diagonals(arr).tolist()
        self.assertSequenceEqual(out, [[1, 2], [3, 5], [6, 7]])

    def test_three_dim(self):
        arr = np.arange(18).reshape(2, 3, 3)
        out = drop_diagonals(arr).tolist()
        self.assertSequenceEqual(out, [[[1, 2], [3, 5], [6, 7]],
                                       [[10, 11], [12, 14], [15, 16]]])

    def test_four_dim(self):
        arr = np.arange(9*4).reshape(2, 3, 3, 2)
        out = drop_diagonals(arr).tolist()
        self.assertSequenceEqual(out, [[[[2,  3],  [4, 5]],
                                        [[6,  7],  [10, 11]],
                                        [[12, 13], [14, 15]]],
                                       [[[20, 21], [22, 23]],
                                        [[24, 25], [28, 29]],
                                        [[30, 31], [32, 33]]]])

    def test_one_dim_unsymmetrical(self):
        arr = np.arange(2)
        self.assertRaises(ValueError, drop_diagonals, arr)

    def test_two_dim_unsymmetrical(self):
        arr = np.arange(6).reshape(3, 2)
        self.assertRaises(ValueError, drop_diagonals, arr)

    def test_tree_dim_unsymmetrical(self):
        arr = np.arange(12).reshape(2, 3, 2)
        self.assertRaises(ValueError, drop_diagonals, arr)

    def test_one_value_two_dim(self):
        arr = np.ones(1).reshape(1, 1)
        out = drop_diagonals(arr).tolist()
        self.assertSequenceEqual(out, [[]])

    def test_list_of_one_value_two_dim(self):
        arr = np.ones(2).reshape(2, 1, 1)
        out = drop_diagonals(arr).tolist()
        self.assertSequenceEqual(out, [[[]], [[]]])

    def test_one_value_tree_dim(self):
        arr = np.ones(1).reshape(1, 1, 1)
        out = drop_diagonals(arr).tolist()
        self.assertSequenceEqual(out, [[[]]])

    def test_empty(self):
        arr = np.array([])
        out = drop_diagonals(arr).tolist()
        self.assertSequenceEqual(out, [])

    def test_empty_tree_dim(self):
        arr = np.array([[[]]])
        out = drop_diagonals(arr).tolist()
        self.assertSequenceEqual(out, [])

    def test_empty_four_dim(self):
        arr = np.array([[[[]]]])
        out = drop_diagonals(arr).tolist()
        self.assertSequenceEqual(out, [])


class TestCouple(TestCase):

    def test_separate_peaks(self):
        shield = [[15, 45, 95]]
        coupling = unpack([[0, 2, 0, 6, 4, 0]])
        out = couple(shield, coupling, separate_peaks=True).tolist()
        expected = [[[19, 17, 19, 17, 13, 11, 13, 11],
                     [48, 48, 46, 46, 44, 44, 42, 42],
                     [100, 96, 94, 90, 100, 96, 94, 90]]]
        self.assertSequenceEqual(out, expected)

    def test_both_one_dimensional(self):
        shield = [15, 45, 95]
        coupling = unpack([0, 2, 0, 6, 4, 0])
        out = couple(shield, coupling).tolist()
        expected = [[19, 17, 19, 17, 13, 11, 13, 11, 48, 48, 46, 46,
                     44, 44, 42, 42, 100, 96, 94, 90, 100, 96, 94, 90]]
        self.assertSequenceEqual(out, expected)

    def test_diagonal_omitted(self):
        shield = [[15, 45, 95], [25, 55, 85]]
        coupling = drop_diagonals(unpack([[0, 2, 0, 6, 4, 0],
                                          [0, 4, 0, 8, 10, 0]]))
        out = couple(shield, coupling).tolist()
        expected = [[19, 13, 17, 11, 48, 44, 46, 42, 100, 96, 94, 90],
                    [31, 23, 27, 19, 62, 52, 58, 48, 94, 84, 86, 76]]
        self.assertSequenceEqual(out, expected)

    def test_one_dimensional_dropped_diagonal(self):
        shield = [15, 45, 95]
        coupling = drop_diagonals(unpack([0, 2, 0, 6, 4, 0]))
        out = couple(shield, coupling).tolist()
        expected = [[19, 13, 17, 11, 48, 44, 46, 42, 100, 96, 94, 90]]
        self.assertSequenceEqual(out, expected)

    def test_both_two_dimensional(self):
        shield = [[15, 45, 95], [25, 55, 85]]
        coupling = unpack([[0, 2, 0, 6, 4, 0],
                           [0, 4, 0, 8, 10, 0]])
        out = couple(shield, coupling).tolist()
        expected = [[19, 17, 19, 17, 13, 11, 13, 11, 48, 48, 46, 46,
                     44, 44, 42, 42, 100, 96, 94, 90, 100, 96, 94, 90],
                    [31, 27, 31, 27, 23, 19, 23, 19, 62, 62, 58, 58,
                     52, 52, 48, 48, 94, 84, 86, 76, 94, 84, 86, 76]]
        self.assertSequenceEqual(out, expected)

    def test_coupling_constants_broadcasting(self):
        shield = [[15, 45, 95], [25, 55, 85]]
        coupling = unpack([0, 2, 0, 6, 4, 0])
        out = couple(shield, coupling).tolist()
        expected = [[19, 17, 19, 17, 13, 11, 13, 11, 48, 48, 46, 46,
                     44, 44, 42, 42, 100, 96, 94, 90, 100, 96, 94, 90],
                    [29, 27, 29, 27, 23, 21, 23, 21, 58, 58, 56, 56,
                     54, 54, 52, 52, 90, 86, 84, 80, 90, 86, 84, 80]]
        self.assertSequenceEqual(out, expected)

    def test_shieldings_broadcasting(self):
        shield = [15, 45, 95]
        coupling = unpack([[0, 2, 0, 6, 4, 0],
                           [0, 4, 0, 8, 10, 0]])
        out = couple(shield, coupling).tolist()
        expected = [[19, 17, 19, 17, 13, 11, 13, 11, 48, 48, 46, 46,
                     44, 44, 42, 42, 100, 96, 94, 90, 100, 96, 94, 90],
                    [21, 17, 21, 17, 13, 9, 13, 9, 52, 52, 48, 48,
                     42, 42, 38, 38, 104, 94, 96, 86, 104, 94, 96, 86]]
        self.assertSequenceEqual(out, expected)

    def test_one_d_couplings(self):
        shield = [[15, 45, 95]]
        coupling = unpack([0, 2, 0, 6, 4, 0]).flatten()
        self.assertRaises(ValueError, couple, shield, coupling)

    def test_tree_d_shieldings(self):
        shield = [[[15], [45], [95]]]
        coupling = unpack([0, 2, 0, 6, 4, 0])
        self.assertRaises(ValueError, couple, shield, coupling)

    def test_four_d_couplings(self):
        shield = [[15, 45]]
        coupling = unpack([[0, 2, 0], [6, 4, 0]])[np.newaxis, ...]
        self.assertRaises(ValueError, couple, shield, coupling)

    def test_shieldings_broadcasting_with_dropped_diagonal(self):
        shield = [15, 45, 95]
        coupling = drop_diagonals(unpack([[0, 2, 0, 6, 4, 0],
                                          [0, 4, 0, 8, 10, 0]]))
        out = couple(shield, coupling).tolist()
        expected = [[19, 13, 17, 11, 48, 44, 46, 42, 100, 96, 94, 90],
                    [21, 13, 17, 9, 52, 42, 48, 38, 104, 94, 96, 86]]
        self.assertSequenceEqual(out, expected)

    def test_couplings_broadcasting_with_dropped_diagonal(self):
        shield = [[15, 45, 95], [25, 55, 85]]
        coupling = drop_diagonals(unpack([0, 2, 0, 6, 4, 0]))
        out = couple(shield, coupling).tolist()
        expected = [[19, 13, 17, 11, 48, 44, 46, 42, 100, 96, 94, 90],
                    [29, 23, 27, 21, 58, 54, 56, 52, 90, 86, 84, 80]]
        self.assertSequenceEqual(out, expected)

