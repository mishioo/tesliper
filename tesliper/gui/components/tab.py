import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

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
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvas = tk.Canvas(self)
        self.scrollbar = AutoScrollbar(self, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.content = ttk.Frame(self.canvas)
        self.content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        itemid = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        # resize content frame along with canvas
        self.canvas.bind(
            "<Configure>", lambda e: self.canvas.itemconfig(itemid, width=e.width)
        )
        self.canvas.grid(row=0, column=0, sticky="nwse")
        self.scrollbar.grid(row=0, column=1, sticky="nwse")
        # squeeze scrollbar inside if fixed width
        tk.Grid.columnconfigure(self, 0, weight=1)


class Tab(ttk.Frame):
    """Base layout for ttk.Notebook tab. It has two panels:
    left with controls, which should be a ScrollableFrame
    and right with view area, which should be a LabelFrame.
    """
    def __init__(self, parent, view: ttk.LabelFrame, controls: ScrollableFrame):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky="nwse")
        tk.Grid.rowconfigure(self, 0, weight=1)
        # only view resizes with window
        tk.Grid.columnconfigure(self, 1, weight=1)

        self.controls = controls
        self.controls.grid(row=0, column=0, sticky="nwse")
        
        self.view = view
        self.view.grid(row=0, column=1, sticky="nwse")
