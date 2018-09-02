###################
###   IMPORTS   ###
###################

import os
import logging as lgg
from collections import namedtuple
import tkinter as tk
import tkinter.ttk as ttk

from tkinter import messagebox
from tkinter.filedialog import askdirectory

from . import components as guicom
from .. import tesliper

_DEVELOPEMENT = False


###################
###   CLASSES   ###
###################

class Loader(ttk.Frame):

    def __init__(self, parent):
        """
        TO DO
        -----
        don't allow energy extraction if already extracted
        """
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky='nwse')
        tk.Grid.columnconfigure(self, 2, weight=1)
        tk.Grid.rowconfigure(self, 2, weight=1)

        # Extract data
        extract_frame = ttk.LabelFrame(self, text='Extract data...')
        extract_frame.grid(column=0, row=0, columnspan=2, sticky='nwe')
        tk.Grid.columnconfigure(extract_frame, 0, weight=1)
        self.b_auto_extract = ttk.Button(
            extract_frame, text='Choose folder', command=self.from_dir
        )
        self.b_auto_extract.grid(column=0, row=0, sticky='nwe')
        self.b_man_extract = ttk.Button(
            extract_frame, text='Choose files', command=self.man_extract
        )
        self.b_man_extract.grid(column=0, row=1, sticky='nwe')

        # Session control
        buttons_frame = ttk.LabelFrame(self, text="Session control", width=90)
        buttons_frame.grid(column=0, row=1, columnspan=2, sticky='nwe')
        tk.Grid.columnconfigure(buttons_frame, (0,1), weight=1)
        self.b_clear_session = ttk.Button(
            buttons_frame, text='Clear session', command=self.parent.new_session
        )
        self.b_clear_session.grid(column=0, row=2, sticky='nwe')
        guicom.WgtStateChanger.either.append(self.b_clear_session)

        self.b_calc = ttk.Button(
            buttons_frame, text='Auto calculate', command=self.not_impl
        )
        self.b_calc.grid(column=0, row=0, sticky='nwe')
        guicom.WgtStateChanger.bars.append(self.b_calc)

        self.b_text_export = ttk.Button(
            buttons_frame, text='Export as .txt', command=self.save_text
        )
        self.b_text_export.grid(column=1, row=0, sticky='nwe')
        self.b_excel_export = ttk.Button(
            buttons_frame, text='Export as .xls', command=self.save_excel
        )
        self.b_excel_export.grid(column=1, row=1, sticky='nwe')
        self.b_csv_export = ttk.Button(
            buttons_frame, text='Export as .csv', command=self.save_csv
        )
        self.b_csv_export.grid(column=1, row=2, sticky='nwe')
        guicom.WgtStateChanger.either.extend(
            [self.b_text_export, self.b_excel_export, self.b_csv_export]
        )

        # Overview control
        self.overview_control_frame = ttk.Labelframe(
            self, text="Overview control", width=90
        )
        self.overview_control_frame.grid(
            column=0, row=2, columnspan=2, sticky='nswe'
        )
        tk.Grid.columnconfigure(self.overview_control_frame, 4, weight=1)
        overview_vars = namedtuple('overview', ['checked', 'all', 'button'])
        self.overview_control = dict()
        for i, name in enumerate('Files Energy IR VCD UV ECD RAM ROA'.split(' ')):
            tk.Label(self.overview_control_frame, text=name, anchor='w'
                     ).grid(column=0, row=i)
            var_checked = tk.IntVar(value=0)
            tk.Label(self.overview_control_frame, textvariable=var_checked
                     ).grid(column=1, row=i)
            tk.Label(self.overview_control_frame, text='/').grid(column=2, row=i)
            var_all = tk.IntVar(value=0)
            tk.Label(self.overview_control_frame, textvariable=var_all
                     ).grid(column=3, row=i)
            butt = ttk.Button(self.overview_control_frame, text='un/check')
            butt.grid(column=4, row=i, sticky='ne')
            self.overview_control[name.lower()] = overview_vars(
                var_checked, var_all, butt
            )

        # Conformers Overview
        self.label_overview = ttk.LabelFrame(self, text='Conformers Overview')
        self.label_overview.grid(column=2, row=0, columnspan=3, rowspan=3, sticky='nwse')
        self.overview = None
        # unify naes with overview in conformers tab
        tk.Grid.rowconfigure(self.label_overview, 0, weight=1)
        tk.Grid.columnconfigure(self.label_overview, 0, weight=1)

    def not_impl(self):
        messagebox.showinfo(
            "Sorry!",
            "We are sorry, but this function is not implemented yet."
        )

    def get_save_output(self):
        popup = guicom.ExportPopup(self, width='220', height='130')
        query = popup.get_query()
        return query

    @guicom.Feedback('Saving...')
    def execute_save_command(self, output, format):
        self.parent.tslr.writer.save_output(output, format)

    @guicom.Feedback('Saving...')
    def save(self):
        pass

    def save_text(self):
        output = self.get_save_output()
        if not output: return
        self.execute_save_command(output, format='txt')

    def save_excel(self):
        output = self.get_save_output()
        if not output: return
        self.execute_save_command(output, format='xlsx')

    def save_csv(self):
        output = self.get_save_output()
        if not output: return
        self.execute_save_command(output, format='csv')

    @guicom.WgtStateChanger
    def clear_session(self):
        if self.parent.tslr:
            pop = messagebox.askokcancel(
                message='Are you sure you want to start new session? Any unsaved '
                        'changes will be lost!',
                title='New session', icon='warning', default='cancel')
            if pop:
                if self.parent.tslr:
                    self.parent.tslr = None
                if self.parent.conf_tab.conf_list:
                    self.parent.conf_tab.conf_list.destroy()
                    self.parent.conf_tab.conf_list = None
                    self.parent.conf_tab.established = False
                if self.parent.spectra_tab.ax:
                    self.parent.spectra_tab.figure.delaxes(
                        self.parent.spectra_tab.ax)
                    self.parent.spectra_tab.ax = None
                    self.parent.spectra_tab.canvas.show()
            else:
                return False
        self.parent.logger.info('\nStarting new session...')
        return True

    def from_dir(self):
        work_dir = askdirectory()
        if not work_dir: return
        self.extract(path=work_dir)

    @guicom.WgtStateChanger
    def man_extract(self):
        # proceed = self.clear_session()
        # if not proceed: return
        # files = askopenfilenames(
        #     filetypes=[("log files", "*.log"), ("out files", "*.out"),
        #                ("all files", "*.*")],
        #     defaultextension='.log'
        # )
        # if not files: return
        # new_dir = os.path.split(files[0])[0]
        # filenames = list(map(lambda p: os.path.split(p)[1], files))
        # self.instantiate_tslr(new_dir, filenames)
        popup = guicom.ExtractPopup(self)
        popup.wait_window()
        query, sox = popup.query, popup.soxhlet
        if not query: return
        self.parent.tslr.soxhlet = sox
        self.extract(query)

    @guicom.Feedback('Extracting...')
    def extract(self, path):
        self.parent.tslr.extract(path)
        if not self.parent.conf_tab.established:
            if self.parent.tslr.energies:
                self.parent.conf_tab.establish()
        elif self.parent.tslr.bars:
            self.parent.conf_tab.unify_data()

    @guicom.Feedback('Calculating populations...')
    def calc_popul(self):
        self.parent.tslr.calculate_populations()

    @guicom.Feedback('Calculating spectra...')
    def calc_spectra(self):
        self.parent.tslr.calculate_spectra()

    @guicom.Feedback('Averaging spectra...')
    def calc_average(self):
        tslr = self.parent.tslr
        for spc in tslr.spectra.values():
            averaged = [spc.average(en) for en in tslr.energies.values()]

    def get_wanted_bars(self):
        popup = guicom.BarsPopup(self, width='250', height='190')
