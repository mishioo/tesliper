import logging as lgg
import tkinter.ttk as ttk

import numpy as np
from matplotlib import cm
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

logger = lgg.getLogger(__name__)


def align_yaxis(axes):
    """Align zeros of the axes."""
    # credits: https://stackoverflow.com/a/59564220/11416569
    y_lims = np.array([ax.get_ylim() for ax in axes])

    # force 0 to appear on all axes, comment if don't need
    y_lims[:, 0] = y_lims[:, 0].clip(None, 0)
    y_lims[:, 1] = y_lims[:, 1].clip(0, None)

    # normalize all axes
    y_mags = (y_lims[:, 1] - y_lims[:, 0]).reshape(len(y_lims), 1)
    y_lims_normalized = y_lims / y_mags

    # find combined range
    y_new_lims_normalized = np.array(
        [np.min(y_lims_normalized), np.max(y_lims_normalized)]
    )

    # denormalize combined range to get new axes
    new_lims = y_new_lims_normalized * y_mags
    for i, ax in enumerate(axes):
        ax.set_ylim(new_lims[i])


class SpectraView(ttk.Frame):
    """Frame embedding matplotlib's canvas for drawing spectra."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
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
                axes.append(bars_ax)
            if experimental is not None:
                extremes = [
                    max(abs(max(experimental[1])), abs(min(experimental[1]))),
                    max(abs(max(spc.y)), abs(min(spc.y))),
                ]
                if min(extremes) / max(extremes) > 0.1:
                    # if both will fit fine in one plot
                    tslr_ax.plot(*experimental, lw=width, color="r")
                else:
                    self.exp_ax = exp_ax = tslr_ax.twinx()
                    exp_ax.plot(*experimental, lw=width, color="r")
                    exp_ax.spines["left"].set_position(("axes", -0.1))
                    exp_ax.spines["left"].set_visible(True)
                    exp_ax.yaxis.set_ticks_position("left")
                    exp_ax.tick_params(axis="y", colors="r")
                    tslr_ax.yaxis.set_label_coords(-0.17, 0.5)
                    # tslr_ax.tick_params(axis='y', colors='navy')
                    axes.append(exp_ax)
            align_yaxis(axes)
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
