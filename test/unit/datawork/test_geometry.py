import pytest
import numpy as np
from hypothesis import given, strategies as st, assume

from tesliper.datawork import geometry


@pytest.fixture(scope="module")
def atoms_take():
    return [1, 2, 1, 3]


@pytest.fixture(scope="module")
def atoms_drop():
    return [3, 1, 2, 1]


@pytest.fixture(scope="module")
def one_dim():
    return list(range(4))


@pytest.fixture(scope="module")
def two_dim():
    return [[y * 10 + x for x in range(4)] for y in range(2)]


@pytest.fixture(scope="module")
def three_dim():
    return [
        [[y * 100 + x * 10 + z for z in range(3)] for x in range(4)] for y in range(2)
    ]


@pytest.fixture(scope="module")
def four_dim():
    return [
        [
            [
                [y * 1000 + x * 100 + z * 10, y * 1000 + x * 100 + z * 10 + 1]
                for z in range(3)
            ]
            for x in range(4)
        ]
        for y in range(2)
    ]


@pytest.mark.skip("To be created.")
def test_take_invalid_atom():
    pass


def test_take_absent_atom(atoms_take, two_dim):
    out = geometry.take_atoms(two_dim, atoms_take, 4)
    np.testing.assert_array_equal(out, [])


def test_take_all_atoms(atoms_take, two_dim):
    out = geometry.take_atoms(two_dim, atoms_take, [1, 2, 3])
    np.testing.assert_array_equal(out, two_dim)


@pytest.mark.skip("To be created.")
def test_take_non_matching_sizes():
    pass


def test_take_one_dimension(atoms_take, one_dim):
    out = geometry.take_atoms(one_dim, atoms_take, 1)
    np.testing.assert_array_equal(out, [0, 2])


def test_take_one_dimension_as_enum(atoms_take, one_dim):
    out = geometry.take_atoms(one_dim, atoms_take, 1)
    np.testing.assert_array_equal(out, [0, 2])


def test_take_two_dimensions(atoms_take, two_dim):
    out = geometry.take_atoms(two_dim, atoms_take, 1)
    np.testing.assert_array_equal(out, [[0, 2], [10, 12]])


def test_take_three_dimensions(atoms_take, three_dim):
    out = geometry.take_atoms(three_dim, atoms_take, 1)
    np.testing.assert_array_equal(
        out, [[[0, 1, 2], [20, 21, 22]], [[100, 101, 102], [120, 121, 122]]]
    )


def test_take_four_dimensions(atoms_take, four_dim):
    out = geometry.take_atoms(four_dim, atoms_take, 1)
    np.testing.assert_array_equal(
        out,
        [
            [[[0, 1], [10, 11], [20, 21]], [[200, 201], [210, 211], [220, 221]]],
            [
                [[1000, 1001], [1010, 1011], [1020, 1021]],
                [[1200, 1201], [1210, 1211], [1220, 1221]],
            ],
        ],
    )


@pytest.mark.skip("To be created.")
def test_take_two_dimensions_atoms():
    pass


def test_take_atoms_keeping(atoms_take):
    out = geometry.take_atoms(atoms_take, atoms_take, 1)
    np.testing.assert_array_equal(out, [1, 1])


@pytest.mark.skip("To be created.")
def test_drop_invalid_atom():
    pass


def test_drop_empty_discarded(atoms_drop, two_dim):
    out = geometry.drop_atoms(two_dim, atoms_drop, [])
    np.testing.assert_array_equal(out, two_dim)


def test_drop_absent_atom(atoms_drop, two_dim):
    out = geometry.drop_atoms(two_dim, atoms_drop, 4)
    np.testing.assert_array_equal(out, two_dim)


def test_drop_all_atoms(atoms_drop, two_dim):
    out = geometry.drop_atoms(two_dim, atoms_drop, [1, 2, 3])
    np.testing.assert_array_equal(out, [])


@pytest.mark.skip("To be created.")
def test_non_matching_sizes():
    pass


def test_drop_one_dimension(atoms_drop, one_dim):
    out = geometry.drop_atoms(one_dim, atoms_drop, 1)
    np.testing.assert_array_equal(out, [0, 2])


def test_drop_two_dimensions(atoms_drop, two_dim):
    out = geometry.drop_atoms(two_dim, atoms_drop, 1)
    np.testing.assert_array_equal(out, [[0, 2], [10, 12]])


def test_drop_three_dimensions(atoms_drop, three_dim):
    out = geometry.drop_atoms(three_dim, atoms_drop, 1)
    np.testing.assert_array_equal(
        out, [[[0, 1, 2], [20, 21, 22]], [[100, 101, 102], [120, 121, 122]]]
    )


def test_drop_four_dimensions(atoms_drop, four_dim):
    out = geometry.drop_atoms(four_dim, atoms_drop, 1)
    np.testing.assert_array_equal(
        out,
        [
            [[[0, 1], [10, 11], [20, 21]], [[200, 201], [210, 211], [220, 221]]],
            [
                [[1000, 1001], [1010, 1011], [1020, 1021]],
                [[1200, 1201], [1210, 1211], [1220, 1221]],
            ],
        ],
    )


@pytest.mark.skip("To be created.")
def test_drop_two_dimensions_atoms():
    pass


def test_drop_atoms_dropping(atoms_drop):
    out = geometry.drop_atoms(atoms_drop, atoms_drop, 1)
    np.testing.assert_array_equal(out, [3, 2])


def test_is_triangular_zero():
    assert geometry.is_triangular(0)


def test_is_triangular_one():
    assert geometry.is_triangular(1)


def test_is_triangular_float():
    assert not geometry.is_triangular(0.5)


def test_is_triangular_inf():
    assert not geometry.is_triangular(float("inf"))


def test_is_triangular_negative():
    assert not geometry.is_triangular(-3)


def test_is_triangular_triangular():
    assert geometry.is_triangular(10)


def test_is_triangular_non_triangular():
    assert not geometry.is_triangular(7)


def test_get_triangular_zero():
    assert geometry.get_triangular(0) == 0


def test_get_triangular_one():
    assert geometry.get_triangular(1) == 1


def test_get_triangular_triangular():
    assert geometry.get_triangular(4) == 10


def test_get_triangular_negative():
    with pytest.raises(ValueError):
        geometry.get_triangular(-3)


def test_get_triangular_float():
    with pytest.raises(ValueError):
        geometry.get_triangular(0.5)


def test_get_triangular_inf():
    with pytest.raises(ValueError):
        geometry.get_triangular(float("inf"))


def test_get_triangular_base_zero():
    assert geometry.get_triangular_base(0) == 0


def test_get_triangular_base_one():
    assert geometry.get_triangular_base(1) == 1


def test_get_triangular_base_float():
    with pytest.raises(ValueError):
        geometry.get_triangular_base(0.5)


def test_get_triangular_base_inf():
    with pytest.raises(ValueError):
        geometry.get_triangular_base(float("inf"))


def test_get_triangular_base_negative():
    with pytest.raises(ValueError):
        geometry.get_triangular_base(-3)


def test_get_triangular_base_triangular():
    assert geometry.get_triangular_base(10) == 4


def test_get_triangular_base_non_triangular():
    with pytest.raises(ValueError):
        geometry.get_triangular_base(7)


st_small_floats = st.floats(
    allow_nan=False, allow_infinity=False, max_value=100, min_value=-100
)


@given(
    st.lists(st_small_floats, min_size=9, max_size=9),
    st.lists(st_small_floats, min_size=3, max_size=30),
)
def test_kabsch_rotate(rotation, points):
    assume(not len(points) % 3)
    # random rotation matrix as proposed by:
    # https://math.stackexchange.com/a/1602779/469731
    rotation, _ = np.linalg.qr(np.reshape(rotation, (3, 3)))
    points = np.reshape(points, (-1, 3))
    points = points - points.mean(axis=0)  # zero-centered
    rotated = points @ rotation
    kabsch = geometry.kabsch_rotate(rotated, points)
    np.testing.assert_array_almost_equal(kabsch, points)


@given(
    st.lists(st_small_floats, min_size=18, max_size=18),
    st.lists(st_small_floats, min_size=6, max_size=60),
)
def test_kabsch_rotate_multidim(rotation, points):
    assume(not len(points) % 6)
    rotation = np.array([np.linalg.qr(r)[0] for r in np.reshape(rotation, (2, 3, 3))])
    points = np.reshape(points, (2, -1, 3))
    points = points - np.expand_dims(points.mean(axis=1), 1)  # zero-centered
    rotated = np.array([p @ r for p, r in zip(points, rotation)])
    kabsch = geometry.kabsch_rotate(rotated, points)
    np.testing.assert_array_almost_equal(kabsch, points)


@given(
    st.lists(st_small_floats, min_size=9, max_size=18),
    st.lists(st_small_floats, min_size=3, max_size=30),
)
def test_kabsch_rotate_a_multidim(rotation, points):
    assume(not len(rotation) % 9)
    assume(not len(points) % 3)
    rotation = np.array([np.linalg.qr(r)[0] for r in np.reshape(rotation, (-1, 3, 3))])
    points = np.reshape(points, (-1, 3))
    points = points - points.mean(axis=0)  # zero-centered
    rotated = np.array([points @ r for r in rotation])
    kabsch = geometry.kabsch_rotate(rotated, points)
    np.testing.assert_array_almost_equal(kabsch, [points] * rotation.shape[0])


@given(
    st.lists(st_small_floats, min_size=9, max_size=18),
    st.lists(st_small_floats, min_size=3, max_size=30),
)
def test_kabsch_rotate_b_multidim(rotation, points):
    assume(not len(rotation) % 9)
    assume(not len(points) % 3)
    rotation = np.array([np.linalg.qr(r)[0] for r in np.reshape(rotation, (-1, 3, 3))])
    points = np.reshape(points, (-1, 3))
    points = points - points.mean(axis=0)  # zero-centered
    rotated = np.array([points @ r for r in rotation])
    kabsch = geometry.kabsch_rotate(points, rotated)
    np.testing.assert_array_almost_equal(kabsch, rotated)


@given(st.lists(st_small_floats, min_size=3, max_size=30), st_small_floats)
def test_rmsd(points, error):
    assume(not len(points) % 3)
    points = np.array(points).reshape(-1, 3)
    np.testing.assert_almost_equal(
        geometry.rmsd(points, points + error),
        np.sqrt(3 * error ** 2),  # error adds up from each coordinate
    )


@given(st.integers(min_value=1, max_value=100), st.integers(min_value=1, max_value=100))
def test_fixed_windows(series_size, window_size):
    assume(window_size <= series_size)
    windowed = geometry.fixed_windows(np.empty((series_size,)), window_size)
    assert windowed.shape == (series_size - window_size + 1, window_size)


@given(st.integers(max_value=0))
def test_fixed_windows_wrong_size_value(size):
    with pytest.raises(ValueError, match=r"must be a positive integer"):
        geometry.fixed_windows([], size)


@pytest.mark.parametrize("size", [0.1, "1", tuple(), [], {}, set()])
def test_fixed_windows_wrong_size_type(size):
    with pytest.raises(TypeError, match=r"must be a positive integer"):
        geometry.fixed_windows([], size)


@pytest.mark.parametrize(
    "ens,out",
    [
        ([], []),
        ([1], []),
        (list(range(4)), [[0, 1, 2], [1, 2, 3]]),
        ([1, 2, 10, 20, 21], [[0, 1], [3, 4]]),
    ],
)
def test_sliding_windows(ens, out):
    assert [x.tolist() for x in geometry.stretching_windows(ens, 2)] == out


@pytest.mark.parametrize(
    "ens,out", [([], []), ([1], [[0]]), ([1, 2, 10, 20, 21], [[0, 1], [2], [3, 4]])]
)
def test_sliding_windows_keep_hermits(ens, out):
    assert [
        x.tolist() for x in geometry.stretching_windows(ens, 2, keep_hermits=True)
    ] == out


@pytest.mark.parametrize(
    "ens,out",
    [
        ([], []),
        ([1], []),
        (list(range(4)), [[0, 1, 2], [1, 2, 3], [2, 3]]),
        ([1, 2, 3, 20, 21], [[0, 1, 2], [1, 2], [3, 4]]),
    ],
)
def test_sliding_windows_soft_bound(ens, out):
    assert [
        x.tolist() for x in geometry.stretching_windows(ens, 2, hard_bound=False)
    ] == out


@given(size=st.floats(max_value=0, allow_nan=False))
@pytest.mark.parametrize("ens", [[], [1], [1, 1]])
def test_sliding_windows_size_non_positive(ens, size):
    with pytest.raises(ValueError):
        next(geometry.stretching_windows(ens, size))
