from unittest import TestCase
from unittest.mock import Mock, patch
from tesliper.glassware.nmr import Shieldings, Couplings
import numpy as np


class TestShieldings(TestCase):

    def setUp(self):
        self.shield = Shieldings(
            genre='h_mst', filenames=['file1.out', 'file2.out'],
            values=[[30, 40, 60], [40, 60, 70]],
            intercept=10, slope=-10
        )

    def test_nucleus(self):
        self.assertTrue(self.shield.nucleus == 'H')

    def test_shielding_values(self):
        self.assertSequenceEqual(
            self.shield.shielding_values.tolist(),
            [[2, 3, 5], [3, 5, 6]]
        )

    def test_couple(self):
        coupls = [[[.0, .2, .4, 2],
                   [.2, .0, .6, 0],
                   [.4, .6, .0, 0]],
                  [[.0, .2, .6, 3],
                   [.2, .0, .8, 0],
                   [.6, .8, .0, 0]]]
        input_mock = Mock(name='input_mock')
        input_mock.values = np.asarray(coupls)
        input_mock.atoms_coupled = np.asarray([1, 1, 1, 9])
        symmetric_mock = Mock(name='symmetric_mock')
        symmetric_mock.drop_diagonals.return_value = [
            [[.2, .4], [.2, .6], [.4, .6]], [[.2, .6], [.2, .8], [.6, .8]]
        ]
        remaining_mock = Mock(name='remaining_mock')
        remaining_mock.values = np.asarray([[[2], [0], [0]], [[3], [0], [0]]])
        with patch('tesliper.glassware.nmr.Couplings') as Cpls:
            Cpls.return_value = Mock(name='Couplings_instance')
            Cpls.return_value.take_atoms.side_effect = [symmetric_mock,
                                                        remaining_mock]
            out = self.shield.couple(input_mock, 100).tolist()
        self.assertSequenceEqual(out, [])
