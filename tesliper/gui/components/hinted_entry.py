import logging
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger(__name__)


class HintedEntry(ttk.Entry):
    """Entry that displays a hint and changes style when empty."""

    def __init__(
        self, parent, hint="Enter text here", hinted_style="Hinted.TEntry", **kwargs
    ):
        ttk.Style().configure("Hinted.TEntry", foreground="grey")
        self._hint = hint
        self.variable = kwargs["textvariable"] = kwargs.get(
            "textvariable", tk.StringVar()
        )
        self._style = kwargs.get("style", "TEntry")
        self._hinted_style = hinted_style
        kwargs["style"] = self._style if self.variable.get() else self._hinted_style
        super().__init__(parent, **kwargs)
        if not self.variable.get():
            self.variable.set(hint)
        self.bind("<FocusIn>", self.entry_focus_in)
        self.bind("<FocusOut>", self.entry_focus_out)

    def entry_focus_in(self, _event=None):
        normal_state = str(self.cget("state")) == "normal"
        if self.is_hinted() and normal_state:
            self.variable.set("")
            super().configure(style=self._style)

    def entry_focus_out(self, _event=None):
        if not self.variable.get():
            self.variable.set(self._hint)
            super().configure(style=self._hinted_style)

    def get(self):
        return "" if self.is_empty() else self.variable.get()

    def set(self, value):
        is_normal = value or self.focus_get() is self
        self.variable.set(value if is_normal else self._hint)
        logger.debug(f" Entry is {'normal' if is_normal else 'hinted'}.")
        super().configure(style=self._style if is_normal else self._hinted_style)

    def is_empty(self):
        return not self.variable.get() or self.is_hinted()

    def is_hinted(self):
        return self.cget("style") == self._hinted_style

    def configure(self, cnf=None, **kwargs):
        is_hinted = self.is_hinted()
        hint = kwargs.pop("hint", None)
        if hint is not None:
            self._hint = hint
            if is_hinted:
                self.variable.set(hint)
        style = kwargs.pop("style", None)
        if style is not None:
            self._style = style
        hinted_style = kwargs.pop("hinted_style", None)
        if hinted_style is not None:
            self._hinted_style = hinted_style
        if style or hinted_style:
            kwargs["style"] = self._hinted_style if is_hinted else self._style
        super().configure(cnf, **kwargs)
