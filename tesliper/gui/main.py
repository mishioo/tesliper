###################
###   IMPORTS   ###
###################

import os
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

from tkinter import messagebox
from threading import Thread

from . import components as guicom
from .tab_loader import Loader
from .tab_spectra import Spectra
from .tab_energies import Conformers

from .. import tesliper

# from ..tesliper import __version__, __author__
_DEVELOPEMENT = True


###################
###   CLASSES   ###
###################


class TesliperApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Tesliper")
        self.tslr = None
        self.thread = Thread()

        self.report_callback_exception = self.report_callback_exception
        self.validate_entry = (self.register(self.validate_entry), '%S', '%P')
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Notebook
        tk.Grid.columnconfigure(self, 0, weight=1)
        tk.Grid.rowconfigure(self, 0, weight=1)
        self.notebook = ttk.Notebook(self)
        self.main_tab = Loader(self)
        self.notebook.add(self.main_tab, text='Main')
        self.spectra_tab = Spectra(self)
        self.notebook.add(self.spectra_tab, text='Spectra')
        self.conf_tab = Conformers(self)
        self.notebook.add(self.conf_tab, text='Conformers')
        # self.info_tab = ttk.Frame(self)
        # self.add(self.info_tab, text='Info')
        self.notebook.grid(column=0, row=0, sticky='nswe')

        # Log & Bar frame
        bottom_frame = tk.Frame(self)
        bottom_frame.grid(column=0, row=1, sticky='nswe')
        tk.Grid.columnconfigure(bottom_frame, 1, weight=1)
        tk.Grid.rowconfigure(bottom_frame, 0, weight=1)

        # Progress bar
        self.progbar = ttk.Progressbar(
            bottom_frame, length=185, orient=tk.HORIZONTAL, mode='determinate'
        )
        self.progbar.grid(column=0, row=0, sticky='sw')
        self.progtext = tk.StringVar()
        self.progtext.set('Idle.')
        self.proglabel = ttk.Label(
            bottom_frame, textvariable=self.progtext, anchor='w',
            foreground='gray'
        )
        self.proglabel.grid(column=1, row=0, sticky='swe')

        # Log window
        # displayed in separate, optional window
        self.log = guicom.ReadOnlyText(
            self, width=50, height=34, wrap=tk.WORD
        )
        ttk.Button(
            bottom_frame, text='Display log', command=self.log.show
        ).grid(column=2, row=0, sticky='se')

        # Logger & handlers
        self.logger = lgg.getLogger(__name__)
        self.loggers = [self.logger, guicom.logger] + tesliper.loggers
        text_handler = guicom.TextHandler(self.log)
        text_handler.setLevel(lgg.INFO)
        text_handler.addFilter(guicom.MaxLevelFilter(lgg.INFO))

        text_warning_handler = guicom.TextHandler(self.log)
        text_warning_handler.setLevel(lgg.WARNING)
        text_warning_handler.addFilter(guicom.MaxLevelFilter(lgg.WARNING))
        text_warning_handler.setFormatter(lgg.Formatter(
            '%(levelname)s: %(message)s'))

        self.error_location = os.getcwd()
        self.error_msg = (
            "Please provide a problem description to Tesliper's "
            "developer along with tslr_err_log.txt file, witch can be "
            "found here: {}".format(self.error_location)
        )
        text_error_handler = guicom.TextHandler(self.log)
        text_error_handler.setLevel(lgg.ERROR)
        text_error_handler.setFormatter(guicom.ShortExcFormatter(
            'ERROR! %(message)s \n' + self.error_msg))

        error_handler = lgg.FileHandler(
            os.path.join(self.error_location, 'tslr_err_log.txt'), delay=True)
        error_handler.setLevel(lgg.ERROR)
        error_handler.setFormatter(lgg.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'))

        self.handlers = [
            text_handler,
            text_warning_handler,
            text_error_handler,
            error_handler]
        for lgr in self.loggers:
            lgr.setLevel(lgg.DEBUG)
            for hdlr in self.handlers:
                lgr.addHandler(hdlr)
        if _DEVELOPEMENT:
            # for purposes of debugging
            self.logger.addHandler(tesliper.mainhandler)
            guicom.logger.addHandler(tesliper.mainhandler)

        # WgtStateChanger
        guicom.WgtStateChanger.gui = self
        self.new_session()
        guicom.WgtStateChanger.set_states()

        self.logger.info(
            'Welcome to Tesliper:\n'
            'Theoretical Spectroscopist Little Helper!'
        )

    def validate_entry(self, inserted, text_if_allowed):
        if any(i not in '0123456789.,+-' for i in inserted):
            return False
        else:
            if text_if_allowed in '.,+-':
                return True
            if text_if_allowed in map(''.join, zip('+-+-', '..,,')):
                return True
            try:
                if text_if_allowed:
                    float(text_if_allowed.replace(',', '.'))
            except ValueError:
                return False
        return True

    def entry_out_validation(self, var):
        value = var.get()
        if ',' in value:
            value = value.replace(',', '.')
        if value.endswith(('.', '+', '-')):
            value = value + '0'
        if value.startswith('+'):
            value = value[1:]
        if value.startswith(('.', '-.')):
            value = value.replace('.', '0.')
        var.set(value)

    def report_callback_exception(self, exc, val, tb):
        self.logger.critical('An unexpected error occurred.', exc_info=True)

    @guicom.WgtStateChanger
    def new_session(self):
        if self.tslr is not None:
            pop = messagebox.askokcancel(
                message='Are you sure you want to start new session? '
                        'Any unsaved changes will be lost!',
                title='New session', icon='warning', default='cancel')
            if not pop:
                return
        # make new Tesliper instance
        self.tslr = tesliper.Tesliper()
        # establish new overview
        if self.main_tab.overview is not None:
            self.main_tab.overview.destroy()
            for checked, _all, __ in self.main_tab.overview_control.values():
                checked.set(0)
                _all.set(0)
        self.main_tab.overview = guicom.ConformersOverview(
            self.main_tab.label_overview, self.main_tab
        )
        self.main_tab.overview.frame.grid(column=0, row=0, sticky='nswe')
        # establish new conf_list
        if self.conf_tab.conf_list is not None:
            self.conf_tab.conf_list.destroy()
        self.conf_tab.conf_list = guicom.EnergiesView(self.conf_tab.overview,
                                                      parent_tab=self.conf_tab)
        self.conf_tab.conf_list.frame.grid(column=0, row=0, sticky='nswe')
        self.conf_tab.established = False
        # clear spectra tab
        # TO DO: clear other axes
        # TO DO: make sure to clear comboboxes and stored settings
        # maybe would be easier to create new tabs?
        if self.spectra_tab.tslr_ax:
            self.spectra_tab.figure.delaxes(self.spectra_tab.tslr_ax)
            self.spectra_tab.tslr_ax = None
            self.spectra_tab.canvas.show()

    def on_closing(self):
        if self.thread.is_alive():
            quit_ = messagebox.askyesno(
                message='Tesliper is still running an operation. '
                        'Do you wish to force exit?',
                title='Exit?', icon='warning', default='no'
            )
            if not quit_:
                return
        self.destroy()
