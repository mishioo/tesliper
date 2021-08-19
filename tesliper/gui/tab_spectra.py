# IMPORTS
import logging as lgg
import math
import queue
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.filedialog import askopenfilename

from matplotlib import cm
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .. import tesliper as tesliper
from . import components as guicom
from .components import EnergiesChoice, ScrollableFrame
from .components.controls import ColorsChoice, ConformersChoice
from .components.helpers import float_entry_out_validation, get_float_entry_validator

# LOGGER
logger = lgg.getLogger(__name__)


# CLASSES
class Spectra(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky="nwse")
        tk.Grid.columnconfigure(self, 1, weight=1)
        tk.Grid.rowconfigure(self, 0, weight=1)

        # Controls frame
        # ScrollableFrame.content is a ttk.Frame where actual controls go
        controls = ScrollableFrame(parent=self)
        controls.grid(column=0, row=0, sticky="news")

        # Spectra name
        s_name_frame = ttk.LabelFrame(controls.content, text="Spectra type:")
        s_name_frame.grid(column=0, row=0)
        self.s_name = tk.StringVar()
        self.s_name_radio = {}
        names = "IR UV Raman VCD ECD ROA".split(" ")
        values = "ir uv raman vcd ecd roa".split(" ")
        positions = [(c, r) for c in range(2) for r in range(3)]
        for n, v, (c, r) in zip(names, values, positions):
            b = ttk.Radiobutton(
                s_name_frame,
                text=n,
                variable=self.s_name,
                value=v,
                command=lambda v=v: self.spectra_chosen(v),
            )
            b.configure(state="disabled")
            b.grid(column=c, row=r, sticky="w", padx=5)
            self.s_name_radio[v] = b

        # Settings
        sett = ttk.LabelFrame(controls.content, text="Settings:")
        sett.grid(column=0, row=1, sticky="we")
        tk.Grid.columnconfigure(sett, (1, 2), weight=1)
        ttk.Label(sett, text="Fitting").grid(column=0, row=0)
        fit = tk.StringVar()
        self.fitting = ttk.Combobox(sett, textvariable=fit, state="disabled", width=13)
        self.fitting.bind("<<ComboboxSelected>>", self.live_preview_callback)
        self.fitting.var = fit
        self.fitting.grid(column=1, row=0, columnspan=2, sticky="e")
        self.fitting["values"] = ("lorentzian", "gaussian")
        guicom.WgtStateChanger.bars.append(self.fitting)
        for no, name in enumerate("Start Stop Step Width Offset Scaling".split(" ")):
            ttk.Label(sett, text=name).grid(column=0, row=no + 1)
            var = tk.StringVar()
            entry = ttk.Entry(
                sett,
                textvariable=var,
                width=10,
                state="disabled",
                validate="key",
                validatecommand=get_float_entry_validator(self),
            )
            entry.bind(
                "<FocusOut>",
                lambda e, var=var: (
                    float_entry_out_validation(var),
                    self.live_preview_callback(),
                ),
            )
            setattr(self, name.lower(), entry)
            entry.var = var
            entry.grid(column=1, row=no + 1, sticky="e")
            unit = tk.StringVar()
            unit.set("-")
            entry.unit = unit
            label = ttk.Label(sett, textvariable=unit)
            label.grid(column=2, row=no + 1, sticky="e")
            guicom.WgtStateChanger.bars.append(entry)

        # Calculation Mode
        self.mode = tk.StringVar()
        self.single_radio = ttk.Radiobutton(
            controls.content,
            text="Single file",
            variable=self.mode,
            value="single",
            state="disabled",
            command=self.mode_chosen,
        )
        self.single_radio.grid(column=0, row=2, sticky="w")
        self.average_radio = ttk.Radiobutton(
            controls.content,
            text="Average by energy",
            variable=self.mode,
            value="average",
            state="disabled",
            command=self.mode_chosen,
        )
        self.average_radio.grid(column=0, row=4, sticky="w")
        self.stack_radio = ttk.Radiobutton(
            controls.content,
            text="Stack by overview",
            variable=self.mode,
            value="stack",
            state="disabled",
            command=self.mode_chosen,
        )
        self.stack_radio.grid(column=0, row=6, sticky="w")

        # TODO: call auto_combobox.update_values() when conformers.kept change
        # FIXME: exception occurs when combobox is selected before s_name_radio
        self.single = ConformersChoice(
            controls.content, tesliper=self.parent.tslr, spectra_var=self.s_name
        )
        self.single.bind(
            "<<ComboboxSelected>>",
            lambda event: self.live_preview_callback(event, mode="single"),
        )
        self.single.grid(column=0, row=3)
        self.single["values"] = ()
        self.average = EnergiesChoice(controls.content, tesliper=self.parent.tslr)
        self.average.bind(
            "<<ComboboxSelected>>",
            lambda event: self.live_preview_callback(event, mode="average"),
        )
        self.average.grid(column=0, row=5)

        self.stack = ColorsChoice(controls.content)
        self.stack.bind("<<ComboboxSelected>>", self.change_colour)
        self.stack.grid(column=0, row=7)
        guicom.WgtStateChanger.bars.extend(
            [self.single_radio, self.single, self.stack_radio, self.stack]
        )
        guicom.WgtStateChanger.both.extend([self.average_radio, self.average])
        self.boxes = dict(single=self.single, average=self.average, stack=self.stack)
        self.current_box = None
        for box in self.boxes.values():
            box.grid_remove()

        # Live preview
        # Recalculate
        frame = ttk.Frame(controls.content)
        frame.grid(column=0, row=8, sticky="n")
        var = tk.BooleanVar()
        var.set(False)
        self.reverse_ax = ttk.Checkbutton(
            frame,
            variable=var,
            text="Reverse x-axis",
            state="disabled",
            command=self.live_preview_callback,
        )
        self.reverse_ax.grid(column=0, row=0, sticky="w")
        self.reverse_ax.var = var
        var = tk.BooleanVar()
        var.set(True)
        self.show_bars = ttk.Checkbutton(
            frame,
            variable=var,
            text="Show activities",
            state="disabled",
            command=self.live_preview_callback,
        )
        self.show_bars.grid(column=0, row=1, sticky="w")
        self.show_bars.var = var
        self.show_bars.previous_value = True
        var = tk.BooleanVar()
        var.set(False)
        self.show_exp = ttk.Checkbutton(
            frame,
            variable=var,
            text="Experimental",
            state="disabled",
            command=self.live_preview_callback,
        )
        self.show_exp.grid(column=0, row=2, sticky="w")
        self.show_exp.var = var
        self.load_exp = ttk.Button(
            frame,
            text="Load...",
            state="disabled",
            command=lambda: (self.load_exp_command(), self.live_preview_callback()),
        )
        self.load_exp.grid(column=1, row=2)
        var = tk.BooleanVar()
        var.set(True)
        self.live_prev = ttk.Checkbutton(
            frame, variable=var, text="Live preview", state="disabled"
        )
        self.live_prev.grid(column=0, row=3, sticky="w")
        self.live_prev.var = var
        # previously labeled 'Recalculate'
        self.recalc_b = ttk.Button(
            frame, text="Redraw", state="disabled", command=self.recalculate_command
        )
        self.recalc_b.grid(column=1, row=3)
        guicom.WgtStateChanger.bars.extend([self.live_prev, self.recalc_b])

        # Spectrum
        spectra_view = ttk.LabelFrame(self, text="Spectra view")
        spectra_view.grid(column=1, row=0, sticky="nwse")
        tk.Grid.columnconfigure(spectra_view, 0, weight=1)
        tk.Grid.rowconfigure(spectra_view, 0, weight=1)
        self.figure = Figure()
        # ensure proper plot resizing
        self.bind("<Configure>", lambda event: self.figure.tight_layout())
        self.canvas = FigureCanvasTkAgg(self.figure, master=spectra_view)
        # self.canvas.draw()
        self.canvas.get_tk_widget().grid(column=0, row=0, sticky="nwse")
        self.tslr_ax = None
        self.bars_ax = None
        self.exp_ax = None
        self.last_used_settings = {
            name: {
                "offset": 0,
                "scaling": 1,
                "show_bars": True,
                "show_exp": False,
                "reverse_ax": name not in ("uv", "ecd"),
            }
            for name in self.s_name_radio
        }
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
        filename = askopenfilename(
            parent=self,
            title="Select spectrum file.",
            filetypes=[
                ("text files", "*.txt"),
                ("xy files", "*.xy"),
                # ("spc files", "*.spc"),
                # spc not supported yet
                ("all files", "*.*"),
            ],
        )
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
            self.current_box.grid_remove()
        self.current_box = self.boxes[mode]
        self.current_box.grid()
        getattr(self, mode).update_values()  # update linked combobox values
        if mode == "single":
            self.show_bars.config(state="normal")
            self.show_bars.var.set(self.show_bars.previous_value)
        else:
            self.show_bars.config(state="disabled")
            self.show_bars.previous_value = self.show_bars.var.get()
            self.show_bars.var.set(False)
        self.live_preview_callback()

    def spectra_chosen(self, event=None):
        tslr = self.parent.tslr
        self.visualize_settings()
        bar = tesliper.dw.DEFAULT_ACTIVITIES[self.s_name.get()]
        self.single["values"] = [k for k, v in tslr.conformers.items() if bar in v]
        self.reverse_ax.config(state="normal")
        self.load_exp.config(state="normal")
        self.show_exp.config(state="normal")
        if self.mode.get():
            self.live_preview_callback()
        else:
            self.single_radio.invoke()

    def visualize_settings(self):
        spectra_name = self.s_name.get()
        spectra_type = tesliper.gw.SpectralData.spectra_type_ref[spectra_name]
        tslr = self.parent.tslr
        last_used = self.last_used_settings[spectra_name]
        settings = tslr.parameters[spectra_type].copy()
        settings.update(last_used)
        for name, sett in settings.items():
            if name == "fitting":
                try:
                    self.fitting.var.set(settings["fitting"].__name__)
                except AttributeError:
                    self.fitting.var.set(settings["fitting"])
            else:
                entry = getattr(self, name)
                entry.var.set(sett)
                try:
                    entry.unit.set(tesliper.gw.Spectra._units[spectra_name][name])
                except AttributeError:
                    logger.debug(f"Pass on {name}")
                except KeyError:
                    if name == "offset":
                        entry.unit.set(
                            tesliper.gw.Spectra._units[spectra_name]["start"]
                        )
                    elif name == "scaling":
                        pass
                    else:
                        raise ValueError(f"Invalid setting name: {name}")

    def live_preview_callback(self, event=None, mode=False):
        # TO DO: separate things, that don't need recalculation
        # TO DO: show/hide bars/experimental plots when checkbox clicked
        # TO DO: rewrite this function with sense
        spectra_name = self.s_name.get()
        mode_con = self.mode.get() == mode if mode else True
        settings_con = (
            spectra_name not in self.last_used_settings
            or self.current_settings != self.last_used_settings[spectra_name]
        )
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
        lowers = [1 if math.isclose(L, 0.0) else L for L in lowers]
        uppers = [-1 if math.isclose(u, 0.0) else u for u in uppers]
        # pick "most centered" axis
        res = [abs(u + L) for L, u in zip(lowers, uppers)]
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
        diff = [abs(u - L) for L, u in zip(lower_lims, upper_lims)]
        margin = [x * 0.05 for x in diff]
        lower_lims = [lim - m for lim, m in zip(lower_lims, margin)]
        upper_lims = [lim + m for lim, m in zip(upper_lims, margin)]
        # set axes limits
        [ax.set_ylim(low, up) for ax, low, up in zip(axes, lower_lims, upper_lims)]

    def show_spectra(self, spc, bars=None, colour=None, width=0.5, stack=False):
        # TO DO: correct spectra drawing when offset used
        spc.offset = float(self.offset.var.get())
        spc.scaling = float(self.scaling.var.get())
        self.new_plot()
        self.tslr_ax = tslr_ax = self.figure.add_subplot(111)
        tslr_ax.set_xlabel(spc.units["x"])
        tslr_ax.set_ylabel(spc.units["y"])
        tslr_ax.hline = tslr_ax.axhline(color="lightgray", lw=width)
        if stack:
            col = cm.get_cmap(colour)
            no = len(spc.y)
            x = spc.x
            for num, y_ in enumerate(spc.y):
                tslr_ax.plot(x, y_, lw=width, color=col(num / no))
        else:
            tslr_ax.plot(spc.x, spc.y, lw=width, color="k")
            values = [spc.y]
            axes = [tslr_ax]
            if self.show_bars.var.get() and bars is not None:
                self.bars_ax = bars_ax = tslr_ax.twinx()
                freqs = (
                    bars.wavelengths[0]
                    if spc.genre in ("uv", "ecd")
                    else bars.frequencies[0]
                )
                freqs = freqs + spc.offset
                # show only activities within range requested in calculations
                blade = (freqs >= min(spc.x)) & (freqs <= max(spc.x))
                markerline, stemlines, baseline = bars_ax.stem(
                    freqs[blade],
                    bars.values[0][blade],
                    linefmt="b-",
                    markerfmt=" ",
                    basefmt=" ",
                )
                stemlines.set_linewidth(width)
                bars_ax.set_ylabel(bars.units)
                bars_ax.tick_params(axis="y", colors="b")
                values.append(bars.values[0])
                axes.append(bars_ax)
            if self.show_exp.var.get() and self.exp_spc is not None:
                maxes = [max(self.exp_spc[1]), max(spc.y)]
                if min(maxes) / max(maxes) > 0.4:
                    # if both will fit fine in one plot
                    tslr_ax.plot(*self.exp_spc, lw=width, color="r")
                    values[0] = maxes + [min(self.exp_spc[1]), min(spc.y)]
                else:
                    self.exp_ax = exp_ax = tslr_ax.twinx()
                    exp_ax.plot(*self.exp_spc, lw=width, color="r")
                    exp_ax.spines["left"].set_position(("axes", -0.1))
                    exp_ax.spines["left"].set_visible(True)
                    exp_ax.yaxis.set_ticks_position("left")
                    exp_ax.tick_params(axis="y", colors="r")
                    tslr_ax.yaxis.set_label_coords(-0.17, 0.5)
                    # tslr_ax.tick_params(axis='y', colors='navy')
                    values.append(self.exp_spc[1])
                    axes.append(exp_ax)
            self.align_axes(axes, values)
        if self.reverse_ax.var.get():
            tslr_ax.invert_xaxis()
        self.figure.tight_layout()
        self.canvas.draw()

    def average_draw(self, spectra_name, option):
        # TO DO: ensure same conformers are taken into account
        self._calculate_spectra(spectra_name, option, "average")
        queue_ = self.parent.thread.queue
        self._show_spectra(queue_)

    def single_draw(self, spectra_name, option):
        self._calculate_spectra(spectra_name, option, "single")
        bar_name = tesliper.dw.DEFAULT_ACTIVITIES[spectra_name]
        with self.parent.tslr.conformers.trimmed_to([option]):
            bars = self.parent.tslr[bar_name]
        queue_ = self.parent.thread.queue
        self._show_spectra(queue_, bars=bars)

    def stack_draw(self, spectra_name, option):
        # TO DO: color of line depending on population
        self._calculate_spectra(spectra_name, option, "stack")
        if self.tslr_ax:
            self.figure.delaxes(self.tslr_ax)
        self.tslr_ax = self.figure.add_subplot(111)
        queue_ = self.parent.thread.queue
        self._show_spectra(queue_, colour=option, stack=True)

    def change_colour(self, event=None):
        if not self.tslr_ax or self.mode.get() != "stack":
            return
        colour = self.stack.var.get()
        col = cm.get_cmap(colour)
        self.tslr_ax.hline.remove()
        lines = self.tslr_ax.get_lines()
        no = len(lines)
        for num, line in enumerate(lines):
            line.set_color(col(num / no))
        self.tslr_ax.hline = self.tslr_ax.axhline(color="lightgray", lw=0.5)
        self.canvas.draw()

    def _show_spectra(self, queue_, bars=None, colour=None, width=0.5, stack=False):
        try:
            spc = queue_.get(0)  # data put to queue by self._calculate_spectra
            self.show_spectra(spc, bars=bars, colour=colour, width=width, stack=stack)
        except queue.Empty:
            self.after(20, self._show_spectra, queue_, bars, colour, width, stack)

    @guicom.ThreadedMethod(progbar_msg="Calculating...")
    def _calculate_spectra(self, spectra_name, option, mode):
        tslr = self.parent.tslr
        if mode == "single":
            spc = tslr.calculate_single_spectrum(
                spectra_name=spectra_name, conformer=option, **self.calculation_params
            )
        else:
            spc = tslr.calculate_spectra(spectra_name, **self.calculation_params)[
                spectra_name
            ]  # tslr.calculate_spectra returns dictionary
            if mode == "average":
                en_name = self.average.get_genre()
                spc = tslr.get_averaged_spectrum(spectra_name, en_name)
        return spc

    @property
    def calculation_params(self):
        d = {
            k: v
            for k, v in self.current_settings.items()
            if k in "start stop step width fitting".split(" ")
        }
        return d

    @property
    def current_settings(self):
        try:
            settings = {
                key: float(getattr(self, key).get())
                for key in "start stop step width offset scaling".split(" ")
            }
            settings.update(
                {
                    key: getattr(self, key).var.get()
                    for key in "reverse_ax show_bars show_exp".split(" ")
                }
            )
            fit = self.fitting.get()
            settings["fitting"] = getattr(tesliper.dw, fit)
        except ValueError:
            return {}
        return settings

    def recalculate_command(self):
        spectra_name = self.s_name.get()
        if not spectra_name:
            logger.debug("spectra_name not specified.")
            return
        self.last_used_settings[spectra_name] = self.current_settings.copy()
        mode = self.mode.get()
        # get value from self.single, self.average or self.stack respectively
        option = getattr(self, mode).var.get()
        if option.startswith("Choose "):
            return
        logger.debug("Recalculating!")
        self.new_plot()
        # call self.single_draw, self.average_draw or self.stack_draw
        # respectively
        drawers = {
            "single": self.single_draw,
            "average": self.average_draw,
            "stack": self.stack_draw,
        }
        spectra_drawer = drawers[mode]
        spectra_drawer(spectra_name, option)
