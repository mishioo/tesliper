from unittest import TestCase
from tesliper.datawork import helpers


class TestTakeAtoms(TestCase):

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

    def test_invalid_atom(self):
        pass

    def test_absent_atom(self):
        out = helpers.take_atoms(self.two_dim, self.atoms, 4).tolist()
        self.assertSequenceEqual(out, [])

    def test_all_atoms(self):
        out = helpers.take_atoms(self.two_dim, self.atoms, [1, 2, 3]).tolist()
        self.assertSequenceEqual(out, self.two_dim)

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

    def test_two_dimensions_atoms(self):
        pass

    def test_atoms_keeping(self):
        out = helpers.take_atoms(self.atoms, self.atoms, 1).tolist()
        self.assertSequenceEqual(out, [1, 1])

    def test_(self):
        pass

    def test_(self):
        pass

    def test_(self):
        pass

    def test_(self):
        pass


class TestDropAtoms(TestCase):

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

    def test_invalid_atom(self):
        pass

    def test_absent_atom(self):
        out = helpers.drop_atoms(self.two_dim, self.atoms, 4).tolist()
        self.assertSequenceEqual(out, self.two_dim)

    def test_all_atoms(self):
        out = helpers.drop_atoms(self.two_dim, self.atoms, [1, 2, 3]).tolist()
        self.assertSequenceEqual(out, [])

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

    def test_two_dimensions_atoms(self):
        pass

    def test_atoms_dropping(self):
        out = helpers.drop_atoms(self.atoms, self.atoms, 1).tolist()
        self.assertSequenceEqual(out, [3, 2])

    def test_(self):
        pass

    def test_(self):
        pass

    def test_(self):
        pass

    def test_(self):
        pass
