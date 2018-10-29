###################
###   IMPORTS   ###
###################

import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import artist
from matplotlib import cm

from . import components as guicom

from .. import tesliper as tesliper

_DEVELOPEMENT = False


###################
###   CLASSES   ###
###################


class Spectra(ttk.Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky='nwse')
        tk.Grid.columnconfigure(self, 1, weight=1)
        tk.Grid.rowconfigure(self, 8, weight=1)

        # Spectra name
        s_name_frame = ttk.LabelFrame(self, text="Spectra type:")
        s_name_frame.grid(column=0, row=0)
        self.s_name = tk.StringVar()
        self.s_name_radio = {}
        names = 'IR UV Raman VCD ECD ROA'.split(' ')
        values = 'ir uv raman vcd ecd roa'.split(' ')
        positions = [(c, r) for c in range(2) for r in range(3)]
        for n, v, (c, r) in zip(names, values, positions):
            b = ttk.Radiobutton(s_name_frame, text=n, variable=self.s_name, value=v,
                                command=lambda v=v: self.spectra_choosen(v))
            b.configure(state='disabled')
            b.grid(column=c, row=r, sticky='w', padx=5)
            self.s_name_radio[v] = b

        # Settings
        sett = ttk.LabelFrame(self, text="Settings:")
        sett.grid(column=0, row=1)
        for no, name in enumerate('Start Stop Step Width'.split(' ')):
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

        # Calculation Mode
        self.mode = tk.StringVar()
        self.single_radio = ttk.Radiobutton(self, text='Single file:',
                                            variable=self.mode, value='single', state='disabled',
                                            command=self.live_preview_callback)
        self.single_radio.grid(column=0, row=2, sticky='w')
        self.average_radio = ttk.Radiobutton(self, text='Average by:',
                                             variable=self.mode, value='average', state='disabled',
                                             command=self.live_preview_callback)
        self.average_radio.grid(column=0, row=4, sticky='w')
        self.stack_radio = ttk.Radiobutton(self, text='Stack by overview',
                                           variable=self.mode, value='stack', state='disabled',
                                           command=self.live_preview_callback)
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
        self.average_ref = {k: v for k, v in zip(average_names, average_keys)}
        self.stack = tk.StringVar()
        self.stack.set('Choose colour...')
        self.stack_box = ttk.Combobox(self, textvariable=self.stack, state='disabled')
        self.stack_box.bind('<<ComboboxSelected>>', self.change_colour)
        self.stack_box.grid(column=0, row=7)
        self.stack_box['values'] = ('Blues Reds Greens spring summer autumn '
                                    'winter copper ocean rainbow '
                                    'nipy_spectral gist_ncar'.split(' '))
        guicom.WgtStateChanger.bars.extend([self.single_radio, self.single_box])
        guicom.WgtStateChanger.both.extend([self.average_radio, self.average_box,
                                            self.stack_radio, self.stack_box])

        # Live preview
        # Recalculate
        frame = ttk.Frame(self)
        frame.grid(column=0, row=8, sticky='n')
        var = tk.BooleanVar()
        var.set(False)
        self.live_prev = ttk.Checkbutton(frame, variable=var, text='Live preview',
                                         state='disabled')
        self.live_prev.grid(column=0, row=0)
        self.live_prev.var = var
        # previously labeled 'Recalculate'
        self.recalc_b = ttk.Button(frame, text='Redraw', state='disabled',
                                   command=self.recalculate_command)
        self.recalc_b.grid(column=1, row=0)
        guicom.WgtStateChanger.bars.extend([self.live_prev, self.recalc_b])

        # Spectrum
        spectra_view = ttk.LabelFrame(self, text='Spectra view')
        spectra_view.grid(column=1, row=0, rowspan=10, sticky='nwse')
        tk.Grid.columnconfigure(spectra_view, 0, weight=1)
        tk.Grid.rowconfigure(spectra_view, 0, weight=1)
        self.figure = Figure()
        # ensure proper plot resizing
        self.bind('<Configure>', lambda event: self.figure.tight_layout())
        self.canvas = FigureCanvasTkAgg(self.figure, master=spectra_view)
        self.canvas.show()
        self.canvas.get_tk_widget().grid(column=0, row=0, sticky='nwse')
        self.ax = None
        self.last_used_settings = {}
        # self.axes = []

        # TO DO:
        # add save/save img buttons

    def spectra_choosen(self, value):
        tslr = self.parent.tslr
        self.visualize_settings()
        self.single_box['values'] = list(tslr.molecules.keys())
        if self.mode.get():
            self.live_preview_callback()
        else:
            self.single_radio.invoke()

    def visualize_settings(self):
        spectra_name = self.s_name.get()
        spectra_type = tesliper.gw.Bars.spectra_type_ref[spectra_name]
        tslr = self.parent.tslr
        try:
            settings = self.last_used_settings[spectra_name]
        except KeyError:
            settings = tslr.parameters[spectra_type]
        for name in 'start stop step width'.split(' '):
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
            # self.mode.get() unnecessary because included in mode_con?
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
                self.ax.plot(x, y_, lw=width, color=col(num / no))
        else:
            self.ax.plot(x, y, lw=width)
        spectra_name = self.s_name.get()
        if spectra_name in ('uv', 'ecd'):
            self.ax.invert_xaxis()
        self.figure.tight_layout()
        self.canvas.show()
        # map(self.figure.delaxes, self.axes)
        # self.axes = []
        # for num, spc in enumerate(spectra):
        # ax = self.figure.add_subplot(len(spectra), 1, num)
        # self.axes.append(ax)
        # ax.plot(spc.abscissa)

    def average_draw(self, spectra_name, option):
        # TO DO: ensure same conformers are taken into account
        tslr = self.parent.tslr
        en_name = self.average_ref[option]
        # en = tslr.energies[en_name]
        # bar_name = tesliper.dw.default_spectra_bars[spectra_name]
        # bar = tslr.bars[bar_name]
        # bar.trimmer.match(en)
        tslr.calculate_spectra(spectra_name, **self.current_settings)
        spc = tslr.get_averaged_spectrum(spectra_name, en_name)
        self.show_spectra(*spc)
        self.canvas.show()

    def single_draw(self, spectra_name, option):
        tslr = self.parent.tslr
        spc = tslr.calculate_single_spectrum(
            spectra_name=spectra_name, conformer=option,
            **self.current_settings
        )
        self.show_spectra(*spc)

    def stack_draw(self, spectra_name, option):
        # TO DO: color of line depending on population
        tslr = self.parent.tslr
        bar_name = tesliper.dw.default_spectra_bars[spectra_name]
        bar = tslr.bars[bar_name]
        # dummy = self.parent.conf_tab._dummy
        # bar.trimmer.match(dummy)
        tslr.calculate_spectra(spectra_name, **self.current_settings)
        spc = tslr.spectra[spectra_name]
        if self.ax: self.figure.delaxes(self.ax)
        self.ax = self.figure.add_subplot(111)
        self.show_spectra(spc.abscissa, spc.values, colour=option, stack=True)

    def change_colour(self, event=None):
        if not self.ax: return
        if self.mode.get() != 'stack': return
        colour = self.stack.get()
        col = cm.get_cmap(colour)
        lines = self.ax.get_lines()
        no = len(lines)
        for num, line in enumerate(lines):
            line.set_color(col(num / no))
        self.canvas.draw()

    @property
    def current_settings(self):
        try:
            settings = {key: float(getattr(self, key).get())
                        for key in ('start stop step width'.split(' '))
                        }
            fit = self.fitting.get()
            settings['fitting'] = getattr(tesliper.dw, fit)
        except ValueError:
            return {}
        return settings

    @guicom.Feedback("Calculating...")
    def recalculate_command(self):
        spectra_name = self.s_name.get()
        if not spectra_name:
            self.parent.logger.debug('spectra_name not specified.')
            return
        self.last_used_settings[spectra_name] = self.current_settings.copy()
        mode = self.mode.get()
        # get value of self.single, self.average or self.stack respectively
        option = getattr(self, mode).get()
        if option.startswith('Choose '):
            return
        self.new_plot()
        # call self.single_draw, self.average_draw or self.stack_draw
        # respectively
        spectra_drawer = getattr(self, '{}_draw'.format(mode))
        spectra_drawer(spectra_name, option)
