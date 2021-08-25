# IMPORTS
import functools
import logging as lgg
import queue
import tkinter as tk
import tkinter.ttk as ttk
from abc import ABC, abstractmethod
from collections import Counter, namedtuple
from pathlib import Path
from tkinter import messagebox
from tkinter.filedialog import askdirectory, askopenfilename, askopenfilenames

import numpy as np

from ... import datawork as dw
from ... import tesliper
from .collapsible_pane import CollapsiblePane
from .helpers import (
    ThreadedMethod,
    WgtStateChanger,
    float_entry_out_validation,
    get_float_entry_validator,
    join_with_and,
)
from .label_separator import LabelSeparator
from .popups import ExportPopup, not_implemented_popup

# LOGGER
logger = lgg.getLogger(__name__)


# CLASSES
class AutoComboboxBase(ttk.Combobox, ABC):
    """Combobox implementing functionality for automatically updating list of available
    values."""

    def __init__(self, parent, **kwargs):
        self.var = tk.StringVar()
        kwargs["textvariable"] = self.var
        kwargs["state"] = "readonly"
        super().__init__(parent, **kwargs)
        root = self.winfo_toplevel()
        root.bind("<<KeptChanged>>", self.update_values, "+")
        root.bind("<<DataExtracted>>", self.update_values, "+")

    @abstractmethod
    def get_available_values(self):
        raise NotImplementedError

    def update_values(self, _event=None):
        """Update displayed values to reflect currently available energy genres.
        If previously chosen genre is no longer available, change it."""
        if _event is not None:
            logger.debug(f"Event caught by {self}.update_values handler.")
        current = self.var.get()
        available = self.get_available_values()
        self["values"] = available
        logger.debug(f"Updated {self} values with {available}.")
        if available and current not in available:
            self.var.set(available[0])
            logger.info(
                f"Option '{current}' is no longer available, "
                f"changed to {available[0]}."
            )
        elif not available:
            self.var.set("Not available.")
            logger.info("No values available, removed selection.")


class EnergiesChoice(AutoComboboxBase):
    """Combobox that enables choice of type of energy."""

    _names_ref = {
        k: v
        for k, v in zip(
            "Thermal Enthalpy Gibbs SCF Zero-Point".split(),
            "ten ent gib scf zpe".split(),
        )
    }
    _genres_ref = {v: k for k, v in _names_ref.items()}

    def __init__(self, parent, tesliper, **kwargs):
        super().__init__(parent, **kwargs)
        self.tesliper = tesliper

    def get_genre(self):
        """Convenience method for getting genre of the energy type chosen."""
        return self._names_ref[self.var.get()]

    def get_available_values(self):
        available_genres = [
            genre
            for genre in self._genres_ref
            if self.tesliper.conformers.has_genre(genre)
        ]
        available = tuple(self._genres_ref[genre] for genre in available_genres)
        return available


class ConformersChoice(AutoComboboxBase):
    """Combobox that enables choice of conformer for spectra calculation."""

    def __init__(self, parent, tesliper, spectra_var, **kwargs):
        super().__init__(parent, **kwargs)
        self.tesliper = tesliper
        self.spectra_var = spectra_var

    def get_available_values(self):
        """Returns filenames of conformers having data for chosen spectra."""
        try:
            activities_genre = dw.DEFAULT_ACTIVITIES[self.spectra_var.get()]
        except KeyError:
            return []
        available = self.tesliper[activities_genre].filenames.tolist()
        return available


class ColorsChoice(AutoComboboxBase):
    def get_available_values(self):
        return (
            "viridis plasma spring summer autumn winter copper rainbow "
            "turbo gnuplot Blues Reds Greens Greys ".split()
        )


class FilterRange(ttk.Frame):
    def __init__(self, parent, tesliper, view, proxy, **kwargs):
        super().__init__(parent, **kwargs)
        self.tesliper = tesliper
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
        lentry = ttk.Entry(
            self,
            textvariable=self.lower_var,
            width=15,
            validate="key",
            validatecommand=get_float_entry_validator(self),
        )
        lentry.grid(column=1, row=0, sticky="new")
        lentry.bind(
            "<FocusOut>",
            lambda e, var=self.lower_var: float_entry_out_validation(var),
        )
        uentry = ttk.Entry(
            self,
            textvariable=self.upper_var,
            width=15,
            validate="key",
            validatecommand=get_float_entry_validator(self),
        )
        uentry.grid(column=1, row=1, sticky="new")
        uentry.bind(
            "<FocusOut>",
            lambda e, var=self.upper_var: float_entry_out_validation(var),
        )

        b_filter = ttk.Button(self, text="Limit to...", command=self.filter_energy)
        b_filter.grid(column=0, row=2, columnspan=3, sticky="new")

        root = self.winfo_toplevel()
        # root.bind("<<KeptChanged>>", self.set_upper_and_lower, "+")
        root.bind("<<DataExtracted>>", self.set_upper_and_lower, "+")

        WgtStateChanger.energies.extend([b_filter, lentry, uentry])

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
            lower, upper = "0.0", "0.0"
        else:
            if showing == "values":
                n = 6
            else:
                n = 4
            lower, upper = map(
                lambda v: "{:.{}f}".format(v * factor, n), (lower, upper)
            )
        finally:
            self.lower_var.set(lower)
            self.upper_var.set(upper)
            self.units_var.set(units)

    def filter_energy(self):
        showing = self.proxy["show"]()
        energy = self.proxy["genre"]()
        factor = 1e-2 if showing == "populations" else 1
        lower = float(self.lower_var.get()) * factor
        upper = float(self.upper_var.get()) * factor
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
    def __init__(self, parent, tesliper, view, proxy, **kwargs):
        super().__init__(parent, **kwargs)
        self.tesliper = tesliper
        self.view = view
        self.proxy = proxy  # dict with getter for "genre" combobox

        float_entry_validator = get_float_entry_validator(self)
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="Window size").grid(column=0, row=0)
        ttk.Label(self, text="Threshold").grid(column=0, row=1)
        ttk.Label(self, text="kcal/mol").grid(column=2, row=0)
        ttk.Label(self, text="angstrom").grid(column=2, row=1)
        self.window_size = tk.StringVar(value="5.0")
        self.threshold = tk.StringVar(value="1.0")
        window_size = ttk.Entry(
            self,
            textvariable=self.window_size,
            width=4,
            validate="key",
            validatecommand=float_entry_validator,
        )
        window_size.grid(column=1, row=0, sticky="new")
        window_size.bind(
            "<FocusOut>",
            lambda e, var=self.window_size: float_entry_out_validation(var),
        )
        threshold = ttk.Entry(
            self,
            textvariable=self.threshold,
            width=4,
            validate="key",
            validatecommand=float_entry_validator,
        )
        threshold.grid(column=1, row=1, sticky="new")
        threshold.bind(
            "<FocusOut>",
            lambda e, var=self.threshold: float_entry_out_validation(var),
        )
        self.ignore_hydrogens = tk.BooleanVar(value=True)
        ignore_hydrogens = ttk.Checkbutton(
            self, text="Ignore hydrogen atoms", variable=self.ignore_hydrogens
        )
        ignore_hydrogens.grid(column=0, row=3, columnspan=3, sticky="new")

        button = ttk.Button(self, text="Filter similar", command=self._filter)
        button.grid(column=0, row=4, columnspan=3, sticky="nwe")

        WgtStateChanger.energies.extend(
            [window_size, threshold, ignore_hydrogens, button]
        )

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
    def __init__(self, parent, tesliper, view, **kwargs):
        super().__init__(parent, text="Filter kept conformers", **kwargs)
        self.tesliper = tesliper
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
        self.energies_choice = EnergiesChoice(
            self.content, tesliper=self.tesliper, width=12
        )
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
        self.range = FilterRange(
            self.content, tesliper=self.tesliper, view=self.view, proxy=proxy
        )
        self.range.grid(column=0, row=3, columnspan=2, sticky="news")

        # RMSD sieve
        LabelSeparator(self.content, text="RMSD sieve").grid(
            column=0, row=4, columnspan=2, sticky="nwe"
        )
        self.rmsd = FilterRMSD(
            self.content, tesliper=self.tesliper, view=self.view, proxy=proxy
        )
        self.rmsd.grid(column=0, row=5, columnspan=2, sticky="news")

        self.show_combo.bind("<<ComboboxSelected>>", self.on_show_selected)
        self.energies_choice.bind("<<ComboboxSelected>>", self.on_energies_selected)
        root = self.winfo_toplevel()
        root.bind("<<DataExtracted>>", self.on_show_selected, "+")
        WgtStateChanger.energies.extend([self.show_combo, self.energies_choice])

    def on_show_selected(self, _event=None):
        if _event is not None:
            logger.debug(f"Event caught by {self}.on_show_selected handler.")
        self.view.refresh(show=self.show_ref[self.show_var.get()])
        self.range.set_upper_and_lower()

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

    def __init__(self, parent, tesliper, view, **kwargs):
        super().__init__(parent, text="Select kept conformers", **kwargs)
        self.tesliper = tesliper
        self.view = view

        self.widgets = dict()
        self.columnconfigure(0, weight=1)
        root = self.winfo_toplevel()
        root.bind("<<KeptChanged>>", self.on_kept_changed, "+")
        root.bind("<<DataExtracted>>", self.on_data_extracted, "+")

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
            var = tk.IntVar(value=0)  # number of conformers selected
            var_all = tk.IntVar(value=0)  # number of conformers in total

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

            WgtStateChanger.tslr.extend([check_butt, uncheck_butt])

            self.widgets[key] = widgets_tuple(
                label, count, slash, all_, check_butt, uncheck_butt
            )
        separator = LabelSeparator(self.content, text="Always discard?")
        separator.grid(column=0, row=1, sticky="we")

        keep_unchecked_frame = ttk.Frame(self.content)
        keep_unchecked_frame.grid(column=0, row=2, sticky="nswe")
        self.kept_vars = {
            k: tk.BooleanVar()
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
            var.set(True)
            self.kept_buttons[key].grid(column=0, row=n, sticky="nw")

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
    def __init__(self, parent, tesliper, view, **kwargs):
        super().__init__(parent, text="Calculate Spectra", **kwargs)
        self.tesliper = tesliper
        self.view = view

        self.content.columnconfigure(0, weight=1)

        # Spectra name
        LabelSeparator(self.content, text="Spectra type:").grid(
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
                width=5,
            )
            b.configure(state="disabled")
            b.grid(column=c, row=r, padx=5)
            self.s_name_radio[v] = b

        # Settings
        LabelSeparator(self.content, text="Settings:").grid(
            column=0, row=2, sticky="we"
        )
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
        WgtStateChanger.bars.append(self.fitting)

        for no, name in enumerate("Start Stop Step Width Offset Scaling".split(" ")):
            ttk.Label(sett, text=name).grid(column=0, row=no + 1)
            var = tk.StringVar()
            entry = ttk.Entry(
                sett,
                textvariable=var,
                width=10,
                state="disabled",
                validate="key",
                validatecommand=get_float_entry_validator(self),
            )
            entry.bind(
                "<FocusOut>",
                lambda e, var=var: (
                    float_entry_out_validation(var),
                    self.live_preview_callback(),
                ),
            )
            setattr(self, name.lower(), entry)
            entry.var = var
            entry.grid(column=1, row=no + 1, sticky="we", padx=(0, 5))
            unit = tk.StringVar()
            unit.set("-")
            entry.unit = unit
            label = ttk.Label(sett, textvariable=unit, width=5)
            label.grid(column=2, row=no + 1, sticky="e")
            WgtStateChanger.bars.append(entry)

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
        # FIXME: exception occurs when combobox is selected before s_name_radio
        self.single = ConformersChoice(
            self.content, tesliper=self.tesliper, spectra_var=self.s_name
        )
        self.single.bind(
            "<<ComboboxSelected>>",
            lambda event: self.live_preview_callback(event, mode="single"),
        )
        self.single.grid(column=0, row=5)
        self.single["values"] = ()
        self.average = EnergiesChoice(self.content, tesliper=self.tesliper)
        self.average.bind(
            "<<ComboboxSelected>>",
            lambda event: self.live_preview_callback(event, mode="average"),
        )
        self.average.grid(column=0, row=7)

        self.stack = ColorsChoice(self.content)
        self.stack.bind("<<ComboboxSelected>>", self.change_colour)
        self.stack.grid(column=0, row=9)
        WgtStateChanger.bars.extend(
            [self.single_radio, self.single, self.stack_radio, self.stack]
        )
        WgtStateChanger.both.extend([self.average_radio, self.average])
        self.boxes = dict(single=self.single, average=self.average, stack=self.stack)
        self.current_box = None
        for box in self.boxes.values():
            box.grid_remove()

        # Live preview
        # Recalculate
        frame = ttk.Frame(self.content)
        frame.grid(column=0, row=10, sticky="new")
        var = tk.BooleanVar()
        var.set(False)
        self.reverse_ax = ttk.Checkbutton(
            frame,
            variable=var,
            text="Reverse x-axis",
            state="disabled",
            command=self.live_preview_callback,
        )
        self.reverse_ax.grid(column=0, row=0, sticky="w")
        self.reverse_ax.var = var
        var = tk.BooleanVar()
        var.set(True)
        self.show_bars = ttk.Checkbutton(
            frame,
            variable=var,
            text="Show activities",
            state="disabled",
            command=self.live_preview_callback,
        )
        self.show_bars.grid(column=0, row=1, sticky="w")
        self.show_bars.var = var
        self.show_bars.previous_value = True
        var = tk.BooleanVar()
        var.set(False)
        self.show_exp = ttk.Checkbutton(
            frame,
            variable=var,
            text="Experimental",
            state="disabled",
            command=self.live_preview_callback,
        )
        self.show_exp.grid(column=0, row=2, sticky="w")
        self.show_exp.var = var
        self.load_exp = ttk.Button(
            frame,
            text="Load...",
            state="disabled",
            command=lambda: (self.load_exp_command(), self.live_preview_callback()),
        )
        self.load_exp.grid(column=1, row=2)
        var = tk.BooleanVar()
        var.set(True)
        self.live_prev = ttk.Checkbutton(
            frame, variable=var, text="Live preview", state="disabled"
        )
        self.live_prev.grid(column=0, row=3, sticky="w")
        self.live_prev.var = var
        # previously labeled 'Recalculate'
        self.recalc_b = ttk.Button(
            frame, text="Redraw", state="disabled", command=self.recalculate_command
        )
        self.recalc_b.grid(column=1, row=3)
        WgtStateChanger.bars.extend([self.live_prev, self.recalc_b])

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
        self._exp_spc = {k: None for k in self.s_name_radio.keys()}

    @property
    def exp_spc(self):
        return self._exp_spc[self.s_name.get()]

    @exp_spc.setter
    def exp_spc(self, value):
        self._exp_spc[self.s_name.get()] = value

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
            try:
                # FIXME: correct to use new API
                spc = self.tesliper.soxhlet.load_spectrum(filename)
                self.exp_spc = spc
            except ValueError:
                logger.warning(
                    "Experimental spectrum couldn't be loaded. "
                    "Please check if format of your file is supported"
                    " or if file is not corrupted."
                )
        else:
            return

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
        bar = tesliper.dw.DEFAULT_ACTIVITIES[self.s_name.get()]
        self.single["values"] = [k for k, v in tslr.conformers.items() if bar in v]
        self.reverse_ax.config(state="normal")
        self.load_exp.config(state="normal")
        self.show_exp.config(state="normal")
        if self.mode.get():
            self.live_preview_callback()
        else:
            self.single_radio.invoke()

    def visualize_settings(self):
        spectra_name = self.s_name.get()
        spectra_type = tesliper.gw.SpectralData.spectra_type_ref[spectra_name]
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
                    entry.unit.set(tesliper.gw.Spectra._units[spectra_name][name])
                except AttributeError:
                    logger.debug(f"Pass on {name}")
                except KeyError:
                    if name == "offset":
                        entry.unit.set(
                            tesliper.gw.Spectra._units[spectra_name]["start"]
                        )
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
            bar_name = tesliper.dw.DEFAULT_ACTIVITIES[spectra_name]
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
        )

    def _draw(self, queue_, **kwargs):
        try:
            spc = queue_.get(0)  # data put to queue by self._calculate_spectra
            self.view.draw_spectra(spc, **kwargs)
        except queue.Empty:
            func = functools.update_wrapper(
                functools.partial(self._draw, **kwargs), self._draw
            )
            self.after(20, func, queue_)

    def change_colour(self, _event=None):
        if _event is not None:
            logger.debug(f"Event caught by {self}.change_colour handler.")
        if self.mode.get() != "stack":
            return
        colour = self.stack.var.get()
        self.view.change_colour(colour)

    @ThreadedMethod(progbar_msg="Calculating...")
    def _calculate_spectra(self, spectra_name, option, mode):
        if mode == "single":
            spc = self.tesliper.calculate_single_spectrum(
                spectra_name=spectra_name, conformer=option, **self.calculation_params
            )
        else:
            spc = self.tesliper.calculate_spectra(
                spectra_name, **self.calculation_params
            )[
                spectra_name
            ]  # tslr.calculate_spectra returns dictionary
            if mode == "average":
                en_name = self.average.get_genre()
                spc = self.tesliper.get_averaged_spectrum(spectra_name, en_name)
        spc.offset = float(self.offset.var.get())
        spc.scaling = float(self.scaling.var.get())
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
            settings["fitting"] = getattr(tesliper.dw, fit)
        except ValueError:
            return {}
        return settings

    def recalculate_command(self):
        spectra_name = self.s_name.get()
        if not spectra_name:
            logger.debug("spectra_name not specified.")
            return
        self.last_used_settings[spectra_name] = self.current_settings.copy()
        mode = self.mode.get()
        # get value from self.single, self.average or self.stack
        option = getattr(self, mode).var.get()
        if option.startswith("Choose "):
            return
        logger.debug("Recalculating!")
        self._calculate_spectra(spectra_name, option, mode)
        self.draw(spectra_name=spectra_name, mode=mode, option=option)


class ExtractData(ttk.LabelFrame):
    def __init__(self, parent, tesliper, view, **kwargs):
        self.tesliper = tesliper
        self.view = view
        super().__init__(parent, text="Extract data", **kwargs)
        self.columnconfigure(0, weight=1)
        self.b_auto_extract = ttk.Button(
            self, text="Choose folder", command=self.from_dir
        )
        self.b_auto_extract.grid(column=0, row=0, sticky="nwe")
        self.b_man_extract = ttk.Button(
            self, text="Choose files", command=self.man_extract
        )
        self.b_man_extract.grid(column=0, row=1, sticky="nwe")

    # TODO: add recursive smart extraction
    # TODO: add option to ignore unknown conformers

    def from_dir(self):
        work_dir = askdirectory()
        if not work_dir:
            return
        self.extract(path=work_dir)

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
        try:
            for file, data in self.tesliper.extract_iterate(path, wanted_files):
                self.view.insert("", tk.END, text=file)
        except TypeError as err:
            logger.warning("Cannot extract from specified directory: " + err.args[0])
            return
        logger.debug(f"Data extracted from {path}")
        self.event_generate("<<DataExtracted>>")


class ExportData(ttk.LabelFrame):
    def __init__(self, parent, tesliper, **kwargs):
        # Change label text
        super().__init__(parent, text="Session control", **kwargs)
        self.tesliper = tesliper

        tk.Grid.columnconfigure(self, (0, 1), weight=1)
        self.b_clear_session = ttk.Button(
            self, text="Clear session", command=self.winfo_toplevel().new_session
        )
        self.b_clear_session.grid(column=0, row=2, sticky="nwe")
        WgtStateChanger.either.append(self.b_clear_session)

        self.b_calc = ttk.Button(
            self, text="Auto calculate", command=not_implemented_popup
        )
        self.b_calc.grid(column=0, row=0, sticky="nwe")
        WgtStateChanger.bars.append(self.b_calc)

        self.b_text_export = ttk.Button(
            self, text="Export as .txt", command=lambda _e: self.save(fmt="txt")
        )
        self.b_text_export.grid(column=1, row=0, sticky="nwe")
        self.b_excel_export = ttk.Button(
            self, text="Export as .xls", command=lambda _e: self.save(fmt="xlsx")
        )
        self.b_excel_export.grid(column=1, row=1, sticky="nwe")
        self.b_csv_export = ttk.Button(
            self, text="Export as .csv", command=lambda _e: self.save(fmt="csv")
        )
        self.b_csv_export.grid(column=1, row=2, sticky="nwe")
        WgtStateChanger.either.extend(
            [self.b_text_export, self.b_excel_export, self.b_csv_export]
        )

    def get_save_query(self):
        popup = ExportPopup(self, width="220", height="130")
        query = popup.get_query()
        return query

    @ThreadedMethod(progbar_msg="Saving...")
    def execute_save_command(self, categories, fmt):
        # TODO: add auto-calculate ?
        root = self.winfo_toplevel()
        if "averaged" in categories:
            root.progtext.set("Averaging spectra...")
            self.tesliper.average_spectra()
            root.progtext.set("Saving...")
        existing = self._exec_save(categories, fmt, mode="x")
        if existing:
            joined = join_with_and(existing).capitalize()
            title = (
                f"{joined} files already exist!"
                if fmt != "xlsx"
                else ".xlsx file already exists!"
            )
            message = (
                f"{joined} files already exist in this directory. "
                "Would you like to overwrite them?"
                if fmt != "xlsx"
                else ".xlsx file already exists in this directory. "
                "Would you like to overwrite it?"
            )
            override = messagebox.askokcancel(title=title, message=message)
            if override:
                # for "xlsx" retry whole process, for other retry only unsuccessful
                cats = existing if fmt != "xlsx" else categories
                self._exec_save(cats, fmt, mode="w")

    def _exec_save(self, categories, fmt, mode):
        """Executes save command, calling appropriate "export" methods of Tesliper
        instance. Returns list of genres' categories, for which the associated method
        raised `FileExistsError`.

        Execution is a little different, if `fmt` is "xlsx", as only one file is
        produced for the whole batch: if `FileExistsError` is raised on first category,
        this method returns `["xlsx"]` and ignores the rest of `categories`.
        """
        savers = {
            "energies": self.tesliper.export_energies,
            "spectral data": self.tesliper.export_spectral_data,
            "spectra": self.tesliper.export_spectra,
            "averaged": self.tesliper.export_averaged,
        }
        existing = []
        for thing in categories:
            try:
                savers[thing](fmt, mode=mode)
            except FileExistsError:
                existing.append(thing)
                if fmt == "xlsx":
                    return ["xlsx"]
            # one .xlsx file for whole batch, must append next data chunks
            mode = "a" if fmt == "xlsx" else mode
        return existing

    def save(self, fmt):
        categories = self.get_save_query()
        if not categories:
            return
        dest = askdirectory()
        if dest:
            self.tesliper.output_dir = dest
            logger.debug(f"Export requested: {categories}; format: {fmt}")
            self.execute_save_command(categories, fmt)
