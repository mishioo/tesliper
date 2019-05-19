import unittest as ut
from unittest import mock
from tesliper.glassware.arrays import FloatArray
import numpy as np


class TestFloatArray(ut.TestCase):

    def setUp(self):
        self.arr = FloatArray(
            genre='bla', filenames=['f1', 'f2', 'f3'], values=[3, 12, 15]
        )

    def test_dtype(self):
        self.assertIs(self.arr.values.dtype, np.float)

    @mock.patch('tesliper.datawork.calculate_average', return_value=10)
    @mock.patch('tesliper.glassware.arrays.logger')
    def test_average_energies_object(self, lggr, clav):
        en = mock.Mock(genre='foo', populations=[1, 1, 1])
        out = self.arr.average(en)
        self.assertIs(type(out), FloatArray)
        self.assertSequenceEqual(out.values.tolist(), [10])
        self.assertSequenceEqual(
            clav.call_args[0][0].tolist(), [3, 12, 15]
        )
        self.assertSequenceEqual(clav.call_args[0][1], [1, 1, 1])
        lggr.debug.assert_called_with('bla averaged by foo.')

    @mock.patch('tesliper.datawork.calculate_average', return_value=10)
    @mock.patch('tesliper.glassware.arrays.logger')
    def test_average_energies_object(self, lggr, clav):
        out = self.arr.average([1, 1, 1])
        self.assertIs(type(out), FloatArray)
        self.assertSequenceEqual(out.values.tolist(), [10])
        self.assertSequenceEqual(
            clav.call_args[0][0].tolist(), [3, 12, 15]
        )
        self.assertSequenceEqual(
            clav.call_args[0][1].tolist(), [1, 1, 1]
        )
        lggr.debug.assert_called_with('bla averaged by unknown.')
