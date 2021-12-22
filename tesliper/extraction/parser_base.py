"""This module contains a definition of Abstract Base Class for file parsers."""
import re
from abc import ABC, abstractmethod
from typing import Callable, Iterable, Union

from ..exceptions import InvalidStateError


class ParserBase(ABC):
    """Abstract Base Class for parsers implemented as finite state machines.

    This base class defines some methods to organize work parsers implemented as finite
    state machines: automates registration of methods and functions as parser's states,
    manages its execution, and registers derived class as parser used for certain type
    of files (which registry is used by :class:`.Soxhlet` object).

    The default parsing flow goes as follow:

    1. method :meth:`.parse` is called with file handle as argument;
    2. method :meth:`.initial` is set as a 'workhorse'
    3. 'workhorse' is called for consecutive lines in file handle
    4. :meth:`.initial` checks if any registered trigger matches current line
    5. :meth:`.workhorse` is changed to method associated with first matching trigger
    6. calling 'workhorse' on consecutive lines continues
    7. :meth:`.parse` returns dictionary with extracted values

    To make this possible, each method marked as state should return dictionary
    (or sequence convertible to dict) and handle changing 'workhorse' to next
    appropriate state. To mark a method as parser's state use ParserBase.state
    decorator in class definition or add a state directly to parser instance
    using 'add_state' method.

    When subclassing ParserBase, one should implement :meth:`.initial` and
    :meth:`.parse` methods. Those abstract methods implement basic functionality,
    described above. See methods' documentation for more details. If you wish not to use
    default ParserBase's protocol, simply override those methods to your liking.

    To register class derived from ParserBase for use by :class:`.Soxhlet` object,
    simply set :attr:`.purpose` class attribute to name, under which class should be
    registered. Setting it to one of names already defined (e.g. 'gaussian') will
    override the default parser used by :class:`.Soxhlet` object.

    Attributes
    ----------
    states: dict
        Dictionary of parser states, created automatically on object
        instantiation from object methods marked as states; method name is used
        as a key by default.
    triggers: dict
        Dictionary of triggers for parser states, created automatically on
        object instantiation from object methods marked as states with triggers;
        key for a particular state trigger should be the same as state's key in
        :attr:`.states` dictionary.
    parsers: dict
        Class attribute, which is a registry of classes subclassing ParserBase and
        defining :attr:`.purpose` class attribute.
    purpose: str
        Class attribute, that helps :class:`.Soxhlet` to identify ParserBase's subclass
        purpose.
    """

    # TODO: make states' triggers can be string, regex or callable

    parsers = {}
    purpose = ""

    def __init__(self):
        self.states = {}
        self.triggers = {}
        states = (
            (name, method)
            for name, method in (
                (n, getattr(self, n)) for n in dir(self) if n != "workhorse"
            )
            if hasattr(method, "is_state") and method.is_state
        )
        for name, method in states:
            self.add_state(method, name, getattr(method, "trigger", None))
        self.workhorse = self.initial

    def __init_subclass__(cls, **kwargs):
        if cls.purpose:
            ParserBase.parsers[cls.purpose] = cls
        if not hasattr(cls.initial, "is_state"):
            cls.initial.is_state = True

    @property
    def workhorse(self) -> Callable:
        """Callable marked as a current state used by parser object.

        Setter can take a callable or a string as a parameter. If name as
        string is passed to setter, it will be translated to a method
        registered as state. If no method was registered under this name,
        :class:`.InvalidStateError` will be raised. No other checks are performed
        when argument is callable."""
        return self._workhorse

    @workhorse.setter
    def workhorse(self, state: Union[Callable, str]):
        if callable(state):
            self._workhorse = state
        else:
            try:
                self._workhorse = self.states[state]
            except KeyError:
                raise InvalidStateError(
                    f"{state} is not callable nor registered state name"
                )

    def add_state(self, state: Callable, name: str = "", trigger: str = ""):
        """Register callable as parser's state.

        This method registers a callable under *name* key in :attr:`.states`
        dictionary. If *trigger* parameter is given, it is registered under the
        same key in :attr:`.triggers` dictionary.

        Parameters
        ----------
        state: Callable
            callable, that is to be registered as parser's state
        name: str, optional
            name under which the callable should be registered;
            defaults to callable.__name__
        trigger: str, optional
            string with regular expression, that will be compiled with re module

        Returns
        -------
        Callable
            callable object registered as state
        """
        if not name:
            name = state.__name__
        self.states[name] = state
        if trigger:
            self.triggers[name] = re.compile(trigger)
        elif hasattr(state, "trigger"):
            self.triggers[name] = re.compile(state.trigger)
        return state

    def remove_state(self, name: str):
        """Removes the state from parser's registered states.

        Parameters
        ----------
        name : str
            name of state, that should be unregistered

        Raises
        ------
        InvalidStateError
            if no callable was registered under the name 'name'
        """
        if name not in self.states:
            raise InvalidStateError(f"No state registered under name: {name}.")
        del self.states[name]
        if name in self.triggers:
            del self.triggers[name]

    @abstractmethod
    def initial(self, line: str) -> dict:
        """An initial parser state.

        A default implementation checks if any of defined triggers matches
        a line and sets an associated state as parser's workhorse, if it does.
        This is an abstract method and should be overridden in subclass.
        Its default implementation can be used, however, by calling
        ``super().initial(line)`` in subclass's method.

        Notes
        -----
        :meth:`.initial` method is always registered as parser's state.

        Parameters
        ----------
        line: str
            currently parsed line

        Returns
        -------
        dict
            empty dictionary"""
        for name, reg in self.triggers.items():
            match = reg.match(line)
            if match:
                self.workhorse = self.states[name]
                return {}
        return {}

    @abstractmethod
    def parse(self, lines: Iterable) -> dict:
        """Parses consecutive elements of iterable and returns data found
        as dictionary.

        Dictionary with extracted data is updated with workhorse's return value,
        so all states should return dictionary or compatible sequence.
        This is an abstract method and should be overridden in subclass.
        Its default implementation can be used, however, by calling
        ``data = super().parse(lines)`` in subclass's method.

        Notes
        -----
        After execution - either successful or interrupted by exception -
        :attr:`.workhorse` is set back to :meth:`.initial` method.

        Parameters
        ----------
        lines: Iterable
            iterable (i.e. file handle), that will be parsed, line by line

        Returns
        -------
        dict
            dictionary with data extracted by parser

        Raises
        ------
        InvalidStateError
            if dictionary can't be updated with state's return value"""
        data = {}
        try:
            for line in lines:
                output = self.workhorse(line)
                try:
                    data.update(output)
                except TypeError as error:
                    raise InvalidStateError(
                        f"State {self.workhorse} should return value "
                        f'convertible to a dictionary, not "{type(output)}".'
                    ) from error
                except ValueError as error:
                    raise InvalidStateError(
                        f"Value returned by state {self.workhorse} could not "
                        f"be converted to dictionary."
                    ) from error
        except Exception:
            raise
        finally:
            self.workhorse = self.initial
        return data

    @staticmethod
    def state(state=None, trigger=None):
        """Convenience decorator for registering a method as parser's state.
        It can be with or without 'trigger' parameter, like this:

        >>> @ParserBase.state
        ... def method(self, arg): pass

        or

        >>> @ParserBase.state(trigger='triggering regex')
        ... def method(self, arg): pass

        This function marks a method *state* as parser's state by defining ``is_state``
        attribute on said method and setting its values to ``True``. If *trigger* is
        given, it is stored in method's attribute *trigger*. During instantiation of
        :class:`.ParserBase`'s subclass, methods marked as states are registered under
        ``method.__name__`` key in its :attr:`.states` (and possibly :attr:`.triggers`)
        attribute. It is meaningless if used outside of :class:`.ParserBase`'s subclass
        definition.

        Parameters
        ----------
        state: Callable
            callable, that is to be registered as parser's state
        trigger: str, optional
            string with regular expression, that will be compiled with re module

        Returns
        -------
        Callable
            callable object registered as state if 'state' was given or
            decorator if only 'trigger' was given

        Raises
        ------
        TypeError
            if no arguments given
        InvalidStateError
            if *state* argument is not callable
        """
        if callable(state):
            state.is_state = True
            if trigger:
                state.trigger = trigger
            return state
        elif state is None and trigger is None:
            raise TypeError("At least one argument must be given.")
        elif trigger is None:
            raise InvalidStateError(
                f"'state' argument should be callable, not {type(state)}"
            )
        else:
            return lambda s, t=trigger: ParserBase.state(s, t)
