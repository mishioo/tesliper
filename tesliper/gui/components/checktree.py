# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk
from collections import OrderedDict

import tesliper
from .helpers import WgtStateChanger


# LOGGER
logger = lgg.getLogger(__name__)


# CLASSES
class BoxVar(tk.BooleanVar):
    def __init__(self, box, *args, **kwargs):
        self.box = box
        super().__init__(*args, **kwargs)
        super().set(True)

    def _set(self, value):
        super().set(value)
        tags = () if value else "discarded"
        self.box.tree.item(self.box.index, tags=tags)

    def set(self, value):
        # set is not called by tkinter when checkbutton is clicked
        self.box.tree.tslr.molecules.kept[int(self.box.index)] = bool(value)
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
        self.tree.trees["main"].parent_tab.discard_not_kept()
        self.tree.trees["main"].parent_tab.update_overview_values()
        self.tree.trees["energies"].parent_tab.refresh()
        # self.tree.selection_set(str(self.index))
        WgtStateChanger.set_states()


class CheckTree(ttk.Treeview):
    trees = dict()

    def __init__(self, master, name, parent_tab=None, **kwargs):
        CheckTree.trees[name] = self
        self.frame = ttk.Frame(master)
        self.parent_tab = parent_tab
        super().__init__(self.frame, **kwargs)
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
        style = ttk.Style()
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
    def tslr(self):
        return self.parent_tab.parent.tslr

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
        try:
            ls = [(self.set(iid, col), iid) for iid in self.get_children("")]
        except tk.TclError:
            ls = [(self.item(iid)["text"], iid) for iid in self.get_children("")]
        try:
            ls = [(-1e10 if v == "--" else float(v), iid) for v, iid in ls]
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

    def click_all(self, index, value):
        # this is not used currently 21.11.2018
        for tree in CheckTree.trees.values():
            tree.boxes[index].var.set(value)
            tree.refresh()

    def refresh(self):
        pass
        # logger.debug(f"Called .refresh on {type(self)}")
        # kept = self.tslr.molecules.kept
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

    def __init__(self, master, parent_tab=None, **kwargs):
        kwargs["columns"] = "ten ent gib scf zpe".split(" ")
        super().__init__(master, "energies", parent_tab=parent_tab, **kwargs)

        # Columns
        for cid, text in zip(
            "#0 ten ent gib scf zpe".split(" "),
            "Filenames Thermal Enthalpy Gibbs SCF Zero-Point".split(" "),
        ):
            if not cid == "#0":
                self.column(cid, width=100, anchor="e", stretch=False)
            self.heading(cid, text=text)
        self.column("#0", width=150)

    def _insert(self, parent="", index=tk.END, iid=None, **kw):
        text = kw["text"]
        if "gib" not in self.tslr.molecules[text]:
            return
        iid = super()._insert(parent=parent, index=index, iid=iid, **kw)
        return iid

    def refresh(self):
        # TO DO: implement this based on table_view_update from main.Conformers
        # super().refresh()
        show = self.parent_tab.show_ref[self.parent_tab.show_var.get()]
        logger.debug("Going to update by showing {}.".format(show))
        if show == "values":
            # we don't want to hide energy values of non-kept conformer
            with self.tslr.molecules.untrimmed:
                scope = self.tslr.energies
        else:
            scope = self.tslr.energies
        values_to_show = zip(*[getattr(scope[e], show) for e in self.e_keys])
        # values in groups of 5, ordered as e_keys
        fnames = set(scope["gib"].filenames)
        for name, iid in self.owned_children.items():
            # owned_children is OrderedDict, so we get name and iid in ordered
            # they were inserted to treeview, which is same as order of data
            # stored in Tesliper instance
            values = (
                ["--"] * 5
                if name not in fnames
                else map(self.formats[show], next(values_to_show))
            )
            # if this conformer's kept value is False,
            # use -- in place of missing values
            for col, value in zip(self.e_keys, values):
                self.set(iid, column=col, value=value)


class ConformersOverview(CheckTree):
    def __init__(self, master, parent_tab=None, **kwargs):
        kwargs["columns"] = "term opt en ir vcd uv ecd ram roa " "imag stoich".split(
            " "
        )
        super().__init__(master, "main", parent_tab=parent_tab, **kwargs)
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
        mol = self.tslr.molecules[text]
        values = {
            "term": "normal" if mol["normal_termination"] else "ERROR",
            "opt": "n/a"
            if "optimization_completed" not in mol
            else "ok"
            if mol["optimization_completed"]
            else False,
            "en": "ok" if all(e in mol for e in EnergiesView.e_keys) else False,
            "ir": "ok" if "dip" in mol else False,
            "vcd": "ok" if "rot" in mol else False,
            "uv": "ok" if "vosc" in mol else False,
            "ecd": "ok" if "vrot" in mol else False,
            "ram": "ok" if "raman1" in mol else False,
            "roa": "ok" if "roa1" in mol else False,
        }
        if "freq" in mol:
            freqs = self.tslr.molecules[text]["freq"]
            imag = str((freqs < 0).sum())
            values["imag"] = imag
        else:
            values["imag"] = False
        values["stoich"] = mol["stoichiometry"]
        iid = super()._insert(parent=parent, index=index, iid=iid, **kw)
        for k, v in values.items():
            self.set(iid, k, v or "X")
        return iid

    @classmethod
    def test_populate(cls, master, num=30):
        import string
        import random

        new = cls(master, columns=("b"))
        new.heading("b", text="afasdgf")
        new.heading("#0", text="asdgasdfg")
        gen = ("".join(random.choices(string.ascii_lowercase, k=7)) for x in range(num))
        for x, bla in enumerate(gen):
            new.insert(text=bla + " " + str(x), values=[x])
        return new
