# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk
from abc import ABC, abstractmethod
from collections import Counter, namedtuple

import numpy as np

from ... import datawork as dw
from . import CollapsiblePane
from .helpers import (
    WgtStateChanger,
    float_entry_out_validation,
    get_float_entry_validator,
)

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

    @abstractmethod
    def get_available_values(self):
        raise NotImplementedError

    def update_values(self):
        """Update displayed values to reflect currently available energy genres.
        If previously chosen genre is no longer available, change it."""
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


class FilterEnergy(ttk.Frame):
    def __init__(self, parent, tesliper, tab):
        super().__init__(parent)
        self.parent = parent
        self.tesliper = tesliper
        self.tab = tab

        self.columnconfigure(1, weight=1)
        ttk.Label(self, text="Minimum").grid(column=0, row=0)
        ttk.Label(self, text="Maximum").grid(column=0, row=1)
        ttk.Label(self, text="Energy type").grid(column=0, row=2)
        self.lower_var = tk.StringVar()
        self.upper_var = tk.StringVar()
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

        self.energies_choice = EnergiesChoice(self, tesliper=self.tesliper, width=12)
        self.energies_choice.grid(column=1, row=2, sticky="new")
        self.energies_choice.bind("<<ComboboxSelected>>", self.set_upper_and_lower)

        b_filter = ttk.Button(self, text="Limit to...", command=self.filter_energy)
        b_filter.grid(column=0, row=3, columnspan=2, sticky="new")

        WgtStateChanger.energies.extend(
            [
                b_filter,
                lentry,
                uentry,
                self.energies_choice,
            ]
        )

    def set_upper_and_lower(self, event=None):
        factor = 100 if self.tab.showing == "populations" else 1
        try:
            energy = self.energies_choice.get_genre()
            arr = getattr(self.tesliper[energy], self.tab.showing)
            lower, upper = arr.min(), arr.max()
        except (KeyError, ValueError):
            lower, upper = "0.0", "0.0"
        else:
            if self.tab.showing == "values":
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
        energy = self.energies_choice.get_genre()
        factor = 1e-2 if self.tab.showing == "populations" else 1
        lower = float(self.lower_var.get()) * factor
        upper = float(self.upper_var.get()) * factor
        self.tesliper.conformers.trim_to_range(
            energy, minimum=lower, maximum=upper, attribute=self.tab.showing
        )
        # TODO: turn below into some higher-level method
        for box, kept in zip(
            self.tab.conf_list.trees["main"].boxes.values(),
            self.tesliper.conformers.kept,
        ):
            box.var.set(kept)
        self.tab.conf_list.refresh()


class FilterRMSD(ttk.Frame):
    def __init__(self, parent, tesliper, tab):
        super().__init__(parent)
        self.parent = parent
        self.tesliper = tesliper
        self.tab = tab

        float_entry_validator = get_float_entry_validator(self)
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="Window size").grid(column=0, row=0)
        ttk.Label(self, text="Threshold").grid(column=0, row=1)
        ttk.Label(self, text="kcal/mol").grid(column=2, row=0)
        ttk.Label(self, text="angstrom").grid(column=2, row=1)
        ttk.Label(self, text="Energy type").grid(column=0, row=2)
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
            self, text="Ignore H", variable=self.ignore_hydrogens
        )
        ignore_hydrogens.grid(column=1, row=3, columnspan=2, sticky="new")

        self.energies_choice = EnergiesChoice(self, tesliper=self.tesliper, width=12)
        self.energies_choice.grid(column=1, row=2, columnspan=2, sticky="nwe")

        button = ttk.Button(self, text="Filter similar", command=self._filter)
        button.grid(column=0, row=4, columnspan=3, sticky="nwe")

        WgtStateChanger.energies.extend(
            [
                window_size,
                threshold,
                ignore_hydrogens,
                self.energies_choice,
                button,
            ]
        )

    def _filter(self):
        self.tesliper.conformers.trim_rmsd(
            threshold=float(self.threshold.get()),
            window_size=float(self.window_size.get()),
            energy_genre=self.energies_choice.get_genre(),
            ignore_hydrogen=self.ignore_hydrogens.get(),
        )
        # TODO: turn below into some higher-level method
        for box, kept in zip(
            self.tab.conf_list.trees["main"].boxes.values(),
            self.tesliper.conformers.kept,
        ):
            box.var.set(kept)
        self.tab.conf_list.refresh()


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

        self.var_all = tk.IntVar(value=0)  # number of conformers in total
        self.widgets = dict()
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
            var = tk.IntVar(value=0)

            label = tk.Label(self.content, text=name, anchor="w")
            count = tk.Label(self.content, textvariable=var, bd=0, width=3)
            slash = tk.Label(self.content, text="/", bd=0)
            all_ = tk.Label(self.content, textvariable=self.var_all, bd=0, width=3)
            check_butt = ttk.Button(
                self.content,
                text="check",
                width=6,
                command=lambda key=key: self.select(key, keep=True),
            )
            uncheck_butt = ttk.Button(
                self.content,
                text="uncheck",
                width=8,
                command=lambda key=key: self.select(key, keep=False),
            )

            count.var = var
            all_.var = self.var_all

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

    def select(self, key, keep):
        confs = self.tesliper.conformers
        condition = self.overview_funcs[key]
        best_match = []
        maxes = {}
        if key == "incompl":
            try:
                count = [
                    [g in conf for g in self.view.genres]
                    for conf in self.tesliper.conformers.values()
                ]
                best_match = [g for g, k in zip(self.view.genres, max(count)) if k]
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
        self.discard_not_kept()
        self.update_overview_values()

    def discard_not_kept(self):
        for key, var in self.kept_vars.items():
            if var.get():
                self.kept_funcs[key]()
        for box, kept in zip(
            self.overview.boxes.values(), self.parent.tslr.conformers.kept
        ):
            box.var.set(kept)
