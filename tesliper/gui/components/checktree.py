# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk
from collections import OrderedDict

import numpy as np

import tesliper

# LOGGER
logger = lgg.getLogger(__name__)


# CLASSES
class BoxVar(tk.BooleanVar):
    def __init__(self, box, *args, **kwargs):
        self.box = box
        if "value" not in kwargs:
            kwargs["value"] = True
        super().__init__(*args, **kwargs)

    @property
    def tesliper(self):
        return self.box.winfo_toplevel().tesliper

    def _set(self, value):
        super().set(value)
        tags = () if value else "discarded"
        self.box.tree.item(self.box.index, tags=tags)

    def set(self, value):
        # set is not called by tkinter when checkbutton is clicked
        self.tesliper.conformers.kept[int(self.box.index)] = bool(value)
        for tree in self.box.tree.trees.values():
            try:
                tree.boxes[self.box.index].var._set(value)
            except KeyError:
                logger.debug(f"{tree} doesn't have box iid {self.box.index}")


class Checkbox(ttk.Checkbutton):
    def __init__(self, master, tree, index, *args, **kwargs):
        self.frame = ttk.Frame(master, width=17, height=20)
        self.tree = tree
        self.index = index
        self.var = BoxVar(self)
        kwargs["variable"] = self.var
        super().__init__(self.frame, *args, command=self.clicked, **kwargs)
        self.frame.pack_propagate(False)
        self.frame.grid_propagate(False)
        self.grid(column=0, row=0)

    def clicked(self):
        logger.debug(f"box index: {self.index}")
        value = self.var.get()
        self.var.set(value)
        self.event_generate("<<KeptChanged>>")


class CheckTree(ttk.Treeview):
    trees = dict()

    def __init__(self, master, name, **kwargs):
        CheckTree.trees[name] = self
        self.frame = ttk.Frame(master)
        style = ttk.Style()
        style.layout(
            "borderless.Treeview", [("mystyle.Treeview.treearea", {"sticky": "nswe"})]
        )
        super().__init__(self.frame, **kwargs, style="borderless.Treeview")
        self.grid(column=0, row=0, rowspan=2, columnspan=2, sticky="nwse")
        tk.Grid.columnconfigure(self.frame, 1, weight=1)
        tk.Grid.rowconfigure(self.frame, 1, weight=1)
        self.vsb = ttk.Scrollbar(self.frame, orient="vertical", command=self.on_bar)
        self.vsb.grid(column=2, row=0, rowspan=2, sticky="nse")

        self.tag_configure("discarded", foreground="gray")

        # Sort button
        but_frame = ttk.Frame(self.frame, height=24, width=17)
        but_frame.grid(column=0, row=0)
        but_frame.grid_propagate(False)
        tk.Grid.columnconfigure(but_frame, 0, weight=1)
        tk.Grid.rowconfigure(but_frame, 0, weight=1)
        style.configure(
            "sorting.TButton", borderwidth=5, highlightthickness=1, relief="flat"
        )
        self.but_sort = ttk.Button(
            but_frame, style="sorting.TButton", command=self._sort_button
        )
        self.but_sort.grid(column=0, row=0, sticky="nwes")

        # Boxes
        self.canvas = tk.Canvas(
            self.frame,
            width=17,
            borderwidth=0,
            background="#ffffff",
            highlightthickness=0,
        )
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.grid(column=0, row=1, sticky="ns")
        self.boxes_frame = ttk.Frame(self.canvas)
        self.canvas.create_window(
            (0, 0), window=self.boxes_frame, anchor="nw", tags="boxes_frame"
        )

        self.boxes_frame.bind("<Configure>", self.onFrameConfigure)
        self.configure(yscrollcommand=self.yscroll)
        self.boxes = OrderedDict()

        self.owned_children = OrderedDict()
        self.children_names = OrderedDict()

    @property
    def tesliper(self):
        return self.winfo_toplevel().tesliper

    @property
    def blade(self):
        return [box.var.get() for box in self.boxes.values()]

    @property
    def dummy(self):
        ls = [self.item(i)["text"] for i in self.get_children()]
        ls = sorted(ls)
        dummy = tesliper.dw.Data("dummy", filenames=ls)
        dummy.trimmer.set(self.blade)
        return dummy

    def _sort_button(self, reverse=True):
        ls = [(b.var.get(), b.index) for b in self.boxes.values()]
        ls.sort(reverse=reverse)
        for i, (val, iid) in enumerate(ls):
            box = self.boxes[iid]
            self.move(iid, "", i)
            box.frame.grid_forget()
            box.frame.grid_propagate(False)
            box.frame.grid(column=0, row=i, sticky="n", pady=0)
        self.but_sort.configure(command=lambda: self._sort_button(not reverse))

    def _sort(self, col, reverse=True):
        # empty records always at the end
        empty = float("-inf") if reverse else float("inf")
        try:
            ls = [(self.set(iid, col), iid) for iid in self.get_children("")]
        except tk.TclError:
            ls = [(self.item(iid)["text"], iid) for iid in self.get_children("")]
        try:
            ls = [(empty if v == "--" else float(v), iid) for v, iid in ls]
        except ValueError:
            pass
        ls.sort(reverse=reverse)
        for i, (val, iid) in enumerate(ls):
            self.move(iid, "", i)
            box = self.boxes[iid]
            box.frame.grid_forget()
            box.frame.grid_propagate(False)
            box.frame.grid(column=0, row=i, sticky="n", pady=0)
        self.heading(col, command=lambda: self._sort(col, not reverse))

    def heading(self, col, *args, command=None, **kwargs):
        command = command if command is not None else lambda: self._sort(col)
        return super().heading(col, *args, command=command, **kwargs)

    def onFrameConfigure(self, event):
        """Reset the scroll region to encompass the inner frame"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def yscroll(self, *args):
        logger.debug(args)
        self.canvas.yview_moveto(args[0])
        logger.debug(self.canvas.yview())

    def _insert(self, parent="", index=tk.END, iid=None, **kw):
        logger.debug(
            f"CALLED on {self.__class__} with parameters: parent={parent!r}, "
            f"index={index!r}, iid={iid!r}, kw={kw}"
        )
        if kw["text"] in self.owned_children:
            return iid
        box = Checkbox(self.boxes_frame, self, index=iid)
        box.frame.grid(column=0, row=len(self.boxes))
        self.boxes[box.index] = box
        iid = super().insert(parent, index, iid=str(box.index), **kw)
        self.owned_children[kw["text"]] = iid
        self.children_names[iid] = kw["text"]
        return iid

    def insert(self, parent="", index=tk.END, iid=None, **kw):
        try:
            text = kw["text"]
        except KeyError:
            raise TypeError("Required keyword argument 'text' not found.")
        if iid is not None:
            logger.debug("Overriding passed iid value.")
        if text in self.trees["main"].owned_children:
            iid = self.trees["main"].owned_children[text]
        else:
            iid = str(self.trees["main"].curr_iid)
            self.trees["main"].curr_iid += 1
        for tree in CheckTree.trees.values():
            tree._insert(parent=parent, index=index, iid=iid, **kw)

    def on_bar(self, *args):
        self.yview(*args)
        # logger.debug(args)
        # logger.debug(self.canvas.yview())

    def refresh(self):
        pass
        # logger.debug(f"Called .refresh on {type(self)}")
        # kept = self.tslr.conformers.kept
        # boxes = self.boxes
        # for iid, name in self.children_names.items():
        #     boxes[iid].var.set(kept[int(iid)])


class EnergiesView(CheckTree):
    formats = dict(
        values=lambda v: "{:.6f}".format(v),
        deltas=lambda v: "{:.4f}".format(v),
        min_factors=lambda v: "{:.4f}".format(v),
        populations=lambda v: "{:.4f}".format(v * 100),
    )
    e_keys = "ten ent gib scf zpe".split(" ")

    def __init__(self, parent, **kwargs):
        kwargs["columns"] = self.e_keys
        super().__init__(parent, "energies", **kwargs)

        # Columns
        for cid, text in zip(
            ["#0"] + self.e_keys,
            "Filenames Thermal Enthalpy Gibbs SCF Zero-Point".split(" "),
        ):
            if not cid == "#0":
                self.column(cid, width=100, anchor="e", stretch=False)
            self.heading(cid, text=text)
        self.column("#0", width=150)

    def refresh(self, show):
        logger.debug("Going to update by showing {}.".format(show))
        if show == "values":
            # we don't want to hide energy values of non-kept conformer
            with self.tesliper.conformers.untrimmed:
                scope = self.tesliper.energies
        else:
            scope = self.tesliper.energies
        formatter = self.formats[show]
        # conformers are always in the same order, so we can use iterator for values
        # and only request next() when conformer's name is known by genre's DataArray
        values = {key: iter(getattr(scope[key], show)) for key in self.e_keys}
        fnames = {key: set(scope[key].filenames) for key in self.e_keys}
        for name, iid in self.owned_children.items():
            # owned_children is OrderedDict, so we get name and iid in ordered
            # they were inserted to treeview, which is same as order of data
            # stored in Tesliper instance
            for key in self.e_keys:
                # if this conformer's kept value is False,
                # use -- in place of missing values
                value = formatter(next(values[key])) if name in fnames[key] else "--"
                self.set(iid, column=key, value=value)


class ConformersOverview(CheckTree):
    def __init__(self, master, **kwargs):
        kwargs["columns"] = "term opt en ir vcd uv ecd ram roa " "imag stoich".split(
            " "
        )
        super().__init__(master, "main", **kwargs)
        self.curr_iid = 0

        # Columns
        self.column("#0", width=150)
        self.heading("#0", text="Filenames")
        for cid, text in zip(
            "term opt en ir vcd uv ecd ram roa imag stoich".split(" "),
            "Termination Opt Energy IR VCD UV ECD Raman ROA Imag "
            "Stoichiometry".split(" "),
        ):
            width = (
                80
                if cid == "term"
                else 90
                if cid == "stoich"
                else 50
                if cid in ("en", "ram")
                else 35
            )
            self.column(cid, width=width, anchor="center", stretch=False)
            self.heading(cid, text=text)
        self.__max_length = 0

    def _insert(self, parent="", index=tk.END, iid=None, **kw):
        # TO DO: correct wrong files counting when smaller set is extracted
        # first
        text = kw["text"]
        conf = self.tesliper.conformers[text]
        values = {
            "term": "normal" if conf["normal_termination"] else "ERROR",
            "opt": "n/a"
            if "optimization_completed" not in conf
            else "ok"
            if conf["optimization_completed"]
            else False,
            "en": "ok" if all(e in conf for e in EnergiesView.e_keys) else False,
            "ir": "ok" if "dip" in conf else False,
            "vcd": "ok" if "rot" in conf else False,
            "uv": "ok" if "vosc" in conf else False,
            "ecd": "ok" if "vrot" in conf else False,
            "ram": "ok" if "raman1" in conf else False,
            "roa": "ok" if "roa1" in conf else False,
        }
        if "freq" in conf:
            freqs = self.tesliper.conformers[text]["freq"]
            imag = str((np.array(freqs) < 0).sum())
            values["imag"] = imag
        else:
            values["imag"] = False
        try:
            values["stoich"] = conf["stoichiometry"]
        except KeyError:
            values["stoich"] = "--"
        iid = super()._insert(parent=parent, index=index, iid=iid, **kw)
        for k, v in values.items():
            self.set(iid, k, v or "X")
        return iid

    @classmethod
    def test_populate(cls, master, num=30):
        import random
        import string

        new = cls(master, columns=("b"))
        new.heading("b", text="afasdgf")
        new.heading("#0", text="asdgasdfg")
        gen = ("".join(random.choices(string.ascii_lowercase, k=7)) for x in range(num))
        for x, bla in enumerate(gen):
            new.insert(text=bla + " " + str(x), values=[x])
        return new
