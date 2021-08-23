# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

from .components import EnergiesView
from .components.controls import FilterEnergies

# LOGGER
logger = lgg.getLogger(__name__)


# CLASSES
class Conformers(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky="nwse")
        tk.Grid.rowconfigure(self, 0, weight=1)
        tk.Grid.columnconfigure(self, 1, weight=1)

        self.overview = ttk.LabelFrame(self, text="Conformers overview")
        self.overview.grid(column=1, row=0, sticky="nwse")
        tk.Grid.rowconfigure(self.overview, 0, weight=1)
        tk.Grid.columnconfigure(self.overview, 0, weight=1)
        self.conf_list = EnergiesView(self.overview, tesliper=self.parent.tslr)
        self.conf_list.frame.grid(column=0, row=0, sticky="nswe")

        # Controls frame
        controls = FilterEnergies(
            parent=self, tesliper=self.parent.tslr, view=self.conf_list
        )
        controls.grid(column=0, row=0, sticky="news")
