import unittest as ut
from unittest import mock
import tesliper as ts


class TestSoxhlet(ut.TestCase):
    def setUp(self):
        self.tslr = ts.Tesliper()
