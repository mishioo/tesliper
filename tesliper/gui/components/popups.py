# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox

# LOGGER
from tkinter.filedialog import askdirectory

from tesliper.glassware import ElectronicData, ScatteringData, VibrationalData

from .label_separator import LabelSeparator

logger = lgg.getLogger(__name__)


def not_implemented_popup():
    messagebox.showinfo(
        "Sorry!", "We are sorry, but this function is not implemented yet."
    )


# CLASSES
class Popup(tk.Toplevel):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.master = master
        self.grab_set()
        try:
            width, height = kwargs["width"], kwargs["height"]
            self.set_geometry(width, height)
        except KeyError:
            pass

    def set_geometry(self, width, height):
        x = self.master.winfo_pointerx()
        y = self.master.winfo_pointery()
        geometry = "{}x{}{:+n}{:+n}".format(width, height, x, y)
        self.geometry(geometry)


class EnergiesDetails(ttk.Frame):
    def __init__(self, master, **kwargs):
        style = kwargs.pop("style", "active.TFrame")
        super().__init__(master, style=style, **kwargs)
        self.genres = "ten ent gib scf zpe".split(" ")
        self.labels = "Thermal Enthalpy Gibbs SCF Zero-Point".split(" ")
        self.vars = [tk.BooleanVar() for _ in self.labels]
        self.checks = [
            ttk.Checkbutton(self, text=label, variable=var, style="active.TCheckbutton")
            for label, var in zip(self.labels, self.vars)
        ]
        for num, check in enumerate(self.checks):
            check.grid(column=0, row=num, padx=5, sticky="nws")
        self.rowconfigure((0, 1, 2, 3, 4), weight=1)

    def get_query(self):
        return [g for g, v in zip(self.genres, self.vars) if v.get()]


class SpectralDataDetails(ttk.Frame):
    def __init__(self, master, **kwargs):
        style = kwargs.pop("style", "active.TFrame")
        super().__init__(master, style=style, **kwargs)
        self.vars = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure((1, 3, 5), weight=1)
        cols = 5
        for num, class_ in enumerate([VibrationalData, ElectronicData, ScatteringData]):
            name = class_.__name__[:-4] + " " + class_.__name__[-4:]
            sep = LabelSeparator(self, text=name, style="active.TFrame")
            sep.label.configure(style="active.TLabel")
            sep.grid(column=0, row=num * 2, sticky="news")
            frame = ttk.Frame(self, style="active.TFrame")
            frame.grid(column=0, row=num * 2 + 1, sticky="news")
            frame.columnconfigure(tuple(range(cols)), weight=1)
            for idx, genre in enumerate(class_.associated_genres):
                var = tk.BooleanVar()
                self.vars[genre] = var
                ttk.Checkbutton(
                    frame, text=genre, variable=var, style="active.TCheckbutton"
                ).grid(column=idx % cols, row=idx // cols, sticky="news")

    def get_query(self):
        return [g for g, v in self.vars.items() if v.get()]


class SpectraDetails(ttk.Frame):
    def __init__(self, master, **kwargs):
        style = kwargs.pop("style", "active.TFrame")
        super().__init__(master, style=style, **kwargs)


class AveragedDetails(ttk.Frame):
    def __init__(self, master, **kwargs):
        style = kwargs.pop("style", "active.TFrame")
        super().__init__(master, style=style, **kwargs)
        self.columnconfigure((1, 2, 3, 4, 5), weight=1)
        self.rowconfigure((1, 2, 3, 4, 5, 6), weight=1)
        self.vars = {}
        spectra = "IR VCD UV ECD Raman ROA".split(" ")
        energies = "Thermal Enthalpy Gibbs SCF Zero-Point".split(" ")
        energy_genres = "ten ent gib scf zpe".split(" ")
        for col, energy in enumerate(energies):
            ttk.Label(
                self, text=energy, style="active.TLabel", width=9, anchor="center"
            ).grid(column=1 + col, row=0, pady=(3, 0), sticky="news")
        for row, spc in enumerate(spectra):
            ttk.Label(self, text=spc, style="active.TLabel").grid(
                column=0, row=1 + row, pady=(3, 0), sticky="news"
            )
            for col, en in enumerate(energy_genres):
                var = tk.BooleanVar()
                cb = ttk.Checkbutton(
                    self, style="checkbox.active.TCheckbutton", variable=var
                )
                cb.grid(column=1 + col, row=1 + row)
                self.vars[(spc.lower(), en)] = var

    def get_query(self):
        return [(s, e) for (s, e), v in self.vars.items() if v.get()]


class ExportPopup(Popup):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Export...")
        self.tesliper = master.winfo_toplevel().tesliper
        self.rowconfigure((1, 2, 3, 4), weight=1)
        self.columnconfigure(1, weight=1)

        path_frame = ttk.Frame(self)
        path_frame.grid(column=0, row=0, columnspan=2, sticky="new")
        path_frame.columnconfigure(1, weight=1)
        ttk.Label(path_frame, text="Path").grid(
            column=0, row=0, padx=5, pady=3, sticky="new"
        )
        self.path = tk.StringVar()
        self.path.set(str(self.tesliper.output_dir))
        self.path_entry = ttk.Entry(
            path_frame, textvariable=self.path, state="readonly"
        )
        self.path_entry.grid(column=1, row=0, sticky="ew")
        self.browse = ttk.Button(path_frame, text="Browse", command=self._browse)
        self.browse.grid(column=2, row=0, sticky="we", padx=5)

        self.labels = ["Energies", "Spectral data", "Spectra", "Averaged"]
        self.vars = [tk.BooleanVar() for _ in self.labels]

        details_frames = {
            "Energies": EnergiesDetails,
            "Spectral data": SpectralDataDetails,
            "Spectra": SpectraDetails,
            "Averaged": AveragedDetails,
        }
        style = ttk.Style()
        active_color = "ghost white"
        style.configure("active.TFrame", background=active_color)
        style.configure("active.TCheckbutton", background=active_color)
        style.configure("active.TLabel", background=active_color)
        style.layout(
            "checkbox.active.TCheckbutton",
            [("Checkbutton.indicator", {"side": "left", "sticky": ""})],
        )
        checks = []
        for n, (label, var) in enumerate(zip(self.labels, self.vars)):
            tab = ttk.Frame(self, style="TabLike.TFrame")
            tab.grid(column=0, row=n + 1, sticky="news")
            check = ttk.Checkbutton(tab, text=label, variable=var)
            check.grid(column=0, row=0, pady=10, padx=5, sticky="w")
            checks.append(check)
            tab.check = check
            details = details_frames[label](self)
            details.grid(column=1, row=1, rowspan=4, sticky="news")
            details.grid_remove()
            kwargs = {"tab": tab, "checkbox": check, "details": details}
            tab.bind("<Enter>", lambda _e, kw=kwargs: self.on_tab_enter(**kw))
            tab.bind("<Leave>", lambda _e, kw=kwargs: self.on_tab_leave(**kw))
            details.bind("<Leave>", lambda _e, kw=kwargs: self.on_tab_leave(**kw))
            tab.details = details

        self.details = ttk.Frame(self)
        self.details.grid(column=1, row=1, rowspan=4, sticky="news")
        self.details.columnconfigure(0, weight=1)
        self.details.rowconfigure(0, weight=1)
        ttk.Label(self.details, text="Hover over the left side\nto see details.").grid(
            column=0, row=0
        )

        checks[0].configure(state="normal" if self.tesliper.energies else "disabled")
        checks[1].configure(state="normal" if self.tesliper.activities else "disabled")
        checks[2].configure(state="normal" if self.tesliper.spectra else "disabled")
        checks[3].configure(state="normal" if self.tesliper.spectra else "disabled")
        self.vars[0].set(True if self.tesliper.energies else False)
        self.vars[1].set(True if self.tesliper.activities else False)
        self.vars[2].set(True if self.tesliper.spectra else False)
        self.vars[3].set(True if self.tesliper.spectra else False)
        self.protocol("WM_DELETE_WINDOW", self.cancel_command)
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(column=0, row=5, pady=2, columnspan=2, sticky="se")
        b_cancel = ttk.Button(buttons_frame, text="Cancel", command=self.cancel_command)
        b_cancel.grid(column=0, row=0, sticky="se")
        b_ok = ttk.Button(buttons_frame, text="OK", command=self.ok_command)
        b_ok.grid(column=1, row=0, padx=5, sticky="se")
        self.query = {}

    def on_tab_enter(self, tab, checkbox, details):
        if str(tab.check["state"]) == tk.DISABLED:
            return
        tab.configure(style="active.TFrame")
        checkbox.configure(style="active.TCheckbutton")
        self.details.grid_remove()
        details.grid()

    def on_tab_leave(self, tab, checkbox, details):
        under_mouse = self.winfo_containing(*self.winfo_pointerxy())
        logger.debug(f"Currently under pointer: {under_mouse}")
        if str(under_mouse).startswith((str(tab), str(details))):
            return
        tab.configure(style="TFrame")
        checkbox.configure(style="TCheckbutton")
        details.grid_remove()
        self.details.grid()

    def _browse(self):
        directory = askdirectory()
        if not directory:
            return
        self.path.set(directory)

    def ok_command(self):
        vals = [v.get() for v in self.vars]
        logger.debug(vals)
        if any(vals):
            self.destroy()
        else:
            messagebox.showinfo(
                "Nothing choosen!", "You must chose what you want to extract."
            )
            self.focus_set()

    def cancel_command(self):
        self.query = None
        self.destroy()

    def get_query(self):
        self.wait_window()
        if self.query is None:
            return {}
        self.query["dest"] = self.path.get()
        self.query["query"] = [
            thing.lower() for thing, var in zip(self.labels, self.vars) if var.get()
        ]
        logger.debug(self.query)
        return self.query


class BarsPopup(Popup):
    bar_names = (
        "IR Inten.,E-M Angle,Dip. Str.,Rot. Str.,Osc. Str. (velo),"
        "Rot. Str. (velo),Osc. Str. (length),Rot. Str. (length),"
        "Raman1,ROA1".split(",")
    )
    bar_keys = "iri emang dip rot vosc vrot losc lrot raman1 roa1".split(" ")

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Data extraction")
        tk.Grid.rowconfigure(self, 6, weight=1)
        tk.Grid.columnconfigure(self, 2, weight=1)
        ttk.Label(self, text="Chose spectral data you wish to extract:").grid(
            column=0, row=0, columnspan=2, sticky="w", padx=5, pady=5
        )
        positions = [(c, r) for r in range(1, 6) for c in range(2)]
        self.vars = [tk.BooleanVar() for _ in self.bar_keys]
        for v, k, n, (c, r) in zip(self.vars, self.bar_keys, self.bar_names, positions):
            b = ttk.Checkbutton(self, text=n, variable=v)
            b.grid(column=c, row=r, sticky="w", pady=2, padx=5)
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(column=0, row=6, columnspan=3, sticky="se", pady=5)
        tk.Grid.rowconfigure(buttons_frame, 0, weight=1)
        tk.Grid.columnconfigure(buttons_frame, 0, weight=1)
        b_cancel = ttk.Button(buttons_frame, text="Cancel", command=self.cancel_command)
        b_cancel.grid(column=0, row=0, sticky="se")
        b_ok = ttk.Button(buttons_frame, text="OK", command=self.ok_command)
        b_ok.grid(column=1, row=0, sticky="se", padx=5)

    def ok_command(self):
        vals = [v.get() for v in self.vars]
        query = [b for b, v in zip(self.bar_keys, vals) if v]
        if query:
            self.destroy()
            self.master.execute_extract_bars(query)
        else:
            messagebox.showinfo(
                "Nothing choosen!", "You must chose which data you want to extract."
            )
            self.focus_set()

    def cancel_command(self):
        self.destroy()
