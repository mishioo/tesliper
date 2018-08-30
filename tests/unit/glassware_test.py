import unittest
from tesliper import glassware as gw
import numpy as np


class TestDataArray(unittest.TestCase):

    def setUp(self):
        self.da = gw.DataArray(
            'mass',
            ['bla.out', 'foo.out', 'ham.out'],
            [[1, 5, 3, 6, 4], [8, 2, 6, 8, 2], [7, 3, 8, 5, 5]]
        )

    def test_instantiation_types(self):
        self.assertEqual('mass', self.da.genre)
        self.assertIsInstance(self.da.values, np.ndarray)
        self.assertIsInstance(self.da.filenames, np.ndarray)
        self.assertEqual(self.da.filenames.shape, (3,))
        self.assertEqual(self.da.values.shape, (3, 5))
        # self.assertIs(self.da.filenames.dtype, np.dtype(str))
        self.assertIs(self.da.values.dtype, np.dtype(float))
        self.assertIs(self.da.dtype, float)

    def test_get_constructor(self):
        self.assertIs(
            gw.DataArray.get_constructor('normal_termination'),
            gw.Booleans
        )
        self.assertIs(
            gw.DataArray.get_constructor('command'),
            gw.Info
        )
        self.assertIs(
            gw.DataArray.get_constructor('scf'),
            gw.Energies
        )
        self.assertIs(
            gw.DataArray.get_constructor('iri'),
            gw.Bars
        )


    def test_make_types(self):
        self.assertIs(
            type(gw.DataArray.make('normal_termination', [], [])),
            gw.Booleans
        )
        self.assertIs(
            type(gw.DataArray.make('command', [], [])),
            gw.Info
        )
        self.assertIs(
            type(gw.DataArray.make('scf', [], [])),
            gw.Energies
        )
        self.assertIs(
            type(gw.DataArray.make('iri', [], [], frequencies=[])),
            gw.Bars
        )

    def test_make_dtypes(self):
        self.assertIs(gw.DataArray.make('scf', [], []).dtype, float)
        self.assertIs(gw.DataArray.make('scf', [], [], dtype=str).dtype, str)
        self.assertIs(gw.DataArray.make('scf', [], [], dtype=int).dtype, int)
        self.assertSequenceEqual(
            gw.DataArray.make('scf', ['a', 'b'], [.23, 1.12],
                              dtype=int).values.tolist(),
            [0, 1]
        )

    def test_instantiation_errors(self):
        self.assertRaises(ValueError, gw.DataArray,
                          'iri', ['a', 'b'], [1, 2, 3])


class TestBars(unittest.TestCase):

    def test_imag(self):
        br = gw.Bars(
            'iri', list('abcd'),
            [[1, 5, 3, 6, 4], [8, 2, 6, 8, 2],
             [7, 3, 8, 5, 5], [5, 9, 4, 7, 2]],
            frequencies=[[a - b for a in range(1, 6)] for b in range(4)]
        )
        self.assertSequenceEqual(br.imaginary.tolist(), [0, 0, 1, 2])
        self.assertDictEqual(br.find_imag(),
                             {k: v for k, v in zip('cd', [1, 2])})


class TestMolecules(unittest.TestCase):

    def setUp(self):
        self.mols = gw.Molecules(bla={'data': [1, 2, 3, 4]})
        self.arrs = gw.Molecules(
            one={'command': '# opt freq B3LYP/6-31G',
                 'freq': [1,2,3,4,5],
                 'stoichiometry': 'C3H8',
                 'scf': 1,
                 'normal_termination': True,
                 'optimized': True,
                 'additional': True},
            two={'command': '# opt freq B3LYP/6-31G',
                 'freq': [-1,2,3,4,5],
                 'stoichiometry': 'C3H8',
                 'scf': 2,
                 'normal_termination': True,
                 'optimized': True,
                 'additional': True},
            tree={'command': '# opt freq B3LYP/6-31G',
                  'freq': [1,2,3,4,5],
                  'stoichiometry': 'C3H9',
                  'scf': 3,
                  'normal_termination': True,
                  'optimized': True,
                  'additional': True},
            four={'command': '# opt freq B3LYP/6-31G',
                  'freq': [1,2,3,4,5],
                  'stoichiometry': 'C3H8',
                  'scf': 4,
                  'normal_termination': True,
                  'optimized': False,
                  'additional': True},
            five={'command': '# opt freq B3LYP/6-31G',
                  'freq': [1,2,3,4,5],
                  'stoichiometry': 'C3H8',
                  'scf': 5,
                  'normal_termination': False,
                  'optimized': True,
                  'additional': True},
            six={'command': '# opt freq B3LYP/6-31G',
                 'freq': [1,2,3,4,5],
                 'stoichiometry': 'C3H8',
                 'scf': 6,
                 'normal_termination': True,
                 'optimized': True}
        )

    def test_instantiation(self):
        mols = gw.Molecules()
        self.assertEqual(mols.kept, [])
        self.assertEqual(mols.filenames, [])
        self.assertEqual(self.mols.kept, [True])
        self.assertEqual(self.mols.filenames, ['bla'])
        self.assertIsInstance(self.mols['bla'], dict)

    def test_setitem(self):
        self.mols['foo'] = {'data': [1, 2, 3, 4]}
        self.assertEqual(len(self.mols), 2)
        self.assertEqual(self.mols.kept, [True, True])
        self.assertEqual(self.mols.filenames, ['bla', 'foo'])
        with self.assertRaises(TypeError):
            self.mols['ham'] = (1, 2)

    def test_delitem(self):
        del self.mols['bla']
        self.assertEqual(self.mols.kept, [])
        self.assertEqual(self.mols.filenames, [])

    def test_update_with_dict(self):
        self.mols.update({'bla2': {'data': [1, 2, 3, 4]}})
        self.assertEqual(len(self.mols), 2)
        self.assertEqual(self.mols.kept, [True, True])
        self.assertEqual(self.mols.filenames, ['bla', 'bla2'])
        self.assertEqual(self.mols['bla'], {'data': [1, 2, 3, 4]})

    def test_update_new(self):
        self.mols.update(bla2={'data': [1, 2, 3, 4]})
        self.assertEqual(len(self.mols), 2)
        self.assertEqual(self.mols.kept, [True, True])
        self.assertEqual(self.mols.filenames, ['bla', 'bla2'])
        self.assertEqual(self.mols['bla'], {'data': [1, 2, 3, 4]})

    def test_update_same(self):
        self.mols.update(bla={'data': 'new'})
        self.assertEqual(len(self.mols), 1)
        self.assertEqual(self.mols.kept, [True])
        self.assertEqual(self.mols.filenames, ['bla'])
        self.assertEqual(self.mols['bla']['data'], 'new')

    def test_update_banned(self):
        with self.assertRaises(TypeError):
            self.mols.update(foo=7)
        with self.assertRaises(TypeError):
            self.mols.update({'foo': 7})
            
    def test_arrayed(self):
        arr = self.arrs.arrayed('scf')
        self.assertIs(type(arr), gw.Energies)
        self.assertEqual(arr.values.shape, (len(self.arrs),))
        self.arrs.kept[2] = False
        arr = self.arrs.arrayed('scf')
        self.assertEqual(arr.values.shape, (len(self.arrs)-1,))
        self.assertSequenceEqual(list(arr.values), [1,2,4,5,6])
        
    def test_trim_incomplete(self):
        self.arrs.trim_incomplete()
        self.assertEqual(self.arrs.kept, [True, True, True, True, True, False])
        
    def test_trim_imaginary(self):
        self.arrs.trim_imaginary_frequencies()
        self.assertEqual(self.arrs.kept, [True, False, True, True, True, True])
        
    def test_trim_stoichiometry(self):
        self.arrs.trim_non_matching_stoichiometry()
        self.assertEqual(self.arrs.kept, [True, True, False, True, True, True])

    def test_trim_not_optimized(self):
        self.arrs.trim_not_optimized()
        self.assertEqual(self.arrs.kept, [True, True, True, False, True, True])
        
    def test_trim_termination(self):
        self.arrs.trim_non_normal_termination()
        self.assertEqual(self.arrs.kept, [True, True, True, True, False, True])
        
    def test_trim_to_range(self):
        self.arrs.trim_to_range('scf', minimum=2, maximum=5)
        self.assertEqual(self.arrs.kept, [False, True, True, True, True, False])
        
    def test_select_all(self):
        pass


if __name__ is '__main__':
    unittest.main()
