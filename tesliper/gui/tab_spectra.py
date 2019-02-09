# IMPORTS
import math
import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.filedialog import askopenfilename
from tkinter import messagebox

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import artist
from matplotlib import cm

from . import components as guicom

from .. import tesliper as tesliper


# LOGGER
logger = lgg.getLogger(__name__)


# CLASSES
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
            b = ttk.Radiobutton(s_name_frame, text=n, variable=self.s_name,
                                value=v,
                                command=lambda v=v: self.spectra_chosen(v))
            b.configure(state='disabled')
            b.grid(column=c, row=r, sticky='w', padx=5)
            self.s_name_radio[v] = b

        # Settings
        sett = ttk.LabelFrame(self, text="Settings:")
        sett.grid(column=0, row=1, sticky='we')
        tk.Grid.columnconfigure(sett, (1, 2), weight=1)
        ttk.Label(sett, text='Fitting').grid(column=0, row=0)
        fit = tk.StringVar()
        self.fitting = ttk.Combobox(sett, textvariable=fit, state='disabled',
                                    width=13)
        self.fitting.bind('<<ComboboxSelected>>', self.live_preview_callback)
        self.fitting.var = fit
        self.fitting.grid(column=1, row=0, columnspan=2, sticky='e')
        self.fitting['values'] = ('lorentzian', 'gaussian')
        guicom.WgtStateChanger.bars.append(self.fitting)
        for no, name in enumerate(
                'Start Stop Step Width Offset Scaling'.split(' ')
        ):
            ttk.Label(sett, text=name).grid(column=0, row=no+1)
            var = tk.StringVar()
            entry = ttk.Entry(sett, textvariable=var, width=10,
                              state='disabled', validate='key',
                              validatecommand=self.parent.validate_entry)
            entry.bind('<FocusOut>',
                       lambda e, var=var: (
                           self.parent.entry_out_validation(var),
                           self.live_preview_callback()
                       ))
            setattr(self, name.lower(), entry)
            entry.var = var
            entry.grid(column=1, row=no+1, sticky='e')
            unit = tk.StringVar()
            unit.set('-')
            entry.unit = unit
            label = ttk.Label(sett, textvariable=unit)
            label.grid(column=2, row=no+1, sticky='e')
            guicom.WgtStateChanger.bars.append(entry)

        # Calculation Mode
        self.mode = tk.StringVar()
        self.single_radio = ttk.Radiobutton(self, text='Single file',
                                            variable=self.mode, value='single',
                                            state='disabled',
                                            command=self.mode_chosen)
        self.single_radio.grid(column=0, row=2, sticky='w')
        self.average_radio = ttk.Radiobutton(self, text='Average by energy',
                                             variable=self.mode,
                                             value='average', state='disabled',
                                             command=self.mode_chosen)
        self.average_radio.grid(column=0, row=3, sticky='w')
        self.stack_radio = ttk.Radiobutton(self, text='Stack by overview',
                                           variable=self.mode, value='stack',
                                           state='disabled',
                                           command=self.mode_chosen)
        self.stack_radio.grid(column=0, row=4, sticky='w')

        self.single = tk.StringVar()
        self.single.set('Choose conformer...')
        self.single_box = ttk.Combobox(self, textvariable=self.single,
                                       state='disabled')
        self.single_box.bind(
            '<<ComboboxSelected>>',
            lambda event: self.live_preview_callback(event, mode='single')
        )
        # self.single_box.grid(column=0, row=3)
        self.single_box['values'] = ()
        self.average = tk.StringVar()
        self.average.set('Choose energy...')
        self.average_box = ttk.Combobox(self, textvariable=self.average,
                                        state='disabled')
        self.average_box.bind(
            '<<ComboboxSelected>>',
            lambda event: self.live_preview_callback(event, mode='average')
        )
        # self.average_box.grid(column=0, row=5)
        average_names = 'Thermal Enthalpy Gibbs SCF Zero-Point'.split(' ')
        self.average_box['values'] = average_names
        average_keys = 'ten ent gib scf zpe'.split(' ')
        self.average_ref = {k: v for k, v in zip(average_names, average_keys)}
        self.stack = tk.StringVar()
        self.stack.set('Choose colour...')
        self.stack_box = ttk.Combobox(self, textvariable=self.stack,
                                      state='disabled')
        self.stack_box.bind('<<ComboboxSelected>>', self.change_colour)
        # self.stack_box.grid(column=0, row=7)
        self.stack_box['values'] = ('Blues Reds Greens spring summer autumn '
                                    'winter copper ocean rainbow '
                                    'nipy_spectral gist_ncar'.split(' '))
        guicom.WgtStateChanger.bars.extend([self.single_radio, self.single_box])
        guicom.WgtStateChanger.both.extend(
            [self.average_radio, self.average_box,
             self.stack_radio, self.stack_box])
        self.boxes = dict(single=self.single_box, average=self.average_box,
                          stack=self.stack_box)
        self.current_box = None

        # Live preview
        # Recalculate
        frame = ttk.Frame(self)
        frame.grid(column=0, row=8, sticky='n')
        var = tk.BooleanVar()
        var.set(True)
        self.show_bars = ttk.Checkbutton(frame, variable=var, text='Show bars',
                                         state='disabled',
                                         command=self.live_preview_callback)
        self.show_bars.grid(column=0, row=0, sticky='w')
        self.show_bars.var = var
        self.show_bars.previous_value = True
        var = tk.BooleanVar()
        var.set(False)
        self.show_exp = ttk.Checkbutton(frame, variable=var,
                                        text='Experimental', state='disabled',
                                        command=self.live_preview_callback)
        self.show_exp.grid(column=0, row=1, sticky='w')
        self.show_exp.var = var
        self.load_exp = ttk.Button(
            frame, text='Load...', state='disabled',
            command=lambda: (
                self.load_exp_command(), self.live_preview_callback()
            )
        )
        self.load_exp.grid(column=1, row=1)
        var = tk.BooleanVar()
        var.set(False)
        self.live_prev = ttk.Checkbutton(frame, variable=var,
                                         text='Live preview', state='disabled')
        self.live_prev.grid(column=0, row=2, sticky='w')
        self.live_prev.var = var
        # previously labeled 'Recalculate'
        self.recalc_b = ttk.Button(frame, text='Redraw', state='disabled',
                                   command=self.recalculate_command)
        self.recalc_b.grid(column=1, row=2)
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
        # self.canvas.draw()
        self.canvas.get_tk_widget().grid(column=0, row=0, sticky='nwse')
        self.tslr_ax = None
        self.bars_ax = None
        self.exp_ax = None
        self.last_used_settings = {}
        self._exp_spc = {k: None for k in self.s_name_radio.keys()}

        # TO DO:
        # add save/save img buttons

    @property
    def exp_spc(self):
        return self._exp_spc[self.s_name.get()]

    @exp_spc.setter
    def exp_spc(self, value):
        self._exp_spc[self.s_name.get()] = value

    def load_exp_command(self):
        filename = askopenfilename(parent=self, title='Select spectrum file.',
                                   filetypes=[("text files", "*.txt"),
                                              ("xy files", "*.xy"),
                                              # ("spc files", "*.spc"),
                                              # spc not supported yet
                                              ("all files", "*.*")])
        if filename:
            try:
                spc = self.parent.tslr.soxhlet.load_spectrum(filename)
                self.exp_spc = spc
            except ValueError:
                logger.warning(
                    "Experimental spectrum couldn't be loaded. "
                    "Please check if format of your file is supported"
                    " or if file is not corrupted."
                )
        else:
            return

    def mode_chosen(self, event=None):
        mode = self.mode.get()
        if self.current_box is not None:
            self.current_box.grid_forget()
        self.current_box = self.boxes[mode]
        self.current_box.grid(column=0, row=5)
        if mode == 'single':
            self.show_bars.config(state='normal')
            self.show_bars.var.set(self.show_bars.previous_value)
        else:
            self.show_bars.config(state='disabled')
            self.show_bars.previous_value = self.show_bars.var.get()
            self.show_bars.var.set(False)
        self.live_preview_callback()

    def spectra_chosen(self, event=None):
        tslr = self.parent.tslr
        self.visualize_settings()
        bar = tesliper.gw.default_spectra_bars[self.s_name.get()]
        self.single_box['values'] = [k for k, v in tslr.molecules.items()
                                     if bar in v]
        self.load_exp.config(state='normal')
        self.show_exp.config(state='normal')
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
            settings = tslr.parameters[spectra_type].copy()
            settings['offset'] = 0
            settings['scaling'] = 1
        for name, sett in settings.items():
            if name == 'fitting':
                try:
                    self.fitting.var.set(settings['fitting'].__name__)
                except AttributeError:
                    self.fitting.var.set(settings['fitting'])
            else:
                entry = getattr(self, name)
                entry.var.set(sett)
                try:
                    entry.unit.set(
                        tesliper.gw.Spectra._units[spectra_name][name])
                except KeyError:
                    if name == 'offset':
                        entry.unit.set(
                            tesliper.gw.Spectra._units[spectra_name]['start'])
                    elif name == 'scaling':
                        pass
                    else:
                        raise ValueError(f'Invalid setting name: {name}')

    def live_preview_callback(self, event=None, mode=False):
        # TO DO: separate things, that don't need recalculation
        # TO DO: show/hide bars/experimental plots when checkbox clicked
        spectra_name = self.s_name.get()
        mode_con = self.mode.get() == mode if mode else True
        settings_con = spectra_name not in self.last_used_settings or \
            self.current_settings != self.last_used_settings[spectra_name]
        core = any([not self.tslr_ax, mode_con, settings_con])
        if all([core, self.live_prev.var.get(), self.mode.get()]):
            # self.mode.get() unnecessary because included in mode_con?
            self.recalculate_command()

    def new_plot(self):
        if self.tslr_ax:
            self.figure.delaxes(self.tslr_ax)
            self.tslr_ax = None
        if self.bars_ax:
            self.figure.delaxes(self.bars_ax)
            self.bars_ax = None
        if self.exp_ax:
            self.figure.delaxes(self.exp_ax)
            self.exp_ax = None

    def align_axes(self, axes, values):
        """Align zeros of the axes, zooming them out by same ratio"""
        # based on https://stackoverflow.com/a/46901839
        if not len(values) == len(axes):
            raise ValueError(
                f"Number of values ({len(values)}) different than number of"
                f"axes ({len(axes)})."
            )
        extrema = [[min(v), max(v)] for v in values]
        # upper and lower limits
        lowers, uppers = zip(*extrema)
        all_positive = min(lowers) > 0
        all_negative = max(uppers) < 0
        # reset for divide by zero issues
        lowers = [1 if math.isclose(l, 0.0) else l for l in lowers]
        uppers = [-1 if math.isclose(u, 0.0) else u for u in uppers]
        # pick "most centered" axis
        res = [abs(u + l) for l, u in zip(lowers, uppers)]
        min_index = res.index(min(res))
        # scale positive or negative part
        multiplier1 = -abs(uppers[min_index] / lowers[min_index])
        multiplier2 = -abs(lowers[min_index] / uppers[min_index])
        lower_lims, upper_lims = [], []
        for i, (low, up) in enumerate(extrema):
            # scale positive or negative part based on which induces valid
            if i != min_index:
                lower_change = up * multiplier2
                upper_change = low * multiplier1
                if upper_change < up:
                    lower_lims.append(lower_change)
                    upper_lims.append(up)
                else:
                    lower_lims.append(low)
                    upper_lims.append(upper_change)
            else:
                lower_lims.append(low)
                upper_lims.append(up)
        # bump by 10% for a margin
        if all_positive:
            lower_lims = [0 for _ in range(len(lower_lims))]
        if all_negative:
            upper_lims = [0 for _ in range(len(upper_lims))]
        diff = [abs(u - l) for l, u in zip(lower_lims, upper_lims)]
        margin = [x * .05 for x in diff]
        lower_lims = [lim - m for lim, m in zip(lower_lims, margin)]
        upper_lims = [lim + m for lim, m in zip(upper_lims, margin)]
        # set axes limits
        [ax.set_ylim(low, up) for ax, low, up in
         zip(axes, lower_lims, upper_lims)]

    def show_spectra(self, spc, bars=None, colour=None, width=0.5,
                     stack=False):
        spc.offset = float(self.offset.var.get())
        spc.scaling = float(self.scaling.var.get())
        self.new_plot()
        self.tslr_ax = tslr_ax = self.figure.add_subplot(111)
        tslr_ax.set_xlabel(spc.units['x'])
        tslr_ax.set_ylabel(spc.units['y'])
        tslr_ax.axhline(color='lightgray', lw=width)
        if stack:
            col = cm.get_cmap(colour)
            no = len(spc.y)
            x = spc.x
            for num, y_ in enumerate(spc.y):
                tslr_ax.plot(x, y_, lw=width, color=col(num / no))
        else:
            tslr_ax.plot(spc.x, spc.y, lw=width, color='k')
            values = [spc.y]
            axes = [tslr_ax]
            if self.show_bars.var.get() and bars is not None:
                self.bars_ax = bars_ax = tslr_ax.twinx()
                freqs = bars.frequencies[0] + spc.offset
                # show only bars within range requested in calculations
                blade = (freqs >= min(spc.x)) & (freqs <= max(spc.x))
                markerline, stemlines, baseline = bars_ax.stem(
                    freqs[blade], bars.values[0][blade], linefmt='b-',
                    markerfmt=' ', basefmt=' '
                )
                for line in stemlines:
                    line.set_linewidth(width)
                bars_ax.set_ylabel(bars.units)
                bars_ax.tick_params(axis='y', colors='b')
                values.append(bars.values[0])
                axes.append(bars_ax)
            if self.show_exp.var.get() and self.exp_spc is not None:
                maxes = [max(self.exp_spc[1]), max(spc.y)]
                if min(maxes) / max(maxes) > 0.4:
                    # if both will fit fine in one plot
                    tslr_ax.plot(*self.exp_spc, lw=width, color='r')
                    values[0] = maxes + [min(self.exp_spc[1]), min(spc.y)]
                else:
                    self.exp_ax = exp_ax = tslr_ax.twinx()
                    exp_ax.plot(*self.exp_spc, lw=width, color='r')
                    exp_ax.spines["left"].set_position(("axes", -0.1))
                    exp_ax.spines["left"].set_visible(True)
                    exp_ax.yaxis.set_ticks_position('left')
                    exp_ax.tick_params(axis='y', colors='r')
                    tslr_ax.yaxis.set_label_coords(-0.17, 0.5)
                    # tslr_ax.tick_params(axis='y', colors='navy')
                    values.append(self.exp_spc[1])
                    axes.append(exp_ax)
            self.align_axes(axes, values)
        spectra_name = self.s_name.get()
        if spectra_name in ('uv', 'ecd'):
            tslr_ax.invert_xaxis()
        self.figure.tight_layout()
        self.canvas.draw()

    def average_draw(self, spectra_name, option):
        # TO DO: ensure same conformers are taken into account
        self._calculate_spectra(spectra_name, option, 'average')
        queue = self.parent.thread.queue
        self._show_spectra(queue)

    def single_draw(self, spectra_name, option):
        self._calculate_spectra(spectra_name, option, 'single')
        bar_name = tesliper.gw.default_spectra_bars[spectra_name]
        with self.parent.tslr.molecules.trimmed_to([option]):
            bars = self.parent.tslr[bar_name]
        queue = self.parent.thread.queue
        self._show_spectra(queue, bars=bars)

    def stack_draw(self, spectra_name, option):
        # TO DO: color of line depending on population
        self._calculate_spectra(spectra_name, option, 'stack')
        if self.tslr_ax:
            self.figure.delaxes(self.tslr_ax)
        self.tslr_ax = self.figure.add_subplot(111)
        queue = self.parent.thread.queue
        self._show_spectra(queue, colour=option, stack=True)

    def change_colour(self, event=None):
        # TO DO: make it color graph same way as show_spectra() does
        if not self.tslr_ax or self.mode.get() != 'stack':
            return
        colour = self.stack.get()
        col = cm.get_cmap(colour)
        lines = self.tslr_ax.get_lines()
        no = len(lines)
        for num, line in enumerate(lines):
            line.set_color(col(num / no))
        self.tslr_ax.axhline(color='lightgray', lw=0.5)
        self.canvas.draw()

    def _show_spectra(self, queue_, bars=None, colour=None, width=0.5,
                      stack=False):
        try:
            spc = queue_.get(0)
            self.show_spectra(spc, bars=bars, colour=colour, width=width,
                              stack=stack)
        except guicom.queue.Empty:
            self.after(
                100, self._show_spectra, queue_, bars, colour, width, stack
            )

    @guicom.Feedback("Calculating...")
    def _calculate_spectra(self, spectra_name, option, mode):
        tslr = self.parent.tslr
        if mode == 'single':
            spc = tslr.calculate_single_spectrum(
                spectra_name=spectra_name, conformer=option,
                **self.calculation_params
            )
        else:
            spc = tslr.calculate_spectra(
                spectra_name, **self.calculation_params
            )
            if mode == 'average':
                en_name = self.average_ref[option]
                spc = tslr.get_averaged_spectrum(spectra_name, en_name)
        print(f'calculate: {type(spc)}')
        return spc


    @property
    def calculation_params(self):
        d = {k: v for k, v in self.current_settings.items()
             if k in 'start stop step width fitting'.split(' ')}
        return d

    @property
    def current_settings(self):
        try:
            settings = {
                key: float(getattr(self, key).get())
                for key in 'start stop step width offset scaling'.split(' ')
            }
            fit = self.fitting.get()
            settings['fitting'] = getattr(tesliper.dw, fit)
        except ValueError:
            return {}
        return settings

    def recalculate_command(self):
        spectra_name = self.s_name.get()
        if not spectra_name:
            logger.debug('spectra_name not specified.')
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
