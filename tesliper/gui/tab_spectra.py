# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

from .components import CalculateSpectra, ScrollableFrame, SpectraView

# LOGGER
logger = lgg.getLogger(__name__)


# CLASSES
class Spectra(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky="nwse")
        tk.Grid.columnconfigure(self, 1, weight=1)
        tk.Grid.rowconfigure(self, 0, weight=1)

        spectra_view = SpectraView(self)
        spectra_view.grid(column=1, row=0, sticky="nwse")

        # Controls frame
        # ScrollableFrame.content is a ttk.Frame where actual controls go
        scrollable_frame = ScrollableFrame(parent=self)
        scrollable_frame.grid(column=0, row=0, sticky="news")
        self.controls = CalculateSpectra(
            scrollable_frame.content, tesliper=parent.tslr, view=spectra_view
        )
        self.controls.grid(column=0, row=0, sticky="nwse")
