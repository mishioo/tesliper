# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk
from functools import reduce

from . import components as guicom

# LOGGER
from .components import ScrollableFrame
from .components.helpers import float_entry_out_validation, get_float_entry_validator

logger = lgg.getLogger(__name__)


# CLASSES
class EnergiesChoice(ttk.Combobox):
    """Combobox that enables choice of type of energy."""

    def __init__(self, parent, **kwargs):
        self.var = tk.StringVar()
        values = "Thermal Enthalpy Gibbs SCF Zero-Point".split(" ")
        genres = "ten ent gib scf zpe".split(" ")
        self._genres_ref = {k: v for k, v in zip(values, genres)}
        kwargs["textvariable"] = self.var
        kwargs["values"] = values
        kwargs["state"] = "readonly"
        super().__init__(parent, **kwargs)

    def get_genre(self):
        """Convenience method for getting genre of the energy type chosen."""
        return self._genres_ref[self.var.get()]


class FilterRMSD(ttk.Frame):
    # TODO: for now should be available only for
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        float_entry_validator = get_float_entry_validator(self)

        ttk.Label(self, text="Window size").grid(column=0, row=0)
        ttk.Label(self, text="Threshold").grid(column=0, row=1)
        # TODO: add default choices
        self.window_size = tk.StringVar()
        self.threshold = tk.StringVar()
        window_size = ttk.Entry(
            self,
            textvariable=self.window_size,
            width=15,
            validate="key",
            validatecommand=float_entry_validator,
        )
        window_size.grid(column=1, row=0, sticky="ne")
        window_size.bind(
            "<FocusOut>",
            lambda e, var=self.window_size: float_entry_out_validation(var),
        )
        threshold = ttk.Entry(
            self,
            textvariable=self.threshold,
            width=15,
            validate="key",
            validatecommand=float_entry_validator,
        )
        threshold.grid(column=1, row=1, sticky="ne")
        threshold.bind(
            "<FocusOut>",
            lambda e, var=self.threshold: float_entry_out_validation(var),
        )
        self.ignore_hydrogens = tk.BooleanVar(value=True)
        ignore_hydrogens = ttk.Checkbutton(
            self, text="Ignore H", variable=self.ignore_hydrogens
        )
        ignore_hydrogens.grid(column=1, row=2, sticky="ne")

        # TODO: add "Energy type" label
        self.energies_choice = EnergiesChoice(self, width=12)
        self.energies_choice.grid(column=0, row=2, sticky="nwe")

        button = ttk.Button(self, text="Filter similar", command=self._filter)
        button.grid(column=0, row=3, columnspan=2, sticky="nwe")

    def _filter(self):
        tslr = self.parent.parent.tslr
        tslr.conformers.trim_rmds(
            threshold=float(self.threshold.get()),
            window_size=float(self.window_size.get()),
            energy_genre=self.energies_choice.get_genre(),
            ignore_hydrogen=self.ignore_hydrogens.get(),
        )
        # TODO: turn below into some higher-level method
        for box, kept in zip(
            self.parent.conf_list.trees["main"].boxes.values(),
            tslr.conformers.kept,
        ):
            box.var.set(kept)
        self.parent.conf_list.refresh()


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
        ttk.Label(controls.content, text="Show:").grid(column=0, row=2, sticky="nw")
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
        self.show_combo.grid(column=1, row=2, sticky="nwe")

        # filter
        filter_frame = ttk.LabelFrame(controls.content, text="Energies range")
        filter_frame.grid(column=0, row=1, columnspan=2, sticky="nwe")
        tk.Grid.columnconfigure(filter_frame, 1, weight=1)
        ttk.Label(filter_frame, text="Minimum").grid(column=0, row=0)
        ttk.Label(filter_frame, text="Maximum").grid(column=0, row=1)
        ttk.Label(filter_frame, text="Energy type").grid(column=0, row=2)
        self.lower_var = tk.StringVar()
        self.upper_var = tk.StringVar()
        lentry = ttk.Entry(
            filter_frame,
            textvariable=self.lower_var,
            width=15,
            validate="key",
            validatecommand=get_float_entry_validator(self),
        )
        lentry.grid(column=1, row=0, sticky="ne")
        lentry.bind(
            "<FocusOut>",
            lambda e, var=self.lower_var: float_entry_out_validation(var),
        )
        uentry = ttk.Entry(
            filter_frame,
            textvariable=self.upper_var,
            width=15,
            validate="key",
            validatecommand=get_float_entry_validator(self),
        )
        uentry.grid(column=1, row=1, sticky="ne")
        uentry.bind(
            "<FocusOut>",
            lambda e, var=self.upper_var: float_entry_out_validation(var),
        )
        self.en_filter_var = tk.StringVar()
        filter_values = "Thermal Enthalpy Gibbs SCF Zero-Point".split(" ")
        filter_id = "ten ent gib scf zpe".split(" ")
        self.filter_ref = {k: v for k, v in zip(filter_values, filter_id)}
        self.filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.en_filter_var,
            values=filter_values,
            state="readonly",
            width=12,
        )
        self.filter_combo.grid(column=1, row=2, sticky="ne")
        self.filter_combo.bind("<<ComboboxSelected>>", self.set_upper_and_lower)

        b_filter = ttk.Button(
            filter_frame, text="Limit to...", command=self.filter_energy
        )
        b_filter.grid(column=0, row=3, columnspan=2, sticky="nwe")
        self.show_combo.set("Energy /Hartree")
        self.filter_combo.set("Thermal")

        self.rmsd = FilterRMSD(filter_frame)
        self.rmsd.grid(column=0, row=4, columnspan=2, sticky="nwe")

        # can't make it work other way
        # dummy = ttk.Frame(frame, width=185)
        # dummy.grid(column=0, row=5)
        # dummy.grid_propagate(False)

        self.established = False

        guicom.WgtStateChanger.energies.extend(
            [
                b_select,
                b_disselect,
                b_filter,
                self.show_combo,
                lentry,
                uentry,
                self.filter_combo,
            ]
        )

    def establish(self):
        self.show_combo.set("Energy /Hartree")
        self.filter_combo.set("Thermal")
        self.established = True

    @property
    def energies(self):
        return reduce(
            lambda obj, attr: getattr(obj, attr, None),
            ("tslr", "energies"),
            self.parent,
        )

    @property
    def showing(self):
        return self.show_ref[self.show_var.get()]

    def discard_lacking_energies(self):
        if not self.parent.main_tab.kept_vars["incompl"].get():
            logger.info("Any conformers without energy data will be discarded.")
            boxes = self.conf_list.trees["main"].boxes
            for num, conf in enumerate(self.parent.tslr.conformers.values()):
                if "gib" not in conf:
                    boxes[str(num)].var.set(False)

    def refresh(self, event=None):
        self.conf_list.refresh()
        self.set_upper_and_lower()

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

    def set_upper_and_lower(self, event=None):
        energy = self.filter_ref[self.en_filter_var.get()]
        arr = getattr(self.energies[energy], self.showing)
        factor = 100 if self.showing == "populations" else 1
        try:
            lower, upper = arr.min(), arr.max()
        except ValueError:
            lower, upper = 0, 0
        else:
            if self.showing == "values":
                n = 6
            else:
                n = 4
            lower, upper = map(
                lambda v: "{:.{}f}".format(v * factor, n), (lower, upper)
            )
        finally:
            self.lower_var.set(lower)
            self.upper_var.set(upper)

    def filter_energy(self):
        energy = self.filter_ref[self.en_filter_var.get()]
        factor = 1e-2 if self.showing == "populations" else 1
        lower = float(self.lower_var.get()) * factor
        upper = float(self.upper_var.get()) * factor
        self.parent.tslr.conformers.trim_to_range(
            energy, minimum=lower, maximum=upper, attribute=self.showing
        )
        for box, kept in zip(
            self.conf_list.trees["main"].boxes.values(),
            self.parent.tslr.conformers.kept,
        ):
            box.var.set(kept)
        self.conf_list.refresh()
