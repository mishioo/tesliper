import unittest as ut
from tesliper.datawork import helpers


class TestSymbolOfElement(ut.TestCase):
    def test_atomic_number_int(self):
        self.assertEqual(helpers.symbol_of_element(1), 'H')

    def test_atomic_number_float(self):
        self.assertEqual(helpers.symbol_of_element(1.0), 'H')

    def test_atomic_number_str(self):
        self.assertEqual(helpers.symbol_of_element('1'), 'H')

    def test_not_atomic_number_int(self):
        self.assertRaises(
            helpers.InvalidElementError, helpers.symbol_of_element, 0
        )

    def test_not_atomic_number_float(self):
        self.assertRaises(ValueError, helpers.symbol_of_element, 0.5)

    def test_not_atomic_number_str(self):
        self.assertRaises(
            helpers.InvalidElementError, helpers.symbol_of_element, '0'
        )

    def test_element_symbol(self):
        self.assertEqual(helpers.symbol_of_element('H'), 'H')

    def test_element_symbol_lowercase(self):
        self.assertEqual(helpers.symbol_of_element('he'), 'He')

    def test_not_element_symbol(self):
        self.assertRaises(ValueError, helpers.symbol_of_element, 'bla')


class TestAtomicNumber(ut.TestCase):
    def test_valid_symbol(self):
        self.assertEqual(helpers.atomic_number('H'), 1)

    def test_lowercase_symbol(self):
        self.assertEqual(helpers.atomic_number('he'), 2)

    def test_invalid_symbol(self):
        self.assertRaises(
            helpers.InvalidElementError, helpers.atomic_number, 'bla'
        )

    def test_atomic_number(self):
        self.assertEqual(helpers.atomic_number(1), 1)

    def test_not_atomic_number(self):
        self.assertRaises(
            helpers.InvalidElementError, helpers.atomic_number, 0
        )


class TestValidateAtoms(ut.TestCase):
    def test_integer(self):
        self.assertSequenceEqual(helpers.validate_atoms(1), [1])

    def test_float(self):
        self.assertSequenceEqual(helpers.validate_atoms(2.0), [2])

    def test_string(self):
        self.assertSequenceEqual(helpers.validate_atoms("B"), [5])

    def test_string_with_spaces(self):
        self.assertSequenceEqual(helpers.validate_atoms("H H C"), [1, 1, 6])

    def test_list_of_integers(self):
        self.assertSequenceEqual(helpers.validate_atoms([1, 1, 6]), [1, 1, 6])

    def test_list_of_floats(self):
        self.assertSequenceEqual(helpers.validate_atoms([1., 6.]), [1, 6])

    def test_list_of_strings(self):
        self.assertSequenceEqual(helpers.validate_atoms(["H", "H"]), [1, 1])


class TestTakeAtoms(ut.TestCase):

    def setUp(self):
        self.atoms = [1, 2, 1, 3]
        self.one_dim = list(range(4))
        self.two_dim = [[y * 10 + x for x in range(4)] for y in range(2)]
        self.tree_dim = [[[y * 100 + x * 10 + z for z in range(3)]
                          for x in range(4)] for y in range(2)]
        self.four_dim = [
            [[[y * 1000 + x * 100 + z * 10, y * 1000 + x * 100 + z * 10 + 1]
              for z in range(3)] for x in range(4)] for y in range(2)
        ]

    @ut.skip("To be created.")
    def test_invalid_atom(self):
        pass

    def test_absent_atom(self):
        out = helpers.take_atoms(self.two_dim, self.atoms, 4).tolist()
        self.assertSequenceEqual(out, [])

    def test_all_atoms(self):
        out = helpers.take_atoms(self.two_dim, self.atoms, [1, 2, 3]).tolist()
        self.assertSequenceEqual(out, self.two_dim)

    @ut.skip("To be created.")
    def test_non_matching_sizes(self):
        pass

    def test_one_dimension(self):
        out = helpers.take_atoms(self.one_dim, self.atoms, 1).tolist()
        self.assertSequenceEqual(out, [0, 2])

    def test_two_dimensions(self):
        out = helpers.take_atoms(self.two_dim, self.atoms, 1).tolist()
        self.assertSequenceEqual(out, [[0, 2], [10, 12]])

    def test_tree_dimensions(self):
        out = helpers.take_atoms(self.tree_dim, self.atoms, 1).tolist()
        self.assertSequenceEqual(
            out, [[[0, 1, 2], [20, 21, 22]], [[100, 101, 102], [120, 121, 122]]]
        )

    def test_four_dimensions(self):
        out = helpers.take_atoms(self.four_dim, self.atoms, 1).tolist()
        self.assertSequenceEqual(
            out, [[[[0, 1], [10, 11], [20, 21]],
                   [[200, 201], [210, 211], [220, 221]]],
                  [[[1000, 1001], [1010, 1011], [1020, 1021]],
                   [[1200, 1201], [1210, 1211], [1220, 1221]]]]
        )

    @ut.skip("To be created.")
    def test_two_dimensions_atoms(self):
        pass

    def test_atoms_keeping(self):
        out = helpers.take_atoms(self.atoms, self.atoms, 1).tolist()
        self.assertSequenceEqual(out, [1, 1])


class TestDropAtoms(ut.TestCase):

    def setUp(self):
        self.atoms = [3, 1, 2, 1]
        self.one_dim = list(range(4))
        self.two_dim = [[y * 10 + x for x in range(4)] for y in range(2)]
        self.tree_dim = [[[y * 100 + x * 10 + z for z in range(3)]
                          for x in range(4)] for y in range(2)]
        self.four_dim = [
            [[[y * 1000 + x * 100 + z * 10, y * 1000 + x * 100 + z * 10 + 1]
              for z in range(3)] for x in range(4)] for y in range(2)
        ]

    @ut.skip("To be created.")
    def test_invalid_atom(self):
        pass

    def test_empty_discarded(self):
        out = helpers.drop_atoms(self.two_dim, self.atoms, []).tolist()
        self.assertSequenceEqual(out, self.two_dim)

    def test_absent_atom(self):
        out = helpers.drop_atoms(self.two_dim, self.atoms, 4).tolist()
        self.assertSequenceEqual(out, self.two_dim)

    def test_all_atoms(self):
        out = helpers.drop_atoms(self.two_dim, self.atoms, [1, 2, 3]).tolist()
        self.assertSequenceEqual(out, [])

    @ut.skip("To be created.")
    def test_non_matching_sizes(self):
        pass

    def test_one_dimension(self):
        out = helpers.drop_atoms(self.one_dim, self.atoms, 1).tolist()
        self.assertSequenceEqual(out, [0, 2])

    def test_two_dimensions(self):
        out = helpers.drop_atoms(self.two_dim, self.atoms, 1).tolist()
        self.assertSequenceEqual(out, [[0, 2], [10, 12]])

    def test_tree_dimensions(self):
        out = helpers.drop_atoms(self.tree_dim, self.atoms, 1).tolist()
        self.assertSequenceEqual(
            out, [[[0, 1, 2], [20, 21, 22]], [[100, 101, 102], [120, 121, 122]]]
        )

    def test_four_dimensions(self):
        out = helpers.drop_atoms(self.four_dim, self.atoms, 1).tolist()
        self.assertSequenceEqual(
            out, [[[[0, 1], [10, 11], [20, 21]],
                   [[200, 201], [210, 211], [220, 221]]],
                  [[[1000, 1001], [1010, 1011], [1020, 1021]],
                   [[1200, 1201], [1210, 1211], [1220, 1221]]]]
        )

    @ut.skip("To be created.")
    def test_two_dimensions_atoms(self):
        pass

    def test_atoms_dropping(self):
        out = helpers.drop_atoms(self.atoms, self.atoms, 1).tolist()
        self.assertSequenceEqual(out, [3, 2])


class TestIsTriangular(ut.TestCase):
    def test_zero(self):
        self.assertTrue(helpers.is_triangular(0))

    def test_one(self):
        self.assertTrue(helpers.is_triangular(1))

    def test_float(self):
        self.assertFalse(helpers.is_triangular(0.5))

    def test_inf(self):
        self.assertFalse(helpers.is_triangular(float('inf')))

    def test_negative(self):
        self.assertFalse(helpers.is_triangular(-3))

    def test_triangular(self):
        self.assertTrue(helpers.is_triangular(10))

    def test_non_triangular(self):
        self.assertFalse(helpers.is_triangular(7))


class TestGetTriangular(ut.TestCase):
    def test_zero(self):
        self.assertEqual(helpers.get_triangular(0), 0)

    def test_one(self):
        self.assertEqual(helpers.get_triangular(1), 1)

    def test_triangular(self):
        self.assertEqual(helpers.get_triangular(4), 10)

    def test_negative(self):
        self.assertRaises(ValueError, helpers.get_triangular, -3)

    def test_float(self):
        self.assertRaises(ValueError, helpers.get_triangular, 0.5)

    def test_inf(self):
        self.assertRaises(ValueError, helpers.get_triangular, float('inf'))


class TestGetTriangularBase(ut.TestCase):
    def test_zero(self):
        self.assertEqual(helpers.get_triangular_base(0), 0)

    def test_one(self):
        self.assertEqual(helpers.get_triangular_base(1), 1)

    def test_float(self):
        self.assertRaises(ValueError, helpers.get_triangular_base, 0.5)

    def test_inf(self):
        self.assertRaises(ValueError, helpers.get_triangular_base, float('inf'))

    def test_negative(self):
        self.assertRaises(ValueError, helpers.get_triangular_base, -3)

    def test_triangular(self):
        self.assertEqual(helpers.get_triangular_base(10), 4)

    def test_non_triangular(self):
        self.assertRaises(ValueError, helpers.get_triangular_base, 7)

