###################
###   IMPORTS   ###
###################

import os
import traceback
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

from threading import Thread

from . import components as guicom
from .tab_loader import Loader
from .tab_spectra import Spectra
from .tab_energies import Conformers

from ..tesliper import tesliper
# from ..tesliper import __version__, __author__
_DEVELOPEMENT = False


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
        guicom.WgtStateChanger().set_states(self.main_tab)

        # Log & Bar frame
        bottom_frame = tk.Frame(self)
        bottom_frame.grid(column=0, row=1, sticky='nswe')
        tk.Grid.columnconfigure(bottom_frame, 1, weight=1)
        tk.Grid.rowconfigure(bottom_frame, 0, weight=1)

        # Log window
        self.label_log = ttk.LabelFrame(bottom_frame, text='Log')
        self.label_log.grid(column=1, row=0, columnspan=4, rowspan=2, sticky='swe')
        self.log = guicom.ReadOnlyText(self.label_log, width=50, height=4, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=tk.YES)

        # Progress bar
        self.progtext = tk.StringVar()
        self.progtext.set('Idle.')
        self.proglabel = ttk.Label(bottom_frame, textvariable=self.progtext, anchor='w', foreground='gray')
        self.proglabel.grid(column=0, row=0, sticky='sw')
        self.progbar = ttk.Progressbar(bottom_frame, length=170, orient=tk.HORIZONTAL, mode='indeterminate')
        self.progbar.grid(column=0, row=1, sticky='swe')

        
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
            #for purposes of debugging
            self.logger.addHandler(tesliper.mainhandler)
            guicom.logger.addHandler(tesliper.mainhandler)

        self.logger.info(
            'Welcome to Tesliper:\n'
            'Theoretical Spectroscopist Little Helper!'
        )
          
        
    def validate_entry(self, inserted, text_if_allowed):
        if any(i not in '0123456789.,+-' for i in inserted):
            return False
        else:
            if text_if_allowed in '.,+-': return True
            if text_if_allowed in map(''.join, zip('+-+-', '..,,')):
                return True
            try:
                if text_if_allowed: float(text_if_allowed.replace(',', '.'))
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

        