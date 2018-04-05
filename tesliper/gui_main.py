###################
###   IMPORTS   ###
###################

import os
import traceback
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

from copy import copy
from functools import reduce
from itertools import zip_longest, cycle
from tkinter import messagebox
from tkinter.filedialog import askdirectory, askopenfilenames
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import cm
from threading import Thread

import tesliper.gui_components as guicom

import tesliper.tesliper as tesliper
from tesliper.tesliper import __version__, __author__
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
        #New session
        self.label_new = ttk.LabelFrame(buttons_frame, text='New session')
        self.label_new.grid(column=0, row=0, sticky='n')
        ttk.Button(self.label_new, text='Location', command=self.from_dir).grid(column=0, row=0)
        ttk.Button(self.label_new, text='From files', command=self.from_files).grid(column=1, row=0)
        
        #Extract
        self.label_extr = ttk.LabelFrame(buttons_frame, text='Extract')
        self.label_extr.grid(column=0, row=1, sticky='n')
        self.b_e_e = ttk.Button(self.label_extr, text='Energies', command=self.extract_energies)
        self.b_e_e.grid(column=0, row=0)
        self.b_e_b = ttk.Button(self.label_extr, text='Bars', command=self.get_wanted_bars)
        self.b_e_b.grid(column=1, row=0)
        guicom.WgtStateChanger.tslr.extend([self.b_e_e, self.b_e_b])

        #Calculate
        self.label_calc = ttk.LabelFrame(buttons_frame, text='Calculate')
        self.label_calc.grid(column=0, row=2, sticky='n')
        #self.b_c_p = ttk.Button(self.label_calc, text='Populations', command=self.calc_popul)
        #self.b_c_p.grid(column=0, row=0)
        self.b_c_s = ttk.Button(self.label_calc, text='Spectra', command=self.calc_spectra)
        self.b_c_s.grid(column=0, row=0)
        self.b_c_a = ttk.Button(self.label_calc, text='Average', command=self.calc_average)
        self.b_c_a.grid(column=1, row=0)
        guicom.WgtStateChanger.bars.append(self.b_c_s)
        guicom.WgtStateChanger.all.append(self.b_c_a)

        #Smart
        self.label_smart = ttk.LabelFrame(buttons_frame, text='Smart')
        self.label_smart.grid(column=0, row=3, sticky='n')
        self.b_s_e = ttk.Button(self.label_smart, text='Extract', command=self.smart_extract)
        self.b_s_e.grid(column=0, row=0)
        self.b_s_c = ttk.Button(self.label_smart, text='Calculate', command=self.not_impl)
        self.b_s_c.grid(column=1, row=0)
        #temporarly
        self.b_s_s = ttk.Button(self.label_smart, text='Save', command=self.not_impl)
        self.b_s_s.grid(column=1, row=1)
        guicom.WgtStateChanger.tslr.append(self.b_s_e)
        guicom.WgtStateChanger.bars.append(self.b_s_c)
        guicom.WgtStateChanger.either.append(self.b_s_s)
        
        #Export
        self.label_export = ttk.LabelFrame(buttons_frame, text='Export')
        self.label_export.grid(column=0, row=4, sticky='n')
        self.b_p_t = ttk.Button(self.label_export, text='Text', command=self.save_text)
        self.b_p_t.grid(column=0, row=0)
        self.b_p_e = ttk.Button(self.label_export, text='Excel', command=self.save_excel)
        self.b_p_e.grid(column=1, row=0)
        self.b_p_c = ttk.Button(self.label_export, text='CSV', command=self.save_csv)
        self.b_p_c.grid(column=1, row=1)
        guicom.WgtStateChanger.either.extend([self.b_p_t, self.b_p_e, self.b_p_c])

        #Load
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
        
        #Dir frame
        dir_frame = ttk.Frame(self)
        dir_frame.grid(column=2, row=0, columnspan=3, rowspan=2, sticky='nwe')
        tk.Grid.columnconfigure(dir_frame, 1, weight=1)
        
        #Work dir
        ttk.Label(dir_frame, text='Work dir').grid(column=0, row=0)
        self.work_dir = tk.StringVar()
        self.work_dir.set('Not specified.')
        self.work_entry = ttk.Entry(dir_frame, textvariable=self.work_dir,
                                state='readonly')
        self.work_entry.grid(column=1, row=0, sticky='we')
        self.b_w_d = ttk.Button(dir_frame, text="Change",
                            command=self.change_work_dir)
        self.b_w_d.grid(column=2, row=0, sticky='e')
        
        #Output dir
        ttk.Label(dir_frame, text='Output dir').grid(column=0, row=1)
        self.out_dir = tk.StringVar()
        self.out_dir.set('Not specified.')
        self.out_entry = ttk.Entry(dir_frame, textvariable=self.out_dir,
                               state='readonly')
        self.out_entry.grid(column=1, row=1, sticky='we')
        self.b_o_d = ttk.Button(dir_frame, text="Change",
                            command=self.change_output_dir)
        self.b_o_d.grid(column=2, row=1, sticky='e')
        guicom.WgtStateChanger.tslr.extend([self.b_o_d, self.b_w_d])
        
        #Log window
        self.label_log = ttk.LabelFrame(self, text='Log')
        self.label_log.grid(column=2, row=2, columnspan=3, rowspan=10, sticky='nwse')
        self.log = guicom.ReadOnlyText(self.label_log, width=50, height=6, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=tk.YES)
        
        #Progress bar
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
        try:
            self.parent.tslr = tesliper.Tesliper(new_dir)
        except:
            self.parent.logger.critical(
                "Sorry! An error occurred during new session instantiation.",
                exc_info=True)
        else:
            self.parent.logger.info(
                "New session instantiated successfully!")
        self.work_dir.set(self.parent.tslr.input_dir)
        self.out_dir.set(self.parent.tslr.output_dir)
        self.parent.conf_tab.make_new_conf_list()
        
    @guicom.WgtStateChanger
    def from_files(self):
        files = askopenfilenames(
            filetypes = [("log files","*.log"), ("out files","*.out")],
            defaultextension='.log'
            )
        if not files: return
        new_dir = os.path.split(files[0])[0]
        filenames = map(lambda p: os.path.split(p)[1], files)
        self.clear_session()
        try:
            self.parent.tslr = tesliper.Tesliper(new_dir)
        except:
            self.parent.logger.critical(
                "Sorry! An error occurred during new session instantiation.",
                exc_info=True)        
        else:
            self.parent.logger.info(
                "New session instantiated successfully!"
                )
        self.parent.tslr.soxhlet.wanted_files = filenames
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
        self.parent.tslr.extract('energies', 'iri')
        self.parent.conf_tab.establish()
            
    @guicom.Feedback('Extracting...')  
    def execute_extract_bars(self, query):
        self.parent.tslr.extract(*query)
        self.parent.conf_tab.unify_data()
        #self.parent.conf_tab.show_imag()
        #self.parent.conf_tab.establish()
        
    @guicom.Feedback('Extracting...')
    def smart_extract(self):
        self.parent.tslr.smart_extract()
        if self.parent.tslr.energies and not self.parent.conf_tab.established:
            self.parent.conf_tab.establish()
        else:
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
        

class Spectra(ttk.Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky='nwse')
        tk.Grid.columnconfigure(self, 1, weight=1)
        tk.Grid.rowconfigure(self, 8, weight=1)

        #Spectra name
        s_name_frame = ttk.LabelFrame(self, text="Spectra type:")
        s_name_frame.grid(column=0, row=0)
        self.s_name = tk.StringVar()
        self.s_name_radio = {}
        names = 'IR UV Raman VCD ECD ROA'.split(' ')
        values = 'ir uv raman vcd ecd roa'.split(' ')
        positions = [(c,r) for c in range(2) for r in range(3)]
        for n, v, (c, r) in zip(names, values, positions):
            b = ttk.Radiobutton(s_name_frame, text=n, variable=self.s_name, value=v,
                command=lambda v=v: self.spectra_choosen(v))
            b.configure(state='disabled')
            b.grid(column=c, row=r, sticky='w', padx=5)
            self.s_name_radio[v] = b
        
        #Settings
        sett = ttk.LabelFrame(self, text="Settings:")
        sett.grid(column=0, row=1)
        for no, name in enumerate('Start Stop Step HWHM'.split(' ')):
            ttk.Label(sett, text=name).grid(column=0, row=no)
            var = tk.StringVar()
            entry = ttk.Entry(sett, textvariable=var, width=10, state='disabled',
                validate='key', validatecommand=self.parent.validate_entry)
            entry.bind('<FocusOut>',
                lambda e, var=var: (self.parent.entry_out_validation(var),
                                    self.live_preview_callback()
                                    )
                        )
            setattr(self, name.lower(), entry)
            entry.var = var
            entry.grid(column=1, row=no)
            unit = tk.StringVar()
            unit.set('-')
            entry.unit = unit
            label = ttk.Label(sett, textvariable=unit)
            label.grid(column=2, row=no)
            guicom.WgtStateChanger.bars.append(entry)
        ttk.Label(sett, text='Fitting').grid(column=0, row=4)
        fit = tk.StringVar()
        self.fitting = ttk.Combobox(sett, textvariable=fit, state='disabled', width=13)
        self.fitting.bind('<<ComboboxSelected>>', self.live_preview_callback)
        self.fitting.var = fit
        self.fitting.grid(column=1, row=4, columnspan=2)
        self.fitting['values'] = ('lorentzian', 'gaussian')
        guicom.WgtStateChanger.bars.append(self.fitting)
        self.settings_established = False
        
        #Calculation Mode
        self.mode = tk.StringVar()
        self.single_radio = ttk.Radiobutton(self, text='Single file:',
            variable=self.mode, value='single', state='disabled',
            command = self.live_preview_callback)
        self.single_radio.grid(column=0, row=2, sticky='w')
        self.average_radio = ttk.Radiobutton(self, text='Average by:',
            variable=self.mode, value='average', state='disabled',
            command = self.live_preview_callback)
        self.average_radio.grid(column=0, row=4, sticky='w')
        self.stack_radio = ttk.Radiobutton(self, text='Stack by overview',
            variable=self.mode, value='stack', state='disabled',
            command = self.live_preview_callback)
        self.stack_radio.grid(column=0, row=6, sticky='w')
        
        self.single = tk.StringVar()
        self.single.set('Choose conformer...')
        self.single_box = ttk.Combobox(self, textvariable=self.single, state='disabled')
        self.single_box.bind('<<ComboboxSelected>>', 
            lambda event: self.live_preview_callback(event, mode='single'))
        self.single_box.grid(column=0, row=3)
        self.single_box['values'] = ()
        self.average = tk.StringVar()
        self.average.set('Choose energy...')
        self.average_box = ttk.Combobox(self, textvariable=self.average, state='disabled')
        self.average_box.bind('<<ComboboxSelected>>', 
            lambda event: self.live_preview_callback(event, mode='average'))
        self.average_box.grid(column=0, row=5)
        average_names = 'Thermal Enthalpy Gibbs SCF Zero-Point'.split(' ')
        self.average_box['values'] = average_names
        average_keys = 'ten ent gib scf zpe'.split(' ')
        self.average_ref = {k:v for k,v in zip(average_names, average_keys)}
        self.stack = tk.StringVar()
        self.stack.set('Choose colour...')
        self.stack_box = ttk.Combobox(self, textvariable=self.stack, state='disabled')
        self.stack_box.bind('<<ComboboxSelected>>', self.change_colour)
        self.stack_box.grid(column=0, row=7)
        self.stack_box['values'] = ('Blues Reds Greens spring summer autumn '
                                    'winter copper ocean rainbow jet '
                                    'nipy_spectral gist_ncar'.split(' '))
        guicom.WgtStateChanger.bars.extend([self.single_radio, self.single_box])
        guicom.WgtStateChanger.both.extend([self.average_radio, self.average_box,
                                    self.stack_radio, self.stack_box])
        
        #Live preview
        #Recalculate
        frame = ttk.Frame(self)
        frame.grid(column=0, row=8, sticky='n')
        var = tk.BooleanVar()
        var.set(False)
        self.live_prev = ttk.Checkbutton(frame, variable=var, text='Live preview', 
                                     state='disabled')
        self.live_prev.grid(column=0, row=0)
        self.live_prev.var = var
        #previously labeled 'Recalculate'
        self.recalc_b = ttk.Button(frame, text='Redraw', state='disabled',
                               command=self.recalculate_command)
        self.recalc_b.grid(column=1, row=0)
        guicom.WgtStateChanger.bars.extend([self.live_prev, self.recalc_b])
        
        #Progress bar
        lab = ttk.Label(self, textvariable=parent.main_tab.progtext, anchor='w', foreground='gray')
        lab.grid(column=0, row=9, sticky='sw')
        self.progbar = ttk.Progressbar(self, orient=tk.HORIZONTAL, mode='indeterminate')
        self.progbar.grid(column=0, row=10, sticky='swe')
        
        #Spectrum
        spectra_view = ttk.LabelFrame(self, text='Spectra view')
        spectra_view.grid(column=1, row=0, rowspan=10, sticky='nwse')
        tk.Grid.columnconfigure(spectra_view, 0, weight=1)
        tk.Grid.rowconfigure(spectra_view, 0, weight=1)
        self.figure = Figure()
        self.canvas = FigureCanvasTkAgg(self.figure, master=spectra_view)
        self.canvas.show()
        self.canvas.get_tk_widget().grid(column=0, row=0, sticky='nwse')
        self.ax = None
        self.last_used_settings = {}
        #self.axes = []
        
        #TO DO:
        #add save/save img buttons
        
    def spectra_choosen(self, value):
        tslr = self.parent.tslr
        bar_name = tesliper.datawork.default_spectra_bars[value]
        bar = tslr.bars[bar_name]
        self.visualize_settings()
        self.single_box['values'] = list(bar.full.filenames)
        if self.mode.get():
            self.live_preview_callback()
        else:
            self.single_radio.invoke()
            
    def visualize_settings(self):
        spectra_name = self.s_name.get()
        spectra_type = tesliper.datawork.Bars.spectra_type_ref[spectra_name]
        tslr = self.parent.tslr
        try:
            settings = self.last_used_settings[spectra_name]
        except KeyError:
            settings = tslr.parameters[spectra_type]
        for name in 'start stop step hwhm'.split(' '):
            entry = getattr(self, name)
            entry.var.set(settings[name])
            entry.unit.set(tslr.units[spectra_type][name])
        try:
            self.fitting.var.set(settings['fitting'].__name__)
        except AttributeError:
            self.fitting.var.set(settings['fitting'])
            
    def live_preview_callback(self, event=None, mode=False):
        spectra_name = self.s_name.get()
        mode_con = self.mode.get() == mode if mode else True
        settings_con = spectra_name not in self.last_used_settings or \
            self.current_settings != self.last_used_settings[spectra_name]
        core = any([not self.ax, mode_con, settings_con])
        if all([core, self.live_prev.var.get(), self.mode.get()]):
            self.recalculate_command()
    
    def new_plot(self):
        if self.ax: self.figure.delaxes(self.ax)
        self.ax = self.figure.add_subplot(111)
        
    def show_spectra(self, x, y, colour=None, width=0.5, stack=False):
        self.new_plot()
        if stack:
            col = cm.get_cmap(colour)
            no = len(y)
            for num, y_ in enumerate(y):
                self.ax.plot(x, y_, lw=width, color=col(num/no))
        else:
            self.ax.plot(x, y, lw=width)
        self.canvas.show()
        # map(self.figure.delaxes, self.axes)
        # self.axes = []
        # for num, spc in enumerate(spectra):
            # ax = self.figure.add_subplot(len(spectra), 1, num)
            # self.axes.append(ax)
            # ax.plot(spc.base)
            
    def average_draw(self, spectra_name, option):
        tslr = self.parent.tslr
        en = tslr.energies[self.average_ref[option]]
        bar_name = tesliper.datawork.default_spectra_bars[spectra_name]
        bar = tslr.bars[bar_name]
        bar.trimmer.match(en)
        tslr.calculate_spectra(spectra_name, **self.current_settings)
        spc = tslr.get_averaged_spectrum(spectra_name, en)
        self.show_spectra(*spc)

    def single_draw(self, spectra_name, option):
        tslr = self.parent.tslr
        spc = tslr.calculate_single_spectrum(spectra_name=spectra_name,
            conformer=option, **self.current_settings)
        self.show_spectra(spc.base, spc.values[0])
        
    def stack_draw(self, spectra_name, option):
        #TO DO: color of line depending on population
        tslr = self.parent.tslr
        bar_name = tesliper.datawork.default_spectra_bars[spectra_name]
        bar = tslr.bars[bar_name]
        dummy = self.parent.conf_tab._dummy
        bar.trimmer.match(dummy)
        tslr.calculate_spectra(spectra_name, **self.current_settings)
        spc = tslr.spectra[spectra_name]
        if self.ax: self.figure.delaxes(self.ax)
        self.ax = self.figure.add_subplot(111)
        self.show_spectra(spc.base, spc.values, colour=option, stack=True)
        
    def change_colour(self, event=None):
        if not self.ax: return
        if self.mode.get() != 'stack': return
        colour = self.stack.get()
        col = cm.get_cmap(colour)
        lines = self.ax.get_lines()
        no = len(lines)
        for num, line in enumerate(lines):
            line.set_color(col(num/no))
        self.canvas.draw()

    @property
    def current_settings(self):
        settings = {key: float(getattr(self, key).get())
                for key in ('start stop step hwhm'.split(' '))
                }
        fit = self.fitting.get()
        settings['fitting'] = getattr(tesliper, fit)
        return settings
        
    @guicom.Feedback("Calculating...")
    def recalculate_command(self):
        spectra_name = self.s_name.get()
        self.last_used_settings[spectra_name] = self.current_settings.copy()
        mode = self.mode.get()
        #get value of self.single, self.average or self.stack respectively
        option = getattr(self, mode).get()
        if option.startswith('Choose '): return
        #call self.single_draw, self.average_draw or self.stack_draw respectively
        spectra_drawer = getattr(self, '{}_draw'.format(mode))
        spectra_drawer(spectra_name, option)

        
        
class Conformers(ttk.Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky='nwse')
        tk.Grid.rowconfigure(self, 0, weight=1)
        tk.Grid.columnconfigure(self, 0, weight=1)
        
        self.overview = ttk.LabelFrame(self, text='Conformers overview')
        self.overview.grid(column=0, row=0, columnspan=6, sticky='nwse')
        tk.Grid.rowconfigure(self.overview, 0, weight=1)
        tk.Grid.columnconfigure(self.overview, 0, weight=1)
        self.conf_list = None
        self.make_new_conf_list()

        b_select = ttk.Button(self, text='Select all', command=self.select_all)
        b_select.grid(column=0, row=1)
        b_disselect = ttk.Button(
            self, text='Disselect all',
            command=self.disselect_all)
        b_disselect.grid(column=0, row=2)
        #ttk.Button(self, text='Refresh', command=self.refresh).grid(column=3, row=2, sticky='swe')
        ttk.Label(self, text='Show:').grid(column=2, row=1, sticky='sw')
        self.show_var = tk.StringVar()
        show_values = ('Energy', 'Delta', 'Population')
        show_id = ('values', 'deltas', 'populations')
        self.show_ref = {k: v for k, v in zip(show_values, show_id)}
        self.show_combo = ttk.Combobox(self, textvariable=self.show_var,
                                   values=show_values, state='readonly')
        self.show_combo.bind('<<ComboboxSelected>>', self.show_combo_sel)
        self.show_combo.grid(column=2, row=2)
        
        #filter
        filter_frame = ttk.LabelFrame(self, text='Filter')
        filter_frame.grid(column=1, row=1, rowspan=2)
        ttk.Label(filter_frame, text='Lower limit').grid(column=0, row=0)
        ttk.Label(filter_frame, text='Upper limit').grid(column=0, row=1)
        self.lower_var = tk.StringVar()
        self.upper_var = tk.StringVar()
        lentry = ttk.Entry(filter_frame, textvariable=self.lower_var, validate='key',
                       validatecommand=self.parent.validate_entry)
        lentry.grid(column=1, row=0)
        lentry.bind('<FocusOut>',
            lambda e, var=self.lower_var: self.parent.entry_out_validation(var)
            )
        uentry = ttk.Entry(filter_frame, textvariable=self.upper_var, validate='key',
              validatecommand=self.parent.validate_entry)
        uentry.grid(column=1, row=1)
        uentry.bind('<FocusOut>',
            lambda e, var=self.upper_var: self.parent.entry_out_validation(var)
            )
        self.en_filter_var = tk.StringVar()
        filter_values = 'Thermal Enthalpy Gibbs SCF Zero-Point'.split(' ')
        filter_id = 'ten ent gib scf zpe'.split(' ')
        self.filter_ref = {k: v for k, v in zip(filter_values, filter_id)}
        self.filter_combo = ttk.Combobox(
            filter_frame, textvariable=self.en_filter_var,
            values=filter_values, state='readonly'
            )
        self.filter_combo.grid(column=3, row=0)
        self.filter_combo.bind('<<ComboboxSelected>>', self.set_upper_and_lower)

        b_filter = ttk.Button(filter_frame, text='Filter by energy type', command=self.filter_energy)
        b_filter.grid(column=3, row=1)
        check_frame = ttk.Frame(filter_frame)
        check_frame.grid(column=4, row=0, rowspan=2)
        var_stoich = tk.BooleanVar(); var_stoich.set(True)
        self.check_stoich = ttk.Checkbutton(
            check_frame, text='Discard non-matching stoichiometry',
            variable=var_stoich, command=self.update)
        self.check_stoich.grid(column=4, row=0, sticky='w')
        self.check_stoich.var = var_stoich
        var_imag = tk.BooleanVar(); var_imag.set(True)
        self.check_imag = ttk.Checkbutton(
            check_frame, text='Discard imaginary frequencies',
            variable=var_imag, command=self.update)
        self.check_imag.grid(column=4, row=1, sticky='w')
        self.check_imag.var = var_imag
        var_missing = tk.BooleanVar(); var_missing.set(True)
        self.check_missing = ttk.Checkbutton(
            check_frame, text='Discard excessive conformers',
            variable=var_missing, command=self.update)
        self.check_missing.grid(column=4, row=2, sticky='w')
        self.check_missing.var = var_missing
        
        self.established = False
        
        # b_stoich = ttk.Button(filter_frame, text='Non-matching\nstoichiometry', command=self.filter_stoich)
        # b_stoich.grid(column=4, row=0, rowspan=2)
        # b_imag = ttk.Button(filter_frame, text='Imaginary\nfrequencies', command=self.filter_imag)
        # b_imag.grid(column=5, row=0, rowspan=2)
        guicom.WgtStateChanger.energies.extend(
            [b_select, b_disselect, self.show_combo, lentry, uentry,
            self.filter_combo, self.check_stoich, self.check_imag,
            self.check_missing]
            #b_filter, b_stoich, b_imag]
            )

    def make_new_conf_list(self):
        self.conf_list = guicom.CheckTree(self.overview, parent_tab = self)
        self.conf_list.frame.grid(column=0, row=0, sticky='nswe')
        
    def establish(self):
        self.make_new_conf_list()
        en = self.parent.tslr.energies.scf.full
        for num, (fnm, stoich) in enumerate(zip_longest(en.filenames, en.stoich)):
            self.conf_list.insert('', 'end', text=fnm)
            self.conf_list.set(num, column='stoich', value=stoich)
        # frame = ttk.Frame(self.conf_list.frame, height=15, width=17)
        # frame.grid(column=0, row=2, sticky='sw')
        # frame.grid_propagate(False)
        self.show_combo.set('Energy')
        self.filter_combo.set('Thermal')
        self.update('values')
        self.show_imag()
        self.established = True
        
    @property
    def energies(self):
        return reduce(
            lambda obj, attr: getattr(obj, attr, None),
            ('tslr', 'energies'), self.parent)

    @property
    def showing(self):
        return self.show_ref[self.show_var.get()]
        
    @property
    def blade(self):
        return [box.var.get() for box in self.conf_list.boxes]
        
    @property
    def _dummy(self):
        self.parent.logger.debug('dummy requested')
        tree = self.conf_list
        ls = [tree.item(i)['text'] for i in tree.get_children()]
        ls = sorted(ls)
        dummy = tesliper.datawork.Data('dummy', filenames = ls)
        dummy.trimmer.set(self.blade)
        return dummy

    def select_all(self):
        self.set_blade(cycle([True]))
        self.set_energies_blade()
        self.update()

    def disselect_all(self):
        self.set_blade(cycle([False]))
        self.set_energies_blade()
        self.update()

    def refresh(self):
        self.parent.logger.debug('conf_tab.refresh called.')
        self.set_energies_blade()
        self.table_view_update()
    
    def set_energies_blade(self):
        dummy = self._dummy
        for en in self.energies.values():
            en.trimmer.match(dummy)
            
    def set_blade(self, blade):
        for box, value in zip(self.conf_list.boxes, blade):
            box.var.set(1 if value else 0)
            #need to check value this way
            #because tkinter doesn't understand numpy.bool_ type
        
    def set_upper_and_lower(self, event=None):
        energy = self.filter_ref[self.en_filter_var.get()]
        arr = getattr(self.energies[energy], self.showing)
        factor = 100 if self.showing == 'populations' else 1
        try:
            lower, upper = arr.min(), arr.max()
        except ValueError:
            lower, upper = 0, 0
        else:
            n = 2 if self.showing == 'populations' else 4
            lower, upper = map(lambda v: '{:.{}f}'.format(v * factor, n),
                               (lower - 0.0001, upper + 0.0001))
        finally:
            self.lower_var.set(lower)
            self.upper_var.set(upper)
    
    def filter_energy(self):
        lower = float(self.lower_var.get())
        upper = float(self.upper_var.get())
        self.parent.logger.debug('lower limit: {}\nupper limit: {}'.format(lower, upper))
        energy = self.filter_ref[self.en_filter_var.get()]
        values = iter(getattr(self.energies[energy], self.showing))
        self.parent.logger.debug('energy: {}\nshowing: {}'.format(energy, self.showing))
        factor = 100 if self.showing == 'populations' else 1
        #must init new_blade with Falses for sake of already discarded
        #new_blade = np.zeros_like(energy.trimmer.blade)
        #iter_new = np.nditer(new_blade, op_flags=['readwrite'])
        #for box, new in zip(self.conf_list.boxes, iter_new):
        #    if box.var.get():
                #must iterate through trimmed object to get correct values
                #so should get next value only if conformer not suppressed
        #        value = next(values)
        #        new[...] = False if not lower <= value * factor <= upper else True
        new_blade = []
        for box in self.conf_list.boxes:
            if box.var.get():
                value = next(values)
                new = False if not lower <= value * factor <= upper else True
                self.parent.logger.debug('value: {}, setting {}'.format(value, new))
            else:
                new = False
                self.parent.logger.debug('no value, setting {}'.format(new))
            new_blade.append(new)
        for en in self.energies.values():
            en.trimmer.set(new_blade)
        self.set_blade(new_blade)
        self.table_view_update()
        
    def filter_stoich(self):
        for en in self.energies.values():
            en.trimm_by_stoich()
        for box, kept in zip(self.conf_list.boxes, en.trimmer.blade):
            if not kept: box.var.set(False)
            #need to check kept value this way
            #because tkinter doesn't understand numpy.bool_ type
        
    def filter_imag(self):
        bar = 'iri' if 'iri' in self.parent.tslr.bars else 'ir'
        imag = self.parent.tslr.bars[bar].full.imag
        # self.set_blade([not value.sum(0) for value in imag])
        for box, value in zip(self.conf_list.boxes, imag):
            if value.sum(0): box.var.set(False)
    
    def unify_data(self):
        stencil = None if not self.established else self._dummy
        self.parent.tslr.unify_data(stencil = stencil)
        if stencil is not None:
            for box, value in zip(self.conf_list.boxes, self.energies.scf.trimmer.blade):
                box.var.set(1 if value else 0)
            #need to check value this way
            #because tkinter doesn't understand numpy.bool_ type

    def show_combo_sel(self, event):
        self.parent.logger.debug('Show combobox selected.')
        self.table_view_update()
        
    def show_imag(self):
        bar = 'iri' if 'iri' in self.parent.tslr.bars else 'ir'
        try:
            bar = self.parent.tslr.bars[bar].full
            imag = bar.imag
            stoich = bar.stoich
        except KeyError:
            imag = []
            stoich = []
        for num, (imag_val, stoich_val) in enumerate(zip(imag, stoich)):
            self.parent.conf_tab.conf_list.set(num, column='imag', value=imag_val.sum(0))
            #self.parent.conf_tab.conf_list.set(num, column='stoich', value=stoich_val)

    def update(self, show=None):
        if self.check_imag.var.get(): self.filter_imag()
        if self.check_stoich.var.get(): self.filter_stoich()
        if self.check_missing.var.get(): self.unify_data()
        if (self.blade == self.energies.scf.trimmer.blade).all():
            self.parent.logger.debug(
                'Energies blades not matchnig internal blade. '\
                'Will call set_energies_blade.')
            self.set_energies_blade()
        self.table_view_update(show)

    def table_view_update(self, show=None):
        show = show if show else self.showing
        self.parent.logger.debug('Going to update by showing {}.'.format(show))
        e_keys = 'ten ent gib scf zpe'.split(' ')
        formats = dict(
            values = lambda v: '{:.4f}'.format(v),
            deltas = lambda v: '{:.4f}'.format(v),
            populations = lambda v: '{:.4f}'.format(v * 100)
            )
        scope = 'full' if show == 'values' else 'trimmed'
        en_get_attr = lambda e, scope, show: reduce(
            lambda obj, attr: getattr(obj, attr), (e, scope, show), self.energies
            )
        trimmed = zip(*[en_get_attr(e, scope, show) for e in e_keys])
        what_to_show = self.blade if show != 'values' else (True for __ in self.blade)
        for index, kept in enumerate(what_to_show):
            values = ['--' for _ in range(5)] if not kept else map(formats[show], next(trimmed))
            for energy, value in zip(e_keys, values):
                self.parent.conf_tab.conf_list.set(index, column=energy, value=value)
        self.set_upper_and_lower()


class TslrNotebook(ttk.Notebook):

    def __init__(self, parent):
        super().__init__(parent)
        self.tslr = None
        self.thread = Thread()
        
        parent.report_callback_exception = self.report_callback_exception
        self.validate_entry = (self.register(self.validate_entry), '%S', '%P')

        self.main_tab = Loader(self)
        self.add(self.main_tab, text='Main')
        
        self.spectra_tab = Spectra(self)
        self.add(self.spectra_tab, text='Spectra')
        
        self.conf_tab = Conformers(self)
        self.add(self.conf_tab, text='Conformers')
        
        # self.info_tab = ttk.Frame(self)
        # self.add(self.info_tab, text='Info')
        
        self.pack(fill=tk.BOTH, expand=True)
        guicom.WgtStateChanger().set_states(self.main_tab)
        
        self.logger = lgg.getLogger(__name__)
        self.loggers = [self.logger, guicom.logger] + tesliper.loggers
        text_handler = guicom.TextHandler(self.main_tab.log)
        text_handler.setLevel(lgg.INFO)
        text_handler.addFilter(guicom.MaxLevelFilter(lgg.INFO))
        
        text_warning_handler = guicom.TextHandler(self.main_tab.log)
        text_warning_handler.setLevel(lgg.WARNING)
        text_warning_handler.addFilter(guicom.MaxLevelFilter(lgg.WARNING))
        text_warning_handler.setFormatter(lgg.Formatter(
            '%(levelname)s: %(message)s'))
        
        self.error_location = os.getcwd()
        self.error_msg = (
            "Please provide a problem description to Tesliper's " \
            "developer along with tslr_err_log.txt file, witch can be " \
            "found here: {}".format(self.error_location)
            )
        text_error_handler = guicom.TextHandler(self.main_tab.log)
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
          
        
    def validate_entry(self, inserted, text_if_allowed):
        if any(i not in '0123456789.,+-' for i in inserted):
            return False
        else:
            try:
                if text_if_allowed == '.': return True
                if text_if_allowed == ',': return True
                if text_if_allowed: float(text_if_allowed.replace(',', '.'))
            except ValueError:
                return False
        return True
        
    def entry_out_validation(self, var):
        value = var.get()
        if ',' in value:
            value = value.replace(',', '.')
        if value.endswith('.'):
            value = value + '0'
        var.set(value)
            
    def report_callback_exception(self, exc, val, tb):
        self.logger.critical('An unexpected error occurred.', exc_info=True)

        