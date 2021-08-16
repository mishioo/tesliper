# IMPORTS
import logging as lgg
import os
import tkinter as tk
import tkinter.ttk as ttk
from collections import Counter, namedtuple
from tkinter import messagebox
from tkinter.filedialog import askdirectory, askopenfilenames
from typing import List

import numpy as np

from . import components as guicom

# LOGGER
from .components import ScrollableFrame

logger = lgg.getLogger(__name__)


OVERVIEW_GENRES = "dip rot vosc vrot losc lrot raman1 roa1 scf zpe ent ten gib".split()


def join_with_and(words: List[str]) -> str:
    """Joins list of strings with "and" between the last two."""
    if len(words) > 2:
        return ", ".join(words[:-1]) + ", and " + words[-1]
    elif len(words) == 2:
        return " and ".join(words)
    elif len(words) == 1:
        return words[0]
    else:
        return ""


# CLASSES
class Loader(ttk.Frame):
    def __init__(self, parent):
        """
        TO DO
        -----
        don't allow energy extraction if already extracted
        """
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky="nwse")
        tk.Grid.columnconfigure(self, 1, weight=1)
        tk.Grid.rowconfigure(self, 0, weight=1)
        self.bind("<FocusIn>", lambda e: self.update_overview_values())

        # Controls frame
        # ScrollableFrame.content is a ttk.Frame where actual controls go
        controls = ScrollableFrame(parent=self)
        controls.grid(column=0, row=0, sticky="news")

        # Extract data
        extract_frame = ttk.LabelFrame(controls.content, text="Extract data...")
        extract_frame.grid(column=0, row=0, columnspan=2, sticky="nwe")
        tk.Grid.columnconfigure(extract_frame, 0, weight=1)
        self.b_auto_extract = ttk.Button(
            extract_frame, text="Choose folder", command=self.from_dir
        )
        self.b_auto_extract.grid(column=0, row=0, sticky="nwe")
        self.b_man_extract = ttk.Button(
            extract_frame, text="Choose files", command=self.man_extract
        )
        self.b_man_extract.grid(column=0, row=1, sticky="nwe")

        # Session control
        buttons_frame = ttk.LabelFrame(
            controls.content, text="Session control", width=90
        )
        buttons_frame.grid(column=0, row=1, columnspan=2, sticky="nwe")
        tk.Grid.columnconfigure(buttons_frame, (0, 1), weight=1)
        self.b_clear_session = ttk.Button(
            buttons_frame, text="Clear session", command=self.parent.new_session
        )
        self.b_clear_session.grid(column=0, row=2, sticky="nwe")
        guicom.WgtStateChanger.either.append(self.b_clear_session)

        self.b_calc = ttk.Button(
            buttons_frame, text="Auto calculate", command=self.not_impl
        )
        self.b_calc.grid(column=0, row=0, sticky="nwe")
        guicom.WgtStateChanger.bars.append(self.b_calc)

        self.b_text_export = ttk.Button(
            buttons_frame, text="Export as .txt", command=self.save_text
        )
        self.b_text_export.grid(column=1, row=0, sticky="nwe")
        self.b_excel_export = ttk.Button(
            buttons_frame, text="Export as .xls", command=self.save_excel
        )
        self.b_excel_export.grid(column=1, row=1, sticky="nwe")
        self.b_csv_export = ttk.Button(
            buttons_frame, text="Export as .csv", command=self.save_csv
        )
        self.b_csv_export.grid(column=1, row=2, sticky="nwe")
        guicom.WgtStateChanger.either.extend(
            [self.b_text_export, self.b_excel_export, self.b_csv_export]
        )

        # Overview control
        # TO DO: consider switching to three buttons: 'include', 'exclude',
        # 'limit to', or similar
        self.overview_control_frame = ttk.Labelframe(
            controls.content, text="Overview control", width=90
        )
        self.overview_control_frame.grid(column=0, row=2, columnspan=2, sticky="nswe")
        tk.Grid.columnconfigure(self.overview_control_frame, 4, weight=1)
        overview_vars = namedtuple("overview", ["kept", "all", "check", "uncheck"])
        self.overview_control_ref = {
            k: v
            for k, v in zip(
                "file en ir vcd uv ecd ram roa incompl term opt " "imag".split(" "),
                "command gib dip rot vosc vrot raman1 roa1 command "
                "normal_termination optimization_completed freq".split(" "),
            )
        }
        self.overview_control = dict()
        for i, (name, key) in enumerate(
            zip(
                "Files Energy IR VCD UV ECD Raman ROA Incompl. Errors "
                "Unopt. Imag.Freq. Incons.".split(),
                "file en ir vcd uv ecd ram roa incompl term " "opt imag incons".split(),
            )
        ):
            tk.Label(self.overview_control_frame, text=name, anchor="w").grid(
                column=0, row=i
            )
            var_checked = tk.IntVar(value=0)
            tk.Label(
                self.overview_control_frame, textvariable=var_checked, bd=0, width=3
            ).grid(column=1, row=i)
            tk.Label(self.overview_control_frame, text="/", bd=0).grid(column=2, row=i)
            var_all = tk.IntVar(value=0)
            tk.Label(
                self.overview_control_frame, textvariable=var_all, bd=0, width=3
            ).grid(column=3, row=i)
            check_butt = ttk.Button(
                self.overview_control_frame,
                text="check",
                width=6,
                command=lambda key=key: self.un_check(key, True),
            )
            check_butt.grid(column=4, row=i, sticky="ne")
            guicom.WgtStateChanger.tslr.append(check_butt)
            uncheck_butt = ttk.Button(
                self.overview_control_frame,
                text="uncheck",
                width=8,
                command=lambda key=key: self.un_check(key, False),
            )
            uncheck_butt.grid(column=5, row=i, sticky="ne")
            guicom.WgtStateChanger.tslr.append(uncheck_butt)
            self.overview_control[key] = overview_vars(
                var_checked, var_all, check_butt, uncheck_butt
            )

        # keep unchecked
        self.keep_unchecked_frame = ttk.LabelFrame(
            controls.content, text="Keep unchecked?"
        )
        self.keep_unchecked_frame.grid(column=0, row=3, columnspan=2, sticky="nswe")
        self.kept_vars = {
            k: tk.BooleanVar()
            for k in "error unopt imag stoich incompl incons".split(" ")
        }
        self.kept_buttons = {
            k: ttk.Checkbutton(
                self.keep_unchecked_frame,
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

        # Conformers Overview
        self.label_overview = ttk.LabelFrame(self, text="Conformers Overview")
        self.label_overview.grid(column=1, row=0, sticky="nwse")
        self.overview = None
        tk.Grid.rowconfigure(self.label_overview, 0, weight=1)
        tk.Grid.columnconfigure(self.label_overview, 0, weight=1)

    def un_check(self, key, keep):
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
            imag=lambda *args: "freq" in args[0]
            and any([f < 0 for f in args[0]["freq"]]),
            incons=lambda *args: any(
                g in args[0] and not len(args[0][g]) == mx for g, mx in args[2].items()
            ),
        )
        confs = self.parent.tslr.conformers
        condition = overview_funcs[key]
        overview = self.overview
        best_match = []
        maxes = {}
        if key == "incompl":
            try:
                count = [
                    [g in conf for g in OVERVIEW_GENRES]
                    for conf in self.parent.tslr.conformers.values()
                ]
                best_match = [g for g, k in zip(OVERVIEW_GENRES, max(count)) if k]
            except ValueError:
                best_match = []
        elif key == "incons":
            sizes = {}
            for fname, conf in self.parent.tslr.conformers.items():
                for genre, value in conf.items():
                    if isinstance(value, (np.ndarray, list, tuple)):
                        sizes.setdefault(genre, {})[fname] = len(value)
            maxes = {
                genre: Counter(v for v in values.values()).most_common()[0][0]
                for genre, values in sizes.items()
            }
        for n, conf in enumerate(confs.values()):
            if condition(conf, best_match, maxes):
                overview.boxes[str(n)].var.set(keep)
        self.discard_not_kept()
        self.update_overview_values()

    @property
    def kept_funcs(self):
        return dict(
            error=self.parent.tslr.conformers.trim_non_normal_termination,
            unopt=self.parent.tslr.conformers.trim_not_optimized,
            imag=self.parent.tslr.conformers.trim_imaginary_frequencies,
            stoich=self.parent.tslr.conformers.trim_non_matching_stoichiometry,
            incompl=self.parent.tslr.conformers.trim_incomplete,
            incons=self.parent.tslr.conformers.trim_inconsistent_sizes,
        )

    def not_impl(self):
        messagebox.showinfo(
            "Sorry!", "We are sorry, but this function is not implemented yet."
        )

    def get_save_query(self):
        popup = guicom.ExportPopup(self, width="220", height="130")
        query = popup.get_query()
        return query

    @guicom.Feedback("Saving...")
    def execute_save_command(self, categories, fmt):
        # TODO: add auto-calculate ?
        if "averaged" in categories:
            self.parent.progtext.set("Averaging spectra...")
            self.parent.tslr.average_spectra()
            self.parent.progtext.set("Saving...")
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
            "energies": self.parent.tslr.export_energies,
            "spectral data": self.parent.tslr.export_spectral_data,
            "spectra": self.parent.tslr.export_spectra,
            "averaged": self.parent.tslr.export_averaged,
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

    def save(self, categories, fmt):
        dest = askdirectory()
        if dest:
            self.parent.tslr.output_dir = dest
            logger.debug(f"Export requested: {categories}; format: {fmt}")
            self.execute_save_command(categories, fmt)

    def save_text(self):
        categories = self.get_save_query()
        if not categories:
            return
        self.save(categories, fmt="txt")

    def save_excel(self):
        categories = self.get_save_query()
        if not categories:
            return
        self.save(categories, fmt="xlsx")

    def save_csv(self):
        categories = self.get_save_query()
        if not categories:
            return
        self.save(categories, fmt="csv")

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
        path = os.path.split(files[0])[0]
        filenames = list(map(lambda p: os.path.split(p)[1], files))
        self.extract(path, filenames)

    @guicom.Feedback("Extracting...")
    def extract(self, path, wanted_files=None):
        # TODO: handle extraction errors
        tslr = self.parent.tslr
        overview = self.overview
        try:
            for file, data in tslr.extract_iterate(path, wanted_files):
                overview.insert("", tk.END, text=file)
        except TypeError as err:
            logger.warning("Cannot extract from specified directory: " + err.args[0])
            return
        # self.parent.conf_tab.conf_list.refresh()
        # TODO: set_overview_values() and update_overview_values() seem to repeat some
        #       actions - confirm if true and refactor them
        self.set_overview_values()
        self.discard_not_kept()
        self.update_overview_values()

    def set_overview_values(self):
        values = {k: 0 for k in self.overview_control.keys()}
        try:
            count = [
                [g in conf for g in OVERVIEW_GENRES]
                for conf in self.parent.tslr.conformers.values()
            ]
            best_match = [g for g, k in zip(OVERVIEW_GENRES, max(count)) if k]
        except ValueError:
            best_match = []
        sizes = {}
        for fname, conf in self.parent.tslr.conformers.items():
            for genre, value in conf.items():
                if isinstance(value, (np.ndarray, list, tuple)):
                    sizes.setdefault(genre, {})[fname] = len(value)
        maxes = {
            genre: Counter(v for v in values.values()).most_common()[0][0]
            for genre, values in sizes.items()
        }
        for num, conf in enumerate(self.parent.tslr.conformers.values()):
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
        for key, value in values.items():
            self.overview_control[key][1].set(value)

    def update_overview_values(self):
        values = {k: 0 for k in self.overview_control.keys()}
        try:
            # TODO: extract this repeated snippet (un_check(), set_overview_values())
            count = [
                [g in conf for g in OVERVIEW_GENRES]
                for conf in self.parent.tslr.conformers.values()
            ]
            best_match = [g for g, k in zip(OVERVIEW_GENRES, max(count)) if k]
        except ValueError:
            best_match = []
        sizes = {}
        for fname, conf in self.parent.tslr.conformers.items():
            for genre, value in conf.items():
                if isinstance(value, (np.ndarray, list, tuple)):
                    sizes.setdefault(genre, {})[fname] = len(value)
        maxes = {
            genre: Counter(v for v in values.values()).most_common()[0][0]
            for genre, values in sizes.items()
        }
        for conf in self.parent.tslr.conformers.kept_values():
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
        for key, items in self.overview_control.items():
            items[0].set(values[key])

    def discard(self, key):
        if key == "incons":
            self.parent.tslr.conformers.allow_data_inconsistency = not self.kept_vars[
                key
            ].get()
        if self.kept_vars[key].get():
            self.kept_funcs[key]()
            for box, kept in zip(
                self.overview.boxes.values(), self.parent.tslr.conformers.kept
            ):
                box.var.set(kept)
        self.update_overview_values()

    def discard_not_kept(self):
        for key, var in self.kept_vars.items():
            if var.get():
                self.kept_funcs[key]()
        for box, kept in zip(
            self.overview.boxes.values(), self.parent.tslr.conformers.kept
        ):
            box.var.set(kept)

    @guicom.Feedback("Calculating populations...")
    def calc_popul(self):
        logger.debug("Calculating populations...")
        self.parent.tslr.calculate_populations()

    @guicom.Feedback("Calculating spectra...")
    def calc_spectra(self):
        self.parent.tslr.calculate_spectra()

    @guicom.Feedback("Averaging spectra...")
    def calc_average(self):
        self.parent.tslr.average_spectra()

    def get_wanted_bars(self):
        # TODO: check if needed, delete if it's not
        popup = guicom.BarsPopup(self, width="250", height="190")
        del popup
