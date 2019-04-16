from unittest import TestCase
from unittest.mock import Mock, patch
from tesliper.glassware.array_base import ArrayProperty


class TestArrayProperty(TestCase):

    def setUp(self):
        class Cls:
            arr = ArrayProperty()
        self.Cls = Cls
        self.arr = Cls()

    def test_class_access(self):
        self.assertIs()

    def test_name(self):
        self.assertEqual(self.Cls.arr.name, 'arr')

    def test_set_no_filenames(self):
        self.arr.arr = [1, 2, 3]

    def test_decorator_with_args(self):
        mck = Mock()

        class Cls:
            @ArrayProperty(dtype=mck)
            def arr(self):
                pass
        self.assertIs(Cls.arr.dtype, mck)

    def test_decorator(self):
        class Cls:
            @ArrayProperty
            def arr(self):
                pass
