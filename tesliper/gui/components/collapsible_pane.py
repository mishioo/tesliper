import logging as lgg
import tkinter.ttk as ttk

# LOGGER
logger = lgg.getLogger(__name__)


# CLASSES
class CollapsiblePane(ttk.LabelFrame):
    """LabelFrame that can be collapsed to show only its label.
    Clicking it will toggle between collapsed and unraveled states.

    Adds `collapsed` parameter to `.configure()` setting it to `True` will hide
    `CollapsiblePane`'s content, and setting to `False` will do the opposite.
    """

    def __init__(
        self,
        parent,
        text="",
        collapsed=False,
        collapsed_mark="▷",
        unraveled_mark="▽",
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.collapsed = collapsed
        self.text = text
        self.collapsed_mark = collapsed_mark
        self.unraveled_mark = unraveled_mark

        ttk.Frame(self).grid(column=0, row=0, sticky="nwe")
        self.content = ttk.Frame(self)
        self.content.grid(column=0, row=0, sticky="news")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.bind("<Button-1>", self.toggle)
        self.configure(collapsed=self.collapsed)

    @property
    def mark(self):
        return self.collapsed_mark if self.collapsed else self.unraveled_mark

    def configure(self, cnf=None, **kwargs):
        if "text" in kwargs:
            self.text = kwargs["text"]
        if "collapsed" in kwargs:
            self.collapsed = kwargs.pop("collapsed")
            kwargs["text"] = f"{self.mark} {self.text}"
            self.content.grid_remove() if self.collapsed else self.content.grid()
        content_config = {
            cfg: kwargs[cfg]
            for cfg in (
                "background",
                "cursor",
                "highlightbackground",
            )
            if cfg in kwargs
        }
        self.content.configure(**content_config)
        super().configure(cnf, **kwargs)

    def toggle(self, _event=None):
        self.configure(collapsed=not self.collapsed)
