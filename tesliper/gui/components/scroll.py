import logging
import logging as lgg
import sys
import tkinter as tk
import tkinter.ttk as ttk
from typing import Type

# LOGGER
logger = lgg.getLogger(__name__)


# CLASSES
class AutoScrollbar(ttk.Scrollbar):
    """A scrollbar that hides automatically when entire canvas is visible.
    Must be placed with `.grid()`.
    """

    def set(self, low, high):
        if float(low) <= 0.0 and float(high) >= 1.0:
            self.grid_remove()
        else:
            self.grid()  # restores widget previously removed from grid
        super().set(low, high)

    def pack(self, *_args, **_kwargs):
        raise tk.TclError("cannot use pack with this widget")

    def place(self, *_args, **_kwargs):
        raise tk.TclError("cannot use place with this widget")


class ScrollableFrame(ttk.Frame):
    """A frame, that allows you to scroll content vertically.
    Shows scrollbar only when it is necessary."""

    def __init__(self, parent, content_cls=ttk.Frame):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = AutoScrollbar(self, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.content = content_cls(self.canvas)
        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.grid(row=0, column=0, sticky="nwse")
        self.scrollbar.grid(row=0, column=1, sticky="nws")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas.columnconfigure(0, weight=1)
        self.canvas.rowconfigure(0, weight=1)

        # Scroll with mouse wheel when cursor over canvas
        self.bind("<Enter>", self._bound_to_mousewheel)
        self.bind("<Leave>", self._unbound_to_mousewheel)

    def _bound_to_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # For Linux
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbound_to_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        scrollable = False
        for scrollcommand in ["xscrollcommand", "yscrollcommand"]:
            try:
                _ = event.widget[scrollcommand]
            except tk.TclError:
                pass
            else:
                scrollable = True
        try:
            disabled = str(event.widget["state"]) == tk.DISABLED
        except tk.TclError:
            # state irrelevant
            disabled = False
        stop_on_widget = scrollable and not disabled
        if not stop_on_widget and not self.scrollbar.get() == (0.0, 1.0):
            # prevent scrolling when content fully visible
            # or when widget generating the event is scrollable itself
            # and this widget is not disabled
            delta = (
                event.delta
                if sys.platform == "darwin"
                else int(-1 * (event.delta / 120))
            )
            self.canvas.yview_scroll(delta, "units")

    def _on_content_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        # keep width of canvas as small as possible
        self.canvas.configure(width=event.width)
