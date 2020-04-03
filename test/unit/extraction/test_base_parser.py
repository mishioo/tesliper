from unittest.mock import Mock, NonCallableMock, patch
import re
from tesliper.extraction import Parser
from tesliper.exceptions import InvalidStateError
import pytest


@pytest.fixture
def prs():
    cls = type("Prsr", (Parser,), {"initial": Mock(spec=[]), "parse": Mock(spec=[])})
    return cls()


@pytest.fixture
def method():
    return Mock(spec=[])


def test_instantiated_directly():
    with pytest.raises(TypeError):
        Parser()


def test_state_no_arguments():
    with pytest.raises(TypeError):
        Parser.state()


def test_state_not_callable():
    func = NonCallableMock()
    with pytest.raises(InvalidStateError):
        Parser.state(func)


def test_state_decorator(method):
    func = Parser.state(method)
    assert hasattr(func, "is_state")
    assert func.is_state


def test_state_decorator_with_trigger(method):
    func = Parser.state(method, "mytrigger")
    assert hasattr(func, "is_state")
    assert func.is_state
    assert hasattr(func, "trigger")
    assert func.trigger == "mytrigger"


def test_subclassed(prs):
    assert "initial" in prs.states
    assert prs.initial == prs.workhorse


def test_subclassed_with_state(method):
    func = method
    func.is_state = True
    cls = type(
        "Prsr",
        (Parser,),
        {"initial": Mock(spec=[]), "parse": Mock(spec=[]), "mystate": func},
    )
    obj = cls()
    assert hasattr(obj, "mystate")
    assert "mystate" in obj.states
    assert obj.initial == obj.workhorse


def test_subclassed_with_trigger():
    class Subclass(Parser):
        def parse(self, lines):
            pass

        def initial(self, line):
            pass

        @Parser.state(trigger="trigger")
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


def test_remove_state(method):
    func = method
    func.is_state = True
    cls = type(
        "Prsr",
        (Parser,),
        {"initial": Mock(spec=[]), "parse": Mock(spec=[]), "mystate": func},
    )
    obj = cls()
    assert "mystate" in obj.states
    obj.remove_state("mystate")
    assert "mystate" not in obj.states


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


def test_remove_state_with_trigger(method):
    func = method
    func.is_state = True
    func.trigger = "regex"
    cls = type(
        "Prsr",
        (Parser,),
        {"initial": Mock(spec=[]), "parse": Mock(spec=[]), "mystate": func},
    )
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


def test_set_workhorse_name(method):
    func = method
    func.is_state = True
    cls = type(
        "Prsr",
        (Parser,),
        {"initial": Mock(spec=[]), "parse": Mock(spec=[]), "mystate": func},
    )
    obj = cls()
    obj.workhorse = "mystate"
    assert obj.workhorse is func


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
