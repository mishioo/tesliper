import unittest as ut
from tesliper.datawork import spectra as sp


class CalculateAverageTest(ut.TestCase):

    def test_one_dim(self):
        out = sp.calculate_average([2, 6], [.25, .75])
        self.assertEqual(out, 5)

    def test_two_dims(self):
        out = sp.calculate_average([[2, 4], [6, 8]], [.25, .75])
        self.assertEqual(out.tolist(), [5, 7])

    def test_three_dims(self):
        out = sp.calculate_average(
            [[[2, 4], [6, 8]],
             [[6, 8], [6, 12]]],
            [.25, .75])
        self.assertEqual(out.tolist(), [[5, 7], [6, 11]])

    def test_normalize(self):
        out = sp.calculate_average([2, 6], [1, 3])
        self.assertEqual(out, 5)

    def test_unmatching_sizes(self):
        self.assertRaises(ValueError, sp.calculate_average, [1, 2], [1, 2, 3])
        self.assertRaises(ValueError, sp.calculate_average, [1, 2, 3], [1, 2])
        self.assertRaises(ValueError, sp.calculate_average, [1, 2, 3], 1)

