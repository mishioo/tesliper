# IMPORTS
import logging
import os
import tkinter as tk
import tkinter.ttk as ttk
from threading import Thread
from tkinter import messagebox

from .. import tesliper
from .._metadata import __version__
from .components import (
    CheckTree,
    ConformersOverview,
    EnergiesView,
    MaxLevelFilter,
    PopupHandler,
    ReadOnlyText,
    ScrollableFrame,
    ShortExcFormatter,
    SpectraView,
    TextHandler,
    ThreadedMethod,
    WgtStateChanger,
)
from .components.controls import (
    CalculateSpectra,
    ExportData,
    ExtractData,
    FilterEnergies,
    SelectConformers,
)

_DEVELOPMENT = "ENV" in os.environ and os.environ["ENV"] == "prod"


# LOGGER
logger = logging.getLogger(__name__)
home_path = os.path.expanduser("~")
ERROR_LOG_DIR = os.path.join(home_path, "tesliper")
os.makedirs(ERROR_LOG_DIR, exist_ok=True)
error_msg = (
    "Please provide a problem description to Tesliper's "
    'developer along with "tslr_err_log.txt" file, which can be '
    f"found here:\n{ERROR_LOG_DIR}"
)
error_handler = logging.FileHandler(
    os.path.join(ERROR_LOG_DIR, "tslr_err_log.txt"), delay=True
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s\n")
)
error_popup_handler = PopupHandler(title_msg="Something unexpected happened! :(")
error_popup_handler.setLevel(logging.ERROR)
error_popup_handler.setFormatter(ShortExcFormatter("%(message)s \n\n" + error_msg))
warning_popup_handler = PopupHandler(title_msg="Sorry!")
warning_popup_handler.setLevel(logging.WARNING)
warning_popup_handler.addFilter(MaxLevelFilter(logging.WARNING))
warning_popup_handler.setFormatter(ShortExcFormatter("%(message)s \n\n"))

handlers = [error_handler, error_popup_handler, warning_popup_handler]

ROOT_LOGGER = logging.getLogger("")
ROOT_LOGGER.setLevel(logging.DEBUG if _DEVELOPMENT else logging.INFO)
for hdlr in handlers:
    ROOT_LOGGER.addHandler(hdlr)
if _DEVELOPMENT:
    # for purposes of debugging
    ROOT_LOGGER.addHandler(tesliper.mainhandler)


# CLASSES
class ViewsNotebook(ttk.Notebook):
    def __init__(self, parent):
        super().__init__(parent)

        self.extract = ConformersOverview(self)
        self.add(self.extract.frame, text="Extracted data")

        self.energies = EnergiesView(self)
        self.add(self.energies.frame, text="Energies list")

        self.spectra = SpectraView(self)
        self.add(self.spectra, text="Spectra view")


class ControlsFrame(ScrollableFrame):
    def __init__(self, parent, extract_view, energies_view, spectra_view, **kwargs):
        super(ControlsFrame, self).__init__(parent, **kwargs)
        tk.Grid.columnconfigure(self, 1, weight=1)

        self.extract = ExtractData(self.content, view=extract_view)
        self.extract.grid(column=0, row=0, sticky="new")
        self.export = ExportData(self.content)
        self.export.grid(column=0, row=1, sticky="new")
        self.select = SelectConformers(self.content, view=extract_view)
        self.select.grid(column=0, row=2, sticky="new")
        self.filter = FilterEnergies(parent=self.content, view=energies_view)
        self.filter.grid(column=0, row=3, sticky="new")
        self.calculate = CalculateSpectra(self.content, view=spectra_view)
        self.calculate.grid(column=0, row=4, sticky="new")


class TesliperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Tesliper v. {__version__}")
        self.thread = Thread()
        self.changer = WgtStateChanger(self)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        tk.Grid.columnconfigure(self, 1, weight=1)
        tk.Grid.rowconfigure(self, 0, weight=1)

        self.tesliper = tesliper.Tesliper()
        self.notebook = ViewsNotebook(self)
        self.notebook.grid(column=1, row=0, sticky="nswe")
        self.controls = ControlsFrame(
            self,
            extract_view=self.notebook.extract,
            energies_view=self.notebook.energies,
            spectra_view=self.notebook.spectra,
        )
        self.controls.grid(column=0, row=0, sticky="nswe")

        # Log & Bar frame
        bottom_frame = tk.Frame(self)
        bottom_frame.grid(column=0, row=1, columnspan=2, sticky="nswe")
        tk.Grid.columnconfigure(bottom_frame, 1, weight=1)
        tk.Grid.rowconfigure(bottom_frame, 0, weight=1)

        # Progress bar
        self.progbar = ttk.Progressbar(
            bottom_frame, length=185, orient=tk.HORIZONTAL, mode="determinate"
        )
        self.progbar.grid(column=0, row=0, sticky="sw")
        self.progtext = tk.StringVar()
        self.progtext.set("Idle.")
        self.proglabel = ttk.Label(
            bottom_frame, textvariable=self.progtext, anchor="w", foreground="gray"
        )
        self.proglabel.grid(column=1, row=0, sticky="swe")

        # Log window
        # displayed in separate, optional window
        self.log = ReadOnlyText(self, width=50, height=34, wrap=tk.WORD)
        ttk.Button(bottom_frame, text="Display log", command=self.log.show).grid(
            column=2, row=0, sticky="se"
        )

        # Logger & handlers
        self.logger = logger
        text_handler = TextHandler(self.log)
        text_handler.setLevel(logging.INFO)
        text_handler.addFilter(MaxLevelFilter(logging.INFO))

        text_warning_handler = TextHandler(self.log)
        text_warning_handler.setLevel(logging.WARNING)
        text_warning_handler.addFilter(MaxLevelFilter(logging.WARNING))
        text_warning_handler.setFormatter(
            logging.Formatter("%(levelname)s: %(message)s")
        )

        text_error_handler = TextHandler(self.log)
        text_error_handler.setLevel(logging.ERROR)
        text_error_handler.setFormatter(
            ShortExcFormatter("ERROR! %(message)s \n" + error_msg)
        )
        text_handlers = [
            text_error_handler,
            text_handler,
            text_warning_handler,
        ]
        for handler in text_handlers:
            ROOT_LOGGER.addHandler(handler)

        self.bind("<<DataExtracted>>", lambda _: self.changer.set_states(), add="+")
        self.bind("<<KeptChanged>>", lambda _: self.changer.set_states(), add="+")

        self.logger.info(
            "Welcome to Tesliper:\n" "Theoretical Spectroscopist Little Helper!"
        )
        try:
            iconpath = os.path.abspath(os.path.realpath(__file__))
            iconpath = os.path.split(os.path.split(iconpath)[0])[0]
            self.iconbitmap(os.path.join(iconpath, "tesliper.ico"))
            self.log.window.iconbitmap(os.path.join(iconpath, "tesliper.ico"))
        except tk.TclError:
            self.logger.warning("Cannot load icon.")

        self.changer.set_states()

    def report_callback_exception(self, exc, val, tb):
        self.logger.critical("An unexpected error occurred.", exc_info=True)

    @ThreadedMethod(progbar_msg="Loading session...")
    def new_tesliper(self, source=None):
        if not source:
            self.tesliper = tesliper.Tesliper()
        else:
            self.tesliper = tesliper.Tesliper.load(source)
            view = self.notebook.extract
            for file, data in self.tesliper.conformers.items():
                view.insert("", tk.END, text=file)
            self.event_generate("<<DataExtracted>>")

    def new_session(self):
        if self.tesliper and self.tesliper.conformers:
            pop = messagebox.askokcancel(
                message="This action will clear the current session "
                "And any unsaved changes will be lost!\n"
                "Would you like to proceed?",
                title="Unsaved changes will be lost!",
                icon="warning",
                default="cancel",
            )
            if not pop:
                return
        self.tesliper.clear()
        self.event_generate("<<Clear>>")
        self.changer.set_states()

    def on_closing(self):
        if self.thread.is_alive():
            quit_ = messagebox.askyesno(
                message="Tesliper is still running an operation. "
                "Do you wish to force exit?",
                title="Exit?",
                icon="warning",
                default="no",
            )
            if not quit_:
                return
        self.destroy()
