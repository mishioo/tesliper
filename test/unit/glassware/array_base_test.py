import unittest as ut
from unittest import mock

from tesliper.exceptions import InconsistentDataError
import tesliper.glassware.array_base as ab


class TestArrayProperty(ut.TestCase):

    def setUp(self):
        class Cls:
            arr = ab.ArrayProperty()
        class Clsx:
            arr = ab.ArrayProperty(check_against='x')
        self.Cls = Cls
        self.Clsx = Clsx
        self.arr = Cls()

    def test_class_access(self):
        self.assertIs(type(self.Cls.arr), ab.ArrayProperty)

    def test_name(self):
        self.assertEqual(self.Cls.arr.name, 'arr')

    def test_check_input_no_attribute(self):
        self.assertRaises(
            AttributeError, self.Clsx.arr.check_input, self.Clsx(), [1, 2, 3]
        )

    def test_check_input_unmatching(self):
        arr = self.Clsx()
        arr.x = [1, 2]
        self.assertRaises(
            ValueError, self.Clsx.arr.check_input, arr, [1, 2, 3]
        )

    def test_check_input_unmatching_allowed(self):
        arr = self.Clsx()
        arr.x = [1, 2]
        arr.allow_data_inconsistency = True
        self.assertSequenceEqual(
            self.Clsx.arr.check_input(arr, [1, 2, 3]).tolist(), [1, 2, 3]
        )

    def test_check_input_inconsistent(self):
        arr = self.Clsx()
        arr.x = [1, 2]
        self.assertRaises(
            InconsistentDataError, self.Clsx.arr.check_input, arr, [[1, 2], [3]]
        )

    def test_check_input_inconsistent_allowed(self):
        with mock.patch(
                'tesliper.glassware.array_base.ArrayProperty._pad',
                return_value=[[1, 2], [3, 0]]
        ) as pad:
            class Clsx:
                arr = ab.ArrayProperty(check_against='x')
            arr = Clsx()
            arr.x = [1, 2]
            arr.allow_data_inconsistency = True
            out = Clsx.arr.check_input(arr, [[1, 2], [3]])
            pad.assert_called_with([[1, 2], [3]])
            self.assertSequenceEqual(out, [[1, 2], [3, 0]])

    def test_pad(self):
        out = self.Cls.arr._pad([[1, 2], [3]])
        self.assertSequenceEqual(out.tolist(), [[1, 2], [3, 0]])

    def test_pad_one_empty(self):
        out = self.Cls.arr._pad([[1, 2], []])
        self.assertSequenceEqual(out.tolist(), [[1, 2], [0, 0]])

    def test_pad_more_sizes(self):
        out = self.Cls.arr._pad([[1, 2], [3], [4, 5, 6]])
        self.assertSequenceEqual(
            out.tolist(), [[1, 2, 0], [3, 0, 0], [4, 5, 6]]
        )

    @ut.expectedFailure
    def test_pad_three_dim(self):
        out = self.Cls.arr._pad([[[1, 2], [3]]])
        self.assertSequenceEqual(out.tolist(), [[1, 2], [3, 0]])

    def test_decorator_with_dtype(self):
        mck = mock.Mock()

        class Cls:
            @ab.ArrayProperty(dtype=mck)
            def arr(self):
                pass
        self.assertIs(Cls.arr.dtype, mck)
        self.assertIs(Cls.arr.fset, None)
        self.assertIs(Cls.arr.fdel, None)
        self.assertIs(Cls.arr.check_against, None)

    def test_decorator(self):
        class Cls:
            @ab.ArrayProperty
            def arr(self):
                pass
        self.assertIs(Cls.arr.fset, None)
        self.assertIs(Cls.arr.fdel, None)
        self.assertIs(Cls.arr.check_against, None)


@mock.patch(
    'tesliper.glassware.array_base.ArrayBase.values',
    new_callable=mock.PropertyMock
)
@mock.patch(
    'tesliper.glassware.array_base.ArrayBase.filenames',
    new_callable=mock.PropertyMock
)
class TestArrayBase(ut.TestCase):

    def setUp(self):
        class Sub(ab.ArrayBase):
            associated_genres = ('bla')
        self.Sub = Sub

    @ut.expectedFailure
    def test_subclass_no_associated_genres(self, fnms, vals):
        def rising():
            class Sub(ab.ArrayBase):
                pass
        self.assertRaises(AttributeError, rising)

    def test_get_args(self, fnms, vals):
        vals.return_value = [1, 2, 3]
        fnms.return_value = ['f1', 'f2', 'f3']
        arr = self.Sub(
            genre='bla', filenames=['f1', 'f2', 'f3'], values=[1, 2, 3]
        )
        self.assertDictEqual(
            arr.get_args(),
            {'genre': 'bla', 'filenames': ['f1', 'f2', 'f3'],
             'values': [1, 2, 3], 'allow_data_inconsistency': False}
        )

    def test_get_args_not_stored_arg(self, fnms, vals):
        class Sub(ab.ArrayBase):
            def __init__(
                    self, genre, filenames, values, other,
                    allow_data_inconsistency=False
            ):
                super().__init__(
                    genre, filenames, values, allow_data_inconsistency
                )
        vals.return_value = [1, 2, 3]
        fnms.return_value = ['f1', 'f2', 'f3']
        arr = Sub(
            genre='bla', filenames=['f1', 'f2', 'f3'], values=[1, 2, 3],
            other='foo'
        )
        self.assertDictEqual(
            arr.get_args(),
            {'genre': 'bla', 'filenames': ['f1', 'f2', 'f3'],
             'values': [1, 2, 3], 'other': None,
             'allow_data_inconsistency': False}
        )

    def test_get_args_not_stored_arg_with_default(self, fnms, vals):
        class Sub(ab.ArrayBase):
            def __init__(
                    self, genre, filenames, values, other='foo',
                    allow_data_inconsistency=False
            ):
                super().__init__(
                    genre, filenames, values, allow_data_inconsistency
                )
        vals.return_value = [1, 2, 3]
        fnms.return_value = ['f1', 'f2', 'f3']
        arr = Sub(
            genre='bla', filenames=['f1', 'f2', 'f3'], values=[1, 2, 3],
            other='foo'
        )
        self.assertDictEqual(
            arr.get_args(),
            {'genre': 'bla', 'filenames': ['f1', 'f2', 'f3'],
             'values': [1, 2, 3], 'other': 'foo',
             'allow_data_inconsistency': False}
        )

    @mock.patch(
        'tesliper.glassware.array_base.ArrayBase.get_args',
        return_value={'genre': 'bla', 'filenames': ['f1', 'f2', 'f3'],
                      'values': [1, 2, 3], 'allow_data_inconsistency': False}
    )
    def test_str(self, get, fnms, vals):
        vals.return_value = [1, 2, 3]
        m = mock.Mock()
        type(m).size = mock.PropertyMock(return_value=3)
        fnms.return_value = m
        arr = self.Sub(
            genre='bla', filenames=['f1', 'f2', 'f3'], values=[1, 2, 3]
        )
        self.assertEqual(
            str(arr), "[Sub of genre 'bla', 3 conformers]"
        )

    @mock.patch(
        'tesliper.glassware.array_base.ArrayBase.get_args',
        return_value={'genre': 'bla', 'filenames': ['f1', 'f2', 'f3'],
                      'values': [1, 2, 3], 'allow_data_inconsistency': False}
    )
    def test_repr(self, get, fnms, vals):
        vals.return_value = [1, 2, 3]
        fnms.return_value = ['f1', 'f2', 'f3']
        arr = self.Sub(
            genre='bla', filenames=['f1', 'f2', 'f3'], values=[1, 2, 3]
        )
        self.assertEqual(
            repr(arr), "Sub(genre='bla', filenames=['f1', 'f2', 'f3'], "
                       "values=[1, 2, 3], allow_data_inconsistency=False)"
        )

    def test_len(self, fnms, vals):
        fnms.return_value = ['f1', 'f2', 'f3']
        arr = self.Sub(
            genre='bla', filenames=['f1', 'f2', 'f3'], values=[1, 2, 3]
        )
        self.assertEqual(len(arr), 3)

    def test_bool(self, fnms, vals):
        type(fnms).size = mock.PropertyMock(return_value=3)
        arr = self.Sub(
            genre='bla', filenames=['f1', 'f2', 'f3'], values=[1, 2, 3]
        )
        self.assertTrue(bool(arr))

    def test_bool_empty(self, fnms, vals):
        m = mock.Mock()
        type(m).size = mock.PropertyMock(return_value=0)
        fnms.return_value = m
        arr = self.Sub(genre='bla', filenames=[], values=[])
        self.assertEqual(arr.filenames.size, 0)
        self.assertFalse(bool(arr))
