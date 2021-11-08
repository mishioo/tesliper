from unittest.mock import Mock

import numpy as np
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from tesliper.datawork import spectra as sp


# test count_imaginary
def test_count_imaginary_empty_array():
    assert sp.count_imaginary(np.array([])).tolist() == []


def test_count_imaginary_single_value_positive():
    assert sp.count_imaginary(np.array([1])).tolist() == 0


def test_count_imaginary_single_value_zero():
    assert sp.count_imaginary(np.array([0])).tolist() == 0


def test_count_imaginary_single_value_negative():
    assert sp.count_imaginary(np.array([-1])).tolist() == 1


def test_count_imaginary_zero_dimensions_positive():
    assert sp.count_imaginary(np.array(1, dtype=int)).tolist() == 0


def test_count_imaginary_zero_dimensions_zero():
    assert sp.count_imaginary(np.array(0, dtype=int)).tolist() == 0


def test_count_imaginary_zero_dimensions_negative():
    assert sp.count_imaginary(np.array(-1, dtype=int)).tolist() == 1


def test_count_imaginary_zero_imag_one_conf():
    assert sp.count_imaginary(np.arange(0, 6, 1).reshape(1, -1)).tolist() == [0]


def test_count_imaginary_one_imag_one_conf():
    assert sp.count_imaginary(np.arange(-1, 6, 1).reshape(1, -1)).tolist() == [1]


def test_count_imaginary_zero_imag_two_confs():
    assert sp.count_imaginary(np.arange(0, 6, 1).reshape(2, -1)).tolist() == [0, 0]


def test_count_imaginary_one_imag_two_confs():
    assert sp.count_imaginary(np.arange(-1, 5, 1).reshape(2, -1)).tolist() == [1, 0]


def test_count_imaginary_two_imag_two_confs():
    assert sp.count_imaginary(np.array([[1, -1, 1], [-1, 1, 1]])).tolist() == [1, 1]


def test_count_imaginary_tree_dimensions():
    with pytest.raises(ValueError):
        sp.count_imaginary(np.array([[[1]]]))


# test find_imaginary
def test_find_imaginary_less_dim_zero_imag():
    assert sp.find_imaginary(np.arange(0, 6, 1).reshape(1, -1)).tolist() == []


def test_find_imaginary_less_dim_one_imag():
    assert sp.find_imaginary(np.arange(-1, 5, 1).reshape(1, -1)).tolist() == [0]


def test_find_imaginary_zero_imag():
    assert sp.find_imaginary(np.arange(0, 6, 1).reshape(2, -1)).tolist() == []


def test_find_imaginary_imag_at_first():
    assert sp.find_imaginary(np.arange(-1, 5, 1).reshape(2, -1)).tolist() == [0]


def test_find_imaginary_imag_at_second():
    assert sp.find_imaginary(np.array([[1, 1, 1], [1, -1, 1]])).tolist() == [1]


def test_find_imaginary_more_dimensions():
    with pytest.raises(ValueError):
        sp.find_imaginary(np.array([[[1]]]))


# test gaussian
def test_gaussian_mean_0_std_dev_1():
    np.testing.assert_array_almost_equal(
        sp.gaussian(np.array([1]), np.array([0]), np.arange(-5, 6, 1), np.sqrt(2)),
        [
            0.0000014867195147343,
            0.0001338302257648850,
            0.0044318484119380100,
            0.0539909665131881000,
            0.2419707245191430000,
            0.3989422804014330000,
            0.2419707245191430000,
            0.0539909665131881000,
            0.0044318484119380100,
            0.0001338302257648850,
            0.0000014867195147343,
        ],  # values from Excel 2010 NORM.DIST
    )


def test_gaussian_width_zero():
    with pytest.raises(ValueError):
        sp.gaussian(np.array([1]), np.array([0]), np.arange(-5, 6, 1), 0)


def test_gaussian_width_below_zero():
    with pytest.raises(ValueError):
        sp.gaussian(np.array([1]), np.array([0]), np.arange(-5, 6, 1), -1)


def test_gaussian_unequal_sizes():
    with pytest.raises(ValueError):
        sp.gaussian(np.array([1, 2]), np.array([0]), np.arange(-5, 6, 1), 1)


def test_gaussian_empty_intensities():
    out = sp.gaussian(np.array([]), np.array([]), np.arange(-5, 6, 1), 1)
    assert out.tolist() == np.zeros(11).tolist()


def test_gaussian_empty_abscissia():
    out = sp.gaussian(np.array([1]), np.array([0]), np.array([]), 1)
    assert out.tolist() == []


# test lorentzian
def test_lorentzian_mean_0_std_dev_1():
    np.testing.assert_array_almost_equal(
        sp.lorentzian(np.array([1]), np.array([0]), np.arange(-5, 6, 1), 1 / 2),  # L/2
        [
            0.00630316606304536,
            0.00979415034411664,
            0.01720593979371840,
            0.03744822190397540,
            0.12732395447351600,
            0.63661977236758100,
            0.12732395447351600,
            0.03744822190397540,
            0.01720593979371840,
            0.00979415034411664,
            0.00630316606304536,
        ]  # values from Excel 2010
        # =(L/(2*PI())) / (POWER((x-x0); 2) + POWER((L/2); 2))
    )


def test_lorentzian_width_zero():
    with pytest.raises(ValueError):
        sp.lorentzian(np.array([1]), np.array([0]), np.arange(-5, 6, 1), 0)


def test_lorentzian_width_below_zero():
    with pytest.raises(ValueError):
        sp.lorentzian(np.array([1]), np.array([0]), np.arange(-5, 6, 1), -1)


def test_lorentzian_unequal_sizes():
    with pytest.raises(ValueError):
        sp.lorentzian(np.array([1, 2]), np.array([0]), np.arange(-5, 6, 1), 1)


def test_lorentzian_empty_intensities():
    out = sp.lorentzian(np.array([]), np.array([]), np.arange(-5, 6, 1), 1)
    assert out.tolist() == np.zeros(11).tolist()


def test_lorentzian_empty_abscissia():
    out = sp.lorentzian(np.array([1]), np.array([0]), np.array([]), 1)
    assert out.tolist() == []


# test calculate_spectra


@pytest.fixture
def fitting():
    mock = Mock()

    def func(intensities, frequencies, abscissa, width, m=mock):
        return np.ones_like(abscissa, dtype=int) * m.call_count

    mock.side_effect = func
    return mock


def test_calculate_spectra_zero_conformers(fitting):
    out = sp.calculate_spectra(np.array([]), np.array([]), np.arange(3), 1, fitting)
    assert out.tolist() == []


def test_calculate_spectra_one_conformer(fitting):
    out = sp.calculate_spectra(
        np.ones((1, 2)), np.ones((1, 2)), np.arange(3), 1, fitting
    )
    assert out.tolist() == [[1, 1, 1]]


def test_calculate_spectra_two_conformers(fitting):
    out = sp.calculate_spectra(
        np.ones((2, 2)), np.ones((2, 2)), np.arange(3), 1, fitting
    )
    assert out.tolist() == [[1, 1, 1], [2, 2, 2]]


def test_calculate_spectra_unmatching_arrays(fitting):
    with pytest.raises(ValueError):
        sp.calculate_spectra(np.ones((2, 2)), np.ones((3, 2)), np.arange(3), 1, fitting)


def test_calculate_spectra_empty_abscissa(fitting):
    out = sp.calculate_spectra(
        np.ones((2, 2)), np.ones((2, 2)), np.array([]), 1, fitting
    )
    assert out.tolist() == [[], []]


# test calculate_average
def test_calculate_average_one_dim():
    out = sp.calculate_average([2, 6], [0.25, 0.75])
    assert out == 5


def test_calculate_average_two_dims():
    out = sp.calculate_average([[2, 4], [6, 8]], [0.25, 0.75])
    assert out.tolist() == [5, 7]


def test_calculate_average_three_dims():
    out = sp.calculate_average([[[2, 4], [6, 8]], [[6, 8], [6, 12]]], [0.25, 0.75])
    assert out.tolist() == [[5, 7], [6, 11]]


def test_calculate_average_normalize():
    out = sp.calculate_average([2, 6], [1, 3])
    assert out == 5


def test_calculate_average_unmatching_sizes():
    with pytest.raises(ValueError):
        sp.calculate_average([1, 2], [1, 2, 3])
    with pytest.raises(ValueError):
        sp.calculate_average([1, 2, 3], [1, 2])
    with pytest.raises(ValueError):
        sp.calculate_average([1, 2, 3], 1)


@given(st.integers(min_value=3, max_value=100), st.integers(), st.integers())
def test_offset_one_peak_same_size(size, peak, shift):
    # TODO: when size == 2 and shift == 1 this gives offset == 1 instead of -1
    #       investigate on this error
    assume(0 <= peak < size)
    assume(0 <= peak + shift < size)
    a, b = np.zeros(size), np.zeros(size)
    a[peak] = 10
    b[peak + shift] = 10
    offset = sp.idx_offset(a, b)
    assert offset == -shift


@given(
    st.floats(min_value=0.1, max_value=1),
    st.floats(min_value=0.1, max_value=1),
    st.integers(min_value=100, max_value=1000),
    st.integers(min_value=100, max_value=1000),
    st.booleans(),
    st.booleans(),
)
def test_unify_abscissa(d1, d2, n1, n2, up, decreasing_abscissa):
    x1 = np.arange(n1) * d1
    x2 = np.arange(n2) * d2
    delta = min([d1, d2]) if up else max([d1, d2])
    if decreasing_abscissa:
        x1, x2 = x1[::-1], x2[::-1]
        d1, d2, delta = -d1, -d2, -delta
    ax, ay, bx, by = sp.unify_abscissa(x1, np.arange(n1), x2, np.arange(n2), up)
    assert np.allclose([ax[1] - ax[0], bx[1] - bx[0]], [delta])


@given(
    st.floats(min_value=0.1, max_value=10),
    st.integers(min_value=100, max_value=1000),
    st.integers(min_value=0, max_value=999),
    st.integers(min_value=0, max_value=999),
)
def test_find_offset(delta, size, peak1, peak2):
    assume(peak1 < size and peak2 < size)
    ay, by = np.zeros(size), np.zeros(size)
    ay[peak1], by[peak2] = 1, 1
    x = np.arange(0, delta * size, delta)
    offset = sp.find_offset(x, ay, x, by)
    assert offset == delta * (peak1 - peak2)


@given(
    st.lists(st.floats(allow_nan=False, allow_infinity=False)),
    st.lists(st.floats(allow_nan=False, allow_infinity=False)),
)
def test_find_scaling(a, b):
    scale = sp.find_scaling(a, b)
    assert scale >= 0
