import logging
import tkinter as tk
import tkinter.ttk as ttk
from abc import ABC, abstractmethod

from tesliper import datawork as dw

# LOGGER
logger = logging.getLogger(__name__)


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

    @property
    def tesliper(self):
        return self.winfo_toplevel().tesliper

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


class GenresChoice(AutoComboboxBase):
    """Combobox that enables choice of type of energy."""

    def __init__(self, parent, genres, names=None, **kwargs):
        super().__init__(parent, **kwargs)
        if names is not None and len(names) != len(genres):
            raise ValueError(
                "One name is needed for each genre. "
                f"Got {len(names)} names and {len(genres)} genres."
            )
        if names is None:
            names = genres
        self._names_ref = {k: v for k, v in zip(names, genres)}
        self._genres_ref = {v: k for k, v in self._names_ref.items()}

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


class EnergiesChoice(GenresChoice):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent=parent,
            genres="ten ent gib scf zpe".split(),
            names="Thermal Enthalpy Gibbs SCF Zero-Point".split(),
            **kwargs,
        )


class GeometriesChoice(GenresChoice):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent=parent,
            genres=["geometry", "input_geom", "optimized_geom"],
            names=["Last read", "Input", "Optimized"],
            **kwargs,
        )


class ConformersChoice(AutoComboboxBase):
    """Combobox that enables choice of conformer for spectra calculation."""

    def __init__(self, parent, spectra_var, **kwargs):
        super().__init__(parent, **kwargs)
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
