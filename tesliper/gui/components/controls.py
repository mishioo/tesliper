# IMPORTS
import functools
import logging as lgg
import queue
import tkinter as tk
import tkinter.ttk as ttk
from collections import Counter, namedtuple
from pathlib import Path
from tkinter import messagebox
from tkinter.filedialog import (
    askdirectory,
    askopenfilename,
    askopenfilenames,
    asksaveasfilename,
)

import numpy as np

from tesliper import Soxhlet
from tesliper import datawork as dw
from tesliper import glassware as gw
from tesliper import writing as wr

# LOGGER
from ...datawork import DEFAULT_ACTIVITIES
from .choices import ColorsChoice, ConformersChoice, EnergiesChoice
from .collapsible_pane import CollapsiblePane
from .helpers import ThreadedMethod, join_with_and
from .label_separator import LabelSeparator
from .numeric_entry import NumericEntry
from .popups import ExportPopup, GjfPopup

logger = lgg.getLogger(__name__)


# CLASSES
class FilterRange(ttk.Frame):
    def __init__(self, parent, view, proxy, **kwargs):
        super().__init__(parent, **kwargs)
        self.view = view
        # dict with getters for "genre" and "show" comboboxes
        # and "units" of currently showing values
        self.proxy = proxy

        self.columnconfigure(1, weight=1)
        self.lower_var = tk.StringVar()
        self.upper_var = tk.StringVar()
        self.units_var = tk.StringVar()
        ttk.Label(self, text="Minimum").grid(column=0, row=0)
        ttk.Label(self, text="Maximum").grid(column=0, row=1)
        ttk.Label(self, textvariable=self.units_var, width=8).grid(column=2, row=0)
        ttk.Label(self, textvariable=self.units_var, width=8).grid(column=2, row=1)
        ttk.Label(self, text="Energy type").grid(column=0, row=2)
        self.lower_entry = NumericEntry(
            self,
            textvariable=self.lower_var,
            width=15,
            scroll_modifier=self.scroll_modifier,
            keep_trailing_zeros=True,
            decimal_digits=6,
        )
        self.lower_entry.grid(column=1, row=0, sticky="new")
        self.upper_entry = NumericEntry(
            self,
            textvariable=self.upper_var,
            width=15,
            scroll_modifier=self.scroll_modifier,
            keep_trailing_zeros=True,
            decimal_digits=6,
        )
        self.upper_entry.grid(column=1, row=1, sticky="new")

        b_filter = ttk.Button(self, text="Limit to...", command=self.filter_energy)
        b_filter.grid(column=0, row=2, columnspan=3, sticky="new")

        root = self.winfo_toplevel()
        # root.bind("<<KeptChanged>>", self.set_upper_and_lower, "+")
        root.bind("<<DataExtracted>>", self.set_upper_and_lower, "+")

        root.changer.register(
            [b_filter, self.lower_entry, self.upper_entry], "energies"
        )

    _scroll_modifiers = {
        "values": lambda v, d: v + 0.00001 * d,
        "deltas": lambda v, d: v + 0.01 * d,
        "min_factors": lambda v, d: v + 1.2 ** d,
        "populations": lambda v, d: v + 1 * d,
    }

    _entry_configure = {
        "values": {
            "min_value": float("-inf"),
            "max_value": float("inf"),
            "decimal_digits": 6,
        },
        "deltas": {"min_value": 0, "max_value": float("inf"), "decimal_digits": 4},
        "min_factors": {"min_value": 0, "max_value": float("inf"), "decimal_digits": 4},
        "populations": {"min_value": 0, "max_value": 100, "decimal_digits": 4},
    }

    @property
    def tesliper(self):
        return self.winfo_toplevel().tesliper

    def on_show_selected(self, _event=None):
        config = self._entry_configure[self.proxy["show"]()]
        self.upper_entry.configure(**config)
        self.lower_entry.configure(**config)
        self.set_upper_and_lower()

    def scroll_modifier(self, value, delta):
        showing = self.proxy["show"]()
        updated = self._scroll_modifiers[showing](value, delta)
        return updated

    def set_upper_and_lower(self, _event=None):
        if _event is not None:
            logger.debug(f"Event caught by {self}.set_upper_and_lower handler.")
        showing = self.proxy["show"]()
        units = self.proxy["units"]()
        factor = 100 if showing == "populations" else 1
        try:
            energy = self.proxy["genre"]()
            arr = getattr(self.tesliper[energy], showing)
            lower, upper = arr.min(), arr.max()
        except (KeyError, ValueError):
            lower, upper = 0, 0
        else:
            lower, upper = lower * factor, upper * factor
        finally:
            self.lower_entry.update(lower)
            self.upper_entry.update(upper)
            self.units_var.set(units)

    def filter_energy(self):
        showing = self.proxy["show"]()
        energy = self.proxy["genre"]()
        factor = 1e-2 if showing == "populations" else 1
        lower = float(self.lower_entry.get()) * factor
        upper = float(self.upper_entry.get()) * factor
        self.tesliper.conformers.trim_to_range(
            energy, minimum=lower, maximum=upper, attribute=showing
        )
        # TODO: turn below into some higher-level method
        for box, kept in zip(
            self.view.trees["main"].boxes.values(),
            self.tesliper.conformers.kept,
        ):
            box.var.set(kept)
        self.event_generate("<<KeptChanged>>")


class FilterRMSD(ttk.Frame):
    def __init__(self, parent, view, proxy, **kwargs):
        super().__init__(parent, **kwargs)
        self.view = view
        self.proxy = proxy  # dict with getter for "genre" combobox

        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="Window size").grid(column=0, row=0)
        ttk.Label(self, text="Threshold").grid(column=0, row=1)
        ttk.Label(self, text="kcal/mol").grid(column=2, row=0)
        ttk.Label(self, text="angstrom").grid(column=2, row=1)
        self.window_size = tk.StringVar(value="5.0")
        self.threshold = tk.StringVar(value="1.0")
        window_size = NumericEntry(
            self,
            textvariable=self.window_size,
            width=4,
            scroll_rate=0.5,
            min_value=0,
        )
        window_size.grid(column=1, row=0, sticky="new")
        threshold = NumericEntry(
            self,
            textvariable=self.threshold,
            width=4,
            scroll_rate=0.1,
            min_value=0,
        )
        threshold.grid(column=1, row=1, sticky="new")
        self.ignore_hydrogens = tk.BooleanVar(value=True)
        ignore_hydrogens = ttk.Checkbutton(
            self, text="Ignore hydrogen atoms", variable=self.ignore_hydrogens
        )
        ignore_hydrogens.grid(column=0, row=3, columnspan=3, sticky="new")

        button = ttk.Button(self, text="Filter similar", command=self._filter)
        button.grid(column=0, row=4, columnspan=3, sticky="nwe")

        self.winfo_toplevel().changer.register(
            [window_size, threshold, ignore_hydrogens, button], "energies"
        )

    @property
    def tesliper(self):
        return self.winfo_toplevel().tesliper

    @ThreadedMethod(progbar_msg="Finding similar conformers...")
    def _filter(self):
        self.tesliper.conformers.trim_rmsd(
            threshold=float(self.threshold.get()),
            window_size=float(self.window_size.get()),
            energy_genre=self.proxy["genre"](),
            ignore_hydrogen=self.ignore_hydrogens.get(),
        )
        # TODO: turn below into some higher-level method
        for box, kept in zip(
            self.view.trees["main"].boxes.values(),
            self.tesliper.conformers.kept,
        ):
            box.var.set(kept)
        self.event_generate("<<KeptChanged>>")


class FilterEnergies(CollapsiblePane):
    def __init__(self, parent, view, **kwargs):
        super().__init__(parent, text="Filter kept conformers", **kwargs)
        self.view = view

        ttk.Label(self.content, text="Show:").grid(column=0, row=0, sticky="new")
        self.show_var = tk.StringVar()
        show_values = (
            "Energy /Hartree",
            "Delta /(kcal/mol)",
            "Min. Boltzmann factor",
            "Population /%",
        )
        show_units = ("Hartree", "kcal/mol", "", "%")
        show_id = ("values", "deltas", "min_factors", "populations")
        self.show_ref = {k: v for k, v in zip(show_values, show_id)}
        self.show_units = {k: v for k, v in zip(show_values, show_units)}
        self.show_combo = ttk.Combobox(
            self.content,
            textvariable=self.show_var,
            values=show_values,
            state="readonly",
        )
        self.show_combo.grid(column=1, row=0, sticky="nwe")
        self.show_combo.set("Energy /Hartree")

        # Energy choice
        ttk.Label(self.content, text="Use:").grid(column=0, row=1, sticky="new")
        self.energies_choice = EnergiesChoice(self.content, width=12)
        self.energies_choice.grid(column=1, row=1, sticky="nwe")

        proxy = {
            "genre": self.energies_choice.get_genre,
            "show": lambda: self.show_ref[self.show_var.get()],
            "units": lambda: self.show_units[self.show_var.get()],
        }
        # filter by energy value
        LabelSeparator(self.content, text="Filter range").grid(
            column=0, row=2, columnspan=2, sticky="nwe"
        )
        self.range = FilterRange(self.content, view=self.view, proxy=proxy)
        self.range.grid(column=0, row=3, columnspan=2, sticky="news")

        # RMSD sieve
        LabelSeparator(self.content, text="RMSD sieve").grid(
            column=0, row=4, columnspan=2, sticky="nwe"
        )
        self.rmsd = FilterRMSD(self.content, view=self.view, proxy=proxy)
        self.rmsd.grid(column=0, row=5, columnspan=2, sticky="news")

        self.show_combo.bind("<<ComboboxSelected>>", self.on_show_selected)
        self.energies_choice.bind("<<ComboboxSelected>>", self.on_energies_selected)
        root = self.winfo_toplevel()
        root.bind("<<DataExtracted>>", self.on_show_selected, "+")
        root.changer.register([self.show_combo, self.energies_choice], "energies")

    @property
    def tesliper(self):
        return self.winfo_toplevel().tesliper

    def on_show_selected(self, _event=None):
        if _event is not None:
            logger.debug(f"Event caught by {self}.on_show_selected handler.")
        self.view.refresh(show=self.show_ref[self.show_var.get()])
        self.range.on_show_selected()

    def on_energies_selected(self, _event=None):
        if _event is not None:
            logger.debug(f"Event caught by {self}.on_energies_selected handler.")
        self.range.set_upper_and_lower()


OVERVIEW_GENRES = "dip rot vosc vrot losc lrot raman1 roa1 scf zpe ent ten gib".split()


class SelectConformers(CollapsiblePane):
    overview_control_ref = {
        k: v
        for k, v in zip(
            "file en ir vcd uv ecd ram roa incompl term opt imag".split(" "),
            "command gib dip rot vosc vrot raman1 roa1 command "
            "normal_termination optimization_completed freq".split(" "),
        )
    }

    overview_funcs = dict(
        file=lambda *args: True,
        en=lambda *args: "gib" in args[0],
        ir=lambda *args: "dip" in args[0],
        vcd=lambda *args: "rot" in args[0],
        uv=lambda *args: "vosc" in args[0],
        ecd=lambda *args: "vrot" in args[0],
        ram=lambda *args: "raman1" in args[0],
        roa=lambda *args: "roa1" in args[0],
        incompl=lambda *args: not all(g in args[0] for g in args[1]),
        term=lambda *args: args[0]["normal_termination"],
        opt=lambda *args: "optimization_completed" in args[0]
        and not args[0]["optimization_completed"],
        imag=lambda *args: "freq" in args[0] and any([f < 0 for f in args[0]["freq"]]),
        incons=lambda *args: any(
            g in args[0] and not len(args[0][g]) == mx for g, mx in args[2].items()
        ),
    )

    def __init__(self, parent, view, **kwargs):
        super().__init__(parent, text="Select kept conformers", **kwargs)
        self.view = view

        self.widgets = dict()
        self.columnconfigure(0, weight=1)
        root = self.winfo_toplevel()
        root.bind("<<KeptChanged>>", self.on_kept_changed, "+")
        root.bind("<<DataExtracted>>", self.on_data_extracted, "+")
        root.bind("<<Clear>>", self.clear, "+")

        count_frame = ttk.Frame(self.content)
        count_frame.grid(column=0, row=0, sticky="news")
        widgets_tuple = namedtuple(
            "widgets", ["label", "count", "slash", "all", "check", "uncheck"]
        )
        for i, (name, key) in enumerate(
            zip(
                "Files Energy IR VCD UV ECD Raman ROA Incompl. Errors "
                "Unopt. Imag.Freq. Incons.".split(),
                "file en ir vcd uv ecd ram roa incompl term opt imag incons".split(),
            )
        ):
            var = tk.IntVar()  # number of conformers selected
            var_all = tk.IntVar()  # number of conformers in total

            label = tk.Label(count_frame, text=name, anchor="w")
            count = tk.Label(count_frame, textvariable=var, bd=0, width=3)
            slash = tk.Label(count_frame, text="/", bd=0)
            all_ = tk.Label(count_frame, textvariable=var_all, bd=0, width=3)
            check_butt = ttk.Button(
                count_frame,
                text="select",
                width=6,
                command=lambda key=key: self.select(key, keep=True),
            )
            uncheck_butt = ttk.Button(
                count_frame,
                text="discard",
                width=8,
                command=lambda key=key: self.select(key, keep=False),
            )

            count.var = var
            all_.var = var_all

            label.grid(column=0, row=i)
            count.grid(column=1, row=i)
            slash.grid(column=2, row=i)
            all_.grid(column=3, row=i)
            check_butt.grid(column=4, row=i, sticky="ne")
            uncheck_butt.grid(column=5, row=i, sticky="ne")

            root.changer.register([check_butt, uncheck_butt], "tesliper")

            self.widgets[key] = widgets_tuple(
                label, count, slash, all_, check_butt, uncheck_butt
            )
        separator = LabelSeparator(self.content, text="Always discard?")
        separator.grid(column=0, row=1, sticky="we")

        keep_unchecked_frame = ttk.Frame(self.content)
        keep_unchecked_frame.grid(column=0, row=2, sticky="nswe")
        self.kept_vars = {
            k: tk.BooleanVar(value=True)
            for k in "error unopt imag stoich incompl incons".split(" ")
        }
        self.kept_buttons = {
            k: ttk.Checkbutton(
                keep_unchecked_frame,
                text=text,
                variable=var,
                command=lambda k=k: self.discard(k),
            )
            for (k, var), text in zip(
                self.kept_vars.items(),
                [
                    "Error termination",
                    "Unoptimised",
                    "Imaginary frequencies",
                    "Non-matching stoichiometry",
                    "Incomplete entries",
                    "Inconsistent data sizes",
                ],
            )
        }
        for n, (key, var) in enumerate(self.kept_vars.items()):
            self.kept_buttons[key].grid(column=0, row=n, sticky="nw")

    @property
    def tesliper(self):
        return self.winfo_toplevel().tesliper

    def clear(self, _event=None):
        for items in self.widgets.values():
            items.all.var.set(0)
            items.count.var.set(0)

    def on_data_extracted(self, _event=None):
        if _event is not None:
            logger.debug(f"Event caught by {self}.on_data_extracted handler.")
        # "all" count should only be called after extraction
        self.update_overview_values(untrimmed=True)
        self.on_kept_changed(_event)

    def on_kept_changed(self, _event=None):
        if _event is not None:
            logger.debug(f"Event caught by {self}.on_kept_changed handler.")
        self.discard_not_kept()
        self.update_overview_values()

    def update_overview_values(self, untrimmed=False):
        logger.debug("Called update_overview_values")
        values = {k: 0 for k in self.widgets.keys()}
        try:
            count = [
                [g in conf for g in OVERVIEW_GENRES]
                for conf in self.tesliper.conformers.values()
            ]
            best_match = [g for g, k in zip(OVERVIEW_GENRES, max(count)) if k]
        except ValueError:
            best_match = []
        sizes = {}
        for fname, conf in self.tesliper.conformers.items():
            for genre, value in conf.items():
                if isinstance(value, (np.ndarray, list, tuple)):
                    sizes.setdefault(genre, {})[fname] = len(value)
        maxes = {
            genre: Counter(v for v in values.values()).most_common()[0][0]
            for genre, values in sizes.items()
        }
        conformers = (
            self.tesliper.conformers.values()
            if untrimmed
            else self.tesliper.conformers.kept_values()
        )
        for conf in conformers:
            values["file"] += 1
            values["term"] += not conf["normal_termination"]
            values["incompl"] += not all(g in conf for g in best_match)
            values["opt"] += (
                "optimization_completed" in conf and not conf["optimization_completed"]
            )
            values["imag"] += "freq" in conf and sum(v < 0 for v in conf["freq"]) > 0
            values["en"] += "gib" in conf
            values["ir"] += "dip" in conf
            values["vcd"] += "rot" in conf
            values["uv"] += "vosc" in conf
            values["ecd"] += "vrot" in conf
            values["ram"] += "raman1" in conf
            values["roa"] += "roa1" in conf
            values["incons"] += any(
                g in conf and not len(conf[g]) == mx for g, mx in maxes.items()
            )
        category = "all" if untrimmed else "count"
        for key, items in self.widgets.items():
            getattr(items, category).var.set(values[key])

    def select(self, key, keep):
        confs = self.tesliper.conformers
        condition = self.overview_funcs[key]
        best_match = []
        maxes = {}
        if key == "incompl":
            try:
                count = [
                    [g in conf for g in OVERVIEW_GENRES]
                    for conf in self.tesliper.conformers.values()
                ]
                best_match = [g for g, k in zip(OVERVIEW_GENRES, max(count)) if k]
            except ValueError:
                best_match = []
        elif key == "incons":
            sizes = {}
            for fname, conf in self.tesliper.conformers.items():
                for genre, value in conf.items():
                    if isinstance(value, (np.ndarray, list, tuple)):
                        sizes.setdefault(genre, {})[fname] = len(value)
            maxes = {
                genre: Counter(v for v in values.values()).most_common()[0][0]
                for genre, values in sizes.items()
            }
        for n, conf in enumerate(confs.values()):
            if condition(conf, best_match, maxes):
                self.view.boxes[str(n)].var.set(keep)
        self.event_generate("<<KeptChanged>>")

    def discard(self, key):
        value = self.kept_vars[key].get()
        if key == "incons":
            self.tesliper.conformers.allow_data_inconsistency = not value
        # trigger discard_not_kept(), update_overview_values()
        # and WgtStateChanger.set_states()
        self.event_generate("<<KeptChanged>>")

    def discard_not_kept(self):
        for key, var in self.kept_vars.items():
            if var.get():
                self.kept_funcs[key]()
        for box, kept in zip(self.view.boxes.values(), self.tesliper.conformers.kept):
            box.var.set(kept)

    @property
    def kept_funcs(self):
        return dict(
            error=self.tesliper.conformers.trim_non_normal_termination,
            unopt=self.tesliper.conformers.trim_not_optimized,
            imag=self.tesliper.conformers.trim_imaginary_frequencies,
            stoich=self.tesliper.conformers.trim_non_matching_stoichiometry,
            incompl=self.tesliper.conformers.trim_incomplete,
            incons=self.tesliper.conformers.trim_inconsistent_sizes,
        )


class CalculateSpectra(CollapsiblePane):
    def __init__(self, parent, view, **kwargs):
        super().__init__(parent, text="Calculate Spectra", **kwargs)
        self.view = view
        root = self.winfo_toplevel()
        root.bind("<<Clear>>", self.clear, "+")

        self.content.columnconfigure(0, weight=1)

        # Spectra name
        LabelSeparator(self.content, text="Spectra type").grid(
            column=0, row=0, sticky="we"
        )
        s_name_frame = ttk.Frame(self.content)
        s_name_frame.grid(column=0, row=1, sticky="we")
        s_name_frame.columnconfigure((0, 1), weight=1)
        self.s_name = tk.StringVar()
        self.s_name_radio = {}
        names = "IR UV Raman VCD ECD ROA".split(" ")
        values = "ir uv raman vcd ecd roa".split(" ")
        positions = [(c, r) for c in range(2) for r in range(3)]
        for n, v, (c, r) in zip(names, values, positions):
            b = ttk.Radiobutton(
                s_name_frame,
                text=n,
                variable=self.s_name,
                value=v,
                command=lambda v=v: self.spectra_chosen(v),
                width=6,
            )
            b.configure(state="disabled")
            b.grid(column=c, row=r, padx=5)
            self.s_name_radio[v] = b
            root.changer.register(b, needs_all_genres=[dw.DEFAULT_ACTIVITIES[v]])

        # Settings
        LabelSeparator(self.content, text="Settings").grid(column=0, row=2, sticky="we")
        sett = ttk.Frame(self.content)
        sett.grid(column=0, row=3, sticky="we")
        tk.Grid.columnconfigure(sett, 1, weight=1)
        ttk.Label(sett, text="Fitting").grid(column=0, row=0)
        fit = tk.StringVar()
        self.fitting = ttk.Combobox(sett, textvariable=fit, state="disabled", width=13)
        self.fitting.bind("<<ComboboxSelected>>", self.live_preview_callback)
        self.fitting.var = fit
        self.fitting.grid(column=1, row=0, columnspan=2, sticky="we")
        self.fitting["values"] = ("lorentzian", "gaussian")
        root.changer.register(
            self.fitting, "bars", key=lambda var=self.s_name: bool(var.get())
        )

        scroll_param = {
            "Start": {"scroll_rate": 50},
            "Stop": {"scroll_rate": 50},
            "Step": {"scroll_rate": 1, "min_value": 0, "include_min_value": False},
            "Width": {"scroll_rate": 0.05, "min_value": 0, "include_min_value": False},
            "Offset": {"scroll_rate": 10},
            "Scaling": {"scroll_factor": 1.1},
        }
        for no, name in enumerate("Start Stop Step Width Offset Scaling".split(" ")):
            ttk.Label(sett, text=name).grid(column=0, row=no + 1)
            var = tk.StringVar()
            entry = NumericEntry(
                sett, textvariable=var, width=10, state="disabled", **scroll_param[name]
            )
            entry.bind("<FocusOut>", lambda e: self.live_preview_callback(), "+")
            entry.bind("<MouseWheel>", lambda e: self.live_preview_callback(), "+")
            entry.bind("<Button-4>", lambda e: self.live_preview_callback(), "+")
            entry.bind("<Button-5>", lambda e: self.live_preview_callback(), "+")

            setattr(self, name.lower(), entry)
            entry.var = var
            entry.grid(column=1, row=no + 1, sticky="we", padx=(0, 5))
            unit = tk.StringVar(value="-")
            entry.unit = unit
            label = ttk.Label(sett, textvariable=unit, width=5)
            label.grid(column=2, row=no + 1, sticky="e")
            root.changer.register(
                entry, "bars", key=lambda var=self.s_name: bool(var.get())
            )

        # Calculation Mode
        self.mode = tk.StringVar()
        self.single_radio = ttk.Radiobutton(
            self.content,
            text="Single file",
            variable=self.mode,
            value="single",
            state="disabled",
            command=self.mode_chosen,
        )
        self.single_radio.grid(column=0, row=4, sticky="w")
        self.average_radio = ttk.Radiobutton(
            self.content,
            text="Average by energy",
            variable=self.mode,
            value="average",
            state="disabled",
            command=self.mode_chosen,
        )
        self.average_radio.grid(column=0, row=6, sticky="w")
        self.stack_radio = ttk.Radiobutton(
            self.content,
            text="Stack by overview",
            variable=self.mode,
            value="stack",
            state="disabled",
            command=self.mode_chosen,
        )
        self.stack_radio.grid(column=0, row=8, sticky="w")

        # TODO: call auto_combobox.update_values() when conformers.kept change
        self.single = ConformersChoice(self.content, spectra_var=self.s_name)
        self.single.bind(
            "<<ComboboxSelected>>",
            lambda event: self.live_preview_callback(event, mode="single"),
        )
        self.single.grid(column=0, row=5)
        self.single["values"] = ()
        self.average = EnergiesChoice(self.content)
        self.average.bind(
            "<<ComboboxSelected>>",
            lambda event: self.live_preview_callback(event, mode="average"),
        )
        self.average.grid(column=0, row=7)

        self.stack = ColorsChoice(self.content)
        self.stack.bind("<<ComboboxSelected>>", self.change_colour)
        self.stack.grid(column=0, row=9)
        root.changer.register(
            [self.single_radio, self.single, self.stack_radio, self.stack],
            "bars",
            key=lambda var=self.s_name: bool(var.get()),
        )
        root.changer.register(
            [self.average_radio, self.average],
            ["bars", "energies"],
            key=lambda var=self.s_name: bool(var.get()),
        )
        self.boxes = dict(single=self.single, average=self.average, stack=self.stack)
        self.current_box = None
        for box in self.boxes.values():
            box.grid_remove()

        # Live preview
        # Recalculate
        frame = ttk.Frame(self.content)
        frame.grid(column=0, row=10, sticky="new")
        frame.columnconfigure(0, weight=1)
        var = tk.BooleanVar()
        self.reverse_ax = ttk.Checkbutton(
            frame,
            variable=var,
            text="Reverse x-axis",
            state="disabled",
            command=self.redraw,
        )
        self.reverse_ax.grid(column=0, row=0, sticky="w")
        self.reverse_ax.var = var
        var = tk.BooleanVar(value=True)
        self.show_bars = ttk.Checkbutton(
            frame,
            variable=var,
            text="Show activities",
            state="disabled",
            command=self.redraw,
        )
        self.show_bars.grid(column=0, row=1, sticky="w")
        self.show_bars.var = var
        self.show_bars.previous_value = True
        var = tk.BooleanVar(value=True)
        self.live_prev = ttk.Checkbutton(
            frame, variable=var, text="Live preview", state="disabled"
        )
        self.live_prev.grid(column=0, row=2, sticky="w")
        self.live_prev.var = var
        # previously labeled 'Recalculate'
        self.recalc_b = ttk.Button(
            frame, text="Redraw", state="disabled", command=self.recalculate_command
        )
        self.recalc_b.grid(column=1, row=2)
        root.changer.register(
            self.reverse_ax, key=lambda var=self.s_name: bool(var.get())
        )
        root.changer.register(
            [self.live_prev, self.recalc_b],
            "bars",
            key=lambda var=self.s_name: bool(var.get()),
        )

        # Experimental spectrum
        LabelSeparator(self.content, text="Experimental spectrum").grid(
            column=0, row=11, sticky="we"
        )
        frame = ttk.Frame(self.content)
        frame.grid(column=0, row=12, sticky="new")
        frame.columnconfigure((0, 1), weight=1)
        var = tk.BooleanVar()
        self.show_exp = ttk.Checkbutton(
            frame,
            variable=var,
            text="Show experimental spectrum",
            state="disabled",
            command=self.redraw,
        )
        self.show_exp.grid(column=0, row=0, columnspan=2, sticky="nw")
        self.show_exp.var = var
        var = tk.BooleanVar(value=True)
        self.allow_double_axis = ttk.Checkbutton(
            frame,
            variable=var,
            text="Allow double y-axis",
            state="disabled",
            command=self.redraw,
        )
        self.allow_double_axis.grid(column=0, row=1, columnspan=2, sticky="nw")
        self.allow_double_axis.var = var
        self.load_exp = ttk.Button(
            frame,
            text="Load from file...",
            state="disabled",
            command=lambda: (self.load_exp_command(), self.live_preview_callback()),
        )
        self.load_exp.grid(column=0, row=2, columnspan=2, sticky="new")
        root.changer.register(
            self.load_exp, key=lambda var=self.s_name: bool(var.get())
        )
        self.auto_scale = ttk.Button(
            frame, text="Auto-scale", state="disabled", command=self.auto_scale_command
        )
        self.auto_scale.grid(column=0, row=3, sticky="new")
        self.auto_shift = ttk.Button(
            frame, text="Auto-shift", state="disabled", command=self.auto_shift_command
        )
        self.auto_shift.grid(column=1, row=3, sticky="new")
        root.changer.register(
            [self.show_exp, self.auto_scale, self.auto_shift, self.allow_double_axis],
            key=lambda wgt=self: wgt.exp_spc is not None,
        )

        self.last_used_settings = {
            name: {
                "offset": 0,
                "scaling": 1,
                "show_bars": True,
                "show_exp": False,
                "reverse_ax": name not in ("uv", "ecd"),
            }
            for name in self.s_name_radio
        }
        self.lastly_drawn_spectra = None
        self._exp_spc = {k: None for k in self.s_name_radio.keys()}

    @property
    def tesliper(self):
        return self.winfo_toplevel().tesliper

    @property
    def exp_spc(self):
        try:
            return self._exp_spc[self.s_name.get()]
        except KeyError:
            # no value selected in s_name radio
            return None

    @exp_spc.setter
    def exp_spc(self, value):
        self._exp_spc[self.s_name.get()] = value

    @property
    def draw_params(self):
        spectra_name = self.s_name.get()
        mode = self.mode.get()
        # get value from self.single, self.average or self.stack
        try:
            option = getattr(self, mode).var.get()
        except AttributeError:
            # mode is not chosen
            option = ""
        return {"spectra_name": spectra_name, "mode": mode, "option": option}

    @ThreadedMethod(progbar_msg="Calculating best fit...")
    def _auto_scale(self):
        self.lastly_drawn_spectra.scale_to(self.exp_spc)
        self.scaling.update(self.lastly_drawn_spectra.scaling)
        return self.lastly_drawn_spectra

    def auto_scale_command(self):
        if self.lastly_drawn_spectra is not None:
            self._auto_scale()
            self.draw(**self.draw_params)

    @ThreadedMethod(progbar_msg="Calculating best fit...")
    def _auto_shift(self):
        self.lastly_drawn_spectra.shift_to(self.exp_spc)
        self.offset.update(self.lastly_drawn_spectra.offset)
        return self.lastly_drawn_spectra

    def auto_shift_command(self):
        if self.lastly_drawn_spectra is not None:
            self._auto_shift()
            self.draw(**self.draw_params)

    def load_exp_command(self):
        filename = askopenfilename(
            parent=self,
            title="Select spectrum file.",
            filetypes=[
                ("text files", "*.txt"),
                ("xy files", "*.xy"),
                # ("spc files", "*.spc"),
                # spc not supported yet
                ("all files", "*.*"),
            ],
        )
        if filename:
            logger.debug(f"File: {filename}")
            try:
                soxhlet = Soxhlet()
                spc = soxhlet.load_spectrum(filename)
            except ValueError:
                logger.warning(
                    "Experimental spectrum couldn't be loaded. "
                    "Please check if format of your file is supported"
                    " or if file is not corrupted."
                )
            else:
                self.exp_spc = gw.SingleSpectrum(
                    genre=self.draw_params["spectra_name"],
                    values=spc[1],
                    abscissa=spc[0],
                )
                self.show_exp.var.set(True)
                self.winfo_toplevel().changer.set_states()

    def mode_chosen(self, _event=None):
        if _event is not None:
            logger.debug(f"Event caught by {self}.mode_chosen handler.")
        mode = self.mode.get()
        if self.current_box is not None:
            self.current_box.grid_remove()
        self.current_box = self.boxes[mode]
        self.current_box.grid()
        getattr(self, mode).update_values()  # update linked combobox values
        if mode == "single":
            self.show_bars.config(state="normal")
            self.show_bars.var.set(self.show_bars.previous_value)
        else:
            self.show_bars.config(state="disabled")
            self.show_bars.previous_value = self.show_bars.var.get()
            self.show_bars.var.set(False)
        self.live_preview_callback()

    def spectra_chosen(self, _event=None):
        if _event is not None:
            logger.debug(f"Event caught by {self}.spectra_chosen handler.")
        tslr = self.tesliper
        self.visualize_settings()
        bar = DEFAULT_ACTIVITIES[self.s_name.get()]
        self.single["values"] = [k for k, v in tslr.conformers.items() if bar in v]
        self.winfo_toplevel().changer.set_states()
        if self.mode.get():
            self.live_preview_callback()
        else:
            self.single_radio.invoke()

    def visualize_settings(self):
        spectra_name = self.s_name.get()
        spectra_type = gw.SpectralActivities.spectra_type_ref[spectra_name]
        tslr = self.tesliper
        last_used = self.last_used_settings[spectra_name]
        settings = tslr.parameters[spectra_type].copy()
        settings.update(last_used)
        for name, sett in settings.items():
            if name == "fitting":
                try:
                    self.fitting.var.set(settings["fitting"].__name__)
                except AttributeError:
                    self.fitting.var.set(settings["fitting"])
            else:
                entry = getattr(self, name)
                entry.var.set(sett)
                try:
                    entry.unit.set(gw.Spectra._units[spectra_name][name])
                except AttributeError:
                    logger.debug(f"Pass on {name}")
                except KeyError:
                    if name == "offset":
                        entry.unit.set(gw.Spectra._units[spectra_name]["start"])
                    elif name == "scaling":
                        pass
                    else:
                        raise ValueError(f"Invalid setting name: {name}")

    def live_preview_callback(self, _event=None, mode=False):
        if _event is not None:
            logger.debug(f"Event caught by {self}.live_preview_callback handler.")
        # TO DO: separate things, that don't need recalculation
        # TO DO: show/hide bars/experimental plots when checkbox clicked
        # TO DO: rewrite this function with sense
        spectra_name = self.s_name.get()
        mode_con = self.mode.get() == mode if mode else True
        settings_con = (
            spectra_name not in self.last_used_settings
            or self.current_settings != self.last_used_settings[spectra_name]
        )
        core = any([not self.view.tslr_ax, mode_con, settings_con])
        if core and self.live_prev.var.get():
            logger.debug("Live preview on, spectra will be recalculated.")
            self.recalculate_command()
        else:
            logger.debug("Live preview off.")

    def draw(self, spectra_name, mode, option):
        queue_ = self.winfo_toplevel().thread.queue
        if mode == "single" and self.show_bars.var.get():
            bar_name = dw.DEFAULT_ACTIVITIES[spectra_name]
            with self.tesliper.conformers.trimmed_to([option]):
                bars = self.tesliper[bar_name]
        else:
            bars = None
        self._draw(
            queue_,
            bars=bars,
            colour=option,
            stack=mode == "stack",
            experimental=self.exp_spc if self.show_exp.var.get() else None,
            reverse_ax=self.reverse_ax.var.get(),
            allow_double_axis=self.allow_double_axis.var.get(),
        )

    def _draw(self, queue_, **kwargs):
        try:
            spc = queue_.get(0)  # data put to queue by self._calculate_spectra
            self.view.draw_spectra(spc, **kwargs)
            self.lastly_drawn_spectra = spc
        except queue.Empty:
            func = functools.update_wrapper(
                functools.partial(self._draw, **kwargs), self._draw
            )
            self.after(20, func, queue_)

    def redraw(self):
        draw_params = self.draw_params
        if draw_params["mode"] == "single" and self.show_bars.var.get():
            bar_name = dw.DEFAULT_ACTIVITIES[draw_params["spectra_name"]]
            with self.tesliper.conformers.trimmed_to([draw_params["option"]]):
                bars = self.tesliper[bar_name]
        else:
            bars = None
        self.view.draw_spectra(
            self.lastly_drawn_spectra,
            bars=bars,
            colour=draw_params["option"],
            stack=draw_params["mode"] == "stack",
            experimental=self.exp_spc if self.show_exp.var.get() else None,
            reverse_ax=self.reverse_ax.var.get(),
            allow_double_axis=self.allow_double_axis.var.get(),
        )

    def change_colour(self, _event=None):
        if _event is not None:
            logger.debug(f"Event caught by {self}.change_colour handler.")
        if self.mode.get() != "stack":
            return
        colour = self.stack.var.get()
        self.view.change_colour(colour)

    def _exec_calculate_spectra(self, spectra_name, conformer=None):
        # should be called in execution thread
        if conformer is not None:
            spc = self.tesliper.calculate_single_spectrum(
                spectra_name=spectra_name,
                conformer=conformer,
                **self.calculation_params,
            )
        else:
            spc = self.tesliper.calculate_spectra(
                spectra_name, **self.calculation_params
            )[
                spectra_name
            ]  # tslr.calculate_spectra returns dictionary
        offset = self.offset.var.get()
        scaling = self.scaling.var.get()
        if offset:  # if not chosen, ignore
            spc.offset = float(offset)
        if scaling:  # if not chosen, ignore
            spc.scaling = float(scaling)
        return spc

    @ThreadedMethod(progbar_msg="Calculating...")
    def _calculate_spectra(self, spectra_name, option, mode):
        spc = self._exec_calculate_spectra(
            spectra_name=spectra_name,
            conformer=option if mode == "single" else None,
        )
        if mode == "average":
            en_name = self.average.get_genre()
            spc = self.tesliper.get_averaged_spectrum(spectra_name, en_name)
        return spc

    @property
    def calculation_params(self):
        d = {
            k: v
            for k, v in self.current_settings.items()
            if k in "start stop step width fitting".split(" ")
        }
        return d

    @property
    def current_settings(self):
        try:
            settings = {
                key: float(getattr(self, key).get())
                for key in "start stop step width offset scaling".split(" ")
            }
            settings.update(
                {
                    key: getattr(self, key).var.get()
                    for key in "reverse_ax show_bars show_exp".split(" ")
                }
            )
            fit = self.fitting.get()
            settings["fitting"] = getattr(dw, fit)
        except ValueError:
            return {}
        return settings

    def recalculate_command(self):
        draw_params = self.draw_params
        spectra_name = draw_params["spectra_name"]
        if not spectra_name:
            logger.debug("Calculation aborted: spectra_name not specified.")
            return
        if not self.current_settings:
            logger.info("Calculation aborted: invalid settings provided.")
            return
        self.last_used_settings[spectra_name] = self.current_settings.copy()
        option = draw_params["option"]
        if not option or option.startswith("Choose "):
            logger.info("Calculation aborted: option not chosen.")
            return
        logger.debug(f"Recalculating with {self.current_settings}")
        self._calculate_spectra(**draw_params)
        self.draw(**draw_params)

    def clear(self, _event=None):
        self.s_name.set("")
        self.mode.set("")
        self.show_bars.config(state="disabled")


class ExtractData(ttk.LabelFrame):
    def __init__(self, parent, view, **kwargs):
        self.view = view
        super().__init__(parent, text="Extract data", **kwargs)
        self.columnconfigure(0, weight=1)
        self.b_man_extract = ttk.Button(
            self, text="Choose files", command=self.man_extract
        )
        self.b_man_extract.grid(column=0, row=0, sticky="nwe")
        self.b_auto_extract = ttk.Button(
            self, text="Choose folder", command=self.from_dir
        )
        self.b_auto_extract.grid(column=0, row=1, sticky="nwe")
        self.ignore_unknown = tk.BooleanVar()
        self.check_ignore_unknown = ttk.Checkbutton(
            self, text="Ignore unknown conformers", variable=self.ignore_unknown
        )
        self.check_ignore_unknown.grid(column=0, row=2, sticky="nwe")
        self.winfo_toplevel().changer.register(self.check_ignore_unknown, "tesliper")

    # TODO: add recursive smart extraction

    @property
    def tesliper(self):
        return self.winfo_toplevel().tesliper

    def from_dir(self):
        work_dir = askdirectory()
        if not work_dir:
            return
        wanted = self.tesliper.conformers.keys() if self.ignore_unknown.get() else None
        self.extract(path=work_dir, wanted_files=wanted)

    def man_extract(self):
        files = askopenfilenames(
            filetypes=[
                ("gaussian output", ("*.log", "*.out")),
                ("log files", "*.log"),
                ("out files", "*.out"),
                ("all files", "*.*"),
            ],
            defaultextension=".log",
        )
        if not files:
            return
        paths = [Path(path) for path in files]
        filenames = [path.name for path in paths]
        directory = paths[0].parent
        self.extract(directory, filenames)

    @ThreadedMethod(progbar_msg="Extracting...")
    def extract(self, path, wanted_files=None):
        # TODO: handle extraction errors
        root = self.winfo_toplevel()
        try:
            for file, data in self.tesliper.extract_iterate(path, wanted_files):
                root.progtext.set(f"Extracting {file}...")
                self.view.insert("", tk.END, text=file)
        except TypeError as err:
            logger.warning("Cannot extract from specified directory: " + err.args[0])
            return
        logger.debug(f"Data extracted from {path}")
        self.event_generate("<<DataExtracted>>")


class ExportData(ttk.LabelFrame):
    def __init__(self, parent, **kwargs):
        # Change label text
        super().__init__(parent, text="Session control", **kwargs)
        root = self.winfo_toplevel()

        tk.Grid.columnconfigure(self, (0, 1), weight=1)
        self.b_save_session = ttk.Button(
            self, text="Save session", command=self.save_session
        )
        self.b_save_session.grid(column=0, row=0, sticky="nwe")
        self.b_load_session = ttk.Button(
            self, text="Load session", command=self.load_session, state="enabled"
        )
        self.b_load_session.grid(column=0, row=1, sticky="nwe")
        self.b_clear_session = ttk.Button(
            self, text="Clear session", command=self.winfo_toplevel().new_session
        )
        self.b_clear_session.grid(column=0, row=2, sticky="nwe")
        root.changer.register([self.b_clear_session, self.b_save_session], "tesliper")

        self.b_text_export = ttk.Button(
            self, text="Export as .txt", command=lambda: self.save(fmt="txt")
        )
        self.b_text_export.grid(column=1, row=0, sticky="nwe")
        self.b_excel_export = ttk.Button(
            self, text="Export as .xls", command=lambda: self.save(fmt="xlsx")
        )
        self.b_excel_export.grid(column=1, row=1, sticky="nwe")
        self.b_csv_export = ttk.Button(
            self, text="Export as .csv", command=lambda: self.save(fmt="csv")
        )
        self.b_csv_export.grid(column=1, row=2, sticky="nwe")
        root.changer.register(
            [self.b_text_export, self.b_excel_export, self.b_csv_export], "tesliper"
        )
        self.b_gjf_export = ttk.Button(
            self, text="Create .gjf files", command=self.export_gjf
        )
        self.b_gjf_export.grid(column=1, row=3, sticky="nwe")
        root.changer.register(
            [self.b_gjf_export], needs_any_genre=gw.Geometry.associated_genres
        )
        # TODO: handle PermissionDenied exception

    @property
    def tesliper(self):
        return self.winfo_toplevel().tesliper

    def save_session(self):
        file = asksaveasfilename(
            filetypes=[
                ("tesliper", "*.tslr"),
                ("all files", "*.*"),
            ],
            defaultextension=".tslr",
        )
        if not file:
            return
        path = Path(file)
        self.tesliper.output_dir = path.parent
        try:
            self.tesliper.serialize(path.name)
        except FileExistsError:
            if self._should_override([path.name]):
                self.tesliper.serialize(path.name, mode="w")

    def load_session(self):
        file = askopenfilename(
            filetypes=[
                ("tesliper", "*.tslr"),
                ("all files", "*.*"),
            ],
            defaultextension=".tslr",
        )
        if not file:
            return
        root = self.winfo_toplevel()
        root.new_session()
        if not root.tesliper.conformers:
            path = Path(file)
            root.new_tesliper(path)

    def get_save_query(self):
        popup = ExportPopup(self, width="700", height="380")
        query = popup.get_query()
        return query

    def _should_override(self, existing: list):
        if not existing:
            return False
        many = len(existing) > 1
        joined = join_with_and(existing)
        title = "Files already exist!"
        message = (
            f"{joined} file{'s' if many else ''} already exist in this directory. "
            f"Would you like to overwrite {'them' if many else 'it'}?"
        )
        return messagebox.askokcancel(parent=self, title=title, message=message)

    @ThreadedMethod(progbar_msg="Saving...")
    def execute_save_command(self, categories, fmt):
        root = self.winfo_toplevel()
        if "spectra" in categories:
            root.progtext.set("Calculating spectra...")
            self.tesliper.spectra = {}
            for spc in categories["spectra"]:
                _ = root.controls.calculate._exec_calculate_spectra(spc.lower())
            root.progtext.set("Saving...")
        if "averaged" in categories:
            root.progtext.set("Averaging spectra...")
            self.tesliper.averaged = {}
            for spc, en in categories["averaged"]:
                averaged = self.tesliper.get_averaged_spectrum(spectrum=spc, energy=en)
                self.tesliper.averaged[(spc, en)] = averaged
            root.progtext.set("Saving...")
        existing = self._exec_save(categories, fmt, mode="x")
        if self._should_override(existing):
            # for "xlsx" retry whole process, for other retry only unsuccessful
            cats = (
                {cat: categories[cat] for cat in existing}
                if fmt != "xlsx"
                else categories
            )
            self._exec_save(cats, fmt, mode="w")

    def _save_all_transitions(self, fmt, mode, transitions, wavelengths):
        wrt = wr.writer(fmt=fmt, destination=self.tesliper.output_dir, mode=mode)
        wrt.transitions(
            transitions=transitions, wavelengths=wavelengths, only_highest=False
        )

    def _exec_save(self, categories, fmt, mode):
        """Executes save command, calling appropriate "export" methods of Tesliper
        instance. Returns list of genres' categories, for which the associated method
        raised `FileExistsError`.

        Execution is a little different, if `fmt` is "xlsx", as only one file is
        produced for the whole batch: if `FileExistsError` is raised on first category,
        this method returns `["xlsx"]` and ignores the rest of `categories`.
        """
        savers = []
        for thing, genres in categories.items():
            try:
                idx = genres.index("transitions-all")
            except ValueError:
                logger.debug("transitions-all not requested")
            else:
                _ = genres.pop(idx)
                savers.append(
                    (
                        functools.partial(
                            self._save_all_transitions,
                            transitions=self.tesliper["transitions"],
                            wavelengths=self.tesliper["wavelen"],
                        ),
                        thing,
                    )
                )
            if thing == "energies":
                saver = functools.partial(
                    self.tesliper.export_data,
                    genres=["freq", "stoichiometry", *genres],
                )
            elif thing == "spectral data":
                saver = functools.partial(self.tesliper.export_data, genres=genres)
            elif thing == "spectra":
                saver = self.tesliper.export_spectra
            elif thing == "averaged":
                saver = self.tesliper.export_averaged
            else:
                logger.warning(f"Unrecognised export category: '{thing}'.")
                continue
            savers.append((saver, thing))
        existing = set()
        for saver, thing in savers:
            try:
                saver(fmt=fmt, mode=mode)
            except FileExistsError:
                # one .xlsx file for whole batch
                if fmt == "xlsx":
                    return ["xlsx"]
                # must append other data chunks
                existing.add(thing)
            except PermissionError as error:
                answer = messagebox.askokcancel(
                    "Permission Error", f"Cannot write to file: {error}. Continue?"
                )
                if not answer:
                    return []  # empty to abort retry
            # next chunks must be appended to .xlsx file
            mode = "a" if fmt == "xlsx" else mode
        return list(existing)

    def save(self, fmt):
        query = self.get_save_query()
        if not query:
            return
        self.tesliper.output_dir = query["dest"]
        logger.info(f"Export requested: {query['query']}; format: {fmt}")
        self.execute_save_command(query["query"], fmt)

    def export_gjf(self):
        query = GjfPopup(self).get_query()
        if not query:
            return
        self.execute_gjf_export(query)

    @ThreadedMethod(progbar_msg="Creating gjf files...")
    def execute_gjf_export(self, query):
        wrt = wr.writer(fmt="gjf", mode="x", **query["init"])
        try:
            wrt.geometry(**query["call"])
        except FileExistsError:
            if self._should_override(["gjf"]):
                wrt.mode = "w"
                wrt.geometry(**query["call"])
        except PermissionError as error:
            messagebox.showwarning(
                "Permission Error", f"Cannot write to file: {error}."
            )
