import unittest as ut
from unittest import mock

import numpy as np
from tesliper.datawork import energies as en


class TestCalculateDeltas(ut.TestCase):

    def test_wrong_type(self):
        self.assertRaises(ValueError, en.calculate_deltas, 'string')

    def test_integer(self):
        self.assertRaises(TypeError, en.calculate_deltas, 1)

    def test_string(self):
        self.assertRaises(ValueError, en.calculate_deltas, 'bla')

    def test_not_iterable(self):
        self.assertRaises(TypeError, en.calculate_deltas, object())

    def test_empty(self):
        out = en.calculate_deltas([])
        self.assertSequenceEqual(out.tolist(), [])

    def test_one_value(self):
        out = en.calculate_deltas([1])
        self.assertSequenceEqual(out.tolist(), [0])

    def test_convertible_string(self):
        out = en.calculate_deltas(['1'])
        self.assertSequenceEqual(out.tolist(), [0])

    def test_more_values(self):
        out = en.calculate_deltas([0, .001, .002])
        self.assertSequenceEqual(out.tolist(), [0, .6275095, 2 * .6275095])


@mock.patch('tesliper.datawork.energies.calculate_deltas')
class TestCalculateMinFactor(ut.TestCase):

    def test_empty(self, deltas):
        deltas.return_value = np.array([])
        out = en.calculate_min_factors([])
        self.assertSequenceEqual(out.tolist(), [])

    def test_one_value(self, deltas):
        deltas.return_value = np.array([0])
        out = en.calculate_min_factors([1])
        self.assertSequenceEqual(out.tolist(), [1])

    def test_more_values(self, deltas):
        deltas.return_value = np.array([0, .6275095, 2 * .6275095])
        out = en.calculate_min_factors([0, .001, .002])
        self.assertSequenceEqual(
            np.round(out, decimals=8).tolist(), [1, 0.34676265, 0.12024433]
        )

    def test_other_temp(self, deltas):
        deltas.return_value = np.array([0, .6275095, 2 * .6275095])
        out = en.calculate_min_factors([0, .001, .002], t=200)
        self.assertSequenceEqual(
            np.round(out, decimals=8).tolist(), [1, 0.20620689, 0.04252128]
        )


@mock.patch('tesliper.datawork.energies.calculate_min_factors')
class TestCalculatePopulations(ut.TestCase):

    def test_empty(self, factors):
        factors.return_value = np.array([])
        out = en.calculate_populations([])
        self.assertSequenceEqual(out.tolist(), [])

    def test_one_value(self, factors):
        factors.return_value = np.array([1])
        out = en.calculate_populations([1])
        self.assertSequenceEqual(out.tolist(), [1])

    def test_more_values(self, factors):
        factors.return_value = np.array([1, 0.34676265, 0.12024433])
        out = en.calculate_populations([0, .001, .002])
        self.assertSequenceEqual(
            np.round(out, decimals=8).tolist(),
            [0.68166002, 0.23637423, 0.08196575]
        )

    def test_other_temp(self, factors):
        factors.return_value = np.array([1, 0.20620689, 0.04252128])
        out = en.calculate_populations([0, .001, .002], t=200)
        self.assertSequenceEqual(
            np.round(out, decimals=8).tolist(),
            [0.8008148, 0.16513353, 0.03405167]
        )
