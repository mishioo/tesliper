from pathlib import Path

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from tesliper.writing.gjf_writer import GjfWriter, _format_coordinates


@given(
    st.lists(st.integers(min_value=1, max_value=118), min_size=4, max_size=4),
    st.lists(
        st.floats(min_value=-100, max_value=100, exclude_min=True, exclude_max=True),
        min_size=12,
        max_size=12,
    ),
)
def test__format_coordinates(atoms, coords):
    coords = [coords[0 + 3 * n : 3 + 3 * n] for n in range(len(atoms))]
    output = list(_format_coordinates(coords, atoms))
    assert len(output) == len(atoms)
    assert all([len(output[0]) == len(output[n]) for n in range(len(output))])


def test_writer_init():
    gjfwriter = GjfWriter(destination="")
    assert gjfwriter.destination == Path("")
    assert gjfwriter.mode == "x"
    assert gjfwriter.link0 == {}
    assert gjfwriter.route == "#"
    assert gjfwriter.comment == "No information provided."
    assert gjfwriter.post_spec == ""


@given(st.text())
def test_link0_unknown(key):
    assume(key.lower() not in GjfWriter._link0_commands)
    with pytest.raises(ValueError):
        GjfWriter(destination="", link0={key: ""})


@pytest.mark.xfail(reason="To be created")
@given(
    st.dictionaries(
        st.one_of(*[st.just(k) for k in GjfWriter._link0_commands]), st.text()
    )
)
def test_link0_known(dict):
    pytest.fail("To be created")


@given(st.text())
def test_route_str_not_startswith_hash(commands):
    assume(not commands.strip().startswith("#"))
    gjfwriter = GjfWriter(destination="", route=commands)
    assert gjfwriter.route == " ".join(["#"] + commands.split())
    assert gjfwriter._route == ["#"] + commands.split()


@given(st.builds(lambda s: "#" + s, st.text()))
def test_route_str_startswith_hash(commands):
    gjfwriter = GjfWriter(destination="", route=commands)
    assert gjfwriter.route == " ".join(commands.split())
    assert gjfwriter._route == commands.split()


st_not_st = st.one_of(
    st.none(),
    st.integers(),
    st.floats(),
    st.sets(st.text(), min_size=1),
    st.dictionaries(st.text(), st.text(), min_size=1),
)


@given(st_not_st)
def test_route_wrong_type(commands):
    with pytest.raises(TypeError):
        GjfWriter(destination="", route=commands)


@given(st.lists(st_not_st, min_size=1))
def test_route_sequence_wrong_type(commands):
    with pytest.raises(TypeError):
        GjfWriter(destination="", route=commands)


def test_route_empty():
    gjfwriter = GjfWriter(destination="", route="")
    assert gjfwriter.route == "#"
    assert gjfwriter._route == ["#"]
