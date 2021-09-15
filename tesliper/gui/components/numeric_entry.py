import logging
import operator
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
        decimal_digits=4,
        keep_trailing_zeros=False,
        min_value=float("-inf"),
        max_value=float("inf"),
        include_min_value=True,
        include_max_value=True,
        **kwargs,
    ):
        self.scroll_factor = scroll_factor
        self.scroll_rate = scroll_rate
        self.scroll_modifier = scroll_modifier
        self.min_value = min_value
        self.max_value = max_value
        self.include_min_value = include_min_value
        self.include_max_value = include_max_value
        kwargs["textvariable"] = kwargs.get("textvariable", None) or tk.StringVar()
        kwargs["validate"] = kwargs.get("validate", None) or "all"
        if "validatecommand" not in kwargs:
            validatecommand = (
                parent.register(self._validate),
                "%S",
                "%P",
                "%s",
                "%V",
                "%d",
            )
            kwargs["validatecommand"] = validatecommand
        if "invalidcommand" not in kwargs:
            invalidcommand = (
                parent.register(self._on_invalid),
                "%S",
                "%P",
                "%s",
                "%V",
                "%d",
            )
            kwargs["invalidcommand"] = invalidcommand
        self.var = kwargs["textvariable"]

        self._decimal_digits = decimal_digits
        self._keep_trailing_zeros = keep_trailing_zeros
        self._previous = ""  # used to recover after invalid "select all + paste"

        super().__init__(parent, **kwargs)
        self.bind("<MouseWheel>", self._on_mousewheel)
        # For Linux
        self.bind("<Button-4>", self._on_mousewheel)
        self.bind("<Button-5>", self._on_mousewheel)

    def is_in_bounds(self, value):
        upper_op = operator.le if self.include_max_value else operator.lt
        lower_op = operator.ge if self.include_min_value else operator.gt
        return upper_op(value, self.max_value) and lower_op(value, self.min_value)

    @property
    def decimal_digits(self):
        return self._decimal_digits

    @decimal_digits.setter
    def decimal_digits(self, value):
        self._decimal_digits = value
        self.update()

    @property
    def keep_trailing_zeros(self):
        return self._keep_trailing_zeros

    @keep_trailing_zeros.setter
    def keep_trailing_zeros(self, value):
        self._keep_trailing_zeros = value
        self.update()

    def update(self):
        try:
            self.var.set(self.format())
        except ValueError:
            # var cant be converted to float
            logger.warning("Cannot update, value can't be converted to float")

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

    def format(self, value=None):
        formatter = f"{{:.{self.decimal_digits}f}}"
        value = value if value is not None else self.var.get()
        value = formatter.format(float(value))
        if not self.keep_trailing_zeros:
            value = value.rstrip("0")  # discard insignificant trailing zeros
        if value.endswith("."):
            value += "0"  # but keep at least one decimal digit
        return value

    def _on_mousewheel(self, event):
        if event is not None:
            logger.debug(f"Event caught by {self}._on_mousewheel handler.")
        try:
            _ = float(self.var.get())
        except ValueError:
            convertible = False
        else:
            convertible = True
        if str(self["state"]) == "disabled" or not convertible:
            return  # ignore event if widget is disabled or edition unfinished
        delta = event.delta if sys.platform == "darwin" else int(event.delta / 120)
        current = float(self.var.get())
        updated = self.scroll_modifier(current, delta)
        updated = self.format(updated)
        if self.is_in_bounds(float(updated)):
            self.var.set(updated)

    @property
    def allowed_chars(self):
        allowed = "0123456789.,"
        if self.min_value < 0:
            allowed += "-"
        return allowed

    def _validate(self, change, after, before, reason, action_code):
        """Enables only values that cen be interpreted as floats."""
        logger.debug(
            f"Input in {self} validation: change={change}, after={after}, "
            f"before={before}, reason={reason}."
        )
        if reason == "focusin":
            self._previous = before
        if action_code and any(c not in self.allowed_chars for c in change):
            return False
        if (
            any(c in ".," for c in change)
            and any(c in ".," for c in before)
            and any(c in ".," for c in after)
        ):
            return False  # do not allow double decimal separator
        if "-" in change and "-" in before and action_code:
            return False  # do not allow double sign
        if "-" in after and not after.startswith("-"):
            return False  # only allow sign in the beginning
        if after in ".,-" or after.endswith((".", ",")):
            # includes also unfinished negative float
            return reason != "focusout"  # consider it invalid only when typing is over
        if not after and reason == "focusout":
            return False  # do not allow no value
        if reason == "focusout":
            try:
                converted = float(after)
            except ValueError:
                return False
            if not self.is_in_bounds(converted):
                return False
            self.var.set(self.format(after))  # format only on valid "focusout"
        return True

    def _on_invalid(self, change, after, before, reason, action_code):
        """Change value to form accepted by float constructor."""
        logger.debug(
            f"Input in {self} invalid: change={change}, after={after}, "
            f"before={before}, reason={reason}."
        )
        if (
            "-" in change
            and not before.startswith("-")
            and action_code  # not deletion
            and self.min_value < 0
        ):
            after = "-" + before
        elif change == "-" and before.startswith("-") and action_code:
            after = before[1:]
        if "," in after:
            # consider both, comma and dot, a decimal separator
            after = after.replace(",", ".")
        if after.endswith("."):
            after = after + "0"
        if after == "-" and self.min_value < 0:
            after = after + "0"
        try:
            converted = float(after)
            if not self.is_in_bounds(converted) and reason == "focusout":
                raise ValueError  # treat out-of-bounds value as invalid on "focusout"
        except ValueError:
            # revert if invalid float
            after = self._previous if reason == "focusout" else before
        else:
            # format only on "focusout"
            after = self.format(after) if reason == "focusout" else after
        self.var.set(after)
