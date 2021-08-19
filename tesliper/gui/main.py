# IMPORTS
import logging
import os
import tkinter as tk
import tkinter.ttk as ttk
from threading import Thread
from tkinter import messagebox

from .. import tesliper
from .components import (
    ConformersOverview,
    EnergiesView,
    MaxLevelFilter,
    PopupHandler,
    ReadOnlyText,
    ShortExcFormatter,
    TextHandler,
    WgtStateChanger,
)
from .tab_energies import Conformers
from .tab_loader import Loader
from .tab_spectra import Spectra

_DEVELOPMENT = "ENV" in os.environ and os.environ["ENV"] == "prod"


# LOGGER
logger = logging.getLogger(__name__)
home_path = os.path.expanduser("~")
ERROR_LOG_DIR = os.path.join(home_path, "tesliper")
os.makedirs(ERROR_LOG_DIR, exist_ok=True)
error_msg = (
    "Please provide a problem description to Tesliper's "
    'developer along with "tslr_err_log.txt" file, witch can be '
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
class TesliperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tesliper")
        self.tslr = tesliper.Tesliper()
        self.thread = Thread()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Notebook
        tk.Grid.columnconfigure(self, 0, weight=1)
        tk.Grid.rowconfigure(self, 0, weight=1)
        self.notebook = ttk.Notebook(self)
        self.main_tab = None
        self.spectra_tab = None
        self.conf_tab = None
        self.notebook.grid(column=0, row=0, sticky="nswe")

        # Log & Bar frame
        bottom_frame = tk.Frame(self)
        bottom_frame.grid(column=0, row=1, sticky="nswe")
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

        # WgtStateChanger
        WgtStateChanger.gui = self
        self.new_session()
        WgtStateChanger.set_states()

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

    def report_callback_exception(self, exc, val, tb):
        self.logger.critical("An unexpected error occurred.", exc_info=True)

    @WgtStateChanger
    def new_session(self):
        if self.tslr.conformers:
            pop = messagebox.askokcancel(
                message="Are you sure you want to start new session? "
                "Any unsaved changes will be lost!",
                title="New session",
                icon="warning",
                default="cancel",
            )
            if not pop:
                return
        self.tslr = tesliper.Tesliper()
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
        self.main_tab = Loader(self)
        self.notebook.add(self.main_tab, text="Main")
        self.spectra_tab = Spectra(self)
        self.notebook.add(self.spectra_tab, text="Spectra")
        self.conf_tab = Conformers(self)
        self.notebook.add(self.conf_tab, text="Conformers")
        # establish new overview
        if self.main_tab.overview is not None:
            self.main_tab.overview.destroy()
            for checked, _all, __ in self.main_tab.overview_control.values():
                checked.set(0)
                _all.set(0)
        self.main_tab.overview = ConformersOverview(
            self.main_tab.label_overview, self.main_tab
        )
        self.main_tab.overview.frame.grid(column=0, row=0, sticky="nswe")
        # establish new conf_list
        if self.conf_tab.conf_list is not None:
            self.conf_tab.conf_list.destroy()
        self.conf_tab.conf_list = EnergiesView(
            self.conf_tab.overview, parent_tab=self.conf_tab
        )
        self.conf_tab.conf_list.frame.grid(column=0, row=0, sticky="nswe")
        self.conf_tab.established = False

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
