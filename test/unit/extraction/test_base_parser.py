from unittest import TestCase
from unittest.mock import Mock, NonCallableMock, patch
from tesliper.extraction import Parser
from tesliper.exceptions import InvalidStateError


class TestParser(TestCase):

    def setUp(self):
        cls = type(
            'Prsr', (Parser,),
            {'initial': Mock(spec=[]), 'parse': Mock(spec=[])}
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
        self.assertTrue(hasattr(func, 'is_state'))
        self.assertTrue(func.is_state)

    def test_state_decorator_with_trigger(self):
        func = Parser.state(self.method, 'mytrigger')
        self.assertTrue(hasattr(func, 'is_state'))
        self.assertTrue(func.is_state)
        self.assertTrue(hasattr(func, 'trigger'))
        self.assertTrue(func.trigger == 'mytrigger')

    def test_subclassed(self):
        self.assertIn('initial', self.prs.states)
        self.assertEqual(self.prs.initial, self.prs.workhorse)

    def test_subclassed_with_state(self):
        func = self.method
        func.is_state = True
        cls = type(
            'Prsr', (Parser,),
            {'initial': Mock(spec=[]), 'parse': Mock(spec=[]), 'mystate': func}
        )
        obj = cls()
        self.assertTrue(hasattr(obj, 'mystate'))
        self.assertIn('mystate', obj.states)
        self.assertEqual(obj.initial, obj.workhorse)

    def test_subclassed_with_trigger(self):
        class Subclass(Parser):
            def parse(self, lines): pass
            def initial(self, line): pass
            @Parser.state(trigger='trigger')
            def mystate(self): pass
        with patch('re.compile') as mocked_re_compile:
            mocked_re_compile.return_value = 'compiled_trigger'
            obj = Subclass()
        self.assertTrue(hasattr(obj, 'mystate'))
        self.assertTrue(hasattr(obj.mystate, 'is_state'))
        self.assertIn('mystate', obj.triggers)
        self.assertTrue(mocked_re_compile.called)
        self.assertEqual(obj.triggers['mystate'], 'compiled_trigger')

    def test_add_state(self):
        func = self.method
        func.__name__ = 'mystate'
        self.prs.add_state(func)
        self.assertIn('mystate', self.prs.states)

    def test_remove_state(self):
        func = self.method
        func.is_state = True
        cls = type(
            'Prsr', (Parser,),
            {'initial': Mock(spec=[]), 'parse': Mock(spec=[]), 'mystate': func}
        )
        obj = cls()
        obj.remove_state('mystate')
        self.assertNotIn('mystate', obj.states)

    def test_remove_invalid(self):
        self.assertRaises(InvalidStateError, self.prs.remove_state, 'invalid')

    def test_set_workhorse(self):
        func = self.method
        self.prs.workhorse = func
        self.assertIs(self.prs.workhorse, func)

    def test_set_workhorse_name(self):
        func = self.method
        func.is_state = True
        cls = type(
            'Prsr', (Parser,),
            {'initial': Mock(spec=[]), 'parse': Mock(spec=[]), 'mystate': func}
        )
        obj = cls()
        obj.workhorse = 'mystate'
        self.assertIs(obj.workhorse, func)

    def test_set_workhorse_invalid(self):
        def func():
            self.prs.workhorse = 'invalid'
        self.assertRaises(InvalidStateError, func)
