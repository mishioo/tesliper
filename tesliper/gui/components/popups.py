# IMPORTS
import logging as lgg
import re
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox

# LOGGER
from tkinter.filedialog import askdirectory

from tesliper import datawork as dw
from tesliper.glassware import (
    ElectronicActivities,
    ElectronicData,
    ScatteringActivities,
    ScatteringData,
    SpectralActivities,
    VibrationalActivities,
    VibrationalData,
)

from . import CollapsiblePane
from .choices import GeometriesChoice
from .helpers import WgtStateChanger
from .hinted_entry import HintedEntry
from .label_separator import LabelSeparator
from .numeric_entry import IntegerEntry

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
        defaults = set("dip rot vdip vrot transitions raman1 roa1".split())
        cols = 3
        classes = [
            VibrationalActivities,
            VibrationalData,
            ElectronicActivities,
            ElectronicData,
            ScatteringActivities,
            ScatteringData,
        ]
        frames = dict()
        transitions_names = {
            "transitions": "Highest contrib. transitions",
            "transitions-all": "All transitions",
        }
        for num, class_ in enumerate(classes):
            name = re.findall("[A-Z][^A-Z]*", class_.__name__)[0] + " Data"
            if name not in frames:
                sep = LabelSeparator(self, text=name, style="active.TFrame")
                sep.label.configure(style="active.TLabel")
                sep.grid(column=0, row=num * 2, sticky="news")
                frame = ttk.Frame(self, style="active.TFrame")
                frame.grid(column=0, row=num * 2 + 1, sticky="news")
                frame.columnconfigure(tuple(range(cols)), weight=1)
                last_idx = 0
            else:
                frame, last_idx = frames[name]
            associated_genres = class_.associated_genres
            if class_ is ElectronicActivities:
                # add transitions
                associated_genres = associated_genres + tuple(transitions_names)
            for idx_, genre in enumerate(associated_genres):
                if genre in transitions_names:
                    full_name = transitions_names[genre]
                else:
                    try:
                        full_name = class_._full_name_ref[genre]
                    except KeyError:
                        full_name = genre

                idx = last_idx + idx_
                val = genre in defaults and master.tesliper.conformers.has_genre(genre)
                var = tk.BooleanVar(value=val)
                self.vars[genre] = var
                cb = ttk.Checkbutton(
                    frame,
                    text=full_name,
                    variable=var,
                    style="active.TCheckbutton",
                    width=30,
                )
                cb.grid(column=idx % cols, row=idx // cols, padx=(5, 0), sticky="news")
                genre_needed = "transitions" if genre == "transitions-all" else genre
                master.changer.register([cb], needs_all_genres=[genre_needed])
            try:
                frames[name] = frame, idx + 1
            except NameError:
                frames[name] = frame, last_idx
        for frame, idx in frames.values():
            self.rowconfigure(frame.grid_info()["row"], weight=idx)

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
            default_params = master.tesliper.standard_parameters[spectra_name]
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


class LinkZero(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        tip_text = (
            "Tip: you may use ${conf} placeholder in path specification to get "
            "a conformer's name or ${num} to get a sequential number."
        )
        self.tip = ttk.Label(
            self, text=tip_text, wraplength=400, justify="left", foreground="gray"
        )

        self.descriptions = {
            "Mem": "amount of dynamic memory used",
            "Chk": "path to the checkpoint file",
            "OldChk": "path to the previous checkpoint file",
            "SChk": "path to which checkpoint file is copied on job step start",
            "RWF": "path to the read-write file",
            "OldMatrix": "path to the unformatted binary matrix element file",
            "OldRawMatrix": "path to the raw binary matrix element file",
            "Int": "path to the two-electron integral file(s)",
            "D2E": "path to the two-electron integral derivative file(s)",
            "KJob": "link number and, optionally, space-separated number",
            "Save": "empty for false, anything else for true",
            "ErrorSave": "aka 'NoSave', empty for false, anything else for true",
            "Subst": "link number and space-separated file path",
        }
        self.command = tk.StringVar()
        self.command_checkbox = ttk.Combobox(
            self,
            textvariable=self.command,
            state="readonly",
            values=list(self.descriptions.keys()),
            width=13,
        )
        self.command_checkbox.bind("<<ComboboxSelected>>", self.combobox_selected)
        self.value = HintedEntry(
            self, hint="← select a link0 command", state="readonly"
        )
        self.value.bind("<Return>", self.add)
        self.add_button = ttk.Button(
            self, text="+", command=self.add, state="disabled", width=1
        )
        self.items_frame = ttk.Frame(self)
        self.items = {}

        self.columnconfigure(1, weight=1)
        self.tip.grid(column=0, row=0, columnspan=3, sticky="ew")
        self.command_checkbox.grid(column=0, row=1, sticky="ew")
        self.value.grid(column=1, row=1, sticky="ew")
        self.add_button.grid(column=2, row=1, sticky="ew")
        self.items_frame.grid(column=0, row=2, columnspan=3, sticky="news")
        self.items_frame.columnconfigure(1, weight=1)

    def edit(self, item, value):
        self.items[item]["value"].configure(text=value)

    def add(self, _event=None):
        item = self.command.get()
        value = self.value.get()
        if item in self.items:
            return self.edit(item, value)
        idx = len(self.items)
        self.items[item] = {
            "command": ttk.Label(self.items_frame, text=item, width=13),
            "value": ttk.Label(self.items_frame, text=value, anchor="e"),
            "button": ttk.Button(
                self.items_frame,
                text="-",
                command=lambda i=item: self.remove(i),
                width=1,
            ),
        }
        self.items[item]["command"].grid(column=0, row=idx, sticky="ew")
        self.items[item]["value"].grid(column=1, row=idx, sticky="ew")
        self.items[item]["button"].grid(column=2, row=idx, sticky="ew")

    def remove(self, item):
        for widget in self.items[item].values():
            widget.grid_forget()
            widget.destroy()
        del self.items[item]

    def combobox_selected(self, _event=None):
        self.add_button.configure(state="normal")
        self.value.configure(state="normal")
        item = self.command.get()
        if item in self.items:
            self.value.set(self.items[item]["value"]["text"])
        else:
            self.value.configure(hint=self.descriptions[item])
            self.value.set("")

    def get_query(self):
        return {key: value["value"].cget("text") for key, value in self.items.items()}


class GjfPopup(Popup):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Create .gjf files...")
        root = master.winfo_toplevel()
        self.tesliper = root.tesliper
        self.changer = WgtStateChanger(root)
        self.query = {}

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

        frame = ttk.Frame(self)
        frame.grid(column=0, row=1, columnspan=2, pady=3, sticky="new")
        # geometry genre selection
        ttk.Label(frame, text="Geometry type").grid(
            column=0, row=0, padx=5, sticky="new"
        )
        self.geom_combobox = GeometriesChoice(frame)
        self.geom_combobox.grid(column=1, row=0, padx=(0, 5), sticky="new")
        self.geom_combobox.update_values()
        # charge and multiplicity
        ttk.Label(frame, text="Multiplicity").grid(
            column=2, row=0, padx=(0, 5), sticky="new"
        )
        self.multiplicity = tk.StringVar(value="1")
        self.multiplicity_entry = IntegerEntry(
            frame, textvariable=self.multiplicity, width=4
        )
        self.multiplicity_entry.grid(column=3, row=0, padx=(0, 5), sticky="new")
        ttk.Label(frame, text="Charge").grid(column=4, row=0, padx=(0, 5), sticky="new")
        self.charge = tk.StringVar(value="0")
        self.charge_entry = IntegerEntry(frame, textvariable=self.charge, width=4)
        self.charge_entry.grid(column=5, row=0, padx=(0, 5), sticky="new")

        # job route entry
        ttk.Label(self, text="Route").grid(column=0, row=2, padx=5, sticky="new")
        self.job = HintedEntry(self, hint="Calculations specification")
        self.job.grid(column=1, row=2, padx=(0, 5), sticky="new")

        # comment / job description
        ttk.Label(self, text="Comment").grid(column=0, row=3, padx=5, sticky="new")
        self.comment = HintedEntry(self, hint="Short description, optional")
        self.comment.grid(column=1, row=3, padx=(0, 5), sticky="new")

        # link0 commands
        pane = CollapsiblePane(self, text="Link0 commands", collapsed=True)
        pane.grid(column=0, row=4, columnspan=2, padx=5, pady=3, sticky="new")
        pane.content.columnconfigure(0, weight=1)
        pane.content.rowconfigure(0, weight=1)
        self.link_zero = LinkZero(pane.content)
        self.link_zero.grid(column=0, row=0, sticky="news")

        # after-geometry specifications
        pane = CollapsiblePane(
            self, text="Post-geometry specifications", collapsed=True
        )
        pane.grid(column=0, row=5, columnspan=2, padx=5, pady=3, sticky="news")
        pane.content.columnconfigure(0, weight=1)
        pane.content.rowconfigure(0, weight=1)
        # post_spec width controlled by grid manager, hence 0 below
        self.post_spec = tk.Text(pane.content, height=4, width=0)
        self.post_spec.grid(column=0, row=0, sticky="news")
        self.rowconfigure(5, weight=1)

        # ok / cancel buttons
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(column=0, row=6, pady=2, columnspan=2, sticky="se")
        b_cancel = ttk.Button(buttons_frame, text="Cancel", command=self.cancel_command)
        b_cancel.grid(column=0, row=0, sticky="se")
        b_ok = ttk.Button(buttons_frame, text="OK", command=self.ok_command)
        b_ok.grid(column=1, row=0, padx=5, sticky="se")

    def _browse(self):
        directory = askdirectory()
        if not directory:
            return
        self.path.set(directory)

    def ok_command(self):
        self.query["init"] = {
            "destination": self.path.get(),
            "link0": self.link_zero.get_query(),
            "route": self.job.get(),
            "comment": self.comment.get() or "No information provided.",
            "post_spec": self.post_spec.get("1.0", "end"),  # Tk.Text instance
        }
        self.query["call"] = {
            "geometry": self.tesliper[self.geom_combobox.get_genre()],
            "charge": int(self.charge.get()),
            "multiplicity": int(self.multiplicity.get()),
        }
        self.destroy()

    def cancel_command(self):
        self.query = {}
        self.destroy()

    def get_query(self):
        self.wait_window()
        logger.debug(f"Request: {self.query}")
        return self.query
