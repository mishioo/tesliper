import unittest
from io import StringIO
from tesliper.extraction import gaussian_parser as gprs


# with open(r'..\..\test_files\acoet-nmr.out', 'r') as file:
#     self.nmr = StringIO(file.read())
# with open(r'..\..\test_files\acoet-opt.out', 'r') as file:
#     self.opt = StringIO(file.read())
# with open(r'..\..\test_files\acoet-td.out', 'r') as file:
#     self.td = StringIO(file.read())

class TestParser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(r'..\..\fixtures\fal-freq.out', 'r') as file:
            cls.freq = StringIO(file.read())

    def setUp(self):
        self.freq.seek(0)
        parser = gprs.GaussianParser()
        self.data = parser.parse(self.freq)

    def test_keys(self):
        self.assertSetEqual(
            set(self.data.keys()),
            {'normal_termination', 'version', 'command', 'charge',
             'multiplicity', 'input_geom', 'scf', 'stoichiometry',
             'zpecorr', 'tencorr', 'entcorr', 'gibcorr', 'zpe', 'ten', 'ent',
             'gib', 'freq', 'mass', 'frc', 'iri', 'depolarp', 'depolaru',
             'ramanactiv', 'geometry', 'atoms'}
        )

    def test_normal_termination(self):
        self.assertTrue(self.data['normal_termination'])

    def test_version(self):
        self.assertEqual(self.data['version'], 'Gaussian 09, Revision E.01')

    def test_command(self):
        self.assertEqual(self.data['command'], '# freq hf/3-21g')

    def test_charge(self):
        self.assertEqual(self.data['charge'], 0.0)

    def test_multiplicity(self):
        self.assertEqual(self.data['multiplicity'], 1.0)

    def test_stoichiometry(self):
        self.assertEqual(self.data['stoichiometry'], 'CH2O')

    def test_scf(self):
        self.assertEqual(self.data['scf'], -113.217409254)

    def test_zpecorr(self):
        self.assertEqual(self.data['zpecorr'], 0.028669)

    def test_tencorr(self):
        self.assertEqual(self.data['tencorr'], 0.031529)

    def test_entcorr(self):
        self.assertEqual(self.data['entcorr'], 0.032474)

    def test_gibcorr(self):
        self.assertEqual(self.data['gibcorr'], 0.006971)

    def test_zpe(self):
        self.assertEqual(self.data['zpe'], -113.188740)

    def test_ten(self):
        self.assertEqual(self.data['ten'], -113.185880)

    def test_ent(self):
        self.assertEqual(self.data['ent'], -113.184936)

    def test_gib(self):
        self.assertEqual(self.data['gib'], -113.210438)

    def test_freq(self):
        self.assertSequenceEqual(
            self.data['freq'],
            []
        )

    def test_mass(self):
        self.assertSequenceEqual(
            self.data['mass'],
            []
        )

    def test_frc(self):
        self.assertSequenceEqual(
            self.data['frc'],
            []
        )

    def test_iri(self):
        self.assertSequenceEqual(
            self.data['iri'],
            []
        )

    def test_depolarp(self):
        self.assertSequenceEqual(
            self.data['depolarp'],
            []
        )

    def test_depolaru(self):
        self.assertSequenceEqual(
            self.data['depolaru'],
            []
        )

    def test_ramanactiv(self):
        self.assertSequenceEqual(
            self.data['ramanactiv'],
            []
        )

    def test_geometry(self):
        self.assertSequenceEqual(
            self.data['geometry'],
            []
        )

    def test_atoms(self):
        self.assertSequenceEqual(
            self.data['atoms'],
            []
        )


if __name__ == '__main__':
    unittest.main()
