import unittest as ut
from unittest.mock import Mock
import numpy as np
from tesliper.datawork import spectra as sp


class CountImaginaryTest(ut.TestCase):
    def test_empty_array(self):
        self.assertSequenceEqual(sp.count_imaginary(np.array([])).tolist(), [])

    def test_single_value_positive(self):
        self.assertEqual(sp.count_imaginary(np.array([1])).tolist(), 0)

    def test_single_value_zero(self):
        self.assertEqual(sp.count_imaginary(np.array([0])).tolist(), 0)

    def test_single_value_negative(self):
        self.assertEqual(sp.count_imaginary(np.array([-1])).tolist(), 1)

    def test_zero_dimensions_positive(self):
        self.assertEqual(sp.count_imaginary(np.array(1, dtype=int)).tolist(), 0)

    def test_zero_dimensions_zero(self):
        self.assertEqual(sp.count_imaginary(np.array(0, dtype=int)).tolist(), 0)

    def test_zero_dimensions_negative(self):
        self.assertEqual(sp.count_imaginary(np.array(-1, dtype=int)).tolist(), 1)

    def test_zero_imag_one_conf(self):
        self.assertSequenceEqual(
            sp.count_imaginary(np.arange(0, 6, 1).reshape(1, -1)).tolist(), [0]
        )

    def test_one_imag_one_conf(self):
        self.assertSequenceEqual(
            sp.count_imaginary(np.arange(-1, 6, 1).reshape(1, -1)).tolist(), [1]
        )

    def test_zero_imag_two_confs(self):
        self.assertSequenceEqual(
            sp.count_imaginary(np.arange(0, 6, 1).reshape(2, -1)).tolist(), [0, 0]
        )

    def test_one_imag_two_confs(self):
        self.assertSequenceEqual(
            sp.count_imaginary(np.arange(-1, 5, 1).reshape(2, -1)).tolist(), [1, 0]
        )

    def test_two_imag_two_confs(self):
        self.assertSequenceEqual(
            sp.count_imaginary(np.array([[1, -1, 1], [-1, 1, 1]])).tolist(), [1, 1]
        )

    def test_tree_dimensions(self):
        self.assertRaises(ValueError, sp.count_imaginary, np.array([[[1]]]))


class FindImaginaryTest(ut.TestCase):
    def test_less_dim_zero_imag(self):
        self.assertSequenceEqual(
            sp.find_imaginary(np.arange(0, 6, 1).reshape(1, -1)).tolist(), []
        )

    def test_less_dim_one_imag(self):
        self.assertSequenceEqual(
            sp.find_imaginary(np.arange(-1, 5, 1).reshape(1, -1)).tolist(), [0]
        )

    def test_zero_imag(self):
        self.assertSequenceEqual(
            sp.find_imaginary(np.arange(0, 6, 1).reshape(2, -1)).tolist(), []
        )

    def test_imag_at_first(self):
        self.assertSequenceEqual(
            sp.find_imaginary(np.arange(-1, 5, 1).reshape(2, -1)).tolist(), [0]
        )

    def test_imag_at_second(self):
        self.assertSequenceEqual(
            sp.find_imaginary(np.array([[1, 1, 1], [1, -1, 1]])).tolist(), [1]
        )

    def test_more_dimensions(self):
        self.assertRaises(ValueError, sp.find_imaginary, np.array([[[1]]]))


class GaussianTest(ut.TestCase):
    def test_mean_0_std_dev_1(self):
        np.testing.assert_array_almost_equal(
            sp.gaussian(np.array([1]), np.array([0]), np.arange(-5, 6, 1), np.sqrt(2)),
            [
                0.0000014867195147343,
                0.0001338302257648850,
                0.0044318484119380100,
                0.0539909665131881000,
                0.2419707245191430000,
                0.3989422804014330000,
                0.2419707245191430000,
                0.0539909665131881000,
                0.0044318484119380100,
                0.0001338302257648850,
                0.0000014867195147343,
            ],  # values from Excel 2010 NORM.DIST
        )

    def test_width_zero(self):
        self.assertRaises(
            ValueError,
            sp.gaussian,
            np.array([1]),
            np.array([0]),
            np.arange(-5, 6, 1),
            0,
        )

    def test_width_below_zero(self):
        self.assertRaises(
            ValueError,
            sp.gaussian,
            np.array([1]),
            np.array([0]),
            np.arange(-5, 6, 1),
            -1,
        )

    def test_unequal_sizes(self):
        self.assertRaises(
            ValueError,
            sp.gaussian,
            np.array([1, 2]),
            np.array([0]),
            np.arange(-5, 6, 1),
            1,
        )

    def test_empty_intensities(self):
        out = sp.gaussian(np.array([]), np.array([]), np.arange(-5, 6, 1), 1)
        self.assertSequenceEqual(out.tolist(), np.zeros(11).tolist())

    def test_empty_abscissia(self):
        out = sp.gaussian(np.array([1]), np.array([0]), np.array([]), 1)
        self.assertSequenceEqual(out.tolist(), [])


class LorentzianTest(ut.TestCase):
    def test_mean_0_std_dev_1(self):
        np.testing.assert_array_almost_equal(
            sp.lorentzian(
                np.array([1]), np.array([0]), np.arange(-5, 6, 1), 1 / 2  # L/2
            ),
            [
                0.00630316606304536,
                0.00979415034411664,
                0.01720593979371840,
                0.03744822190397540,
                0.12732395447351600,
                0.63661977236758100,
                0.12732395447351600,
                0.03744822190397540,
                0.01720593979371840,
                0.00979415034411664,
                0.00630316606304536,
            ]  # values from Excel 2010
            # =(L/(2*PI())) / (POWER((x-x0); 2) + POWER((L/2); 2))
        )

    def test_width_zero(self):
        self.assertRaises(
            ValueError,
            sp.lorentzian,
            np.array([1]),
            np.array([0]),
            np.arange(-5, 6, 1),
            0,
        )

    def test_width_below_zero(self):
        self.assertRaises(
            ValueError,
            sp.lorentzian,
            np.array([1]),
            np.array([0]),
            np.arange(-5, 6, 1),
            -1,
        )

    def test_unequal_sizes(self):
        self.assertRaises(
            ValueError,
            sp.lorentzian,
            np.array([1, 2]),
            np.array([0]),
            np.arange(-5, 6, 1),
            1,
        )

    def test_empty_intensities(self):
        out = sp.lorentzian(np.array([]), np.array([]), np.arange(-5, 6, 1), 1)
        self.assertSequenceEqual(out.tolist(), np.zeros(11).tolist())

    def test_empty_abscissia(self):
        out = sp.lorentzian(np.array([1]), np.array([0]), np.array([]), 1)
        self.assertSequenceEqual(out.tolist(), [])


class CalculateSpectraTest(ut.TestCase):
    def setUp(self):
        self.fitting = Mock()

        def fitting(intensities, frequencies, abscissa, width):
            return np.ones_like(abscissa, dtype=int) * self.fitting.call_count

        self.fitting.side_effect = fitting

    def test_zero_conformers(self):
        out = sp.calculate_spectra(
            np.array([]), np.array([]), np.arange(3), 1, self.fitting
        )
        self.assertSequenceEqual(out.tolist(), [])

    def test_one_conformer(self):
        out = sp.calculate_spectra(
            np.ones((1, 2)), np.ones((1, 2)), np.arange(3), 1, self.fitting
        )
        self.assertSequenceEqual(out.tolist(), [[1, 1, 1]])

    def test_two_conformers(self):
        out = sp.calculate_spectra(
            np.ones((2, 2)), np.ones((2, 2)), np.arange(3), 1, self.fitting
        )
        self.assertSequenceEqual(out.tolist(), [[1, 1, 1], [2, 2, 2]])

    def test_unmatching_arrays(self):
        self.assertRaises(
            ValueError,
            sp.calculate_spectra,
            np.ones((2, 2)),
            np.ones((3, 2)),
            np.arange(3),
            1,
            self.fitting,
        )

    def test_empty_abscissa(self):
        out = sp.calculate_spectra(
            np.ones((2, 2)), np.ones((2, 2)), np.array([]), 1, self.fitting
        )
        self.assertSequenceEqual(out.tolist(), [[], []])


class CalculateAverageTest(ut.TestCase):
    def test_one_dim(self):
        out = sp.calculate_average([2, 6], [0.25, 0.75])
        self.assertEqual(out, 5)

    def test_two_dims(self):
        out = sp.calculate_average([[2, 4], [6, 8]], [0.25, 0.75])
        self.assertEqual(out.tolist(), [5, 7])

    def test_three_dims(self):
        out = sp.calculate_average([[[2, 4], [6, 8]], [[6, 8], [6, 12]]], [0.25, 0.75])
        self.assertEqual(out.tolist(), [[5, 7], [6, 11]])

    def test_normalize(self):
        out = sp.calculate_average([2, 6], [1, 3])
        self.assertEqual(out, 5)

    def test_unmatching_sizes(self):
        self.assertRaises(ValueError, sp.calculate_average, [1, 2], [1, 2, 3])
        self.assertRaises(ValueError, sp.calculate_average, [1, 2, 3], [1, 2])
        self.assertRaises(ValueError, sp.calculate_average, [1, 2, 3], 1)
