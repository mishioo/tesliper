import unittest
from io import StringIO
from tesliper.extraction import gaussian_parser as gp


class TestRegexs(unittest.TestCase):

    def test_number_matches(self):
        self.assertRegex('1', gp.number)
        self.assertRegex(' 1', gp.number)
        self.assertRegex(' -1', gp.number)
        self.assertRegex('23', gp.number)
        self.assertRegex('0.2', gp.number)
        self.assertRegex('0.243', gp.number)
        self.assertRegex('123.657', gp.number)
        self.assertRegex('-0.42', gp.number)
        self.assertRegex('-3425.42', gp.number)
        self.assertRegex('.92', gp.number)
        self.assertRegex('-.42', gp.number)

    # def test_number_not_matches(self):
    # self.assertNotRegex('-', gp.number)
    # self.assertNotRegex('.', gp.number)
    # self.assertNotRegex('- 1', gp.number)  # matches :(
    # self.assertNotRegex('12-', gp.number)
    # self.assertNotRegex('42.', gp.number)

    # def test_number_sci_matches(self):
    # self.assertRegex('3e24', gp.number)
    # self.assertRegex('3e-656', gp.number)
    # self.assertRegex('3E24', gp.number)
    # self.assertRegex('3E-24', gp.number)
    # self.assertRegex('-3e24', gp.number)
    # self.assertRegex('-3e-656', gp.number)
    # self.assertRegex('-3E24', gp.number)
    # self.assertRegex('-3E-24', gp.number)
    # self.assertRegex('3.23e24', gp.number)
    # self.assertRegex('3.23e-656', gp.number)
    # self.assertRegex('3.23E24', gp.number)
    # self.assertRegex('3.23E-24', gp.number)
    # self.assertRegex('-3.23e24', gp.number)
    # self.assertRegex('-3.23e-656', gp.number)
    # self.assertRegex('-3.23E24', gp.number)
    # self.assertRegex('-3.23E-24', gp.number)

    # def test_number_sci_not_matches(self):
    # self.assertNotRegex('42e', gp.number)
    # self.assertNotRegex('42e-', gp.number)
    # self.assertNotRegex('42.e', gp.number)
    # self.assertNotRegex('42.e-', gp.number)
    # self.assertNotRegex('42E', gp.number)
    # self.assertNotRegex('42E-', gp.number)
    # self.assertNotRegex('42.E', gp.number)
    # self.assertNotRegex('42.E-', gp.number)

    def test_command(self):
        self.assertRegex(
            ' ------------------------------------------\n'
            ' #P td=(singlets,nstates=80) B3LYP/Def2TZVP\n'
            ' ------------------------------------------\n',
            gp.command
        )
        self.assertRegex(
            " -------------------------\n"
            " # opt freq wB97xd/6-31G**\n"
            " -------------------------\n",
            gp.command
        )


class TestParser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(r'..\..\test_files\acoet-freq.out', 'r') as file:
            cls.freq = StringIO(file.read())
        # with open(r'..\..\test_files\acoet-nmr.out', 'r') as file:
        #     self.nmr = StringIO(file.read())
        # with open(r'..\..\test_files\acoet-opt.out', 'r') as file:
        #     self.opt = StringIO(file.read())
        # with open(r'..\..\test_files\acoet-td.out', 'r') as file:
        #     self.td = StringIO(file.read())

    def setUp(self):
        self.freq.seek(0)
        parser = gp.GaussianParser()
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


class TestParse(unittest.TestCase):

    def setUp(self):
        with open(r'..\..\test_files\vibra\Tolbutamid_c1.log') as file:
            vibr_cont = file.read()
        with open(r'..\..\test_files\electr\Tolbutamid_c1.log') as file:
            electr_cont = file.read()


if __name__ == '__main__':
    unittest.main()
