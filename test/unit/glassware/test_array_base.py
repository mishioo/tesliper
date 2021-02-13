import sys
from unittest import mock

from tesliper.exceptions import InconsistentDataError
import tesliper.glassware.array_base as ab
import pytest
import numpy as np

from hypothesis import given, strategies as st


@pytest.mark.parametrize(
    "values,lengths",
    [
        ([], ()),
        ([1], ()),
        ([[]], (0,)),
        ([[1]], (1,)),
        ([[1, 2], [1]], (2,)),
        ([[[1], [2]], [[1]]], (2, 1)),
        ([[[1, 2], [2]], [[1]]], (2, 2)),
        ([[[1], [2]], [[1, 2]]], (2, 2)),
        ([[[1], 2], [[1, 2]]], (2,)),
        ([[[1, 2]], [[1], 2]], (2,)),
    ],
)
def test_longest_subsequences(values, lengths):
    assert ab.longest_subsequences(values) == lengths


@pytest.mark.parametrize(
    "values,lengths",
    [(["a"], ()), ([["a"]], (1,)), ([["aa"]], (1,))],
)
def test_longest_subsequences_str(values, lengths):
    assert ab.longest_subsequences(values) == lengths


@pytest.mark.parametrize(
    "values,lengths",
    [
        ([], (0,)),
        ([1], (1,)),
        ([[]], (1, 0)),
        ([[1]], (1, 1)),
        ([[1, 2], [1]], (2, 2)),
        ([[[1], [2]], [[1]]], (2, 2, 1)),
        ([[[1, 2], [2]], [[1]]], (2, 2, 2)),
        ([[[1], [2]], [[1, 2]]], (2, 2, 2)),
        ([[[1], 2], [[1, 2]]], (2, 2)),
        ([[[1, 2]], [[1], 2]], (2, 2)),
    ],
)
def test_find_best_shape(values, lengths):
    assert ab.find_best_shape(values) == lengths


@pytest.mark.parametrize(
    "values,depth,flatted",
    [
        ([[1, 2], [3]], 2, [1, 2, 3]),
        ([[1, 2], []], 2, [1, 2]),
        ([[1, [2]], [3]], 2, [1, [2], 3]),
        ([[1, [2]], [3]], None, [1, 2, 3]),
        ([[[[1]]]], 1, [[[[1]]]]),  # ndim - 3
        ([[[[1]]]], 2, [[[1]]]),  # ndim - 2
        ([[[[1]]]], 3, [[1]]),  # ndim - 1
        ([[[[1]]]], 4, [1]),  # ndim
    ],
)
def test_flatten(values, depth, flatted):
    assert list(ab.flatten(values, depth)) == flatted


@pytest.mark.parametrize(
    "values,masked",
    [
        ([], []),
        ([1], [1]),
        ([[1, 2], [3]], [[1, 2], [3, 0]]),
        ([[1, 2], []], [[1, 2], [0, 0]]),
        ([[1, 2], [3], [4, 5, 6]], [[1, 2, 0], [3, 0, 0], [4, 5, 6]]),
        ([[[1, 2], [3]]], [[[1, 2], [3, 0]]]),
        ([[[1, 2], []]], [[[1, 2], [0, 0]]]),
        (
            [[[1, 2], [3]], [[1, 2, 3]]],
            [[[1, 2, 0], [3, 0, 0]], [[1, 2, 3], [0, 0, 0]]],
        ),
        (
            [[[[], [1, 2]]], [[[]], [[3]]]],
            [
                [[[0, 0], [1, 2]], [[0, 0], [0, 0]]],
                [[[0, 0], [0, 0]], [[3, 0], [0, 0]]],
            ],
        ),
    ],
)
def test_to_masked(values, masked):
    masked = np.array(masked)
    masked = np.ma.array(masked, mask=(masked == 0))
    array = ab.to_masked(values)
    np.testing.assert_array_equal(array, masked)
    np.testing.assert_array_equal(array.mask, masked.mask)


def test_to_masked_inconsistent_dims():
    with pytest.raises(ValueError):
        ab.to_masked([[1], 1])


@pytest.mark.parametrize(
    "values,mask",
    [
        ([], []),
        ([1], [1]),
        ([[1, 2], [3]], [[1, 1], [1, 0]]),
        ([[1, 2], []], [[1, 1], [0, 0]]),
        ([[1, 2], [3], [4, 5, 6]], [[1, 1, 0], [1, 0, 0], [1, 1, 1]]),
        ([[[1, 2], [3]]], [[[1, 1], [1, 0]]]),
        ([[[1, 2], []]], [[[1, 1], [0, 0]]]),
        (
            [[[1, 2], [3]], [[1, 2, 3]]],
            [[[1, 1, 0], [1, 0, 0]], [[1, 1, 1], [0, 0, 0]]],
        ),
        (
            [[[[], [1, 2]]], [[[]], [[3]]]],
            [
                [[[0, 0], [1, 2]], [[0, 0], [0, 0]]],
                [[[0, 0], [0, 0]], [[1, 0], [0, 0]]],
            ],
        ),
    ],
)
def test__mask(values, mask):
    mask = np.array(mask, dtype=bool)
    values = ab._mask(values, mask.shape)
    np.testing.assert_array_equal(values, mask)


@pytest.mark.xfail
def test__mask_shape_more_dims():
    shape = (1, 1, 1)
    mask = ab._mask([[1]], shape)
    assert mask.shape == shape


def test__mask_shape_less_dims():
    shape = (1, 1)
    mask = ab._mask([[[1]]], shape)
    assert mask.shape == shape


@pytest.mark.parametrize("shape", [(1, 2), (2, 1), (2, 2)])
def test__mask_shape_bigger(shape):
    mask = ab._mask([[1]], shape)
    assert mask.shape == shape


@pytest.mark.xfail
@pytest.mark.parametrize("shape", [(1, 2), (2, 1), (2, 2)])
def test__mask_shape_smaller(shape):
    mask = ab._mask([[1, 1], [1, 1]], shape)
    assert mask.shape == shape


def test_mask(mocker):
    values = mock.Mock()
    shape = mock.Mock()
    mocker.patch("tesliper.glassware.array_base.find_best_shape", return_value=shape)
    mocker.patch("tesliper.glassware.array_base._mask")
    ab.mask(values)
    ab.find_best_shape.assert_called_with(values)
    ab._mask.assert_called_with(values, shape)


@pytest.fixture
def class_array():
    class Cls:
        arr = ab.ArrayProperty(dtype=int)

    return Cls


@pytest.fixture
def class_array_check_x():
    class Cls:
        arr = ab.ArrayProperty(dtype=int, check_against="x")

    return Cls


@pytest.fixture
def class_array_xetters():
    class Cls:
        arr = ab.ArrayProperty(
            dtype=int, fget=mock.Mock(), fset=mock.Mock(), fdel=mock.Mock()
        )

    return Cls


def test_getter_called(class_array_xetters):
    arr = class_array_xetters()
    _ = arr.arr
    class_array_xetters.arr.fget.assert_called()
    class_array_xetters.arr.fget.assert_called_with(arr)


def test_setter_called(class_array_xetters):
    arr = class_array_xetters()
    arr.arr = 1
    class_array_xetters.arr.fset.assert_called()
    class_array_xetters.arr.fset.assert_called_with(arr, 1)


def test_deletter_called(class_array_xetters):
    arr = class_array_xetters()
    del arr.arr
    class_array_xetters.arr.fdel.assert_called()
    class_array_xetters.arr.fdel.assert_called_with(arr)


def test_sanitizer_called():
    class Cls:
        arr = ab.ArrayProperty(fsan=mock.Mock(return_value=[1, 2, 3]))

    arr = Cls()
    arr.arr = 1
    assert arr.arr.tolist() == [1, 2, 3]
    Cls.arr.fsan.assert_called()


def test_docs_from_getter():
    class Cls:
        def func(self):
            """Docstring for testing."""

        arr = ab.ArrayProperty(fget=func)

    assert Cls.arr.__doc__ == """Docstring for testing."""


def test_array_property_class_access(class_array):
    assert type(class_array.arr) is ab.ArrayProperty


def test_array_property_name(class_array):
    assert class_array.arr.name == "arr"


def test_array_property_check_input_no_attribute(class_array_check_x):
    with pytest.raises(AttributeError):
        class_array_check_x.arr.check_input(class_array_check_x(), [1, 2, 3])


def test_array_property_check_input_against(class_array_check_x):
    arr = class_array_check_x()
    arr.x = [1, 2, 3]
    assert class_array_check_x.arr.check_input(arr, [4, 5, 6]).tolist() == [4, 5, 6]


def test_array_property_check_input_against_deep(class_array_check_x):
    class_array_check_x.arr.check_depth = 2
    arr = class_array_check_x()
    arr.x = [[1], [2], [3]]
    assert class_array_check_x.arr.check_input(arr, [[4], [5], [6]]).tolist() == [
        [4],
        [5],
        [6],
    ]


def test_array_property_check_input_against_deeper(class_array_check_x):
    class_array_check_x.arr.check_depth = 2
    arr = class_array_check_x()
    arr.x = [[[1]], [[2]], [[3]]]
    assert class_array_check_x.arr.check_input(arr, [[4], [5], [6]]).tolist() == [
        [4],
        [5],
        [6],
    ]


def test_array_property_check_input_against_deep_unmatching(class_array_check_x):
    class_array_check_x.arr.check_depth = 2
    arr = class_array_check_x()
    arr.x = [[1], [2], [3]]
    with pytest.raises(ValueError):
        class_array_check_x.arr.check_input(arr, [1, 2, 3])


def test_array_property_check_input_against_deep_unmatching_allowed(
    class_array_check_x,
):
    class_array_check_x.arr.check_depth = 2
    arr = class_array_check_x()
    arr.allow_data_inconsistency = True
    arr.x = [[1], [2], [3]]
    assert class_array_check_x.arr.check_input(arr, [4, 5, 6]).tolist() == [4, 5, 6]


def test_array_property_check_input_unmatching(class_array_check_x):
    arr = class_array_check_x()
    arr.x = [1, 2]
    with pytest.raises(ValueError):
        class_array_check_x.arr.check_input(arr, [1, 2, 3])


def test_array_property_check_input_unmatching_allowed(class_array_check_x):
    arr = class_array_check_x()
    arr.x = [1, 2]
    arr.allow_data_inconsistency = True
    assert class_array_check_x.arr.check_input(arr, [1, 2, 3]).tolist() == [1, 2, 3]


def test_array_property_check_input_inconsistent(class_array_check_x):
    arr = class_array_check_x()
    arr.x = [1, 2]
    with pytest.raises(InconsistentDataError):
        class_array_check_x.arr.check_input(arr, [[1, 2], [3]])


def test_array_property_check_input_inconsistent_allowed(
    monkeypatch, class_array_check_x
):
    pad_mock = mock.Mock(return_value=[[1, 2], [3, 0]])
    monkeypatch.setattr(ab, "to_masked", pad_mock)
    arr = class_array_check_x()
    arr.x = [1, 2]
    arr.allow_data_inconsistency = True
    out = class_array_check_x.arr.check_input(arr, [[1, 2], [3]])
    pad_mock.assert_called_with([[1, 2], [3]], dtype=int)
    assert out == [[1, 2], [3, 0]]


def test_array_property_decorator_with_dtype():
    mck = mock.Mock()

    class Cls:
        @ab.ArrayProperty(dtype=mck)
        def arr(self):
            pass

    assert Cls.arr.dtype is mck
    assert Cls.arr.fset is None
    assert Cls.arr.fdel is None
    assert Cls.arr.check_against is None


def test_array_property_decorator():
    class Cls:
        @ab.ArrayProperty
        def arr(self):
            pass

    assert Cls.arr.fset is None
    assert Cls.arr.fdel is None
    assert Cls.arr.check_against is None


single_value = {
    int: st.integers(min_value=-sys.maxsize, max_value=sys.maxsize),
    float: st.floats(allow_nan=False),
    str: st.characters(blacklist_categories=["Cs"], blacklist_characters=["\x00"]),
}
list_of_identical = {
    key: st.builds(lambda v, n: [v] * n, strat, st.integers(min_value=1, max_value=10))
    for key, strat in single_value.items()
}
list_of_unique = {
    key: st.lists(strat, min_size=2, unique=True) for key, strat in single_value.items()
}
list_of_identical_lists = {
    key: st.builds(lambda v, n: [v] * n, strat, st.integers(min_value=1, max_value=10))
    for key, strat in list_of_unique.items()
}
list_of_unique_lists = {
    key: st.builds(
        lambda vals: [list(v) for v in vals],
        st.integers(min_value=1, max_value=10).flatmap(
            lambda n: st.lists(
                st.tuples(*[strat for _ in range(n)]), min_size=2, unique=True
            ),
        ),
    )
    for key, strat in single_value.items()
}


@pytest.fixture
def mock_check_input(monkeypatch):
    monkeypatch.setattr(
        ab.ArrayProperty,
        "check_input",
        mock.Mock(side_effect=lambda i, x: ab.np.array(x)),
    )


@pytest.fixture(params=(int, float, str), scope="module")
def class_collapsable_array(request):
    class Cls:
        arr = ab.CollapsibleArrayProperty(dtype=request.param)

    return Cls


@pytest.fixture(scope="module")
def instance_not_adi():
    return mock.Mock(allow_data_inconsistency=False)


@pytest.fixture(scope="module")
def instance_adi():
    return mock.Mock(allow_data_inconsistency=True)


@pytest.mark.usefixtures("mock_check_input")
@given(st.data())
def test_collapsable_single_value(class_collapsable_array, instance_not_adi, data):
    value = data.draw(single_value[class_collapsable_array.arr.dtype])
    assert class_collapsable_array.arr.check_input(
        instance_not_adi, value
    ).tolist() == [value]
    ab.ArrayProperty.check_input.assert_not_called()


@pytest.mark.usefixtures("mock_check_input")
@given(st.data(), st.integers(min_value=1, max_value=10))
def test_collapsable_list_of_identical(
    class_collapsable_array, instance_not_adi, data, number
):
    value = data.draw(single_value[class_collapsable_array.arr.dtype])
    arr = [value] * number
    assert class_collapsable_array.arr.check_input(instance_not_adi, arr).tolist() == [
        value
    ]
    ab.ArrayProperty.check_input.assert_called()


@pytest.mark.usefixtures("mock_check_input")
@given(st.data())
def test_collapsable_list_of_unique(class_collapsable_array, instance_not_adi, data):
    values = data.draw(list_of_unique[class_collapsable_array.arr.dtype])
    with pytest.raises(InconsistentDataError):
        class_collapsable_array.arr.check_input(instance_not_adi, values)


@pytest.mark.usefixtures("mock_check_input")
@given(st.data())
def test_collapsable_list_of_unique_allowed(
    class_collapsable_array, instance_adi, data
):
    values = data.draw(list_of_unique[class_collapsable_array.arr.dtype])
    assert (
        class_collapsable_array.arr.check_input(instance_adi, values).tolist() == values
    )


@pytest.mark.usefixtures("mock_check_input")
def test_collapsable_empty_list(class_collapsable_array, instance_not_adi):
    assert class_collapsable_array.arr.check_input(instance_not_adi, []).tolist() == []


@pytest.mark.usefixtures("mock_check_input")
@given(st.data())
def test_cllapsable_list_of_identical_lists(
    class_collapsable_array, instance_not_adi, data
):
    values = data.draw(list_of_identical_lists[class_collapsable_array.arr.dtype])
    assert class_collapsable_array.arr.check_input(
        instance_not_adi, values
    ).tolist() == [values[0]]


@pytest.mark.usefixtures("mock_check_input")
@given(st.data())
def test_cllapsable_list_of_unique_lists(
    class_collapsable_array, instance_not_adi, data
):
    values = data.draw(list_of_unique_lists[class_collapsable_array.arr.dtype])
    with pytest.raises(InconsistentDataError):
        class_collapsable_array.arr.check_input(instance_not_adi, values)


@pytest.mark.usefixtures("mock_check_input")
@given(st.data())
def test_cllapsable_list_of_unique_lists_allowed(
    class_collapsable_array, instance_adi, data
):
    values = data.draw(list_of_unique_lists[class_collapsable_array.arr.dtype])
    assert (
        class_collapsable_array.arr.check_input(instance_adi, values).tolist() == values
    )


@pytest.fixture
def filenames_mock(monkeypatch):
    mocked = mock.PropertyMock()
    monkeypatch.setattr(ab.ArrayBase, "filenames", mocked)
    return mocked


@pytest.fixture
def values_mock(monkeypatch):
    mocked = mock.PropertyMock()
    monkeypatch.setattr(ab.ArrayBase, "values", mocked)
    return mocked


@pytest.fixture
def array_subclass():
    class Sub(ab.ArrayBase):
        associated_genres = "bla"

    return Sub


def test_array_base_subclass_no_associated_genres():
    class Sub(ab.ArrayBase):
        pass

    assert Sub.associated_genres is NotImplemented


def test_array_base_get_args(filenames_mock, values_mock, array_subclass):
    values_mock.return_value = [1, 2, 3]
    filenames_mock.return_value = ["f1", "f2", "f3"]
    arr = array_subclass(genre="bla", filenames=["f1", "f2", "f3"], values=[1, 2, 3])
    assert arr.get_repr_args() == {
        "genre": "bla",
        "filenames": ["f1", "f2", "f3"],
        "values": [1, 2, 3],
        "allow_data_inconsistency": False,
    }


def test_array_base_get_args_not_stored_arg(filenames_mock, values_mock):
    class Sub(ab.ArrayBase):
        def __init__(
            self, genre, filenames, values, other, allow_data_inconsistency=False
        ):
            super().__init__(genre, filenames, values, allow_data_inconsistency)

    values_mock.return_value = [1, 2, 3]
    filenames_mock.return_value = ["f1", "f2", "f3"]
    arr = Sub(genre="bla", filenames=["f1", "f2", "f3"], values=[1, 2, 3], other="foo")
    assert arr.get_repr_args() == {
        "genre": "bla",
        "filenames": ["f1", "f2", "f3"],
        "values": [1, 2, 3],
        "other": None,
        "allow_data_inconsistency": False,
    }


def test_array_base_get_args_not_stored_arg_with_default(filenames_mock, values_mock):
    class Sub(ab.ArrayBase):
        def __init__(
            self,
            genre,
            filenames,
            values,
            other="foo",
            allow_data_inconsistency=False,
        ):
            super().__init__(genre, filenames, values, allow_data_inconsistency)

    values_mock.return_value = [1, 2, 3]
    filenames_mock.return_value = ["f1", "f2", "f3"]
    arr = Sub(genre="bla", filenames=["f1", "f2", "f3"], values=[1, 2, 3], other="foo")
    assert arr.get_repr_args() == {
        "genre": "bla",
        "filenames": ["f1", "f2", "f3"],
        "values": [1, 2, 3],
        "other": "foo",
        "allow_data_inconsistency": False,
    }


@pytest.fixture
def get_repr_args_mock(monkeypatch):
    monkeypatch.setattr(
        ab.ArrayBase,
        "get_repr_args",
        mock.Mock(
            return_value={
                "genre": "bla",
                "filenames": ["f1", "f2", "f3"],
                "values": [1, 2, 3],
                "allow_data_inconsistency": False,
            }
        ),
    )


def test_array_base_str(
    get_repr_args_mock, filenames_mock, values_mock, array_subclass
):
    values_mock.return_value = [1, 2, 3]
    m = mock.Mock()
    type(m).size = mock.PropertyMock(return_value=3)
    filenames_mock.return_value = m
    arr = array_subclass(genre="bla", filenames=["f1", "f2", "f3"], values=[1, 2, 3])
    assert str(arr) == "[Sub of genre 'bla', 3 conformers]"


def test_array_base_repr(
    get_repr_args_mock, filenames_mock, values_mock, array_subclass
):
    values_mock.return_value = [1, 2, 3]
    filenames_mock.return_value = ["f1", "f2", "f3"]
    arr = array_subclass(genre="bla", filenames=["f1", "f2", "f3"], values=[1, 2, 3])
    assert (
        repr(arr) == "Sub(genre='bla', filenames=['f1', 'f2', 'f3'], "
        "values=[1, 2, 3], allow_data_inconsistency=False)"
    )


def test_array_base_len(filenames_mock, values_mock, array_subclass):
    filenames_mock.return_value = ["f1", "f2", "f3"]
    arr = array_subclass(genre="bla", filenames=["f1", "f2", "f3"], values=[1, 2, 3])
    assert len(arr) == 3


def test_array_base_bool(filenames_mock, values_mock, array_subclass):
    type(filenames_mock).size = mock.PropertyMock(return_value=3)
    arr = array_subclass(genre="bla", filenames=["f1", "f2", "f3"], values=[1, 2, 3])
    assert bool(arr)


def test_array_base_bool_empty(filenames_mock, values_mock, array_subclass):
    m = mock.Mock()
    type(m).size = mock.PropertyMock(return_value=0)
    filenames_mock.return_value = m
    arr = array_subclass(genre="bla", filenames=[], values=[])
    assert arr.filenames.size == 0
    assert not bool(arr)
