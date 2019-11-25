import unittest as ut
from tesliper import glassware as gw
from tesliper.glassware import molecules as ml


class TestMolecules(ut.TestCase):
    def setUp(self):
        self.empty = ml.Molecules()
        self.mols = ml.Molecules(bla={"data": [1, 2, 3, 4]})
        base = {
            "normal_termination": True,
            "version": "Gaussian 09, Revision E.01",
            "command": "# opt freq=vcd B3LYP/Def2TZVP",
            "optimization_completed": True,
            "charge": 0,
            "multiplicity": 1,
            "input_geom": [],
            "stoichiometry": "CH3F",
            "molecule_atoms": (6, 1, 1, 1, 9),
            "geometry": [],
            "freq": [1, 2, 3, 4, 5],
            "mass": [2, 1, 3, 2, 1],
            "iri": [27, 8, 569, 1, 3],
            "emang": [1.9, 1.4, 4.4, 1.1, 1.3],
            "wavelen": [231, 144, 137],
            "vdip": [0.0003, 0.008, 0.0022],
            "transitions": [
                ((20, 25, 0.1),),
                ((21, 25, -0.2), (23, 25, 0.6)),
                ((13, 25, -0.1), (15, 25, 0.3), (18, 25, -0.4)),
            ],
            "zpecorr": 0.5,
            "zpe": -200,
            "scf": 0,
        }
        noopt = {**base, "zpe": -210, "optimization_completed": False}
        imag = {**base, "zpe": -220, "freq": [-1, 2, 3, 4, 5]}
        stoich = {**base, "zpe": -230, "stoichiometry": "CH3F_other"}
        term = {**base, "zpe": -240, "normal_termination": False}
        size = {**base, "zpe": -250, "mass": [1, 2, 3]}
        incom = {**base, "zpe": -260}
        del incom["scf"]
        self.full = ml.Molecules(
            base=base,
            noopt=noopt,
            imag=imag,
            stoich=stoich,
            term=term,
            size=size,
            incom=incom,
        )

    def test_instantiation(self):
        self.assertEqual(self.empty.kept, [])
        self.assertEqual(self.empty.filenames, [])
        self.assertEqual(self.mols.kept, [True])
        self.assertEqual(self.mols.filenames, ["bla"])
        self.assertIsInstance(self.mols["bla"], dict)

    def test_setitem(self):
        self.mols["foo"] = {"data": [1, 2, 3, 4]}
        self.assertEqual(len(self.mols), 2)
        self.assertEqual(self.mols.kept, [True, True])
        self.assertEqual(self.mols.filenames, ["bla", "foo"])
        with self.assertRaises(TypeError):
            self.mols["ham"] = (1, 2)

    def test_delitem_single(self):
        del self.mols["bla"]
        self.assertEqual(self.mols.kept, [])
        self.assertEqual(self.mols.filenames, [])

    def test_delitem_many(self):
        del self.full["imag"]
        self.assertSequenceEqual(self.full.kept, [True] * 6)
        self.assertSequenceEqual(
            self.full.filenames, ["base", "noopt", "stoich", "term", "size", "incom"]
        )
        self.assertSequenceEqual(
            [m["_index"] for m in self.full.values()], list(range(6))
        )

    def test_update_with_dict(self):
        self.mols.update({"bla2": {"data": [1, 2, 3, 4]}})
        self.assertEqual(len(self.mols), 2)
        self.assertEqual(self.mols.kept, [True, True])
        self.assertEqual(self.mols.filenames, ["bla", "bla2"])
        self.assertEqual(self.mols["bla"], {"_index": 0, "data": [1, 2, 3, 4]})

    def test_update_new(self):
        self.mols.update(bla2={"data": [5, 2, 3, 4]})
        self.assertEqual(len(self.mols), 2)
        self.assertEqual(self.mols.kept, [True, True])
        self.assertEqual(self.mols.filenames, ["bla", "bla2"])
        self.assertEqual(self.mols["bla2"], {"_index": 1, "data": [5, 2, 3, 4]})

    def test_update_same(self):
        self.mols.update(bla={"data": "new"})
        self.assertEqual(len(self.mols), 1)
        self.assertEqual(self.mols.kept, [True])
        self.assertEqual(self.mols.filenames, ["bla"])
        self.assertEqual(self.mols["bla"]["data"], "new")

    def test_update_repeated(self):
        self.mols.update({"bla": {"data": "new"}}, bla={"other": "foo"})
        self.assertEqual(len(self.mols), 1)
        self.assertEqual(self.mols.kept, [True])
        self.assertEqual(self.mols.filenames, ["bla"])
        self.assertEqual(self.mols["bla"]["data"], "new")
        self.assertEqual(self.mols["bla"]["other"], "foo")

    def test_update_banned(self):
        with self.assertRaises(TypeError):
            self.mols.update(foo=7)
        with self.assertRaises(TypeError):
            self.mols.update({"foo": 7})

    def test_arrayd_default_parameter(self):
        zpe = self.full.arrayed("zpe")
        self.assertEqual(298.15, zpe.t)

    def test_arrayd_empty(self):
        gib = self.full.arrayed("gib")
        self.assertSequenceEqual([], gib.filenames.tolist())
        self.assertSequenceEqual([], gib.values.tolist())
        self.assertEqual(298.15, gib.t)

    def test_arrayed_types(self):
        zpe = self.full.arrayed("zpe")
        self.assertIs(gw.Energies, type(zpe))
        normal_termination = self.full.arrayed("normal_termination")
        self.assertIs(gw.BooleanArray, type(normal_termination))
        command = self.full.arrayed("command")
        self.assertIs(gw.InfoArray, type(command))
        iri = self.full.arrayed("iri")
        self.assertIs(gw.GroundStateBars, type(iri))
        vdip = self.full.arrayed("vdip")
        self.assertIs(gw.ExcitedStateBars, type(vdip))
        emang = self.full.arrayed("emang")
        self.assertIs(gw.FloatArray, type(emang))

    def test_arrayed_trimmed(self):
        arr = self.full.arrayed("zpe")
        self.assertEqual(arr.values.shape, (len(self.full),))
        self.full.kept[2] = False
        arr = self.full.arrayed("zpe")
        self.assertEqual(arr.values.shape, (len(self.full) - 1,))
        self.assertSequenceEqual(list(arr.values), [-200, -210, -230, -240, -250, -260])

    def test_trim_not_optimized(self):
        self.full.trim_not_optimized()
        self.assertEqual([True, False, True, True, True, True, True], self.full.kept)

    def test_trim_imaginary(self):
        self.full.trim_imaginary_frequencies()
        self.assertEqual([True, True, False, True, True, True, True], self.full.kept)

    def test_trim_stoichiometry(self):
        self.full.trim_non_matching_stoichiometry()
        self.assertEqual([True, True, True, False, True, True, True], self.full.kept)

    def test_trim_termination(self):
        self.full.trim_non_normal_termination()
        self.assertEqual([True, True, True, True, False, True, True], self.full.kept)

    def test_trim_inconsistent_sizes(self):
        self.full.trim_inconsistent_sizes()
        self.assertEqual([True, True, True, True, True, False, True], self.full.kept)

    def test_trim_incomplete(self):
        self.full.trim_incomplete()
        self.assertEqual([True, True, True, True, True, True, False], self.full.kept)

    def test_trim_to_range_min(self):
        self.full.trim_to_range("zpe", minimum=-235)
        self.assertEqual([True, True, True, True, False, False, False], self.full.kept)

    def test_trim_to_range_max(self):
        self.full.trim_to_range("zpe", maximum=-225)
        self.assertEqual([False, False, False, True, True, True, True], self.full.kept)

    def test_trim_to_range_min_max(self):
        self.full.trim_to_range("zpe", minimum=-255, maximum=-205)
        self.assertEqual([False, True, True, True, True, True, False], self.full.kept)

    def test_trim_to_range_errors(self):
        with self.assertRaises(ValueError):
            self.full.trim_to_range("command")
        with self.assertRaises(ValueError):
            self.full.trim_to_range("zpe", attribute="bla")
        with self.assertRaises(ValueError):
            self.full.trim_to_range("zpe", attribute="full_name")

    def test_select_all(self):
        self.full.kept = [True, False, True, False, True, False, False]
        self.assertFalse(all(self.full.kept))
        self.full.select_all()
        self.assertTrue(all(self.full.kept))

    def test_kept_raises(self):
        with self.assertRaises(TypeError):
            self.full.kept = 1
        with self.assertRaises(TypeError):
            self.full.kept = {"bla": 1}
        with self.assertRaises(KeyError):
            self.full.kept = ["zero"]
        with self.assertRaises(ValueError):
            self.full.kept = [True] * 2
        with self.assertRaises(ValueError):
            self.full.kept = [True] * 20
        with self.assertRaises(IndexError):
            self.full.kept = [200]
        with self.assertRaises(TypeError):
            self.full.kept = [[]]

    def test_kept(self):
        self.full.kept = "imag stoich term".split(" ")
        self.assertSequenceEqual(
            [False, False, True, True, True, False, False], self.full.kept
        )
        self.full.kept = [1, 3, 5]
        self.assertSequenceEqual(
            [False, True, False, True, False, True, False], self.full.kept
        )
        self.full.kept = [True, False, False, True, False, False, True]
        self.assertSequenceEqual(
            [True, False, False, True, False, False, True], self.full.kept
        )
        self.full.kept = []
        self.assertSequenceEqual([False] * 7, self.full.kept)

    def test_inconsistency_allowed(self):
        with self.mols.inconsistency_allowed:
            self.assertTrue(self.mols.allow_data_inconsistency)
        self.assertFalse(self.mols.allow_data_inconsistency)
