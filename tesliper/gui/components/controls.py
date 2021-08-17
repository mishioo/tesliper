# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

from .helpers import (
    WgtStateChanger,
    float_entry_out_validation,
    get_float_entry_validator,
)

# LOGGER
logger = lgg.getLogger(__name__)


# CLASSES
class EnergiesChoice(ttk.Combobox):
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
        self.var = tk.StringVar()
        self.tesliper = tesliper
        kwargs["textvariable"] = self.var
        kwargs["state"] = "readonly"
        super().__init__(parent, **kwargs)

    def get_genre(self):
        """Convenience method for getting genre of the energy type chosen."""
        return self._names_ref[self.var.get()]

    def update_values(self):
        """Update displayed values to reflect currently available energy genres.
        If previously chosen genre is no longer available, change it."""
        current = self.var.get()
        available_genres = [
            genre
            for genre in self._genres_ref
            if self.tesliper.conformers.has_genre(genre)
        ]
        available = tuple(self._genres_ref[genre] for genre in available_genres)
        self["values"] = available
        logger.debug(f"Updated energy values with {available}.")
        if available and current not in available:
            self.var.set(available[0])
            logger.info(
                f"Energy genre '{current}' is no longer available, "
                f"changed to {available[0]}."
            )
        elif not available:
            self.var.set("Not available.")
            logger.info("No energy genre is available, removed selection.")


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
