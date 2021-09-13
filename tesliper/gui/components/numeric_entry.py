import logging
import sys
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger(__name__)


class NumericEntry(ttk.Entry):
    """Entry that holds a numeric value. Implements validation and changing value
    on mouse wheel event.

    Parameters
    ----------
    scroll_rate : float
        Value to add/substract to/from current value on scroll wheel event.
        Must not be specified if scroll_factor is given.
    scroll_factor : float
        Value by which to multiply/divide current value on scroll wheel event.
        Must not be specified if scroll_rate is given.
    scroll_modifier : callable[float, int]
        Custom function calculating new value after mouse wheel event.
        Must accept current value and standardized scroll delta value as parameters.

    Raises
    ------
    TypeError
        If both, scroll_rate and scroll_factor are specified.
    """

    # TODO: add formatting of float value stored in StringVar
    def __init__(
        self,
        parent,
        scroll_rate=None,
        scroll_factor=None,
        scroll_modifier=None,
        **kwargs,
    ):
        self.scroll_factor = scroll_factor
        self.scroll_rate = scroll_rate
        self.scroll_modifier = scroll_modifier
        kwargs["textvariable"] = kwargs.get("textvariable", None) or tk.StringVar()
        kwargs["validate"] = kwargs.get("validate", None) or "all"
        if "validatecommand" not in kwargs:
            validatecommand = parent.register(self._validate), "%S", "%P", "%s", "%V"
            kwargs["validatecommand"] = validatecommand
        if "invalidcommand" not in kwargs:
            invalidcommand = parent.register(self._on_invalid), "%S", "%P", "%s", "%V"
            kwargs["invalidcommand"] = invalidcommand
        self.var = kwargs["textvariable"]

        super().__init__(parent, **kwargs)
        self.bind("<MouseWheel>", self._on_mousewheel)
        # For Linux
        self.bind("<Button-4>", self._on_mousewheel)
        self.bind("<Button-5>", self._on_mousewheel)

    @property
    def scroll_factor(self):
        return self._scroll_factor

    @scroll_factor.setter
    def scroll_factor(self, value):
        if value is not None and getattr(self, "scroll_rate", None) is not None:
            raise TypeError("Only one, scroll_rate or scroll_factor may be specified.")
        self._scroll_factor = value

    @property
    def scroll_rate(self):
        return self._scroll_rate

    @scroll_rate.setter
    def scroll_rate(self, value):
        if value is not None and getattr(self, "scroll_factor", None) is not None:
            raise TypeError("Only one, scroll_rate or scroll_factor may be specified.")
        self._scroll_rate = value

    @property
    def scroll_modifier(self):
        if self._scroll_modifier is not None:
            return self._scroll_modifier
        elif getattr(self, "scroll_rate") is not None:
            return lambda v, d, r=self.scroll_rate: v + r * d
        elif getattr(self, "scroll_factor") is not None:
            return lambda v, d, f=self.scroll_factor: v * f ** d
        else:
            return lambda v, d: v

    @scroll_modifier.setter
    def scroll_modifier(self, value):
        self._scroll_modifier = value

    def _on_mousewheel(self, event):
        if event is not None:
            logger.debug(f"Event caught by {self}._on_mousewheel handler.")
        if str(self["state"]) == "disabled":
            return  # ignore event if widget is disabled
        delta = event.delta if sys.platform == "darwin" else int(event.delta / 120)
        current = float(self.var.get())
        updated = self.scroll_modifier(current, delta)
        self.var.set(updated)

    def _validate(self, change, after, before, reason):
        """Enables only values that cen be interpreted as floats."""
        logger.debug(
            f"Input in {self} validation: change={change}, after={after}, "
            f"before={before}, reason={reason}."
        )
        focus_out = reason == "focusout"
        if any(c not in "0123456789.,+-" for c in change):
            return False
        if any(c in ".," for c in change) and any(c in ".," for c in before):
            return False  # do not allow double decimal separator
        if any(c in "+-" for c in change) and any(c in "+-" for c in before):
            return False  # do not allow double sign
        if any(c in "+-" for c in after) and not after.startswith(("+", "-")):
            return False  # only allow sign in the beginning
        if after in ".,+-" or after.endswith((".", ",")):
            # includes also unfinished negative or explicitly positive float
            return not focus_out  # consider it invalid only when typing is over
        return True

    def _on_invalid(self, change, after, before, reason):
        """Change value to form accepted by float constructor."""
        logger.debug(
            f"Input in {self} invalid: change={change}, after={after}, "
            f"before={before}, reason={reason}."
        )
        if change == "-" and not before.startswith("-"):
            after = "-" + before
        elif change == "+" and before.startswith("-"):
            after = before[1:]
        if "," in after:
            # consider both, comma and dot, a decimal separator
            after = after.replace(",", ".")
        if after.startswith((".", "-.")):
            after = after.replace(".", "0.")
        if after.endswith((".", "+", "-")):
            after = after + "0"
        if after.startswith("+"):
            after = after[1:]
        try:
            if after:
                float(after)
        except ValueError:
            return self.var.set(before)  # revert if invalid float
        self.var.set(after)
