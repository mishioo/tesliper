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
        self._genres = _DerivedDefaultDict(
            lambda g, r=self.root: r.tslr.conformers.has_genre(g)
        )
        self._standards = {
            "energies": self._energies,
            "bars": self._bars,
            "tesliper": self._tesliper,
        }

    def _energies(self):
        return any(self._genres[g] for g in self.energies_genres)

    def _bars(self):
        return any(self._genres[g] for g in self.bars_genres)

    def _tesliper(self):
        return bool(self.root.tslr.conformers)

    def register(
        self,
        widgets,
        dependencies=None,
        needs_all_genres=None,
        needs_any_genre=None,
        key=None,
    ):
        if isinstance(dependencies, str):
            dependencies = [dependencies]
        elif dependencies is None:
            dependencies = []
        for dep in dependencies:
            if dep not in self._standards:
                raise ValueError(f"Unknown dependency: {dep}.")
        if not isinstance(widgets, Iterable):
            widgets = [widgets]
        for wgt in widgets:

            def _conditions(
                obj=self,
                deps=dependencies,
                allg=needs_all_genres,
                anyg=needs_any_genre,
                key=key,
            ):
                dep_ = all(obj._standards[d]() for d in deps)
                all_ = all(obj._genres[g] for g in allg) if allg else True
                any_ = any(obj._genres[g] for g in anyg) if anyg else True
                key_ = key() if key else True
                return all([dep_, all_, any_, key_])

            self._dependencies[wgt] = _conditions

    def set_states(self):
        self._genres.clear()
        for widget, condition in self._dependencies.items():
            changer = self.enable if condition() else self.disable
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
