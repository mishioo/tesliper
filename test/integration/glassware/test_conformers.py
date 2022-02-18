import string

import hypothesis.strategies as st
import pytest
from hypothesis import given

from tesliper import Conformers


@pytest.fixture
def empty():
    return Conformers()


@pytest.mark.parametrize(
    "method,args",
    [
        ("trim_incomplete", ()),
        ("trim_incomplete", (["gib", "iri"],)),
        ("trim_incomplete", (["gib", "iri"], True)),
        ("trim_incomplete", (None, True)),
        ("trim_imaginary_frequencies", ()),
        ("trim_non_matching_stoichiometry", ()),
        ("trim_non_matching_stoichiometry", ("CH2Cl2",)),
        ("trim_not_optimized", ()),
        ("trim_non_normal_termination", ()),
        ("trim_inconsistent_sizes", ()),
        ("trim_to_range", ("gib",)),
        ("trim_rmsd", (1, 1)),
        ("trim_rmsd", (1, 1, "last_read_geom", "scf", False)),
    ],
)
def test_trimming_empty_does_nothing(empty, method, args):
    method_ = getattr(empty, method)
    _ = method_(*args)
    assert empty.kept == []


@st.composite
def name_and_kept(draw):
    n = draw(st.integers(min_value=0, max_value=50))
    names = st.lists(
        st.text(max_size=20, alphabet=string.printable),
        min_size=n,
        max_size=n,
        unique=True,
    )
    kept = st.lists(st.booleans(), min_size=n, max_size=n)
    return (draw(names), draw(kept))


@given(name_and_kept())
def test_arrayed_filenames(lists):
    names, kept = lists
    c = Conformers()
    c.update({n: {} for n in names})
    c.kept = kept
    assert c.arrayed("filenames").values.tolist() == [
        n for n, k in zip(names, kept) if k
    ]
