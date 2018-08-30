import unittest
import os
import tesliper as tslr


class TestSoxhlet(unittest.TestCase):

    def setUp(self):
        self.vpath = os.path.abspath(r'.\test\unit\test_files\vibra')
        self.epath = os.path.abspath(r'.\test\unit\test_files\electr')
        self.npath = os.path.abspath(r'.\test\unit\test_files')
        self.tslr = tslr.Tesliper()
        
        
if __name__ == '__main__':
    unittest.main()