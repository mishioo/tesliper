from tkinter import ttk


class LabelSeparator(ttk.Frame):
    """A horizontal separator with centered text over it."""

    # based on https://stackoverflow.com/q/38396900/11416569
    def __init__(self, parent, text="", **kwargs):
        super().__init__(parent, **kwargs)
        self.columnconfigure(0, weight=1)

        self.separator = ttk.Separator(self, orient="horizontal")
        self.separator.grid(row=0, column=0, sticky="ew")

        self.label = ttk.Label(self, text=text)
        self.label.grid(row=0, column=0)
