import logging
import logging as lgg
import sys
import tkinter as tk
import tkinter.ttk as ttk
from typing import Type

# LOGGER
logger = lgg.getLogger(__name__)


def is_scrollable(widget):
    scrollable = False
    for scrollcommand in ["xscrollcommand", "yscrollcommand"]:
        try:
            _ = widget[scrollcommand]
        except tk.TclError:
            logger.debug(f"Widget {widget} does not offer '{scrollcommand}' config.")
        except TypeError:
            logger.debug(f"Widget {widget} not subscriptable with config keys.")
        else:
            scrollable = True
    try:
        disabled = str(widget["state"]) == tk.DISABLED
    except tk.TclError:
        # state irrelevant
        logger.debug(f"Widget {widget} does not offer 'state' config.")
        disabled = False
    return scrollable and not disabled


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

        self._scheduled = None
        self._hold_scrolling = False
        self._hold_delay = 500

        # Scroll with mouse wheel when cursor over canvas
        self.bind("<Enter>", self._bound_to_mousewheel)
        self.bind("<Leave>", self._unbound_to_mousewheel)

        # Enable delayed scrolling hold on other scrollable widgets
        self.bind_all("<Enter>", self._on_child_enter, "+")
        self.bind_all("<Leave>", self._on_child_leave, "+")

    def _on_child_enter(self, event):
        """If entered widget is ScrollableFrame's child and scrollable,
        schedule passing scroll control to this widget."""
        command = self._child_reverse_bindtags(event.widget)
        if not command:
            self._scheduled = self.after(self._hold_delay, self._on_child_stop, event)

    def _on_child_leave(self, event):
        """If widget left before scheduled hold was executed, cancel it and revert
        changes. Give scroll control to ScrollableFrame."""
        if self._scheduled is not None:
            self._child_reverse_bindtags(event.widget)
            self.after_cancel(self._scheduled)
            self._scheduled = None
        self._hold_scrolling = False

    def _on_child_stop(self, event):
        """Give scroll control to widget over the mouse cursor."""
        self._child_reverse_bindtags(event.widget)
        self._scheduled = None
        self._hold_scrolling = True

    def _child_reverse_bindtags(self, widget):
        """Reverse order of widget's bindtags to control if widget-specific or "all"
        bindings are executed first. Do it only if widget is a child of ScrollableFrame.
        """
        if not str(widget).startswith(str(self.canvas)):
            logger.debug(f"Bindtags reverse aborted: widget is not a child of {self}.")
            return "ok"  # or maybe "continue"?
        elif not is_scrollable(widget):
            logger.debug("Bindtags reverse aborted: non-scrollable or disabled widget.")
            return "ok"  # or maybe "continue"?
        reversed_ = widget.bindtags()[::-1]
        widget.bindtags(reversed_)
        logger.debug(f"New bindtags order: {reversed_}.")

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
        logger.debug(f"Event caught by {self}._on_mousewheel handler.")
        # prevent scrolling when content fully visible
        # or when scrolling is held by other scrollable widget
        if not self._hold_scrolling and not self.scrollbar.get() == (0.0, 1.0):
            delta = (
                event.delta
                if sys.platform == "darwin"
                else int(-1 * (event.delta / 120))
            )
            self.canvas.yview_scroll(delta, "units")
            # don't propagate event to other bindtags
            # to enable delayed hold on scrollable widgets
            return "break"

    def _on_content_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        # keep width of canvas as small as possible
        self.canvas.configure(width=event.width)
