# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk
from abc import ABC, abstractmethod

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

    def __init__(self, parent, tesliper, **kwargs):
        self.var = tk.StringVar()
        self.tesliper = tesliper
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
