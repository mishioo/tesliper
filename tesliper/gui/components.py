# IMPORTS
import os
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
from tkinter.filedialog import askdirectory, askopenfilenames
from tkinter.scrolledtext import ScrolledText
from threading import Thread
from collections import OrderedDict
from copy import copy
from functools import partial, wraps
import queue

import tesliper


# LOGGER
logger = lgg.getLogger(__name__)


# CLASSES

# HELPERS
class TextHandler(lgg.Handler):

    def __init__(self, widget, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget = widget

    def emit(self, record):
        msg = self.format(record)
        self.widget.insert('end', msg + '\n', record.levelname)
        self.widget.yview('end')


class MaxLevelFilter:

    def __init__(self, max_level):
        self.max_level = max_level

    def filter(self, record):
        return record.levelno <= self.max_level


class ShortExcFormatter(lgg.Formatter):

    def format(self, record):
        record = copy(record)
        record.exc_text = ''
        return super().format(record)

    def formatException(self, ei):
        output = ''
        return output


class PopupHandler(lgg.Handler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def emit(self, record):
        msg = self.format(record)
        messagebox.showerror('Something unexpected happened! :(', msg)


class ReadOnlyText(ScrolledText):

    def __init__(self, master, **kwargs):
        self.window = tk.Toplevel(master)
        self.hide()
        self.window.title('Tesliper Log')
        self.window.protocol('WM_DELETE_WINDOW', self.hide)
        kwargs['state'] = 'disabled'
        super().__init__(self.window, **kwargs)
        self.pack(fill=tk.BOTH, expand=tk.YES)
        self.tag_config('DEBUG', foreground='gray')
        self.tag_config('INFO', foreground='black')
        self.tag_config('WARNING', foreground='dark violet',
                        font="Courier 10 italic")
        self.tag_config('ERROR', foreground='red3')
        self.tag_config('CRITICAL', foreground='red3', font="Courier 10 bold")

    def insert(self, *args, **kwargs):
        self.configure(state='normal')
        super().insert(*args, **kwargs)
        self.configure(state='disabled')

    def delete(self, *args, **kwargs):
        self.configure(state='normal')
        super().delete(*args, **kwargs)
        self.configure(state='disabled')

    def show(self):
        self.window.deiconify()

    def hide(self):
        self.window.withdraw()


class WgtStateChanger:
    """
    TO DO
    -----
    Consider excluding recalculate_command from state changers (currently 
    it is state changer through GUIFeedback and FeedbackThread).
    """

    tslr = []
    energies = []
    bars = []
    either = []
    both = []
    spectra = []
    all = []
    gui = None

    def __init__(self, function=None):
        if function is not None:
            self.function = function
        else:
            self.function = lambda *args, **kwargs: None
        wraps(function)(self)

    def __call__(self, other, *args, **kwargs):
        outcome = self.function(other, *args, **kwargs)
        self.set_states()
        return outcome

    def __get__(self, obj, objtype):
        if obj is None:
            # instance attribute accessed on class, return self
            return self
        else:
            return partial(self.__call__, obj)

    @property
    def changers(self):
        tslr = WgtStateChanger.gui.tslr
        bars = False if not tslr else any(tslr.spectral.values())
        energies = False if not tslr else any(tslr.energies.values())
        spectra = False if not tslr else any(tslr.spectra.values())
        return dict(
            tslr=self.enable if tslr else self.disable,
            energies=self.enable if energies else self.disable,
            bars=self.enable if bars else self.disable,
            either=self.enable if (bars or energies) else self.disable,
            both=self.enable if (bars and energies) else self.disable,
            spectra=self.enable if spectra else self.disable,
            all=self.enable if (energies and spectra) else self.disable
        )

    @staticmethod
    def enable(widget):
        if isinstance(widget, ttk.Combobox):
            widget.configure(state='readonly')
        else:
            widget.configure(state='normal')

    @staticmethod
    def disable(widget):
        widget.configure(state='disabled')

    @staticmethod
    def change_spectra_radio():
        tslr = WgtStateChanger.gui.tslr
        bars = tslr.spectral.values()
        spectra_available = [bar.spectra_name for bar in bars if bar]
        radio = WgtStateChanger.gui.spectra_tab.s_name_radio
        for option, widget in radio.items():
            state = 'disabled' if not tslr or \
                option not in spectra_available else 'normal'
            widget.configure(state=state)

    @classmethod
    def set_states(cls):
        inst = cls()
        for dependency, changer in inst.changers.items():
            for widget in getattr(inst, dependency):
                changer(widget)
        WgtStateChanger.change_spectra_radio()


class FeedbackThread(Thread):
    def __init__(self, gui, progbar_msg, target, args, kwargs):
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.progbar_msg = progbar_msg
        self.gui = gui
        self.queue = queue.Queue()
        super().__init__(daemon=True)

    @WgtStateChanger
    def run(self):
        self.exc = None
        self.gui.progtext.set(self.progbar_msg)
        self.gui.progbar.configure(mode='indeterminate')
        self.gui.progbar.start()
        try:
            return_value = self.target(*self.args, **self.kwargs)
            self.queue.put(return_value)
        except BaseException as exc:
            self.exc = exc
        self.gui.progbar.stop()
        self.gui.progbar.configure(mode='determinate')
        self.gui.progtext.set('Idle.')
        if self.exc:
            logger.critical('Something unexpected happend.',
                            exc_info=self.exc)
            return
            # raise self.exc
        else:
            return return_value


class Feedback:

    def __init__(self, progbar_msg):
        self.progbar_msg = progbar_msg

    def __call__(self, function):
        def wrapper(other, *args, **kwargs):
            # other becomes self from decorated method
            if other.parent.thread.is_alive():
                msg = "Can't start {}, while {} is still running.".format(
                    function, other.parent.thread.target)
                logger.info(msg)
                return  # log and do nothing
            else:
                other.parent.thread = FeedbackThread(
                    other.parent, self.progbar_msg, function,
                    [other] + list(args), kwargs
                )
            other.parent.thread.start()

        return wrapper


# POPUPS

class Popup(tk.Toplevel):

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.master = master
        self.grab_set()
        try:
            width, height = kwargs['width'], kwargs['height']
            self.set_geometry(width, height)
        except KeyError:
            pass

    def set_geometry(self, width, height):
        x = self.master.winfo_pointerx()
        y = self.master.winfo_pointery()
        geometry = '{}x{}{:+n}{:+n}'.format(width, height, x, y)
        self.geometry(geometry)


class ExportPopup(Popup):

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Export...")
        self.labels = 'Energies Bars Spectra Averaged'.split(' ')
        self.vars = [tk.BooleanVar() for _ in self.labels]
        checks = [ttk.Checkbutton(self, text=l, variable=v)
                  for l, v in zip(self.labels, self.vars)]
        for n, check in enumerate(checks):
            check.grid(column=0, row=n, pady=2, padx=5, sticky='nw')
        checks[0].configure(
            state='normal' if self.master.parent.tslr.energies else 'disabled'
        )
        checks[1].configure(
            state='normal' if self.master.parent.tslr.bars else 'disabled'
        )
        checks[2].configure(
            state='normal' if self.master.parent.tslr.spectra else 'disabled'
        )
        checks[3].configure(
            state='normal' if self.master.parent.tslr.spectra else 'disabled'
        )
        self.vars[0].set(True if self.master.parent.tslr.energies else False)
        self.vars[1].set(True if self.master.parent.tslr.bars else False)
        self.vars[2].set(True if self.master.parent.tslr.spectra else False)
        self.vars[3].set(True if self.master.parent.tslr.spectra else False)
        self.protocol("WM_DELETE_WINDOW", self.cancel_command)
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(column=0, row=4, pady=2, sticky='se')
        b_cancel = ttk.Button(buttons_frame, text="Cancel", command=self.cancel_command)
        b_cancel.grid(column=0, row=0, sticky='se')
        b_ok = ttk.Button(buttons_frame, text="OK", command=self.ok_command)
        b_ok.grid(column=1, row=0, padx=5, sticky='se')
        tk.Grid.rowconfigure(self, 4, weight=1)
        tk.Grid.columnconfigure(self, 0, weight=1)
        self.query = []

    def ok_command(self):
        vals = [v.get() for v in self.vars]
        logger.debug(vals)
        if any(vals):
            self.destroy()
        else:
            messagebox.showinfo("Nothing choosen!",
                                "You must chose what you want to extract.")
            self.focus_set()

    def cancel_command(self):
        self.vars = []
        self.destroy()

    def get_query(self):
        self.wait_window()
        self.query = [thing.lower() for thing, var
                      in zip(self.labels, self.vars) if var.get()]
        logger.debug(self.query)
        return self.query


class BarsPopup(Popup):
    bar_names = "IR Inten.,E-M Angle,Dip. Str.,Rot. Str.,Osc. Str. (velo)," \
                "Rot. Str. (velo),Osc. Str. (length),Rot. Str. (length)," \
                "Raman1,ROA1".split(',')
    bar_keys = "iri emang dip rot vosc vrot losc lrot raman1 roa1".split(' ')

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Bars extraction")
        tk.Grid.rowconfigure(self, 6, weight=1)
        tk.Grid.columnconfigure(self, 2, weight=1)
        ttk.Label(self, text="Chose bars you wish to extract:").grid(
            column=0, row=0, columnspan=2, sticky='w', padx=5, pady=5)
        positions = [(c, r) for r in range(1, 6) for c in range(2)]
        self.vars = [tk.BooleanVar() for _ in self.bar_keys]
        for v, k, n, (c, r) in zip(self.vars, self.bar_keys, self.bar_names,
                                   positions):
            b = ttk.Checkbutton(self, text=n, variable=v)
            b.grid(column=c, row=r, sticky='w', pady=2, padx=5)
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(column=0, row=6, columnspan=3, sticky='se', pady=5)
        tk.Grid.rowconfigure(buttons_frame, 0, weight=1)
        tk.Grid.columnconfigure(buttons_frame, 0, weight=1)
        b_cancel = ttk.Button(buttons_frame, text="Cancel", command=self.cancel_command)
        b_cancel.grid(column=0, row=0, sticky='se')
        b_ok = ttk.Button(buttons_frame, text="OK", command=self.ok_command)
        b_ok.grid(column=1, row=0, sticky='se', padx=5)

    def ok_command(self):
        vals = [v.get() for v in self.vars]
        query = [b for b, v in zip(self.bar_keys, vals) if v]
        if query:
            self.destroy()
            self.master.execute_extract_bars(query)
        else:
            messagebox.showinfo("Nothing choosen!",
                                "You must chose which bars you want to extract.")
            self.focus_set()

    def cancel_command(self):
        self.destroy()


class ExtractPopup(Popup):
    names = "Energies,IR Inten.,E-M Angle,Dip. Str.,Rot. Str.," \
            "Raman1,ROA1,Osc. Str. (velo),Rot. Str. (velo)," \
            "Osc. Str. (length),Rot. Str. (length)".split(',')
    keys = "energies iri emang dip rot raman1 roa1 vosc vrot losc lrot".split(' ')

    def __init__(self, master, *args, **kwargs):
        self.soxhlet = None
        self.query = []

        super().__init__(master, *args, **kwargs)
        self.title("Extract data...")
        tk.Grid.columnconfigure(self, 0, weight=1)
        tk.Grid.rowconfigure(self, 4, weight=1)
        upper_frame = ttk.Frame(self)
        upper_frame.grid(column=0, row=0, sticky='we')
        tk.Grid.columnconfigure(upper_frame, 0, weight=1)
        tk.Grid.rowconfigure(upper_frame, 0, weight=1)
        path_frame = ttk.Frame(upper_frame)
        path_frame.grid(column=0, row=0, sticky='we')
        tk.Grid.columnconfigure(path_frame, 1, weight=1)
        tk.Grid.rowconfigure(path_frame, 0, weight=1)
        ttk.Label(path_frame, text="Path ").grid(column=0, row=0, sticky='w')
        self.path = tk.StringVar()
        self.path.set("Not specified.")
        self.entry = ttk.Entry(path_frame, textvariable=self.path, state='readonly')
        self.entry.grid(column=1, row=0, sticky='we')
        self.amount = tk.StringVar()
        self.amount.set("No files have been selected yet.")
        ttk.Label(upper_frame, textvariable=self.amount).grid(
            column=0, row=1, sticky='w'
        )
        select_buttons_frame = ttk.Frame(upper_frame)
        select_buttons_frame.grid(column=1, row=0, rowspan=2, sticky='e')
        tk.Grid.columnconfigure(select_buttons_frame, 0, weight=1)
        self.select_directory = ttk.Button(
            select_buttons_frame, text="Select directory",
            command=self.select_directory_command
        )
        self.select_directory.grid(column=0, row=0, sticky='we',
                                   pady=2, padx=5)
        self.select_files = ttk.Button(
            select_buttons_frame, text="Select files",
            command=self.select_files_command
        )
        self.select_files.grid(column=0, row=1, sticky='we', padx=5)
        self.smart = tk.BooleanVar()
        ttk.Checkbutton(
            upper_frame, text="Execute smart data extraction?",
            variable=self.smart, command=self.execute_smart_button_command
        ).grid(column=0, row=2, sticky='w', pady=2, padx=5)
        self.smart.set(True)

        self.buttons_frame = ttk.Frame(self)
        # self.buttons_frame.grid(column=0, row=1, sticky='we')
        self.buttons = []
        self.vars = [tk.BooleanVar() for __ in self.keys]
        positions = [(0, r) for r in range(3)] + \
                    [(c, r) for c in range(1, 5) for r in range(1, 3)]
        for n, v, (c, r) in zip(self.names, self.vars, positions):
            b = ttk.Checkbutton(self.buttons_frame, text=n, variable=v,
                                state='disabled')
            b.grid(column=c, row=r, sticky='w', pady=1, padx=5)
            self.buttons.append(b)
        self.bottom_buttons_frame = ttk.Frame(self)
        self.bottom_buttons_frame.grid(
            column=0, row=4, sticky='se', pady=5, padx=5
        )
        self.button_extract = ttk.Button(
            self.bottom_buttons_frame, text="Extract data",
            command=self.extract_command, state='disabled'
        )
        self.button_extract.grid(column=1, row=0, sticky='se')
        self.cancel_button = ttk.Button(
            self.bottom_buttons_frame, text="Cancel",
            command=self.cancel_command
        )
        self.cancel_button.grid(column=0, row=0, sticky='se', padx=5)
        self.protocol("WM_DELETE_WINDOW", self.cancel_command)

    def create_soxhlet(self, path, wanted_files=None):
        soxhlet = tesliper.Soxhlet(path, wanted_files)
        try:
            ext = soxhlet.guess_extension()
        except ValueError:
            messagebox.showerror(
                "Mixed output files!",
                ".log and .out files mixed in choosen directory!")
            self.button_extract.configure(state='disabled')
            self.path.set("Not selected")
            self.amount.set("No files have been selected yet.")
            self.soxhlet = None
            self.focus_set()
            return
        except TypeError:
            messagebox.showerror(
                "No output files found.",
                "Didn't found any .log or .out files in choosen directory.")
            self.button_extract.configure(state='disabled')
            self.path.set("Not selected")
            self.amount.set("No files have been selected yet.")
            self.soxhlet = None
            self.focus_set()
            return
        self.path.set(path)
        self.soxhlet = soxhlet
        amount = \
            f"All {len(soxhlet.output_files)} output files in directory" \
            if not wanted_files else \
            f"{len(soxhlet.output_files)} *{ext} files"
        self.amount.set(f"{amount} have been selected.")
        self.button_extract.configure(state='normal')
        return soxhlet

    def select_directory_command(self):
        path = askdirectory()
        if path:
            self.create_soxhlet(path)

    def select_files_command(self):
        files = askopenfilenames(
            filetypes=[("any output", "*.log *.out"), ("log files", "*.log"),
                       ("out files", "*.out"), ("all files", "*.*")])
        if files:
            path = os.path.split(files[0])[0]
            filenames = list(map(lambda p: os.path.split(p)[1], files))
            self.create_soxhlet(path, filenames)

    def extract_command(self):
        if self.smart.get():
            self.query = 'smart'
        else:
            self.query = [
                thing for thing, var in zip(self.keys, self.vars) if var.get()
            ]
        logger.debug(self.query)
        self.destroy()

    def cancel_command(self):
        self.query = []
        self.soxhlet = None
        self.destroy()

    def execute_smart_button_command(self):
        state = 'normal' if not self.smart.get() else 'disabled'
        for b in self.buttons:
            b.configure(state=state)
        if not self.smart.get():
            self.buttons_frame.grid(column=0, row=1, sticky='we')
        else:
            self.buttons_frame.grid_forget()


# CHECK TREE
class BoxVar(tk.BooleanVar):

    def __init__(self, box, *args, **kwargs):
        self.box = box
        super().__init__(*args, **kwargs)
        super().set(True)

    def _set(self, value):
        super().set(value)
        tags = () if value else 'discarded'
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
        kwargs['variable'] = self.var
        super().__init__(self.frame, *args, command=self.clicked, **kwargs)
        self.frame.pack_propagate(False)
        self.frame.grid_propagate(False)
        self.grid(column=0, row=0)

    def clicked(self):
        logger.debug(f'box index: {self.index}')
        value = self.var.get()
        self.var.set(value)
        self.tree.trees['main'].parent_tab.discard_not_kept()
        self.tree.trees['main'].parent_tab.update_overview_values()
        self.tree.trees['energies'].parent_tab.refresh()
        # self.tree.selection_set(str(self.index))


class CheckTree(ttk.Treeview):
    trees = dict()

    def __init__(self, master, name, parent_tab=None, **kwargs):
        CheckTree.trees[name] = self
        self.frame = ttk.Frame(master)
        self.parent_tab = parent_tab
        super().__init__(self.frame, **kwargs)
        self.grid(column=0, row=0, rowspan=2, columnspan=2, sticky='nwse')
        tk.Grid.columnconfigure(self.frame, 1, weight=1)
        tk.Grid.rowconfigure(self.frame, 1, weight=1)
        self.vsb = ttk.Scrollbar(self.frame, orient='vertical',
                                 command=self.on_bar)
        self.vsb.grid(column=2, row=0, rowspan=2, sticky='nse')

        self.tag_configure('discarded', foreground='gray')

        # Sort button
        but_frame = ttk.Frame(self.frame, height=24, width=17)
        but_frame.grid(column=0, row=0)
        but_frame.grid_propagate(False)
        tk.Grid.columnconfigure(but_frame, 0, weight=1)
        tk.Grid.rowconfigure(but_frame, 0, weight=1)
        style = ttk.Style()
        style.configure('sorting.TButton',
                        borderwidth=5,
                        highlightthickness=1,
                        relief='flat')
        self.but_sort = ttk.Button(but_frame, style='sorting.TButton',
                                   command=self._sort_button)
        self.but_sort.grid(column=0, row=0, sticky='nwes')

        # Boxes
        self.canvas = tk.Canvas(self.frame, width=17, borderwidth=0,
                                background="#ffffff", highlightthickness=0)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.grid(column=0, row=1, sticky='ns')
        self.boxes_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.boxes_frame, anchor="nw",
                                  tags="boxes_frame")

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
        ls = [self.item(i)['text'] for i in self.get_children()]
        ls = sorted(ls)
        dummy = tesliper.dw.Data('dummy', filenames=ls)
        dummy.trimmer.set(self.blade)
        return dummy

    def _sort_button(self, reverse=True):
        ls = [(b.var.get(), b.index) for b in self.boxes.values()]
        ls.sort(reverse=reverse)
        for i, (val, iid) in enumerate(ls):
            box = self.boxes[iid]
            self.move(iid, '', i)
            box.frame.grid_forget()
            box.frame.grid_propagate(False)
            box.frame.grid(column=0, row=i, sticky='n', pady=0)
        self.but_sort.configure(command=lambda: self._sort_button(not reverse))

    def _sort(self, col, reverse=True):
        try:
            ls = [(self.set(iid, col), iid) for iid in self.get_children('')]
        except tk.TclError:
            ls = [(self.item(iid)['text'],
                   iid) for iid in self.get_children('')]
        try:
            ls = [(-1e10 if v == '--' else float(v), iid) for v, iid in ls]
        except ValueError:
            pass
        ls.sort(reverse=reverse)
        for i, (val, iid) in enumerate(ls):
            self.move(iid, '', i)
            box = self.boxes[iid]
            box.frame.grid_forget()
            box.frame.grid_propagate(False)
            box.frame.grid(column=0, row=i, sticky='n', pady=0)
        self.heading(col, command=lambda: self._sort(col, not reverse))

    def heading(self, col, *args, command=None, **kwargs):
        command = command if command is not None else lambda: self._sort(col)
        return super().heading(col, *args, command=command, **kwargs)

    def onFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def yscroll(self, *args):
        logger.debug(args)
        self.canvas.yview_moveto(args[0])
        logger.debug(self.canvas.yview())

    def _insert(self, parent='', index=tk.END, iid=None, **kw):
        logger.debug(
            f"CALLED on {self.__class__} with parameters: parent={parent!r}, "
            f"index={index!r}, iid={iid!r}, kw={kw}"
        )
        if kw['text'] in self.owned_children:
            return iid
        box = Checkbox(self.boxes_frame, self, index=iid)
        box.frame.grid(column=0, row=len(self.boxes))
        self.boxes[box.index] = box
        iid = super().insert(parent, index, iid=str(box.index), **kw)
        self.owned_children[kw['text']] = iid
        self.children_names[iid] = kw['text']
        return iid

    def insert(self, parent='', index=tk.END, iid=None, **kw):
        try:
            text = kw['text']
        except KeyError:
            raise TypeError("Required keyword argument 'text' not found.")
        if iid is not None:
            logger.debug('Overriding passed iid value.')
        if text in self.trees['main'].owned_children:
            iid = self.trees['main'].owned_children[text]
        else:
            iid = str(self.trees['main'].curr_iid)
            self.trees['main'].curr_iid += 1
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
        values=lambda v: '{:.6f}'.format(v),
        deltas=lambda v: '{:.4f}'.format(v),
        min_factors=lambda v: '{:.4f}'.format(v),
        populations=lambda v: '{:.4f}'.format(v * 100)
    )
    e_keys = 'ten ent gib scf zpe'.split(' ')

    def __init__(self, master, parent_tab=None, **kwargs):
        kwargs['columns'] = 'ten ent gib scf zpe'.split(' ')
        super().__init__(master, 'energies', parent_tab=parent_tab, **kwargs)

        # Columns
        for cid, text in zip(
                '#0 ten ent gib scf zpe'.split(' '),
                'Filenames Thermal Enthalpy Gibbs SCF Zero-Point'.split(' ')
        ):
            if not cid == '#0':
                self.column(cid, width=100, anchor='e', stretch=False)
            self.heading(cid, text=text)
        self.column('#0', width=150)

    def _insert(self, parent='', index=tk.END, iid=None, **kw):
        text = kw['text']
        if 'gib' not in self.tslr.molecules[text]:
            return
        iid = super()._insert(parent=parent, index=index, iid=iid, **kw)
        return iid

    def refresh(self):
        # TO DO: implement this based on table_view_update from main.Conformers
        # super().refresh()
        show = self.parent_tab.show_ref[self.parent_tab.show_var.get()]
        logger.debug('Going to update by showing {}.'.format(show))
        if show == 'values':
            # we don't want to hide energy values of non-kept conformer
            with self.tslr.molecules.untrimmed:
                scope = self.tslr.energies
        else:
            scope = self.tslr.energies
        values_to_show = zip(*[getattr(scope[e], show) for e in self.e_keys])
        # values in groups of 5, ordered as e_keys
        fnames = set(scope['gib'].filenames)
        for name, iid in self.owned_children.items():
            # owned_children is OrderedDict, so we get name and iid in ordered
            # they were inserted to treeview, which is same as order of data
            # stored in Tesliper instance
            values = ['--'] * 5 if name not in fnames else \
                map(self.formats[show], next(values_to_show))
            # if this conformer's kept value is False,
            # use -- in place of missing values
            for col, value in zip(self.e_keys, values):
                self.set(iid, column=col, value=value)


class ConformersOverview(CheckTree):

    def __init__(self, master, parent_tab=None, **kwargs):
        kwargs['columns'] = 'term opt en ir vcd uv ecd ram roa ' \
                            'imag stoich'.split(' ')
        super().__init__(master, 'main', parent_tab=parent_tab, **kwargs)
        self.curr_iid = 0

        # Columns
        self.column('#0', width=150)
        self.heading('#0', text='Filenames')
        for cid, text in zip(
                'term opt en ir vcd uv ecd ram roa imag stoich'.split(' '),
                'Termination Opt Energy IR VCD UV ECD Raman ROA Imag '
                'Stoichiometry'.split(' ')
        ):
            width = 80 if cid == 'term' else 90 if cid == 'stoich' else \
                50 if cid in ('en', 'ram') else 35
            self.column(cid, width=width, anchor='center', stretch=False)
            self.heading(cid, text=text)
        self.__max_length = 0

    def _insert(self, parent='', index=tk.END, iid=None, **kw):
        # TO DO: correct wrong files counting when smaller set is extracted
        # first
        text = kw['text']
        mol = self.tslr.molecules[text]
        values = {
            'term': 'normal' if mol['normal_termination'] else 'ERROR',
            'opt': 'n/a' if 'optimization_completed' not in mol else
                'ok' if mol['optimization_completed'] else False,
            'en': 'ok' if all(
                e in mol for e in EnergiesView.e_keys) else False,
            'ir': 'ok' if 'dip' in mol else False,
            'vcd': 'ok' if 'rot' in mol else False,
            'uv': 'ok' if 'vosc' in mol else False,
            'ecd': 'ok' if 'vrot' in mol else False,
            'ram': 'ok' if 'raman1' in mol else False,
            'roa': 'ok' if 'roa1' in mol else False
        }
        if 'freq' in mol:
            freqs = self.tslr.molecules[text]['freq']
            imag = str((freqs < 0).sum())
            values['imag'] = imag
        else:
            values['imag'] = False
        values['stoich'] = mol['stoichiometry']
        iid = super()._insert(parent=parent, index=index, iid=iid, **kw)
        for k, v in values.items():
            self.set(iid, k, v or 'X')
        return iid

    @classmethod
    def test_populate(cls, master, num=30):
        import string, random
        new = cls(master, columns=('b'))
        new.heading('b', text='afasdgf')
        new.heading('#0', text='asdgasdfg')
        gen = (''.join(random.choices(string.ascii_lowercase, k=7))
               for x in range(num))
        for x, bla in enumerate(gen):
            new.insert(text=bla + ' ' + str(x), values=[x])
        return new
