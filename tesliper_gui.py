from functools import reduce
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox
from tkinter.filedialog import askdirectory, askopenfilename
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import cm
from threading import Thread

import tesliper


class ReadOnlyText(Text):

    def __init__(self, *args, **kwargs):
        kwargs.pop('state', None)
        super().__init__(*args, state='disabled', **kwargs)
    
    def insert(self, *args, **kwargs):
        self.configure(state='normal')
        super().insert(*args, **kwargs)
        self.configure(state='disabled')
        
    def delete(self, *args, **kwargs):
        self.configure(state='normal')
        super().delete(*args, **kwargs)
        self.configure(state='disabled')

class LoggingThread(Thread):
    def __init__(self, gui, progbar, target, args, kwargs):
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.progbar = progbar
        self.gui = gui
        super().__init__()

    def run(self):
        self.exc = None
        self.gui.main_tab.progtext.set(self.progbar)
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
            
    def __init__(self, progbar):
        self.progbar = progbar
        
    def __call__(self, function):
        def wrapper(other, *args, **kwargs):
            if other.parent.thread.is_alive():
                raise RuntimeError
            else:
                other.parent.thread = LoggingThread(other.parent, self.progbar, function, [other]+list(args), kwargs)
            other.parent.thread.start()
            #other.parent.thread.join()
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
        
        #New session
        self.label_new = Labelframe(self, text='New session')
        self.label_new.grid(column=0, row=0, rowspan=3, sticky=N)
        Button(self.label_new, text='From location', command=self.from_dir).grid(column=0, row=0)
        Button(self.label_new, text='From files', command=self.not_impl).grid(column=0, row=1)
        
        #Smart
        self.label_smart = Labelframe(self, text='Smart')
        self.label_smart.grid(column=0, row=3, rowspan=4, sticky=N)
        self.b_s_e = Button(self.label_smart, text='Extract', command=self.not_impl)
        self.b_s_e.grid(column=0, row=0)
        self.b_s_c = Button(self.label_smart, text='Calculate', command=self.not_impl)
        self.b_s_c.grid(column=0, row=1)
        self.b_s_s = Button(self.label_smart, text='Save', command=self.not_impl)
        self.b_s_s.grid(column=0, row=2)

        #Extract
        self.label_extr = Labelframe(self, text='Extract')
        self.label_extr.grid(column=0, row=7, rowspan=3, sticky=N)
        self.b_e_e = Button(self.label_extr, text='Energies', command=self.extract_energies)
        self.b_e_e.grid(column=0, row=0)
        self.b_e_b = Button(self.label_extr, text='Bars', command=self.get_wanted_bars)
        self.b_e_b.grid(column=0, row=1)

        #Calculate
        self.label_calc = Labelframe(self, text='Calculate')
        self.label_calc.grid(column=1, row=0, rowspan=4, sticky=N)
        #self.b_c_p = Button(self.label_calc, text='Populations', command=self.calc_popul)
        #self.b_c_p.grid(column=0, row=0)
        self.b_c_s = Button(self.label_calc, text='Spectra', command=self.calc_spectra)
        self.b_c_s.grid(column=0, row=1)
        self.b_c_a = Button(self.label_calc, text='Average')
        self.b_c_a.grid(column=0, row=2)

        #Load
        self.label_load = Labelframe(self, text='Load')
        self.label_load.grid(column=1, row=4, rowspan=5, sticky=N)
        self.b_l_p = Button(self.label_load, text='Populations')
        self.b_l_p.grid(column=0, row=0)
        self.b_l_b = Button(self.label_load, text='Bars')
        self.b_l_b.grid(column=0, row=1)
        self.b_l_s = Button(self.label_load, text='Spectra')
        self.b_l_s.grid(column=0, row=2)
        self.b_l_t = Button(self.label_load, text='Settings')
        self.b_l_t.grid(column=0, row=3)
        
        #Work dir
        Label(self, text='Work dir').grid(column=2, row=0)
        self.work_dir = StringVar()
        self.work_dir.set('Not specified.')
        self.work_entry = Entry(self, textvariable=self.work_dir, state='readonly')
        self.work_entry.grid(column=3, row=0, columnspan=2, sticky=(W,E))
        self.b_w_d = Button(self, text="Change")
        self.b_w_d.grid(column=4, row=0, sticky=E)
        
        #Output dir
        Label(self, text='Output dir').grid(column=2, row=1)
        self.out_dir = StringVar()
        self.out_dir.set('Not specified.')
        self.out_entry = Entry(self, textvariable=self.out_dir, state='readonly')
        self.out_entry.grid(column=3, row=1, columnspan=2, sticky=(W,E))
        self.b_o_d = Button(self, text="Change")
        self.b_o_d.grid(column=4, row=1, sticky=E)
        
        #Log window
        self.label_log = Labelframe(self, text='Log')
        self.label_log.grid(column=2, row=2, columnspan=3, rowspan=10, sticky=(N,W,S,E))
        self.log = ReadOnlyText(self.label_log, width=50, height=6, wrap=WORD)
        self.log.pack(fill=BOTH, expand=YES)
        self.log.insert(END, 'Welcome to Tesliper:\n'
                        'Theoretical Spectroscopist Little Helper!\n')
        
        #Progress bar
        self.progtext = StringVar()
        self.progtext.set('Idle.')
        self.proglabel = Label(self, textvariable=self.progtext, anchor='w', foreground='gray')
        self.proglabel.grid(column=0, row=10, columnspan=2, sticky=(S,W))
        self.progbar = Progressbar(self, orient=HORIZONTAL, mode='indeterminate')
        self.progbar.grid(column=0, row=11, columnspan=2, sticky=(S,W,E))
        
        if not self.parent.tslr: self.tslr_dependent_change_state('disabled')
        
    def not_impl(self):
        messagebox.showinfo("Sorry!", "We are sorry, but this function is not implemented yet.")
        
    def from_dir(self):
        new_dir = askdirectory()
        if not new_dir:
            return
        self.parent.tslr = tesliper.Tesliper(new_dir)
        self.work_dir.set(new_dir)
        self.out_dir.set(self.parent.tslr.output_dir)
        self.tslr_dependent_change_state('normal')
        self.parent.conf_tab.make_new_conf_list()
        
    def from_files(self):
        pass
        
                
    @GUIFeedback('Extracting...')  
    def extract_energies(self):
        self.parent.tslr.extract('energies')
        self.parent.conf_tab.establish()
            
    @GUIFeedback('Extracting...')  
    def execute_extract_bars(self, query):
        self.parent.tslr.extract(*query)
        #stype = self.parent.tslr.soxhlet.spectra_type
        self.parent.spectra_tab.enable_widgets()
        if not self.parent.spectra_tab.settings_established:
            self.parent.spectra_tab.establish_settings()
     
    @GUIFeedback('Calculating populations...')
    def calc_popul(self):
        self.parent.tslr.calculate_populations()
                
    @GUIFeedback('Calculating spectra...')
    def calc_spectra(self):
        self.parent.tslr.calculate_spectra()
        
    def get_wanted_bars(self):
        popup = Toplevel(self)
        popup.grab_set()
        popup.title("Bars extraction")
        Grid.rowconfigure(popup, 6, weight=1)
        Grid.columnconfigure(popup, 2, weight=1)
        Label(popup, text="Chose bars you wish to extract:").grid(
            column=0, row=0, columnspan=2, sticky=W, padx=5, pady=5)
        bar_names = "IR Inten.,E-M Angle,Dip. Str.,Rot. Str.,Osc. (velo),"\
                    "R(velocity), Osc. (length),R(length),Raman1,ROA1".split(',')
        bar_keys = "iri e-m dip rot vosc vrot losc lrot raman1 roa1".split(' ')
        positions = [(c,r) for r in range(1,6) for c in range(2)]
        vars = [BooleanVar() for _ in bar_keys]
        for v, k, n, (c, r) in zip(vars, bar_keys, bar_names, positions):
            Checkbutton(popup, text=n, variable=v).grid(column=c, row=r, sticky=W, pady=2, padx=5)
        def ok_command():
            vals = [v.get() for v in vars]
            query = [b for b, v in zip(bar_keys, vals) if v]
            if query:
                self.execute_extract_bars(query)
                popup.destroy()
            else:
                messagebox.showinfo("Nothing choosen!", "You must chose which bars you want to extract.")
                popup.focus_set()
        def cancel_command():
            popup.destroy()
        buttons_frame = Frame(popup)
        buttons_frame.grid(column=0, row=6, columnspan=3, sticky=(S,E), pady=5)
        Grid.rowconfigure(buttons_frame, 0, weight=1)
        Grid.columnconfigure(buttons_frame, 0, weight=1)
        Button(buttons_frame, text="Cancel", command=cancel_command).grid(column=0, row=0, sticky=(S,E))
        Button(buttons_frame, text="OK", command=ok_command).grid(column=1, row=0, sticky=(S,E), padx=5)
        popup.geometry('220x190')
        
    def tslr_dependent_change_state(self, state):
        #b_c_p removed
        tslr_dep = [getattr(self, 'b_{}'.format(name)) for name in \
                    's_e s_c s_s e_e e_b c_s c_a l_p l_b l_s l_t w_d o_d'\
                    .split(' ')]
        en_dep = []
        bar_dep = []
        spc_dep = []
        for widget in tslr_dep:
            widget.config(state=state)


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
            entry = Entry(sett, textvariable=var, width=10, state='disabled')
            entry.bind('<FocusOut>', self.live_preview_callback)
            setattr(self, name.lower(), entry)
            entry.var = var
            entry.grid(column=1, row=no)
            unit = StringVar()
            unit.set('-')
            entry.unit = unit
            label = Label(sett, textvariable=unit)
            label.grid(column=2, row=no)
        Label(sett, text='Fitting').grid(column=0, row=4)
        fit = StringVar()
        self.fitting = Combobox(sett, textvariable=fit, state='disabled', width=13)
        self.fitting.bind('<<ComboboxSelected>>', self.live_preview_callback)
        self.fitting.var = fit
        self.fitting.grid(column=1, row=4, columnspan=2)
        self.fitting['values'] = ('lorentzian', 'gaussian')
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
            lambda event: self.live_preview_callback(event, forced=True))
        self.single_box.grid(column=0, row=3)
        self.single_box['values'] = ()
        self.average = StringVar()
        self.average.set('Choose energy...')
        self.average_box = Combobox(self, textvariable=self.average, state='disabled')
        self.average_box.bind('<<ComboboxSelected>>', 
            lambda event: self.live_preview_callback(event, forced=True))
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
        self.last_used_settings = None
        #self.axes = []
        
        #TO DO:
        #add save/save img buttons
        
    def enable_widgets(self):
        #print('enable')
        tslr = self.parent.tslr
        bar = None
        bars = [tslr.bars[key] for key in tslr.bars if key != 'freq']
        for bar in bars:
            self.s_name_radio[bar.spectra_name].configure(state='normal')
        if not bar: return
        self.single_box.configure(state='readonly')
        self.single_radio.configure(state='normal')
        self.single_box['values'] = list(bar.filenames)
        self.live_prev.configure(state='normal')
        self.recalc_b.configure(state='normal')
        if tslr.energies:
            for widget in (self.average_box, self.stack_box):
                widget.configure(state='readonly')
            for widget in (self.average_radio, self.stack_radio):
                widget.configure(state='normal')
        #print(bar.type, bar.spectra_name)
        self.s_name_radio[bar.spectra_name].invoke()
        #self.s_name.set(bar.spectra_name)
        if not self.settings_established:
            self.establish_settings()
        self.visualize_settings()
        
    def spectra_choosen(self, value):
        tslr = self.parent.tslr
        bar_name = tslr.default_spectra_bars[value]
        bar = tslr.bars[bar_name]
        self.visualize_settings()
        if self.mode.get():
            self.live_preview_callback(forced=True)
        else:
            self.single_radio.invoke()
            
    def visualize_settings(self):
        spectra_type = 'electr' if self.s_name.get() in ('uv', 'ecd') else 'vibra'
        #print(self.s_name.get(), spectra_type)
        for name in 'start stop step hwhm'.split(' '):
            entry = getattr(self, name)
            tslr = self.parent.tslr
            entry.var.set(tslr.parameters[spectra_type][name])
            entry.unit.set(tslr.units[spectra_type][name])
        self.fitting.var.set(tslr.parameters[spectra_type]['fitting'].__name__)
        
    def establish_settings(self):
        #print('establish')
        for name in 'start stop step hwhm'.split(' '):
            entry = getattr(self, name)
            entry.configure(state='normal')
        self.fitting.configure(state='readonly')
        self.settings_established = True

    def live_preview_callback(self, event=None, forced=False):
        if all([
            self.live_prev, self.mode.get(),
            any([not self.ax, forced,
                self.current_settings != self.last_used_settings])
            ]): self.recalculate_command()
    
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
        print(spc.values)
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
        self.last_used_settings = self.current_settings.copy()
        spectra_name = self.s_name.get()
        mode = self.mode.get()
        option = getattr(self, mode).get()
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

        Button(self, text='Select all', command=self.select_all).grid(column=0, row=1)
        Button(self, text='Disselect all', command=lambda: [box.var.set(False) for box in self.conf_list.boxes]).grid(column=0, row=2)
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
        self.lower_var = DoubleVar()
        self.upper_var = DoubleVar()
        validate_entry = (self.register(self.validate_entry), '%S', '%P')
        Entry(filter_frame, textvariable=self.lower_var, validate='key', validatecommand=validate_entry).grid(column=1, row=0)
        Entry(filter_frame, textvariable=self.upper_var, validate='key', validatecommand=validate_entry).grid(column=1, row=1)
        self.en_filter_var = StringVar()
        filter_values = 'Thermal Enthalpy Gibbs SCF Zero-Point'.split(' ')
        filter_id = 'ten ent gib scf zpe'.split(' ')
        self.filter_ref = {k: v for k, v in zip(filter_values, filter_id)}
        self.filter_combo = Combobox(filter_frame, textvariable=self.en_filter_var, values=filter_values, state='readonly')
        self.filter_combo.grid(column=3, row=0)
        self.filter_combo.bind('<<ComboboxSelected>>', self.set_upper_and_lower)

        Button(filter_frame, text='By energy type', command=self.filter_energy).grid(column=3, row=1)
        Button(filter_frame, text='Non-matching\nstoichiometry', command=self.filter_stoich)\
            .grid(column=4, row=0, rowspan=2)
        Button(filter_frame, text='Imaginary\nfrequencies', command=self.filter_imag).grid(column=5, row=0, rowspan=2)
    
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
        lower = self.lower_var.get()
        upper = self.upper_var.get()
        energy = self.filter_ref[self.en_filter_var.get()]
        values = iter(getattr(self.energies[energy], self.showing))
        factor = 100 if self.showing == 'populations' else 1
        for box in self.conf_list.boxes:
            if box.var.get():
                value = next(values)
                if not lower <= value * factor <= upper:
                    box.var.set(False)
        self.update()
        
    def validate_entry(self, inserted, text_if_allowed):
        if any(i not in '0123456789.+-' for i in inserted):
            return False
        else:
            try:
                if text_if_allowed: float(text_if_allowed)
            except ValueError:
                return False
        return True
    
    @property
    def energies(self):
        return reduce(lambda obj, attr: getattr(obj, attr, None), ('tslr', 'energies'), self.parent)

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
        self.update()
        
    def filter_imag(self):
        freq = self.parent.tslr.bars.freq.full
        for box, imag in zip(self.conf_list.boxes, freq.imag):
            if imag.sum(0): box.var.set(False)
        self.update()
        self.set_upper_and_lower()
    
    def show_combo_sel(self, event):
        self.set_upper_and_lower()
        self.update()
            
    def establish(self):
        self.make_new_conf_list()
        freq = self.parent.tslr.bars.freq
        for num, (fnm, stoich, imag) in enumerate(zip(freq.filenames, freq.stoich, freq.imag)):
            self.parent.conf_tab.conf_list.insert('', 'end', text=fnm)
            self.parent.conf_tab.conf_list.set(num, column='stoich', value=stoich)
            self.parent.conf_tab.conf_list.set(num, column='imag', value=imag.sum(0))
        self.show_combo.set('Energy')
        self.filter_combo.set('Thermal')
        self.set_upper_and_lower()
        self.update('values')
            
    def update(self, show=None):
        show = show if show else self.showing
        for en in self.energies.values(): en.trimmer.set(self.blade)
        e_keys = 'ten ent gib scf zpe'.split(' ')
        formats = dict(
            values = lambda v: '{:.4f}'.format(v),
            deltas = lambda v: '{:.4f}'.format(v),
            populations = lambda v: '{:.2f}'.format(v * 100)
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

                
class TslrNotebook(Notebook):
    
    def __init__(self, parent):
        super().__init__(parent)
        self.tslr = None
        self.thread = Thread()
        
        self.main_tab = Loader(self)
        self.add(self.main_tab, text='Main')
        
        self.spectra_tab = Spectra(self)
        self.add(self.spectra_tab, text='Spectra')
        
        self.conf_tab = Conformers(self)
        self.add(self.conf_tab, text='Conformers')
        
        self.info_tab = Frame(self)
        self.add(self.info_tab, text='Info')
        
        self.pack(fill=BOTH, expand=True)
        
        
if __name__ == '__main__':
    
    root = Tk()
    root.title("Tesliper")
    n = TslrNotebook(root)

    root.mainloop()
