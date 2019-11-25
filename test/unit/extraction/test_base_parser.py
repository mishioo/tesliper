from unittest import TestCase
from unittest.mock import Mock, NonCallableMock, patch
import re
from tesliper.extraction import Parser
from tesliper.exceptions import InvalidStateError


class TestParser(TestCase):
    def setUp(self):
        cls = type(
            "Prsr", (Parser,), {"initial": Mock(spec=[]), "parse": Mock(spec=[])}
        )
        self.prs = cls()
        self.method = Mock(spec=[])

    def test_instantiated_directly(self):
        self.assertRaises(TypeError, Parser)

    def test_state_no_arguments(self):
        self.assertRaises(TypeError, Parser.state)

    def test_state_not_callable(self):
        func = NonCallableMock()
        self.assertRaises(InvalidStateError, Parser.state, func)

    def test_state_decorator(self):
        func = Parser.state(self.method)
        self.assertTrue(hasattr(func, "is_state"))
        self.assertTrue(func.is_state)

    def test_state_decorator_with_trigger(self):
        func = Parser.state(self.method, "mytrigger")
        self.assertTrue(hasattr(func, "is_state"))
        self.assertTrue(func.is_state)
        self.assertTrue(hasattr(func, "trigger"))
        self.assertTrue(func.trigger == "mytrigger")

    def test_subclassed(self):
        self.assertIn("initial", self.prs.states)
        self.assertEqual(self.prs.initial, self.prs.workhorse)

    def test_subclassed_with_state(self):
        func = self.method
        func.is_state = True
        cls = type(
            "Prsr",
            (Parser,),
            {"initial": Mock(spec=[]), "parse": Mock(spec=[]), "mystate": func},
        )
        obj = cls()
        self.assertTrue(hasattr(obj, "mystate"))
        self.assertIn("mystate", obj.states)
        self.assertEqual(obj.initial, obj.workhorse)

    def test_subclassed_with_trigger(self):
        class Subclass(Parser):
            def parse(self, lines):
                pass

            def initial(self, line):
                pass

            @Parser.state(trigger="trigger")
            def mystate(self):
                pass

        with patch("re.compile") as mocked_re_compile:
            mocked_re_compile.return_value = "compiled_trigger"
            obj = Subclass()
        self.assertTrue(hasattr(obj, "mystate"))
        self.assertTrue(hasattr(obj.mystate, "is_state"))
        self.assertIn("mystate", obj.triggers)
        self.assertTrue(mocked_re_compile.called)
        self.assertEqual(obj.triggers["mystate"], "compiled_trigger")

    def test_add_state(self):
        func = self.method
        func.__name__ = "mystate"
        self.prs.add_state(func)
        self.assertIn("mystate", self.prs.states)

    def test_remove_state(self):
        func = self.method
        func.is_state = True
        cls = type(
            "Prsr",
            (Parser,),
            {"initial": Mock(spec=[]), "parse": Mock(spec=[]), "mystate": func},
        )
        obj = cls()
        self.assertIn("mystate", obj.states)
        obj.remove_state("mystate")
        self.assertNotIn("mystate", obj.states)

    def test_add_state_with_trigger_as_string(self):
        func = self.method
        func.__name__ = "mystate"
        func.trigger = "regex"
        self.prs.add_state(func)
        self.assertIn("mystate", self.prs.states)
        self.assertIn("mystate", self.prs.triggers)
        self.assertEqual(self.prs.triggers["mystate"], re.compile("regex"))

    def test_add_state_with_trigger_as_regex(self):
        func = self.method
        func.__name__ = "mystate"
        func.trigger = re.compile("regex")
        self.prs.add_state(func)
        self.assertIn("mystate", self.prs.states)
        self.assertIn("mystate", self.prs.triggers)
        self.assertEqual(self.prs.triggers["mystate"], re.compile("regex"))

    def test_remove_state_with_trigger(self):
        func = self.method
        func.is_state = True
        func.trigger = "regex"
        cls = type(
            "Prsr",
            (Parser,),
            {"initial": Mock(spec=[]), "parse": Mock(spec=[]), "mystate": func},
        )
        obj = cls()
        self.assertIn("mystate", obj.states)
        self.assertIn("mystate", obj.triggers)
        obj.remove_state("mystate")
        self.assertNotIn("mystate", obj.states)
        self.assertNotIn("mystate", obj.triggers)

    def test_remove_invalid(self):
        self.assertRaises(InvalidStateError, self.prs.remove_state, "invalid")

    def test_set_workhorse(self):
        func = self.method
        self.prs.workhorse = func
        self.assertIs(self.prs.workhorse, func)

    def test_set_workhorse_name(self):
        func = self.method
        func.is_state = True
        cls = type(
            "Prsr",
            (Parser,),
            {"initial": Mock(spec=[]), "parse": Mock(spec=[]), "mystate": func},
        )
        obj = cls()
        obj.workhorse = "mystate"
        self.assertIs(obj.workhorse, func)

    def test_set_workhorse_invalid(self):
        def func():
            self.prs.workhorse = "invalid"

        self.assertRaises(InvalidStateError, func)

    def test_initial_matching(self):
        self.prs.initial.side_effect = lambda line: super(
            type(self.prs), self.prs
        ).initial(line)
        self.prs.states["mystate"] = self.method
        self.prs.triggers["mystate"] = re.compile("yes")
        out = self.prs.initial("yes, this line will match")
        self.prs.initial.assert_called()
        self.assertEqual(out, {})
        self.assertIs(self.prs.workhorse, self.method)

    def test_initial_not_matching(self):
        self.prs.initial.side_effect = lambda line: super(
            type(self.prs), self.prs
        ).initial(line)
        self.prs.states["mystate"] = self.method
        self.prs.triggers["mystate"] = re.compile("yes")
        out = self.prs.initial("this line will not match")
        self.prs.initial.assert_called()
        self.assertDictEqual(out, {})
        self.assertIs(self.prs.workhorse, self.prs.initial)

    def test_parse(self):
        self.prs.initial.return_value = {"example": "data"}
        self.prs.parse.side_effect = lambda lines: super(
            type(self.prs), self.prs
        ).parse(lines)
        out = self.prs.parse(["some line"])
        self.prs.initial.assert_called()
        self.assertDictEqual(out, {"example": "data"})

    def test_parse_initial_resetting(self):
        self.method.return_value = {}
        self.prs.workhorse = self.method
        self.prs.parse.side_effect = lambda lines: super(
            type(self.prs), self.prs
        ).parse(lines)
        self.prs.parse(["some line"])
        self.method.assert_called()
        self.assertIs(self.prs.workhorse, self.prs.initial)

    def test_parse_raises_not_iterable(self):
        self.method.return_value = 1
        self.prs.workhorse = self.method
        self.prs.parse.side_effect = lambda lines: super(
            type(self.prs), self.prs
        ).parse(lines)
        self.assertRaises(InvalidStateError, self.prs.parse, ["some line"])
        self.assertIs(self.prs.workhorse, self.prs.initial)

    def test_parse_raises_cant_convert_value(self):
        self.method.return_value = "wrong sequence"
        self.prs.workhorse = self.method
        self.prs.parse.side_effect = lambda lines: super(
            type(self.prs), self.prs
        ).parse(lines)
        self.assertRaises(InvalidStateError, self.prs.parse, ["some line"])
        self.assertIs(self.prs.workhorse, self.prs.initial)
