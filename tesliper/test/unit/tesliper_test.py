import unittest
import os
import tesliper as tsl


class TestSoxhlet(unittest.TestCase):

    def setUp(self):
        self.vpath = os.path.abspath(r'.\test\unit\test_files\vibra')
        self.vsox = tsl.Soxhlet(self.vpath)
        self.epath = os.path.abspath(r'.\test\unit\test_files\electr')
        self.esox = tsl.Soxhlet(self.epath)
        self.npath = os.path.abspath(r'.\test\unit\test_files')
        self.nsox = tsl.Soxhlet(self.npath)
        
    def test_path_vibra(self):
        self.assertEqual(os.path.abspath(r'.\test\unit\test_files\vibra'), self.vsox.path)
        
    def test_command_extraction_vibra(self):
        self.assertEqual(' opt freq=vcd B3LYP/Def2TZVP'.lower(), self.vsox.command)
        
    def test_spectra_type_determination_vibra(self):
        self.assertEqual('vibra', self.vsox.spectra_type)
        
    def test_gaussian_files_empty(self):
        self.assertEqual(None, self.nsox.gaussian_files)
        
        
if __name__ == '__main__':
    unittest.main()