import unittest
from tesliper.extraction import gaussian_parser as gp


class TestRegexs(unittest.TestCase):
    def test_number_matches(self):
        self.assertRegex("1", gp.number)
        self.assertRegex(" 1", gp.number)
        self.assertRegex(" -1", gp.number)
        self.assertRegex("23", gp.number)
        self.assertRegex("0.2", gp.number)
        self.assertRegex("0.243", gp.number)
        self.assertRegex("123.657", gp.number)
        self.assertRegex("-0.42", gp.number)
        self.assertRegex("-3425.42", gp.number)
        self.assertRegex(".92", gp.number)
        self.assertRegex("-.42", gp.number)

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
            " ------------------------------------------\n"
            " #P td=(singlets,nstates=80) B3LYP/Def2TZVP\n"
            " ------------------------------------------\n",
            gp.command,
        )
        self.assertRegex(
            " -------------------------\n"
            " # opt freq wB97xd/6-31G**\n"
            " -------------------------\n",
            gp.command,
        )


if __name__ == "__main__":
    unittest.main()
