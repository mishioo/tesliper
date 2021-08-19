import logging as lgg
import math
import tkinter.ttk as ttk

from matplotlib import cm
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

logger = lgg.getLogger(__name__)


def align_axes(axes, values):
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


class SpectraView(ttk.Frame):
    """Frame embedding matplotlib's canvas for drawing spectra."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky="nwse")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.figure = Figure()
        # ensure proper plot resizing
        self.bind("<Configure>", lambda event: self.figure.tight_layout())
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().grid(column=0, row=0, sticky="nwse")
        self.tslr_ax = None
        self.bars_ax = None
        self.exp_ax = None
        # TO DO:
        # add save/save img buttons

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

    def draw_spectra(
        self,
        spc,
        bars=None,
        colour=None,
        width=0.5,
        stack=False,
        experimental=None,
        reverse_ax=False,
    ):
        # TO DO: correct spectra drawing when offset used
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
            if bars is not None:
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
            if experimental is not None:
                maxes = [max(experimental[1]), max(spc.y)]
                if min(maxes) / max(maxes) > 0.4:
                    # if both will fit fine in one plot
                    tslr_ax.plot(*experimental, lw=width, color="r")
                    values[0] = maxes + [min(experimental[1]), min(spc.y)]
                else:
                    self.exp_ax = exp_ax = tslr_ax.twinx()
                    exp_ax.plot(*experimental, lw=width, color="r")
                    exp_ax.spines["left"].set_position(("axes", -0.1))
                    exp_ax.spines["left"].set_visible(True)
                    exp_ax.yaxis.set_ticks_position("left")
                    exp_ax.tick_params(axis="y", colors="r")
                    tslr_ax.yaxis.set_label_coords(-0.17, 0.5)
                    # tslr_ax.tick_params(axis='y', colors='navy')
                    values.append(experimental[1])
                    axes.append(exp_ax)
            align_axes(axes, values)
        if reverse_ax:
            tslr_ax.invert_xaxis()
        self.figure.tight_layout()
        self.canvas.draw()

    def change_colour(self, colour):
        if not self.tslr_ax:
            return
        col = cm.get_cmap(colour)
        self.tslr_ax.hline.remove()
        lines = self.tslr_ax.get_lines()
        no = len(lines)
        for num, line in enumerate(lines):
            line.set_color(col(num / no))
        self.tslr_ax.hline = self.tslr_ax.axhline(color="lightgray", lw=0.5)
        self.canvas.draw()
