# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox

# LOGGER
from tkinter.filedialog import askdirectory

from tesliper import datawork as dw
from tesliper.glassware import ElectronicData, ScatteringData, VibrationalData

from ... import SpectralData
from .helpers import WgtStateChanger
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
        # TODO: add choice for corrections, stoichiometry, and imaginary
        style = kwargs.pop("style", "active.TFrame")
        super().__init__(master, style=style, **kwargs)
        self.genres = "ten ent gib scf zpe".split(" ")
        self.labels = "Thermal Enthalpy Gibbs SCF Zero-Point".split(" ")
        self.vars = [
            tk.BooleanVar(value=master.tesliper.conformers.has_genre(g))
            for g in self.genres
        ]
        self.checks = [
            ttk.Checkbutton(self, text=label, variable=var, style="active.TCheckbutton")
            for label, var in zip(self.labels, self.vars)
        ]
        for num, check in enumerate(self.checks):
            check.grid(column=0, row=num, padx=5, sticky="nws")
        for check, genre in zip(self.checks, self.genres):
            master.changer.register([check], needs_all_genres=[genre])
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
        defaults = set("dip rot vdip vrot transitions raman1 roa1".split())
        cols = 5
        for num, class_ in enumerate([VibrationalData, ElectronicData, ScatteringData]):
            name = class_.__name__[:-4] + " " + class_.__name__[-4:]
            sep = LabelSeparator(self, text=name, style="active.TFrame")
            sep.label.configure(style="active.TLabel")
            sep.grid(column=0, row=num * 2, sticky="news")
            frame = ttk.Frame(self, style="active.TFrame")
            frame.grid(column=0, row=num * 2 + 1, sticky="news")
            frame.columnconfigure(tuple(range(cols)), weight=1)
            associated_genres = class_.associated_genres
            if class_ is VibrationalData:
                # get rid of frequencies genre
                associated_genres = associated_genres[1:]
            if class_ is ElectronicData:
                # get rid of wavelengths genre, add transitions
                associated_genres = associated_genres[1:] + ("transitions",)
            for idx, genre in enumerate(associated_genres):
                val = genre in defaults and master.tesliper.conformers.has_genre(genre)
                var = tk.BooleanVar(value=val)
                self.vars[genre] = var
                cb = ttk.Checkbutton(
                    frame, text=genre, variable=var, style="active.TCheckbutton"
                )
                cb.grid(column=idx % cols, row=idx // cols, padx=(5, 0), sticky="news")
                master.changer.register([cb], needs_all_genres=[genre])

    def get_query(self):
        return [g for g, v in self.vars.items() if v.get()]


class SpectraDetails(ttk.Frame):
    def __init__(self, master, **kwargs):
        style = kwargs.pop("style", "active.TFrame")
        super().__init__(master, style=style, **kwargs)
        self.vars = {}
        spectra = "IR VCD UV ECD Raman ROA".split(" ")
        self.rowconfigure((0, 1, 2, 3, 4, 5), weight=1)
        calculations = master.master.winfo_toplevel().controls.calculate
        for idx, spc in enumerate(spectra):
            spectra_name = spc.lower()
            spectra_type = SpectralData.spectra_type_ref[spectra_name]
            default_params = master.tesliper.standard_parameters[spectra_type]
            last_used = {
                k: calculations.last_used_settings[spectra_name][k]
                for k in "start stop step width fitting".split(" ")
                if k in calculations.last_used_settings[spectra_name]
            }
            default = not last_used or last_used == default_params

            act_genre = dw.DEFAULT_ACTIVITIES[spectra_name]
            var = tk.BooleanVar(value=master.tesliper.conformers.has_genre(act_genre))
            self.vars[spc] = var
            cb = ttk.Checkbutton(
                self, text=spc, variable=var, style="active.TCheckbutton"
            )
            cb.grid(column=0, row=idx, padx=(5, 0), sticky="nws")
            master.changer.register([cb], needs_all_genres=[act_genre])
            text = "[user parameters]" if not default else "[default parameters]"
            label = ttk.Label(
                self, text=text if var.get() else "", style="active.TLabel"
            )
            label.grid(column=1, row=idx, padx=(5, 0), sticky="nws")
            cb.configure(
                command=lambda t=text, w=label, v=var: w.configure(
                    text=t if v.get() else ""
                )
            )

    def get_query(self):
        return [g for g, v in self.vars.items() if v.get()]


class AveragedDetails(ttk.Frame):
    def __init__(self, master, **kwargs):
        style = kwargs.pop("style", "active.TFrame")
        super().__init__(master, style=style, **kwargs)
        self.columnconfigure((1, 2, 3, 4, 5), weight=1)
        self.rowconfigure((1, 2, 3, 4, 5, 6), weight=1)
        self.vars = {}
        self.checks = {}
        self.alls = {}
        spectra = "IR VCD UV ECD Raman ROA".split(" ")
        energy_names = "Thermal Enthalpy Gibbs SCF Zero-Point".split(" ")
        energy_genres = "ten ent gib scf zpe".split(" ")

        # for checking default values
        has_it = {en: master.tesliper.conformers.has_genre(en) for en in energy_genres}
        for spectra_name in (s.lower() for s in spectra):
            act_genre = dw.DEFAULT_ACTIVITIES[spectra_name]
            has_it[spectra_name] = master.tesliper.conformers.has_genre(act_genre)

        # labels and checkboxes
        for col, energy in enumerate(energy_names):
            ttk.Label(
                self, text=energy, style="active.TLabel", width=9, anchor="center"
            ).grid(column=1 + col, row=0, pady=(3, 0), sticky="news")
        for row, spc in enumerate(spectra):
            ttk.Label(self, text=spc, style="active.TLabel").grid(
                column=0, row=1 + row, pady=(3, 0), sticky="news"
            )
            for col, en in enumerate(energy_genres):
                label = (spc.lower(), en)
                var = tk.BooleanVar(value=has_it[spc.lower()] and has_it[en])
                cb = ttk.Checkbutton(
                    self,
                    style="checkbox.active.TCheckbutton",
                    variable=var,
                    command=lambda label=label: self.single_clicked(label),
                )
                cb.grid(column=1 + col, row=1 + row)
                act_genre = dw.DEFAULT_ACTIVITIES[spc.lower()]
                master.changer.register([cb], needs_all_genres=[act_genre, en])
                self.vars[label] = var
                self.checks[label] = cb

        # buttons for select/disselect all in row/column
        for row, spc in enumerate(s.lower() for s in spectra):
            cb = ttk.Checkbutton(self, style="checkbox.active.TCheckbutton")
            cb.configure(command=lambda cb=cb, idx=spc: self.all_clicked(cb, idx))
            cb.grid(column=6, row=1 + row)
            act_genre = dw.DEFAULT_ACTIVITIES[spc]
            master.changer.register([cb], needs_all_genres=[act_genre])
            self.alls[spc] = cb
        for col, en in enumerate(energy_genres):
            cb = ttk.Checkbutton(self, style="checkbox.active.TCheckbutton")
            cb.configure(command=lambda cb=cb, idx=en: self.all_clicked(cb, idx))
            cb.grid(column=1 + col, row=7)
            master.changer.register([cb], needs_all_genres=[en])
            self.alls[en] = cb
        ttk.Label(
            self, text="All", style="active.TLabel", width=9, anchor="center"
        ).grid(column=col + 2, row=0, pady=(3, 0), sticky="news")
        ttk.Label(self, text="All", style="active.TLabel").grid(
            column=0, row=row + 2, pady=(3, 0), sticky="news"
        )

    def all_clicked(self, cb, idx):
        for key, var in self.vars.items():
            if idx in key:
                theother = tuple(set(key) - set([idx]))[0]
                var.set(
                    # never set disabled checkbox as "selected"
                    str(self.checks[key]["state"]) != "disabled"
                    and cb.instate(["selected"])
                )
                self.set_all_box(theother)

    def set_all_box(self, idx):
        vals = [
            v.get()
            for k, v in self.vars.items()
            # ignore disabled checkboxes
            if idx in k and str(self.checks[k]["state"]) != "disabled"
        ]
        all_same = all(vals[0] == val for val in vals[1:])
        if vals and all(vals):
            self.alls[idx].state(["!alternate", "selected"])
        elif not all_same:
            self.alls[idx].state(["alternate", "!selected"])
        else:
            self.alls[idx].state(["!alternate", "!selected"])

    def update_all_boxes(self):
        # should be called after updating states of checkboxes
        for idx in self.alls:
            self.set_all_box(idx)

    def single_clicked(self, label):
        for idx in label:
            self.set_all_box(idx)

    def get_query(self):
        return [(s, e) for (s, e), v in self.vars.items() if v.get()]


class ExportPopup(Popup):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Export...")
        root = master.winfo_toplevel()
        self.tesliper = root.tesliper
        self.changer = WgtStateChanger(root)
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
        self.checks = []
        self.details = []

        details_frames_class = {
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
        for n, (label, var) in enumerate(zip(self.labels, self.vars)):
            tab = ttk.Frame(self, style="TabLike.TFrame")
            tab.grid(column=0, row=n + 1, sticky="news")
            check = ttk.Checkbutton(tab, text=label, variable=var)
            check.grid(column=0, row=0, pady=10, padx=5, sticky="w")
            self.checks.append(check)
            details = details_frames_class[label](self)
            details.grid(column=1, row=1, rowspan=4, sticky="news")
            details.grid_remove()
            kwargs = {"tab": tab, "checkbox": check, "details": details}
            tab.bind("<Enter>", lambda _e, kw=kwargs: self.on_tab_enter(**kw))
            tab.bind("<Leave>", lambda _e, kw=kwargs: self.on_tab_leave(**kw))
            details.bind("<Leave>", lambda _e, kw=kwargs: self.on_tab_leave(**kw))
            self.details.append(details)

        self.details_frame = ttk.Frame(self)
        self.details_frame.grid(column=1, row=1, rowspan=4, sticky="news")
        self.details_frame.columnconfigure(0, weight=1)
        self.details_frame.rowconfigure(0, weight=1)
        ttk.Label(
            self.details_frame, text="Hover over the left side\nto see details."
        ).grid(column=0, row=0)

        self.changer.register(self.checks[0], dependencies="energies")
        self.changer.register(self.checks[1:], dependencies="bars")
        self.changer.set_states()
        self.details[-1].update_all_boxes()
        self.protocol("WM_DELETE_WINDOW", self.cancel_command)
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(column=0, row=5, pady=2, columnspan=2, sticky="se")
        b_cancel = ttk.Button(buttons_frame, text="Cancel", command=self.cancel_command)
        b_cancel.grid(column=0, row=0, sticky="se")
        b_ok = ttk.Button(buttons_frame, text="OK", command=self.ok_command)
        b_ok.grid(column=1, row=0, padx=5, sticky="se")
        self.query = {}

    def on_tab_enter(self, tab, checkbox, details):
        if str(checkbox["state"]) == tk.DISABLED:
            return
        tab.configure(style="active.TFrame")
        checkbox.configure(style="active.TCheckbutton")
        self.details_frame.grid_remove()
        details.grid()

    def on_tab_leave(self, tab, checkbox, details):
        under_mouse = self.winfo_containing(*self.winfo_pointerxy())
        logger.debug(f"Currently under pointer: {under_mouse}")
        if str(under_mouse).startswith((str(tab), str(details))):
            return
        tab.configure(style="TFrame")
        checkbox.configure(style="TCheckbutton")
        details.grid_remove()
        self.details_frame.grid()

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
        self.query["query"] = {
            thing.lower(): details.get_query()
            for thing, var, details in zip(self.labels, self.vars, self.details)
            if var.get()
        }
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
