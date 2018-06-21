###################
###   IMPORTS   ###
###################

import os
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

from tkinter import messagebox
from tkinter.filedialog import askdirectory, askopenfilenames

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
        tk.Grid.columnconfigure(self, 3, weight=1)
        tk.Grid.rowconfigure(self, 10, weight=1)
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(column=0, row=0, columnspan=2, rowspan=10, sticky='nwe')
        # New session
        self.label_new = ttk.LabelFrame(buttons_frame, text='New session')
        self.label_new.grid(column=0, row=0, sticky='n')
        ttk.Button(self.label_new, text='Location', command=self.from_dir).grid(column=0, row=0)
        ttk.Button(self.label_new, text='From files', command=self.from_files).grid(column=1, row=0)

        # Extract
        self.label_extr = ttk.LabelFrame(buttons_frame, text='Extract')
        self.label_extr.grid(column=0, row=1, sticky='n')
        self.b_e_e = ttk.Button(self.label_extr, text='Energies', command=self.extract_energies)
        self.b_e_e.grid(column=0, row=0)
        self.b_e_b = ttk.Button(self.label_extr, text='Bars', command=self.get_wanted_bars)
        self.b_e_b.grid(column=1, row=0)
        guicom.WgtStateChanger.tslr.extend([self.b_e_e, self.b_e_b])

        # Calculate
        self.label_calc = ttk.LabelFrame(buttons_frame, text='Calculate')
        self.label_calc.grid(column=0, row=2, sticky='n')
        # self.b_c_p = ttk.Button(self.label_calc, text='Populations', command=self.calc_popul)
        # self.b_c_p.grid(column=0, row=0)
        self.b_c_s = ttk.Button(self.label_calc, text='Spectra', command=self.calc_spectra)
        self.b_c_s.grid(column=0, row=0)
        self.b_c_a = ttk.Button(self.label_calc, text='Average', command=self.calc_average)
        self.b_c_a.grid(column=1, row=0)
        guicom.WgtStateChanger.bars.append(self.b_c_s)
        guicom.WgtStateChanger.all.append(self.b_c_a)

        # Smart
        self.label_smart = ttk.LabelFrame(buttons_frame, text='Smart')
        self.label_smart.grid(column=0, row=3, sticky='n')
        self.b_s_e = ttk.Button(self.label_smart, text='Extract', command=self.smart_extract)
        self.b_s_e.grid(column=0, row=0)
        self.b_s_c = ttk.Button(self.label_smart, text='Calculate', command=self.not_impl)
        self.b_s_c.grid(column=1, row=0)
        # temporarly
        self.b_s_s = ttk.Button(self.label_smart, text='Save', command=self.not_impl)
        self.b_s_s.grid(column=1, row=1)
        guicom.WgtStateChanger.tslr.append(self.b_s_e)
        guicom.WgtStateChanger.bars.append(self.b_s_c)
        guicom.WgtStateChanger.either.append(self.b_s_s)

        # Export
        self.label_export = ttk.LabelFrame(buttons_frame, text='Export')
        self.label_export.grid(column=0, row=4, sticky='n')
        self.b_p_t = ttk.Button(self.label_export, text='Text', command=self.save_text)
        self.b_p_t.grid(column=0, row=0)
        self.b_p_e = ttk.Button(self.label_export, text='Excel', command=self.save_excel)
        self.b_p_e.grid(column=1, row=0)
        self.b_p_c = ttk.Button(self.label_export, text='CSV', command=self.save_csv)
        self.b_p_c.grid(column=1, row=1)
        guicom.WgtStateChanger.either.extend([self.b_p_t, self.b_p_e, self.b_p_c])

        # Load
        # self.label_load = ttk.LabelFrame(buttons_frame, text='Load')
        # self.label_load.grid(column=0, row=5, sticky='n')
        # self.b_l_p = ttk.Button(self.label_load, text='Populations')
        # self.b_l_p.grid(column=0, row=0)
        # self.b_l_b = ttk.Button(self.label_load, text='Bars')
        # self.b_l_b.grid(column=1, row=0)
        # self.b_l_s = ttk.Button(self.label_load, text='Spectra')
        # self.b_l_s.grid(column=0, row=1)
        # self.b_l_t = ttk.Button(self.label_load, text='Settings')
        # self.b_l_t.grid(column=1, row=1)
        # guicom.WgtStateChanger.tslr.extend([self.b_l_p, self.b_l_b, self.b_l_s, self.b_l_t])

        # #Dir frame
        # dir_frame = ttk.Frame(self)
        # dir_frame.grid(column=2, row=0, columnspan=3, rowspan=2, sticky='nwe')
        # tk.Grid.columnconfigure(dir_frame, 1, weight=1)

        # #Work dir
        # ttk.Label(dir_frame, text='Work dir').grid(column=0, row=0)
        # self.work_dir = tk.StringVar()
        # self.work_dir.set('Not specified.')
        # self.work_entry = ttk.Entry(dir_frame, textvariable=self.work_dir,
        # state='readonly')
        # self.work_entry.grid(column=1, row=0, sticky='we')
        # self.b_w_d = ttk.Button(dir_frame, text="Change",
        # command=self.change_work_dir)
        # self.b_w_d.grid(column=2, row=0, sticky='e')

        # #Output dir
        # ttk.Label(dir_frame, text='Output dir').grid(column=0, row=1)
        # self.out_dir = tk.StringVar()
        # self.out_dir.set('Not specified.')
        # self.out_entry = ttk.Entry(dir_frame, textvariable=self.out_dir,
        # state='readonly')
        # self.out_entry.grid(column=1, row=1, sticky='we')
        # self.b_o_d = ttk.Button(dir_frame, text="Change",
        # command=self.change_output_dir)
        # self.b_o_d.grid(column=2, row=1, sticky='e')
        # guicom.WgtStateChanger.tslr.extend([self.b_o_d, self.b_w_d])

        # Log window
        self.label_log = ttk.LabelFrame(self, text='Log')
        self.label_log.grid(column=2, row=0, columnspan=3, rowspan=2, sticky='nwe')
        self.log = guicom.ReadOnlyText(self.label_log, width=50, height=6, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=tk.YES)

        # Conformers Overview
        self.label_overview = ttk.LabelFrame(self, text='Conformers Overview')
        self.label_overview.grid(column=2, row=2, columnspan=3, rowspan=10, sticky='nwse')
        self.overview = guicom.ConformersOverview(self.label_overview, self)
        self.overview.frame.grid(column=0, row=0, sticky='nswe')
        # unify naes with ovweview in conformers tab
        tk.Grid.rowconfigure(self.label_overview, 0, weight=1)
        tk.Grid.columnconfigure(self.label_overview, 0, weight=1)

        # Progress bar
        self.progtext = tk.StringVar()
        self.progtext.set('Idle.')
        self.proglabel = ttk.Label(self, textvariable=self.progtext, anchor='w', foreground='gray')
        self.proglabel.grid(column=0, row=10, columnspan=2, sticky='sw')
        self.progbar = ttk.Progressbar(self, orient=tk.HORIZONTAL, mode='indeterminate')
        self.progbar.grid(column=0, row=11, columnspan=2, sticky='swe')

    def not_impl(self):
        messagebox.showinfo("Sorry!",
                            "We are sorry, but this function is not implemented yet.")

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

    @guicom.WgtStateChanger
    def from_dir(self):
        proceed = self.clear_session()
        if not proceed: return
        new_dir = askdirectory()
        if not new_dir: return
        self.instantiate_tslr(new_dir)

    @guicom.WgtStateChanger
    def from_files(self):
        proceed = self.clear_session()
        if not proceed: return
        files = askopenfilenames(
            filetypes=[("log files", "*.log"), ("out files", "*.out")],
            defaultextension='.log'
        )
        if not files: return
        new_dir = os.path.split(files[0])[0]
        filenames = list(map(lambda p: os.path.split(p)[1], files))
        self.instantiate_tslr(new_dir, filenames)

    @guicom.Feedback('Starting new session...')
    def instantiate_tslr(self, new_dir, filenames=None):
        try:
            self.parent.tslr = tesliper.Tesliper(new_dir,
                                                 wanted_files=filenames)
        except:
            self.parent.logger.critical(
                "Sorry! An error occurred during new session instantiation.",
                exc_info=True)
        else:
            self.parent.logger.info(
                "New session instantiated successfully!"
            )
        self.work_dir.set(self.parent.tslr.input_dir)
        self.out_dir.set(self.parent.tslr.output_dir)
        self.parent.conf_tab.make_new_conf_list()

    def change_work_dir(self):
        new_dir = askdirectory()
        if not new_dir: return
        self.parent.tslr.change_dir(input_dir=new_dir)
        self.work_dir.set(self.parent.tslr.input_dir)

    def change_output_dir(self):
        new_dir = askdirectory()
        if not new_dir: return
        self.parent.tslr.change_dir(output_dir=new_dir)
        self.out_dir.set(self.parent.tslr.output_dir)

    @guicom.Feedback('Extracting...')
    def extract_energies(self):
        if not self.parent.conf_tab.established:
            self.parent.tslr.extract('energies', 'iri')
            if self.parent.tslr.energies:
                self.parent.conf_tab.establish()
        else:
            self.parent.logger.warning('Energies already extracted.')

    @guicom.Feedback('Extracting...')
    def execute_extract_bars(self, query):
        self.parent.tslr.extract(*query)
        if self.parent.tslr.bars:
            self.parent.conf_tab.unify_data()
        # self.parent.conf_tab.show_imag()
        # self.parent.conf_tab.establish()

    @guicom.Feedback('Extracting...')
    def smart_extract(self):
        self.parent.tslr.smart_extract()
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
