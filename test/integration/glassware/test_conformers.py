import pytest

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
        ("trim_rmsd", (1, 1, "geometry", "scf", False)),
    ],
)
def test_trimming_empty_does_nothing(empty, method, args):
    method_ = getattr(empty, method)
    _ = method_(*args)
    assert empty.kept == []
