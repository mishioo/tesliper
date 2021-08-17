# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

from .components import ScrollableFrame
from .components.controls import FilterEnergy, FilterRMSD
from .components.helpers import WgtStateChanger

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
        self.conf_list = None  # obj is created in main.TesliperApp.new_session
        self.bind("<FocusIn>", self.refresh)

        # Controls frame
        # ScrollableFrame.content is a ttk.Frame where actual controls go
        controls = ScrollableFrame(parent=self)
        controls.grid(column=0, row=0, sticky="news")

        # control frame
        control_frame = ttk.LabelFrame(controls.content, text="Overview control")
        control_frame.grid(column=0, row=0, columnspan=2, sticky="nwe")
        tk.Grid.columnconfigure(control_frame, 0, weight=1)

        b_select = ttk.Button(control_frame, text="Select all", command=self.select_all)
        b_select.grid(column=0, row=0, sticky="nwe")
        b_disselect = ttk.Button(
            control_frame, text="Disselect all", command=self.disselect_all
        )
        b_disselect.grid(column=0, row=1, sticky="nwe")
        ttk.Label(controls.content, text="Show:").grid(column=0, row=1, sticky="new")
        self.show_var = tk.StringVar()
        show_values = (
            "Energy /Hartree",
            "Delta /(kcal/conf)",
            "Min. Boltzmann factor",
            "Population /%",
        )
        show_id = ("values", "deltas", "min_factors", "populations")
        self.show_ref = {k: v for k, v in zip(show_values, show_id)}
        self.show_combo = ttk.Combobox(
            controls.content,
            textvariable=self.show_var,
            values=show_values,
            state="readonly",  # , width=21
        )
        self.show_combo.bind("<<ComboboxSelected>>", self.refresh)
        self.show_combo.grid(column=1, row=1, sticky="nwe")
        self.show_combo.set("Energy /Hartree")

        # filter by energy value
        filter_frame = ttk.LabelFrame(controls.content, text="Energies range")
        filter_frame.grid(column=0, row=2, columnspan=2, sticky="nwe")
        filter_frame.columnconfigure(0, weight=1)
        self.filter = FilterEnergy(filter_frame, tesliper=self.parent.tslr, tab=self)
        self.filter.grid(row=0, column=0, sticky="news")

        # RMSD sieve
        rmsd_frame = ttk.LabelFrame(controls.content, text="RMSD sieve")
        rmsd_frame.grid(column=0, row=4, columnspan=2, sticky="nwe")
        rmsd_frame.columnconfigure(0, weight=1)
        self.rmsd = FilterRMSD(rmsd_frame, tesliper=self.parent.tslr, tab=self)
        self.rmsd.grid(row=0, column=0, sticky="news")

        self.established = False

        WgtStateChanger.energies.extend(
            [
                b_select,
                b_disselect,
                self.show_combo,
            ]
        )

    def establish(self):
        self.show_combo.set("Energy /Hartree")
        self.established = True

    @property
    def showing(self):
        return self.show_ref[self.show_var.get()]

    def discard_lacking_energies(self):
        # TODO: is it necessary?
        if not self.parent.main_tab.kept_vars["incompl"].get():
            logger.info("Any conformers without energy data will be discarded.")
            boxes = self.conf_list.trees["main"].boxes
            for num, conf in enumerate(self.parent.tslr.conformers.values()):
                if "gib" not in conf:
                    boxes[str(num)].var.set(False)

    def refresh(self, event=None):
        self.conf_list.refresh()
        # TODO: figure out if there is a better way to schedule energies_choice updates
        #       maybe set up custom events and bindings?
        self.filter.energies_choice.update_values()
        self.rmsd.energies_choice.update_values()
        self.filter.set_upper_and_lower()

    def select_all(self):
        for box in self.conf_list.boxes.values():
            box.var.set(True)
        self.parent.main_tab.discard_not_kept()
        self.discard_lacking_energies()
        self.refresh()

    def disselect_all(self):
        for box in self.conf_list.boxes.values():
            box.var.set(False)
        self.refresh()
