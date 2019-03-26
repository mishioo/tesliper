from unittest import TestCase
import numpy as np
from tesliper.datawork.nmr import drop_diagonals, couple, unpack


class TestUnpack(TestCase):
    def test_unpack(self):
        out = unpack([[1, 2, 3], [4, 5, 6]]).tolist()
        self.assertSequenceEqual(out, [[[1, 2], [2, 3]], [[4, 5], [5, 6]]])


class TestDropDiagonals(TestCase):
    def test_empty(self):
        arr = np.array([])
        out = drop_diagonals(arr).tolist()
        self.assertSequenceEqual(out, [])

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

    def test_empty_tree_dim(self):
        arr = np.array([[[]]])
        out = drop_diagonals(arr).tolist()
        self.assertSequenceEqual(out, [])

    def test_empty_four_dim(self):
        arr = np.array([[[[]]]])
        out = drop_diagonals(arr).tolist()
        self.assertSequenceEqual(out, [])


class TestCouple(TestCase):
    pass
