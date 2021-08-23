# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

from .components import BarsPopup, ConformersOverview, ScrollableFrame, ThreadedMethod
from .components.controls import ExportData, ExtractData, SelectConformers

# LOGGER
logger = lgg.getLogger(__name__)


OVERVIEW_GENRES = "dip rot vosc vrot losc lrot raman1 roa1 scf zpe ent ten gib".split()


# CLASSES
class Loader(ttk.Frame):
    def __init__(self, parent):
        """
        TO DO
        -----
        don't allow energy extraction if already extracted
        """
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky="nwse")
        tk.Grid.columnconfigure(self, 1, weight=1)
        tk.Grid.rowconfigure(self, 0, weight=1)
        self.bind("<FocusIn>", self.on_focus_in)

        # Conformers Overview
        self.label_overview = ttk.LabelFrame(self, text="Conformers Overview")
        self.label_overview.grid(column=1, row=0, sticky="nwse")
        self.overview = ConformersOverview(
            self.label_overview, tesliper=self.parent.tslr
        )
        self.overview.frame.grid(column=0, row=0, sticky="nswe")
        tk.Grid.rowconfigure(self.label_overview, 0, weight=1)
        tk.Grid.columnconfigure(self.label_overview, 0, weight=1)

        # Controls frame
        # ScrollableFrame.content is a ttk.Frame where actual controls go
        controls = ScrollableFrame(parent=self)
        controls.grid(column=0, row=0, sticky="news")

        self.extract = ExtractData(
            controls.content, tesliper=self.parent.tslr, tab=self
        )
        self.extract.grid(column=0, row=0, sticky="news")
        self.export = ExportData(controls.content, tesliper=self.parent.tslr)
        self.export.grid(column=0, row=1, sticky="news")
        self.select = SelectConformers(
            controls.content, tesliper=self.parent.tslr, tab=self
        )
        self.select.grid(column=0, row=2, sticky="news")

    def on_focus_in(self, _event=None):
        self.select.update_overview_values()

    @ThreadedMethod(progbar_msg="Calculating populations...")
    def calc_popul(self):
        logger.debug("Calculating populations...")
        self.parent.tslr.calculate_populations()

    @ThreadedMethod(progbar_msg="Calculating spectra...")
    def calc_spectra(self):
        self.parent.tslr.calculate_spectra()

    @ThreadedMethod(progbar_msg="Averaging spectra...")
    def calc_average(self):
        self.parent.tslr.average_spectra()

    def get_wanted_bars(self):
        # TODO: check if needed, delete if it's not
        popup = BarsPopup(self, width="250", height="190")
        del popup
