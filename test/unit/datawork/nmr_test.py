from unittest import TestCase
from tesliper.datawork import nmr


class TestTakeAtoms(TestCase):

    def setUp(self):
        self.atoms = [1, 2, 1, 3]
        self.one_dim = list(range(4))
        self.two_dim = [[y*10+x for x in range(4)] for y in range(2)]
        self.tree_dim = [[[y*100+x*10+z for z in range(3)]
                          for x in range(4)] for y in range(2)]

    def test_invalid_atom(self):
        pass

    def test_absent_atom(self):
        out = nmr.take_atoms(self.two_dim, self.atoms, 4).tolist()
        self.assertSequenceEqual(out, [])

    def test_non_matching_sizes(self):
        pass

    def test_one_dimension(self):
        out = nmr.take_atoms(self.one_dim, self.atoms, 1).tolist()
        self.assertSequenceEqual(out, [0, 2])

    def test_two_dimensions(self):
        out = nmr.take_atoms(self.two_dim, self.atoms, 1).tolist()
        self.assertSequenceEqual(out, [[0, 2], [10, 12]])

    def test_tree_dimensions(self):
        out = nmr.take_atoms(self.tree_dim, self.atoms, 1).tolist()
        self.assertSequenceEqual(
            out, [[[0, 1, 2], [20, 21, 22]], [[100, 101, 102], [120, 121, 122]]]
        )

    def test_two_dimensions_atoms(self):
        pass

    def test_atom_symbol(self):
        pass

    def test_(self):
        pass

    def test_(self):
        pass

    def test_(self):
        pass

    def test_(self):
        pass
