from unittest import mock
import pytest
from hypothesis import assume, given, strategies as st

from tesliper.extraction.parameters_parser import (
    ParametersParser,
    quantity,
    fitting,
    ParsingError,
)


@given(
    s1=st.text(alphabet=st.characters(blacklist_categories=("Cs", "Nd", "No"))),
    s2=st.text().filter(lambda x: not x or not x[0].isnumeric()),
    f=st.floats(allow_nan=False, allow_infinity=False),
)
def test_quantity(s1, s2, f):
    assume(not s1.endswith((".", "-")))
    test_string = f"{s1}{f}{s2}"
    assert f == quantity(test_string), test_string


@given(s=st.text(alphabet=st.characters(blacklist_categories=("Cs", "Nd", "No"))))
def test_quantity_raises(s):
    with pytest.raises(ParsingError):
        quantity(s)


@given(
    s1=st.text(),
    s2=st.text().filter(lambda x: not x or not x[0].isnumeric()),
    f=st.one_of(st.just("gaussian"), st.just("lorentzian")),
)
def test_fitting(s1, s2, f):
    test_string = f"{s1}{f}{s2}"
    assert callable(fitting(test_string))


@given(
    s=st.text().filter(lambda x: all(f not in x for f in ["gaussian", "lorentzian"]))
)
def test_fitting_raises(s):
    with pytest.raises(ParsingError):
        fitting(s)


@pytest.fixture
def get_config(tmp_path):
    def write_config(config):
        file = tmp_path / "par.txt"
        with file.open("w") as handle:
            handle.write(config)
        return file

    return write_config


@pytest.fixture
def stdconfig(get_config):
    return (
        "[PARAMETERS]\n"
        "width = 1\n"
        "start = 0\n"
        "stop = 100\n"
        "step = 5\n"
        "fitting = gaussian\n"
    )


def test_parser(stdconfig, get_config):
    file = get_config(stdconfig)
    p = ParametersParser()
    data = p.parse(file)
    assert data.keys() == p._transformers.keys()
    assert callable(data["fitting"])
    assert all(isinstance(data[k], float) for k in ("width", "start", "stop", "step"))
    assert data == p.parameters


def test_parser_aliases(get_config):
    file = get_config(
        "[PARAMETERS]\n"
        "Half width of band in half height = 1\n"
        "Start Range = 0\n"
        "Stop range = 100\n"
        "Step = 5\n"
        "Fitting Function = Gaussian\n"
    )
    p = ParametersParser()
    data = p.parse(file)
    assert data.keys() == p._transformers.keys()


def test_parser_missing_param(stdconfig, get_config):
    file = get_config("[PARAMETERS]\nwidth = 1\n")
    p = ParametersParser()
    data = p.parse(file)
    assert list(data) == ["width"]


def test_parser_missing_header(stdconfig, get_config):
    file = get_config("\n".join(stdconfig.split("\n")[1:]))
    p = ParametersParser()
    data = p.parse(file)
    assert data.keys() == p._transformers.keys()


def test_parser_different_header(stdconfig, get_config):
    config = ["[SPAM]\n"] + stdconfig.split("\n")[1:]
    file = get_config("\n".join(config))
    p = ParametersParser()
    data = p.parse(file)
    assert data.keys() == p._transformers.keys()


def test_parser_two_sections(stdconfig, get_config):
    config = stdconfig + "\n[OTHER]\nfoo = bar\n"
    file = get_config(config)
    p = ParametersParser()
    with pytest.raises(ParsingError):
        p.parse(file)
