# IMPORTS
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from threading import Thread
from copy import copy
from functools import partial, wraps
import queue

from ...glassware.arrays import Bars


# LOGGER
logger = lgg.getLogger(__name__)


# CLASSES
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

    def __init__(self, *args, title_msg='', **kwargs):
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
        molecules = WgtStateChanger.gui.tslr.molecules
        bars, energies = False, False
        for mol in molecules.trimmed_values():
            bars = bars or any(
                key in mol for key in
                'dip rot vosc vrot losc lrot raman1 roa1'.split()
            )
            energies = energies or all(
                key in mol for key in 'zpe ent ten gib scf'.split()
            )
        spectra = bool(WgtStateChanger.gui.tslr.spectra)
        return dict(
            tslr=self.enable if molecules else self.disable,
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
        bars = {
            k: False for k in 'dip rot vosc vrot losc lrot raman1 roa1'.split()
        }
        for mol in tslr.molecules.values():
            for key in bars.keys():
                bars[key] = bars[key] or key in mol
        spectra_available = [
            Bars.spectra_name_ref[bar] for bar, got in bars.items() if got
        ]
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