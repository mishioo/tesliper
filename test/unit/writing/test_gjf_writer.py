import string
from pathlib import Path
from string import Template

import pytest
from hypothesis import given, strategies as st, assume

from tesliper.writing.gjf_writer import GjfWriter


@pytest.fixture
def gjfwriter():
    return GjfWriter(destination="")


def test_writer_init(gjfwriter):
    assert gjfwriter.destination == Path("")
    assert gjfwriter.mode == "x"
    assert gjfwriter.link0 == {}
    assert gjfwriter.route == "#"
    assert gjfwriter.comment == "No information provided."
    assert gjfwriter.post_spec == ""
    assert gjfwriter.filename_template.template == "${filename}.${ext}"


@given(st.text())
def test_link0_unknown(gjfwriter, key):
    assume(key.lower() not in gjfwriter._link0_commands)
    with pytest.raises(ValueError):
        gjfwriter.link0 = {key: ""}


@pytest.mark.xfail(reason="To be created")
@given(
    st.dictionaries(
        st.one_of(*[st.just(k) for k in GjfWriter._link0_commands]), st.text()
    )
)
def test_link0_known(gjfwriter, dict):
    pytest.fail("To be created")


@given(st.text())
def test_route_str_not_startswith_hash(gjfwriter, commands):
    assume(not commands.strip().startswith("#"))
    gjfwriter.route = commands
    assert gjfwriter.route == " ".join(["#"] + commands.split())
    assert gjfwriter._route == ["#"] + commands.split()


@given(st.builds(lambda s: "#" + s, st.text()))
def test_route_str_startswith_hash(gjfwriter, commands):
    gjfwriter.route = commands
    assert gjfwriter.route == " ".join(commands.split())
    assert gjfwriter._route == commands.split()
