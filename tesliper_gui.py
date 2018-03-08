import os
import logging as lgg

from functools import reduce, partial
from itertools import zip_longest
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox
from tkinter.filedialog import askdirectory, askopenfilenames
from tkinter.scrolledtext import ScrolledText
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import cm
from threading import Thread

import tesliper


class TextHandler(lgg.Handler):
    
    def __init__(self, widget, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget = widget
        
    def emit(self, record):
        msg = self.format(record)
        self.widget.insert('end', msg + '\n', record.levelname)
        self.widget.yview('end')


class ReadOnlyText(ScrolledText):

    def __init__(self, *args, **kwargs):
        kwargs.pop('state', None)
        super().__init__(*args, state='disabled', **kwargs)
        self.tag_config('DEBUG', foreground='gray')
        self.tag_config('INFO', foreground='black')
        self.tag_config('WARNING', foreground='dark orange', font="Courier 10 italic")
        self.tag_config('ERROR', foreground='dark violet')
        self.tag_config('CRITICAL', foreground='red3', font="Courier 10 bold")
        
    def insert(self, *args, **kwargs):
        self.configure(state='normal')
        super().insert(*args, **kwargs)
        self.configure(state='disabled')
        
    def delete(self, *args, **kwargs):
        self.configure(state='normal')
        super().delete(*args, **kwargs)
        self.configure(state='disabled')

        
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
    
    def __init__(self, function):
        self.function = function
    
    def __call__(self, other, *args, **kwargs):
        outcome = self.function(other, *args, **kwargs)
        try:
            self.gui = other.parent
        except AttributeError:
            self.gui = other.gui
        self.tslr_inst = self.gui.tslr
        for dependency, changer in self.changers.items():
            for widget in getattr(self, dependency):
                changer(widget)
        self.change_spectra_radio()
        return outcome
        
    def __get__(self, obj, objtype):
        if obj is None:
            # instance attribute accessed on class, return self
            return self
        else:
            return partial(self.__call__, obj)
        
    @property
    def changers(self):
        bars = None if not self.tslr_inst else self.tslr_inst.bars.spectral
        energies = None if not self.tslr_inst else self.tslr_inst.energies
        return dict(
            tslr = self.enable if self.tslr_inst else self.disable,
            energies = self.enable if energies else self.disable,
            bars = self.enable if bars else self.disable,
            either = self.enable if (bars or energies) else self.disable,
            both = self.enable if (bars and energies) else self.disable
            )
        
    def enable(self, widget):
        if isinstance(widget, Combobox):
            widget.configure(state='readonly')
        else:
            widget.configure(state='normal')
            
    def disable(self, widget):
        widget.configure(state='disabled')
        
    def change_spectra_radio(self):
        if self.tslr_inst:
            bars = self.tslr_inst.bars.spectral.values()
            spectra_avaiable = [bar.spectra_name for bar in bars]
        radio = self.gui.spectra_tab.s_name_radio
        for option, widget in radio.items():
            state = 'disabled' if not self.tslr_inst or not \
                    option in spectra_avaiable else 'normal'
            widget.configure(state=state)
            

class FeedbackThread(Thread):
    def __init__(self, gui, progbar_msg, target, args, kwargs):
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.progbar_msg = progbar_msg
        self.gui = gui
        super().__init__()

    @WgtStateChanger
    def run(self):
        self.exc = None
        self.gui.main_tab.progtext.set(self.progbar_msg)
        self.gui.main_tab.progbar.start()
        self.gui.spectra_tab.progbar.start()
        try:
            return_value = self.target(*self.args, **self.kwargs)
        except BaseException as exc:
            self.exc = exc
        self.gui.main_tab.progbar.stop()
        self.gui.spectra_tab.progbar.stop()
        self.gui.main_tab.progtext.set('Idle.')
        if self.exc:
            raise self.exc
        return return_value

        
class GUIFeedback:
            
    def __init__(self, progbar_msg):
        self.progbar_msg = progbar_msg
        
    def __call__(self, function):
        def wrapper(other, *args, **kwargs):
            #other becomes self from decorated method
            if other.parent.thread.is_alive():
                raise RuntimeError
            else:
                other.parent.thread = FeedbackThread(
                    other.parent, self.progbar_msg, function,
                    [other]+list(args), kwargs
                    )
            other.parent.thread.start()
        return wrapper
        
        
class Loader(Frame):
    
    def __init__(self, parent):
        """
        TO DO
        -----
        don't allow energy extraction if already extracted
        """
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky=(N,W,S,E))
        Grid.columnconfigure(self, 3, weight=1)
        Grid.rowconfigure(self, 10, weight=1)
        buttons_frame = Frame(self)
        buttons_frame.grid(column=0, row=0, columnspan=2, rowspan=10, sticky='nwe')
        #New session
        self.label_new = Labelframe(buttons_frame, text='New session')
        self.label_new.grid(column=0, row=0, sticky=N)
        Button(self.label_new, text='Location', command=self.from_dir).grid(column=0, row=0)
        Button(self.label_new, text='From files', command=self.from_files).grid(column=1, row=0)
        
        #Extract
        self.label_extr = Labelframe(buttons_frame, text='Extract')
        self.label_extr.grid(column=0, row=1, sticky=N)
        self.b_e_e = Button(self.label_extr, text='Energies', command=self.extract_energies)
        self.b_e_e.grid(column=0, row=0)
        self.b_e_b = Button(self.label_extr, text='Bars', command=self.get_wanted_bars)
        self.b_e_b.grid(column=1, row=0)
        WgtStateChanger.tslr.extend([self.b_e_e, self.b_e_b])

        #Calculate
        self.label_calc = Labelframe(buttons_frame, text='Calculate')
        self.label_calc.grid(column=0, row=2, sticky=N)
        #self.b_c_p = Button(self.label_calc, text='Populations', command=self.calc_popul)
        #self.b_c_p.grid(column=0, row=0)
        self.b_c_s = Button(self.label_calc, text='Spectra', command=self.calc_spectra)
        self.b_c_s.grid(column=0, row=0)
        self.b_c_a = Button(self.label_calc, text='Average', command=self.calc_average)
        self.b_c_a.grid(column=1, row=0)
        WgtStateChanger.bars.append(self.b_c_s)
        WgtStateChanger.both.append(self.b_c_a)

        #Smart
        self.label_smart = Labelframe(buttons_frame, text='Smart')
        self.label_smart.grid(column=0, row=3, sticky=N)
        self.b_s_e = Button(self.label_smart, text='Extract', command=self.not_impl)
        self.b_s_e.grid(column=0, row=0)
        self.b_s_c = Button(self.label_smart, text='Calculate', command=self.not_impl)
        self.b_s_c.grid(column=1, row=0)
        self.b_s_s = Button(self.label_smart, text='Save', command=self.not_impl)
        self.b_s_s.grid(column=1, row=1)
        WgtStateChanger.tslr.append(self.b_s_e)
        WgtStateChanger.bars.append(self.b_s_c)
        WgtStateChanger.either.append(self.b_s_s)

        #Load
        self.label_load = Labelframe(buttons_frame, text='Load')
        self.label_load.grid(column=0, row=4, sticky=N)
        self.b_l_p = Button(self.label_load, text='Populations')
        self.b_l_p.grid(column=0, row=0)
        self.b_l_b = Button(self.label_load, text='Bars')
        self.b_l_b.grid(column=1, row=0)
        self.b_l_s = Button(self.label_load, text='Spectra')
        self.b_l_s.grid(column=0, row=1)
        self.b_l_t = Button(self.label_load, text='Settings')
        self.b_l_t.grid(column=1, row=1)
        WgtStateChanger.tslr.extend([self.b_l_p, self.b_l_b, self.b_l_s, self.b_l_t])
        
        #Dir frame
        dir_frame = Frame(self)
        dir_frame.grid(column=2, row=0, columnspan=3, rowspan=2, sticky='nwe')
        Grid.columnconfigure(dir_frame, 1, weight=1)
        
        #Work dir
        Label(dir_frame, text='Work dir').grid(column=0, row=0)
        self.work_dir = StringVar()
        self.work_dir.set('Not specified.')
        self.work_entry = Entry(dir_frame, textvariable=self.work_dir,
                                state='readonly')
        self.work_entry.grid(column=1, row=0, sticky=(W,E))
        self.b_w_d = Button(dir_frame, text="Change",
                            command=self.change_work_dir)
        self.b_w_d.grid(column=2, row=0, sticky=E)
        
        #Output dir
        Label(dir_frame, text='Output dir').grid(column=0, row=1)
        self.out_dir = StringVar()
        self.out_dir.set('Not specified.')
        self.out_entry = Entry(dir_frame, textvariable=self.out_dir,
                               state='readonly')
        self.out_entry.grid(column=1, row=1, sticky=(W,E))
        self.b_o_d = Button(dir_frame, text="Change",
                            command=self.change_output_dir)
        self.b_o_d.grid(column=2, row=1, sticky=E)
        WgtStateChanger.tslr.extend([self.b_o_d, self.b_w_d])
        
        #Log window
        self.label_log = Labelframe(self, text='Log')
        self.label_log.grid(column=2, row=2, columnspan=3, rowspan=10, sticky=(N,W,S,E))
        self.log = ReadOnlyText(self.label_log, width=50, height=6, wrap=WORD)
        self.log.pack(fill=BOTH, expand=YES)
        
        #Progress bar
        self.progtext = StringVar()
        self.progtext.set('Idle.')
        self.proglabel = Label(self, textvariable=self.progtext, anchor='w', foreground='gray')
        self.proglabel.grid(column=0, row=10, columnspan=2, sticky=(S,W))
        self.progbar = Progressbar(self, orient=HORIZONTAL, mode='indeterminate')
        self.progbar.grid(column=0, row=11, columnspan=2, sticky=(S,W,E))
        
    def not_impl(self):
        messagebox.showinfo("Sorry!", "We are sorry, but this function is not implemented yet.")
    
    @WgtStateChanger
    def clear_session(self):
        pass

    @WgtStateChanger        
    def from_dir(self, new_dir=None):
        if not new_dir: new_dir = askdirectory()
        if not new_dir: return
        self.clear_session()
        try:
            self.parent.tslr = tesliper.Tesliper(new_dir)
        except:
            self.parent.logger.critical(
                "Sorry! An error occurred during new session instantiation. "\
                + self.parent.error_msg
                )        
        else:
            self.parent.logger.info(
                "New session instantiated successfully!"
                )
        self.work_dir.set(new_dir)
        self.out_dir.set(self.parent.tslr.output_dir)
        self.parent.conf_tab.make_new_conf_list()
        
    @WgtStateChanger
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
                "Sorry! An error occurred during new session instantiation. "\
                + self.parent.error_msg
                )        
        else:
            self.parent.logger.info(
                "New session instantiated successfully!"
                )
        self.parent.tslr.soxhlet.wanted_files = filenames
        self.work_dir.set(new_dir)
        self.out_dir.set(self.parent.tslr.output_dir)
        self.parent.conf_tab.make_new_conf_list()
        
    def change_work_dir(self):
        new_dir = askdirectory()
        if not new_dir: return
        self.parent.tslr.change_dir(input_dir=new_dir)
        self.work_dir.set(new_dir)
        
    def change_output_dir(self):
        new_dir = askdirectory()
        if not new_dir: return
        self.parent.tslr.change_dir(output_dir=new_dir)
        self.out_dir.set(new_dir)
        
    @GUIFeedback('Extracting...')  
    def extract_energies(self):
        self.parent.tslr.extract('energies', 'iri')
        self.parent.conf_tab.establish()
            
    @GUIFeedback('Extracting...')  
    def execute_extract_bars(self, query):
        self.parent.tslr.extract(*query)
        #self.parent.conf_tab.show_imag()
        #self.parent.conf_tab.establish()
     
    @GUIFeedback('Calculating populations...')
    def calc_popul(self):
        self.parent.tslr.calculate_populations()
                
    @GUIFeedback('Calculating spectra...')
    def calc_spectra(self):
        self.parent.tslr.calculate_spectra()
        
    @GUIFeedback('Calculating averages...')
    def calc_average(self):
        pass
        
    class BarsPopup(Toplevel):
    
        bar_names = "IR Inten.,E-M Angle,Dip. Str.,Rot. Str.,Osc. (velo),"\
                    "R(velocity), Osc. (length),R(length),Raman1,ROA1".split(',')
        bar_keys = "iri emang dip rot vosc vrot losc lrot raman1 roa1".split(' ')
        
        def __init__(self, master, *args, **kwargs):
            super().__init__(master, *args, **kwargs)
            self.master = master
            self.grab_set()
            self.title("Bars extraction")
            Grid.rowconfigure(self, 6, weight=1)
            Grid.columnconfigure(self, 2, weight=1)
            Label(self, text="Chose bars you wish to extract:").grid(
                column=0, row=0, columnspan=2, sticky=W, padx=5, pady=5)
            positions = [(c,r) for r in range(1,6) for c in range(2)]
            self.vars = [BooleanVar() for _ in self.bar_keys]
            for v, k, n, (c, r) in zip(self.vars, self.bar_keys, self.bar_names, positions):
                Checkbutton(self, text=n, variable=v).grid(column=c, row=r, sticky=W, pady=2, padx=5)
            buttons_frame = Frame(self)
            buttons_frame.grid(column=0, row=6, columnspan=3, sticky=(S,E), pady=5)
            Grid.rowconfigure(buttons_frame, 0, weight=1)
            Grid.columnconfigure(buttons_frame, 0, weight=1)
            b_cancel = Button(buttons_frame, text="Cancel", command=self.cancel_command)
            b_cancel.grid(column=0, row=0, sticky=(S,E))
            b_ok = Button(buttons_frame, text="OK", command=self.ok_command)
            b_ok.grid(column=1, row=0, sticky=(S,E), padx=5)
            self.geometry('220x190')
            
        def ok_command(self):
            vals = [v.get() for v in self.vars]
            query = [b for b, v in zip(self.bar_keys, vals) if v]
            if query:
                self.destroy()
                self.master.execute_extract_bars(query)
            else:
                messagebox.showinfo("Nothing choosen!", "You must chose which bars you want to extract.")
                self.focus_set()
                
        def cancel_command(self):
            self.destroy()
        
    def get_wanted_bars(self):
        popup = self.BarsPopup(self)
        

class Spectra(Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky=(N,W,S,E))
        Grid.columnconfigure(self, 1, weight=1)
        Grid.rowconfigure(self, 8, weight=1)

        #Spectra name
        s_name_frame = Labelframe(self, text="Spectra type:")
        s_name_frame.grid(column=0, row=0)
        self.s_name = StringVar()
        self.s_name_radio = {}
        names = 'IR UV Raman VCD ECD ROA'.split(' ')
        values = 'ir uv raman vcd ecd roa'.split(' ')
        positions = [(c,r) for c in range(2) for r in range(3)]
        for n, v, (c, r) in zip(names, values, positions):
            b = Radiobutton(s_name_frame, text=n, variable=self.s_name, value=v,
                command=lambda v=v: self.spectra_choosen(v))
            b.configure(state='disabled')
            b.grid(column=c, row=r, sticky=W, padx=5)
            self.s_name_radio[v] = b
        
        #Settings
        sett = Labelframe(self, text="Settings:")
        sett.grid(column=0, row=1)
        for no, name in enumerate('Start Stop Step HWHM'.split(' ')):
            Label(sett, text=name).grid(column=0, row=no)
            var = StringVar()
            entry = Entry(sett, textvariable=var, width=10, state='disabled',
                validate='key', validatecommand=self.parent.validate_entry)
            entry.bind('<FocusOut>',
                lambda e, var=var: (self.parent.entry_out_validation(var),
                                    self.live_preview_callback()
                                    )
                        )
            setattr(self, name.lower(), entry)
            entry.var = var
            entry.grid(column=1, row=no)
            unit = StringVar()
            unit.set('-')
            entry.unit = unit
            label = Label(sett, textvariable=unit)
            label.grid(column=2, row=no)
            WgtStateChanger.bars.append(entry)
        Label(sett, text='Fitting').grid(column=0, row=4)
        fit = StringVar()
        self.fitting = Combobox(sett, textvariable=fit, state='disabled', width=13)
        self.fitting.bind('<<ComboboxSelected>>', self.live_preview_callback)
        self.fitting.var = fit
        self.fitting.grid(column=1, row=4, columnspan=2)
        self.fitting['values'] = ('lorentzian', 'gaussian')
        WgtStateChanger.bars.append(self.fitting)
        self.settings_established = False
        
        #Calculation Mode
        self.mode = StringVar()
        self.single_radio = Radiobutton(self, text='Single file:',
                                        variable=self.mode, value='single',
                                        state='disabled')
        self.single_radio.grid(column=0, row=2, sticky=W)
        self.average_radio = Radiobutton(self, text='Average by:',
                                         variable=self.mode, value='average',
                                         state='disabled')
        self.average_radio.grid(column=0, row=4, sticky=W)
        self.stack_radio = Radiobutton(self, text='Stack by overview',
                                       variable=self.mode, value='stack',
                                       state='disabled')
        self.stack_radio.grid(column=0, row=6, sticky=W)
        
        self.single = StringVar()
        self.single.set('Choose conformer...')
        self.single_box = Combobox(self, textvariable=self.single, state='disabled')
        self.single_box.bind('<<ComboboxSelected>>', 
            lambda event: self.live_preview_callback(event, mode='single'))
        self.single_box.grid(column=0, row=3)
        self.single_box['values'] = ()
        self.average = StringVar()
        self.average.set('Choose energy...')
        self.average_box = Combobox(self, textvariable=self.average, state='disabled')
        self.average_box.bind('<<ComboboxSelected>>', 
            lambda event: self.live_preview_callback(event, mode='average'))
        self.average_box.grid(column=0, row=5)
        average_names = 'Thermal Enthalpy Gibbs SCF Zero-Point'.split(' ')
        self.average_box['values'] = average_names
        average_keys = 'ten ent gib scf zpe'.split(' ')
        self.average_ref = {k:v for k,v in zip(average_names, average_keys)}
        self.stack = StringVar()
        self.stack.set('Choose colour...')
        self.stack_box = Combobox(self, textvariable=self.stack, state='disabled')
        self.stack_box.bind('<<ComboboxSelected>>', self.change_colour)
        self.stack_box.grid(column=0, row=7)
        self.stack_box['values'] = ('Blues Reds Greens spring summer autumn '
                                    'winter copper ocean rainbow jet '
                                    'nipy_spectral gist_ncar'.split(' '))
        WgtStateChanger.bars.extend([self.single_radio, self.single_box])
        WgtStateChanger.both.extend([self.average_radio, self.average_box,
                                    self.stack_radio, self.stack_box])
        
        #Live preview
        #Recalculate
        frame = Frame(self)
        frame.grid(column=0, row=8, sticky='n')
        var = BooleanVar()
        var.set(False)
        self.live_prev = Checkbutton(frame, variable=var, text='Live preview', 
                                     state='disabled')
        self.live_prev.grid(column=0, row=0)
        self.live_prev.var = var
        #previously labeled 'Recalculate'
        self.recalc_b = Button(frame, text='Redraw', state='disabled',
                               command=self.recalculate_command)
        self.recalc_b.grid(column=1, row=0)
        WgtStateChanger.bars.extend([self.live_prev, self.recalc_b])
        
        #Progress bar
        lab = Label(self, textvariable=parent.main_tab.progtext, anchor=W, foreground='gray')
        lab.grid(column=0, row=9, sticky=(S,W))
        self.progbar = Progressbar(self, orient=HORIZONTAL, mode='indeterminate')
        self.progbar.grid(column=0, row=10, sticky=(S,W,E))
        
        #Spectrum
        spectra_view = Labelframe(self, text='Spectra view')
        spectra_view.grid(column=1, row=0, rowspan=10, sticky=(N,S,W,E))
        Grid.columnconfigure(spectra_view, 0, weight=1)
        Grid.rowconfigure(spectra_view, 0, weight=1)
        self.figure = Figure()
        self.canvas = FigureCanvasTkAgg(self.figure, master=spectra_view)
        self.canvas.show()
        self.canvas.get_tk_widget().grid(column=0, row=0, sticky=(N,S,W,E))
        self.ax = None
        self.last_used_settings = {}
        #self.axes = []
        
        #TO DO:
        #add save/save img buttons
        
    def spectra_choosen(self, value):
        tslr = self.parent.tslr
        bar_name = tslr.default_spectra_bars[value]
        bar = tslr.bars[bar_name]
        self.visualize_settings()
        self.single_box['values'] = list(bar.filenames)
        if self.mode.get():
            self.live_preview_callback()
        else:
            self.single_radio.invoke()
            
    def visualize_settings(self):
        spectra_name = self.s_name.get()
        spectra_type = tesliper.Bars.spectra_type_ref[spectra_name]
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
        #CURRENTLY ASUMES SAME SIZE OF DATA
        #TO DO: fix upper
        tslr = self.parent.tslr
        en = tslr.energies[self.average_ref[option]]
        blade = self.parent.conf_tab.blade
        en.trimmer.set(blade)
        bar_name = tslr.default_spectra_bars[spectra_name]
        bars = tslr.bars[bar_name]
        bars.trimmer.set(blade)
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
        blade = self.parent.conf_tab.blade
        bar_name = tslr.default_spectra_bars[spectra_name]
        bars = tslr.bars[bar_name]
        bars.trimmer.set(blade)
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
        
    @GUIFeedback("Calculating...")
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

        
class BoxVar(BooleanVar):
    
    def __init__(self, box, *args, **kwargs):
        self.box = box
        super().__init__(*args, **kwargs)
        super().set(True)
        
    def set(self, value):
        super().set(value)
        if value:
            self.box.tree.item(self.box.index, tags=())
        else:
            self.box.tree.item(self.box.index, tags='discarded')

        
class Checkbox(Checkbutton):
    def __init__(self, master, tree, index, box_command, *args, **kwargs):
        self.frame = Frame(master, width=17, height=20)
        self.tree = tree
        self.index = index
        self.box_command = box_command
        self.var = BoxVar(self)
        kwargs['variable'] = self.var
        super().__init__(self.frame, *args, command=self.clicked, **kwargs)
        self.frame.pack_propagate(False)
        self.frame.grid_propagate(False)
        self.grid(column=0, row=0)
        
    def clicked(self):
        if self.var.get():
            self.tree.item(self.index, tags=())
        else:
            self.tree.item(self.index, tags='discarded')
        self.box_command()
        #self.tree.selection_set(str(self.index))

        
class CheckTree(Treeview):
    def __init__(self, master, box_command=None, **kwargs):
        self.frame = Frame(master)
        kwargs['columns'] = 'ten ent gib scf zpe imag stoich'.split(' ')
        super().__init__(self.frame, **kwargs)
        self.grid(column=0, row=0, rowspan=2, columnspan=2, sticky=(N,W,S,E))
        Grid.columnconfigure(self.frame, 1, weight=1)
        Grid.rowconfigure(self.frame, 1, weight=1)
        self.vsb = Scrollbar(self.frame, orient='vertical', command=self.on_bar)
        self.vsb.grid(column=2, row=0, rowspan=2, sticky=(N,S))
        
        self.tag_configure('discarded', foreground='gray')

        #Columns
        for cid, text in zip('#0 stoich imag ten ent gib scf zpe'.split(' '),
                             'Filenames, Stoichiometry, Imag, Thermal, '\
                             'Enthalpy, Gibbs, SCF, Zero-Point'.split(', ')):
            if not cid in ('#0', 'stoich', 'imag'): self.column(cid, width=20, anchor='e')
            self.heading(cid, text=text)
        self.column('#0', width=100)
        self.column('stoich', width=100)
        self.column('imag', width=40, anchor='center', stretch=False)

        #Sort button
        but_frame = Frame(self.frame, height=24, width=17)
        but_frame.grid(column=0, row=0)
        but_frame.grid_propagate(False)
        Grid.columnconfigure(but_frame, 0, weight=1)
        Grid.rowconfigure(but_frame, 0, weight=1)
        style = Style()
        style.configure('sorting.TButton',
            borderwidth=5,
            highlightthickness=1,
            relief='flat')
        self.but_sort = Button(but_frame, style='sorting.TButton', command=self._sort_button)
        self.but_sort.grid(column=0, row=0, sticky='nwes')
        
        #Boxes
        self.box_command = box_command
        self.canvas = Canvas(self.frame, width=17, borderwidth=0, 
                             background="#ffffff", highlightthickness=0)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.grid(column=0, row=1, sticky=(N,S))
        self.boxes_frame = Frame(self.canvas)
        self.canvas.create_window((0,0), window=self.boxes_frame, anchor="nw", 
                                  tags="boxes_frame")
        
        self.boxes_frame.bind("<Configure>", self.onFrameConfigure)
        self.configure(yscrollcommand=self.yscroll)
        self.boxes = []

    
    def _sort_button(self, reverse=True):
        ls = [(b.var.get(), b.index) for b in self.boxes]
        ls.sort(reverse=reverse)
        for i, (val, k) in enumerate(ls):
            box = self.boxes[k]
            self.move(k, '', i)
            box.frame.grid_forget()
            box.frame.grid_propagate(False)
            box.frame.grid(column=0, row=i, sticky='n', pady=0)
        self.but_sort.configure(command=lambda: self._sort_button(not reverse))
        
    def _sort(self, col, reverse=True):
        try:
            ls = [(self.set(k, col), k) for k in self.get_children('')]
        except TclError:
            ls = [(self.item(k)['text'], k) for k in self.get_children('')]
        try:
            ls = [(-1e10 if v == '--' else float(v), k) for v, k in ls]
        except ValueError:
            pass
        ls.sort(reverse=reverse)
        for i, (val, k) in enumerate(ls):
            self.move(k, '', i)
            box = self.boxes[int(k)]
            box.frame.grid_forget()
            box.frame.grid_propagate(False)
            box.frame.grid(column=0, row=i, sticky='n', pady=0)
        self.heading(col, command=lambda: self._sort(col, not reverse))
        
    def heading(self, col, *args, command=None, **kwargs):
        command = command if command is not None else lambda: self._sort(col)
        return super().heading(col, *args, command=command, **kwargs)
        
    @classmethod
    def test_populate(cls, master, num=30):
        import string, random
        new = cls(master, columns=('b'))
        new.heading('b', text='afasdgf')
        new.heading('#0', text='asdgasdfg')
        gen = (''.join(random.choices(string.ascii_lowercase, k=7)) for x in range(num))
        for x, bla in enumerate(gen):
            new.insert(text=bla + ' ' + str(x), values=[x])
        return(new)
        
    def onFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def yscroll(self, *args):
        self.canvas.yview_moveto(args[0])
        
    def insert(self, parent='', index=END, iid=None, **kw):
        box = Checkbox(self.boxes_frame, self, box_command = self.box_command,
                       index=len(self.boxes))
        box.frame.grid(column=0, row=box.index)
        self.boxes.append(box)
        return super().insert(parent, index, iid=str(box.index), **kw)
        
    def on_bar(self, *args):
        self.yview(*args)

        
class Conformers(Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky=(N,W,S,E))
        Grid.rowconfigure(self, 0, weight=1)
        Grid.columnconfigure(self, 0, weight=1)
        
        self.overview = Labelframe(self, text='Conformers overview')
        self.overview.grid(column=0, row=0, columnspan=6, sticky=(N,W,S,E))
        Grid.rowconfigure(self.overview, 0, weight=1)
        Grid.columnconfigure(self.overview, 0, weight=1)
        self.conf_list = None
        self.make_new_conf_list()

        b_select = Button(self, text='Select all', command=self.select_all)
        b_select.grid(column=0, row=1)
        b_disselect = Button(
            self, text='Disselect all',
            command=lambda: [box.var.set(False) for box in self.conf_list.boxes]
            )
        b_disselect.grid(column=0, row=2)
        #Button(self, text='Refresh', command=self.refresh).grid(column=3, row=2, sticky=(S,W))
        Label(self, text='Show:').grid(column=2, row=1, sticky='sw')
        self.show_var = StringVar()
        show_values = ('Energy', 'Delta', 'Population')
        show_id = ('values', 'deltas', 'populations')
        self.show_ref = {k: v for k, v in zip(show_values, show_id)}
        self.show_combo = Combobox(self, textvariable=self.show_var,
                                   values=show_values, state='readonly')
        self.show_combo.bind('<<ComboboxSelected>>', self.show_combo_sel)
        self.show_combo.grid(column=2, row=2)
        
        #filter
        filter_frame = Labelframe(self, text='Filter')
        filter_frame.grid(column=1, row=1, rowspan=2)
        Label(filter_frame, text='Lower limit').grid(column=0, row=0)
        Label(filter_frame, text='Upper limit').grid(column=0, row=1)
        self.lower_var = StringVar()
        self.upper_var = StringVar()
        lentry = Entry(filter_frame, textvariable=self.lower_var, validate='key',
                       validatecommand=self.parent.validate_entry)
        lentry.grid(column=1, row=0)
        lentry.bind('<FocusOut>',
            lambda e, var=self.lower_var: self.parent.entry_out_validation(var)
            )
        uentry = Entry(filter_frame, textvariable=self.upper_var, validate='key',
              validatecommand=self.parent.validate_entry)
        uentry.grid(column=1, row=1)
        uentry.bind('<FocusOut>',
            lambda e, var=self.upper_var: self.parent.entry_out_validation(var)
            )
        self.en_filter_var = StringVar()
        filter_values = 'Thermal Enthalpy Gibbs SCF Zero-Point'.split(' ')
        filter_id = 'ten ent gib scf zpe'.split(' ')
        self.filter_ref = {k: v for k, v in zip(filter_values, filter_id)}
        self.filter_combo = Combobox(
            filter_frame, textvariable=self.en_filter_var,
            values=filter_values, state='readonly'
            )
        self.filter_combo.grid(column=3, row=0)
        self.filter_combo.bind('<<ComboboxSelected>>', self.set_upper_and_lower)

        b_filter = Button(filter_frame, text='Filter by energy type', command=self.filter_energy)
        b_filter.grid(column=3, row=1)
        check_frame = Frame(filter_frame)
        check_frame.grid(column=4, row=0, rowspan=2)
        var_stoich = BooleanVar(); var_stoich.set(False)
        self.check_stoich = Checkbutton(
            check_frame, text='Discard non-matching stoichiometry',
            variable=var_stoich, command=self.discard_stoich)
        self.check_stoich.grid(column=4, row=0, sticky='w')
        self.check_stoich.var = var_stoich
        var_imag = BooleanVar(); var_imag.set(False)
        self.check_imag = Checkbutton(
            check_frame, text='Discard imaginary frequencies',
            variable=var_imag, command=self.discard_imag)
        self.check_imag.grid(column=4, row=1, sticky='w')
        self.check_imag.var = var_imag
        var_missing = BooleanVar(); var_missing.set(True)
        self.check_missing = Checkbutton(
            check_frame, text='Discard excessive conformers',
            variable=var_missing, command=self.discard_missing)
        self.check_missing.grid(column=4, row=2, sticky='w')
        self.check_missing.var = var_missing
        
        #TO DO: change filter function to reflect change to checkbuttons
        
        # b_stoich = Button(filter_frame, text='Non-matching\nstoichiometry', command=self.filter_stoich)
        # b_stoich.grid(column=4, row=0, rowspan=2)
        # b_imag = Button(filter_frame, text='Imaginary\nfrequencies', command=self.filter_imag)
        # b_imag.grid(column=5, row=0, rowspan=2)
        WgtStateChanger.energies.extend(
            [b_select, b_disselect, self.show_combo, lentry, uentry,
            self.filter_combo, self.check_stoich, self.check_imag,
            self.check_missing]
            #b_filter, b_stoich, b_imag]
            )
        
    def discard_imag(self):
        if self.check_imag.var.get():
            self.filter_imag()

    def discard_stoich(self):
        if self.check_stoich.var.get():
            self.filter_stoich()
        
    def discard_missing(self):
        if self.check_missing.var.get():
            self.unify_data()
    
    def set_upper_and_lower(self, event=None):
        energy = self.filter_ref[self.en_filter_var.get()]
        arr = getattr(self.energies[energy], self.showing)
        factor = 100 if self.showing == 'populations' else 1
        lower, upper = arr.min(), arr.max()
        n = 2 if self.showing == 'populations' else 4
        lower, upper = map(lambda v: '{:.{}f}'.format(v * factor, n), (lower - 0.0001, upper + 0.0001))
        self.lower_var.set(lower)
        self.upper_var.set(upper)
    
    def filter_energy(self):
        lower = float(self.lower_var.get())
        upper = float(self.upper_var.get())
        energy = self.filter_ref[self.en_filter_var.get()]
        values = iter(getattr(self.energies[energy], self.showing))
        factor = 100 if self.showing == 'populations' else 1
        for box in self.conf_list.boxes:
            if box.var.get():
                value = next(values)
                if not lower <= value * factor <= upper:
                    box.var.set(False)
        self.update()
        
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
        
    def select_all(self):
        for box in self.conf_list.boxes:
            box.var.set(True)
        self.update()

    def disselect_all(self):
        for box in self.conf_list.boxes:
            box.var.set(False)
        self.update()

    def refresh(self):
        for en in self.energies.values():
            en.trimmer.update(self.blade)
        self.update()
    
    def make_new_conf_list(self):
        if self.conf_list:
            self.conf_list.destroy()
        self.conf_list = CheckTree(self.overview, box_command = self.refresh)
        self.conf_list.frame.grid(column=0, row=0, sticky='nswe')
        
    def filter_stoich(self):
        for en in self.energies.values():
            en.trimm_by_stoich()
        for box, kept in zip(self.conf_list.boxes, en.trimmer.blade):
            box.var.set(1 if kept else 0)
            #need to check kept value this way
            #because tkinter doesn't understand numpy.bool_ type
        
    def filter_imag(self):
        bar = 'iri' if 'iri' in self.parent.tslr.bars else 'ir'
        imag = self.parent.tslr.bars[bar].full.imag
        for box, value in zip(self.conf_list.boxes, imag):
            if value.sum(0): box.var.set(False)
        self.set_upper_and_lower()
    
    def show_combo_sel(self, event):
        self.set_upper_and_lower()
        self.update()
        
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

    def establish(self):
        self.make_new_conf_list()
        en = self.parent.tslr.energies.scf.full
        for num, (fnm, stoich) in enumerate(zip_longest(en.filenames, en.stoich)):
            self.parent.conf_tab.conf_list.insert('', 'end', text=fnm)
            self.parent.conf_tab.conf_list.set(num, column='stoich', value=stoich)
        self.show_combo.set('Energy')
        self.filter_combo.set('Thermal')
        self.set_upper_and_lower()
        self.update('values')
        self.show_imag()
        
    def update(self, show=None):
        if self.check_imag.var.get(): self.filter_imag()
        if self.check_stoich.var.get(): self.filter_stoich()
        if self.check_missing.var.get(): self.unify_data()
        if (self.blade == self.energies.scf.trimmer.blade).all():
            for en in self.energies.values(): en.trimmer.set(self.blade)
        self.table_view_update(show)

    def table_view_update(self, show=None):
        show = show if show else self.showing
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
        what_to_show = self.blade if show != 'values' else (True for _ in self.blade)
        for index, kept in enumerate(what_to_show):
            values = ['--' for _ in range(5)] if not kept else map(formats[show], next(trimmed))
            for energy, value in zip(e_keys, values):
                self.parent.conf_tab.conf_list.set(index, column=energy, value=value)

    def unify_data(self):
        bars = self.parent.tslr.bars
        ens = self.energies
        dummy = tesliper.Data(filenames = ens.scf.full.filenames,
                              stoich = ens.scf.full.stoich)
        dummy.trimmer.set(self.blade)
        for bar in bars.values():
            try:
                dummy.trimmer.unify(bar)
            except Exeption:
                self.parent.logger.warning(
                    'A problem occured during data unification. '\
                    'Make sure your file sets have any common filenames.')
        fnames = [bar.filenames for bar in bars.values()]
        if not all(x.shape == y.shape and (x == y).all() for x, y \
                   in zip(fnames[:-1], fnames[1:])):
            self.unify_data()
        else:
            if not (dummy.trimmer.blade == self.blade).all():
                for en in ens.values():
                    en.trimmer.match(dummy)
                for box, value in zip(self.conf_list.boxes, dummy.trimmer.blade):
                    box.var.set(value)
                self.update()


class TslrNotebook(Notebook):

    def __init__(self, parent):
        super().__init__(parent)
        self.tslr = None
        self.thread = Thread()
        
        self.validate_entry = (self.register(self.validate_entry), '%S', '%P')

        self.main_tab = Loader(self)
        self.add(self.main_tab, text='Main')
        
        self.spectra_tab = Spectra(self)
        self.add(self.spectra_tab, text='Spectra')
        
        self.conf_tab = Conformers(self)
        self.add(self.conf_tab, text='Conformers')
        
        self.info_tab = Frame(self)
        self.add(self.info_tab, text='Info')
        
        self.pack(fill=BOTH, expand=True)
        self.main_tab.clear_session()
        
        self.logger = lgg.getLogger(__name__)
        self.logger.setLevel(lgg.INFO)
        text_handler = TextHandler(self.main_tab.log)
        text_handler.setLevel(lgg.INFO)
        self.logger.addHandler(text_handler)
        
        self.error_locarion = os.getcwd()
        self.error_msg = (
            "Please provide a problem description to Tesliper's " \
            "developer along with tslr_err_log.txt file, witch can be " \
            "found here: {}".format(self.error_locarion)
            )
        error_handler = lgg.FileHandler(
            os.path.join(self.error_locarion, 'tslr_err_log.txt'), delay=True)
        error_handler.setLevel(lgg.ERROR)
        self.logger.addHandler(text_handler)
        
        tesliper.logger.addHandler(text_handler)
        tesliper.logger.addHandler(error_handler)
        
        self.logger.info(
            'Welcome to Tesliper:\n'
            'Theoretical Spectroscopist Little Helper!\n'
            )
        self.logger.info("This is info.")
        self.logger.warning("This is warning.")
        self.logger.error("This is error.")
        self.logger.critical("This is critical.")
        
    def validate_entry(self, inserted, text_if_allowed):
        if any(i not in '0123456789.+-' for i in inserted):
            return False
        else:
            try:
                if text_if_allowed == '.': return True
                if text_if_allowed: float(text_if_allowed)
            except ValueError:
                return False
        return True
        
    def entry_out_validation(self, var):
        value = var.get()
        if value.endswith('.'):
            var.set(value + '0')
    
        
if __name__ == '__main__':
    
    root = Tk()
    root.title("Tesliper")
    n = TslrNotebook(root)
    tslr = n.tslr
    

    root.mainloop()
