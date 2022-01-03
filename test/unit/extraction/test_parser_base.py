import re
from unittest.mock import Mock, NonCallableMock, patch

import pytest

from tesliper.exceptions import InvalidStateError
from tesliper.extraction import ParserBase


@pytest.fixture
def subclass_params():
    return {
        "initial": Mock(spec=[]),
        "parse": Mock(spec=[]),
        "purpose": "",
        "extensions": tuple(),
    }


@pytest.fixture
def params_with_state(subclass_params, method):
    method.is_state = True
    subclass_params["mystate"] = method
    return subclass_params


@pytest.fixture
def prs(subclass_params):
    cls = type("Prsr", (ParserBase,), subclass_params)
    return cls()


@pytest.fixture
def prs_with_state(params_with_state):
    cls = type("Prsr", (ParserBase,), params_with_state)
    return cls()


@pytest.fixture
def method():
    return Mock(spec=[])


def test_instantiated_directly():
    with pytest.raises(TypeError):
        ParserBase()


def test_state_no_arguments():
    with pytest.raises(TypeError):
        ParserBase.state()


def test_state_not_callable():
    func = NonCallableMock()
    with pytest.raises(InvalidStateError):
        ParserBase.state(func)


def test_state_decorator(method):
    func = ParserBase.state(method)
    assert hasattr(func, "is_state")
    assert func.is_state


def test_state_decorator_with_trigger(method):
    func = ParserBase.state(method, "mytrigger")
    assert hasattr(func, "is_state")
    assert func.is_state
    assert hasattr(func, "trigger")
    assert func.trigger == "mytrigger"


def test_subclassed(prs):
    assert "initial" in prs.states
    assert prs.initial == prs.workhorse


def test_subclassed_with_state(prs_with_state):
    assert hasattr(prs_with_state, "mystate")
    assert "mystate" in prs_with_state.states
    assert prs_with_state.initial == prs_with_state.workhorse


def test_subclassed_with_trigger():
    class Subclass(ParserBase):
        purpose = ""
        extensions = tuple()

        def parse(self, lines):
            pass

        def initial(self, line):
            pass

        @ParserBase.state(trigger="trigger")
        def mystate(prs, method):
            pass

    with patch("re.compile") as mocked_re_compile:
        mocked_re_compile.return_value = "compiled_trigger"
        obj = Subclass()
    assert hasattr(obj, "mystate")
    assert hasattr(obj.mystate, "is_state")
    assert "mystate" in obj.triggers
    assert mocked_re_compile.called
    assert obj.triggers["mystate"] == "compiled_trigger"


def test_add_state(prs, method):
    func = method
    func.__name__ = "mystate"
    prs.add_state(func)
    assert "mystate" in prs.states


def test_remove_state(prs_with_state):
    assert "mystate" in prs_with_state.states
    prs_with_state.remove_state("mystate")
    assert "mystate" not in prs_with_state.states


def test_add_state_with_trigger_as_string(prs, method):
    func = method
    func.__name__ = "mystate"
    func.trigger = "regex"
    prs.add_state(func)
    assert "mystate" in prs.states
    assert "mystate" in prs.triggers
    assert prs.triggers["mystate"] == re.compile("regex")


def test_add_state_with_trigger_as_regex(prs, method):
    func = method
    func.__name__ = "mystate"
    func.trigger = re.compile("regex")
    prs.add_state(func)
    assert "mystate" in prs.states
    assert "mystate" in prs.triggers
    assert prs.triggers["mystate"] == re.compile("regex")


def test_remove_state_with_trigger(params_with_state):
    params_with_state["mystate"].trigger = "regex"
    cls = type("Prsr", (ParserBase,), params_with_state)
    obj = cls()
    assert "mystate" in obj.states
    assert "mystate" in obj.triggers
    obj.remove_state("mystate")
    assert "mystate" not in obj.states
    assert "mystate" not in obj.triggers


def test_remove_invalid(prs):
    with pytest.raises(InvalidStateError):
        prs.remove_state("invalid")


def test_set_workhorse(prs, method):
    func = method
    prs.workhorse = func
    assert prs.workhorse is func


def test_set_workhorse_name(prs_with_state):
    prs_with_state.workhorse = "mystate"
    assert prs_with_state.workhorse is prs_with_state.mystate


def test_set_workhorse_invalid(prs):
    def func():
        prs.workhorse = "invalid"

    with pytest.raises(InvalidStateError):
        func()


def test_initial_matching(prs, method):
    prs.initial.side_effect = lambda line: super(type(prs), prs).initial(line)
    prs.states["mystate"] = method
    prs.triggers["mystate"] = re.compile("yes")
    out = prs.initial("yes, this line will match")
    prs.initial.assert_called()
    assert out == {}
    assert prs.workhorse is method


def test_initial_not_matching(prs, method):
    prs.initial.side_effect = lambda line: super(type(prs), prs).initial(line)
    prs.states["mystate"] = method
    prs.triggers["mystate"] = re.compile("yes")
    out = prs.initial("this line will not match")
    prs.initial.assert_called()
    assert out == {}
    assert prs.workhorse is prs.initial


def test_parse(prs):
    prs.initial.return_value = {"example": "data"}
    prs.parse.side_effect = lambda lines: super(type(prs), prs).parse(lines)
    out = prs.parse(["some line"])
    prs.initial.assert_called()
    assert out == {"example": "data"}


def test_parse_initial_resetting(prs, method):
    method.return_value = {}
    prs.workhorse = method
    prs.parse.side_effect = lambda lines: super(type(prs), prs).parse(lines)
    prs.parse(["some line"])
    method.assert_called()
    assert prs.workhorse is prs.initial


def test_parse_raises_not_iterable(prs, method):
    method.return_value = 1
    prs.workhorse = method
    prs.parse.side_effect = lambda lines: super(type(prs), prs).parse(lines)
    with pytest.raises(InvalidStateError):
        prs.parse(["some line"])
    assert prs.workhorse is prs.initial


def test_parse_raises_cant_convert_value(prs, method):
    method.return_value = "wrong sequence"
    prs.workhorse = method
    prs.parse.side_effect = lambda lines: super(type(prs), prs).parse(lines)
    with pytest.raises(InvalidStateError):
        prs.parse(["some line"])
    assert prs.workhorse is prs.initial
