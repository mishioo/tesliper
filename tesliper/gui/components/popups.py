# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox

# LOGGER
from tkinter.filedialog import askdirectory

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


class ExportPopup(Popup):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Export...")
        self.tesliper = master.winfo_toplevel().tesliper
        self.rowconfigure(4, weight=1)
        self.columnconfigure(0, weight=1)

        path_frame = ttk.Frame(self)
        path_frame.grid(column=0, row=0, sticky="new")
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
        checks = [
            ttk.Checkbutton(self, text=label, variable=var)
            for label, var in zip(self.labels, self.vars)
        ]
        for n, check in enumerate(checks):
            check.grid(column=0, row=n + 1, pady=2, padx=5, sticky="nw")
        tslr = master.winfo_toplevel().tesliper
        checks[0].configure(state="normal" if tslr.energies else "disabled")
        checks[1].configure(state="normal" if tslr.activities else "disabled")
        checks[2].configure(state="normal" if tslr.spectra else "disabled")
        checks[3].configure(state="normal" if tslr.spectra else "disabled")
        self.vars[0].set(True if tslr.energies else False)
        self.vars[1].set(True if tslr.activities else False)
        self.vars[2].set(True if tslr.spectra else False)
        self.vars[3].set(True if tslr.spectra else False)
        self.protocol("WM_DELETE_WINDOW", self.cancel_command)
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(column=0, row=5, pady=2, sticky="se")
        b_cancel = ttk.Button(buttons_frame, text="Cancel", command=self.cancel_command)
        b_cancel.grid(column=0, row=0, sticky="se")
        b_ok = ttk.Button(buttons_frame, text="OK", command=self.ok_command)
        b_ok.grid(column=1, row=0, padx=5, sticky="se")
        self.query = {}

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
