# IMPORTS
import logging as lgg
import queue
import tkinter as tk
import tkinter.ttk as ttk
from collections import defaultdict
from copy import copy
from functools import partial, wraps
from threading import Thread
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from typing import Iterable, List

from ...glassware.arrays import SpectralData

# LOGGER
logger = lgg.getLogger(__name__)


# FUNCTIONS
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
class TextHandler(lgg.Handler):
    def __init__(self, widget, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget = widget

    def emit(self, record):
        msg = self.format(record)
        self.widget.insert("end", msg + "\n", record.levelname)
        self.widget.yview("end")


class MaxLevelFilter:
    def __init__(self, max_level):
        self.max_level = max_level

    def filter(self, record):
        return record.levelno <= self.max_level


class ShortExcFormatter(lgg.Formatter):
    def format(self, record):
        record = copy(record)
        record.exc_text = ""
        return super().format(record)

    def formatException(self, ei):
        output = ""
        return output


class PopupHandler(lgg.Handler):
    def __init__(self, *args, title_msg="", **kwargs):
        super().__init__(*args, **kwargs)
        self.title_msg = title_msg

    def emit(self, record):
        msg = self.format(record)
        if record.levelno == lgg.INFO:
            messagebox.showinfo(self.title_msg, msg)
        elif record.levelno == lgg.WARNING:
            messagebox.showwarning(self.title_msg, msg)
        elif record.levelno >= lgg.ERROR:
            messagebox.showerror(self.title_msg, msg)


class ReadOnlyText(ScrolledText):
    def __init__(self, master, **kwargs):
        self.window = tk.Toplevel(master)
        self.hide()
        self.window.title("Tesliper Log")
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        kwargs["state"] = "disabled"
        super().__init__(self.window, **kwargs)
        self.pack(fill=tk.BOTH, expand=tk.YES)
        self.tag_config("DEBUG", foreground="gray")
        self.tag_config("INFO", foreground="black")
        self.tag_config("WARNING", foreground="dark violet", font="Courier 10 italic")
        self.tag_config("ERROR", foreground="red3")
        self.tag_config("CRITICAL", foreground="red3", font="Courier 10 bold")

    def insert(self, *args, **kwargs):
        self.configure(state="normal")
        super().insert(*args, **kwargs)
        self.configure(state="disabled")

    def delete(self, *args, **kwargs):
        self.configure(state="normal")
        super().delete(*args, **kwargs)
        self.configure(state="disabled")

    def show(self):
        self.window.deiconify()

    def hide(self):
        self.window.withdraw()


class _DerivedDefaultDict(defaultdict):
    def __missing__(self, key):
        value = self.default_factory(key)
        self[key] = value
        return value


class WgtStateChanger:
    def __init__(self, root):
        self.root = root
        self.bars_genres = tuple("dip rot vosc vrot losc lrot raman1 roa1".split())
        self.energies_genres = tuple("zpe ent ten gib scf".split())
        self._dependencies = {}

    def _short_register_proxy(self, widgets, genres, needs_all=False, key=None):
        param = "needs_all_genres" if needs_all else "needs_any_genre"
        kwargs = {param: genres, "key": key}
        self.register(widgets, **kwargs)

    def energies(self, widgets, needs_all=False, key=None):
        self._short_register_proxy(
            widgets, genres="zpe ent ten gib scf".split(), needs_all=needs_all, key=key
        )

    def bars(self, widgets, needs_all=False, key=None):
        self._short_register_proxy(
            widgets,
            genres=self.bars_genres,
            needs_all=needs_all,
            key=key,
        )

    def tesliper(self, widgets):
        self.register(widgets, key=lambda t=self.root.tslr: bool(t.conformers))

    def bars_and_energies(self, widgets):
        self.register(
            widgets,
            key=lambda cs=self.root.tslr.conformers: (
                cs.has_any_genre(self.bars_genres)
                and cs.has_any_genre(self.energies_genres)
            ),
        )

    def register(self, widgets, needs_all_genres=None, needs_any_genre=None, key=None):
        if not isinstance(widgets, Iterable):
            widgets = [widgets]
        for wgt in widgets:
            self._dependencies[wgt] = (needs_all_genres, needs_any_genre, key)

    def set_states(self):
        genres = _DerivedDefaultDict(
            lambda g, cs=self.root.tslr.conformers: cs.has_genre(g)
        )
        for widget, deps in self._dependencies.items():
            all_ = all(genres[g] for g in deps[0]) if deps[0] else True
            any_ = any(genres[g] for g in deps[1]) if deps[1] else True
            key_ = deps[2]() if deps[2] else True
            changer = self.enable if all_ and any_ and key_ else self.disable
            changer(widget)
        self.change_spectra_radio()

    @staticmethod
    def enable(widget):
        if isinstance(widget, ttk.Combobox):
            widget.configure(state="readonly")
        else:
            widget.configure(state="normal")

    @staticmethod
    def disable(widget):
        widget.configure(state="disabled")

    def change_spectra_radio(self):
        # TODO: change to registering in WgtStateChanger for individual genres
        tslr = self.root.tslr
        bars = {k: False for k in self.bars_genres}
        for conf in tslr.conformers.values():
            for key in bars.keys():
                bars[key] = bars[key] or key in conf
        spectra_available = [
            SpectralData.spectra_name_ref[bar] for bar, got in bars.items() if got
        ]
        radio = self.root.controls.calculate.s_name_radio
        for option, widget in radio.items():
            state = (
                "disabled" if not tslr or option not in spectra_available else "normal"
            )
            widget.configure(state=state)


class FeedbackThread(Thread):
    def __init__(self, gui, progbar_msg, target, args, kwargs):
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.progbar_msg = progbar_msg
        self.gui = gui
        self.queue = queue.Queue()
        super().__init__(daemon=True)

    def run(self):
        self.exc = None
        self.gui.progtext.set(self.progbar_msg)
        self.gui.progbar.configure(mode="indeterminate")
        self.gui.progbar.start()
        try:
            return_value = self.target(*self.args, **self.kwargs)
            self.queue.put(return_value)
        except BaseException as exc:
            self.exc = exc
        self.gui.progbar.stop()
        self.gui.progbar.configure(mode="determinate")
        self.gui.progtext.set("Idle.")
        if self.exc:
            logger.critical("Something unexpected happend.", exc_info=self.exc)
            return
            # raise self.exc
        else:
            return return_value


class ThreadedMethod:
    def __init__(self, progbar_msg):
        self.progbar_msg = progbar_msg

    def __call__(self, function):
        def wrapper(widget, *args, **kwargs):
            # widget is `self` from decorated method
            root = widget.winfo_toplevel()
            if root.thread.is_alive():
                msg = "Can't start {}, while {} is still running.".format(
                    function, root.thread.target
                )
                logger.info(msg)
                return  # log and do nothing
            else:
                root.thread = FeedbackThread(
                    root,
                    self.progbar_msg,
                    function,
                    [widget] + list(args),
                    kwargs,
                )
            root.thread.start()

        return wrapper
