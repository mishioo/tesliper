###################
###   IMPORTS   ###
###################

import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from threading import Thread
from collections import OrderedDict
from copy import copy
from functools import partial

import tesliper


##################
###   LOGGER   ###
##################

logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)
logger.debug("Workin', baby!")


###################
###   CLASSES   ###
###################

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
        self.tag_config('WARNING', foreground='dark violet', font="Courier 10 italic")
        self.tag_config('ERROR', foreground='red3')
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
    spectra = []
    all = []
    
    def __init__(self, function=None):
        if function is not None:
            self.function = function
        else:
            self.function = lambda *args, **kwargs: None
    
    def __call__(self, other, *args, **kwargs):
        outcome = self.function(other, *args, **kwargs)
        self.set_states(other)
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
        spectra = None if not self.tslr_inst else self.tslr_inst.spectra
        return dict(
            tslr = self.enable if self.tslr_inst else self.disable,
            energies = self.enable if energies else self.disable,
            bars = self.enable if bars else self.disable,
            either = self.enable if (bars or energies) else self.disable,
            both = self.enable if (bars and energies) else self.disable,
            spectra = self.enable if spectra else self.disable,
            all = self.enable if (energies and spectra) else self.disable
            )
        
    def enable(self, widget):
        if isinstance(widget, ttk.Combobox):
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
    
    def set_states(self, other):
        try:
            self.gui = other.parent
        except AttributeError:
            self.gui = other.gui
        self.tslr_inst = self.gui.tslr
        for dependency, changer in self.changers.items():
            for widget in getattr(self, dependency):
                changer(widget)
        self.change_spectra_radio()


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
            logger.critical('Something unexpected happend.',
                                     exc_info = self.exc)
            return
            #raise self.exc
        return return_value

        
class Feedback:
            
    def __init__(self, progbar_msg):
        self.progbar_msg = progbar_msg
        
    def __call__(self, function):
        def wrapper(other, *args, **kwargs):
            #other becomes self from decorated method
            if other.parent.thread.is_alive():
                msg = "Can't start {}, while {} is still running.".format(
                    function, other.parent.thread.target)
                logger.debug(msg)
                return #log and do nothing
            else:
                other.parent.thread = FeedbackThread(
                    other.parent, self.progbar_msg, function,
                    [other]+list(args), kwargs
                    )
            other.parent.thread.start()
        return wrapper
        
        
class Popup(tk.Toplevel):

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.master = master
        self.grab_set()
        try:
            width, height = kwargs['width'], kwargs['height']
            self.set_geometry(width, height)
        except KeyError:
            pass

    def set_geometry(self, width, height):
        x = self.master.winfo_pointerx()
        y = self.master.winfo_pointery()
        geometry = '{}x{}{:+n}{:+n}'.format(width, height, x, y)
        self.geometry(geometry)


class BarsPopup(Popup):

    bar_names = "IR Inten.,E-M Angle,Dip. Str.,Rot. Str.,Osc. Str. (velo),"\
                "Rot. Str. (velo),Osc. Str. (length),Rot. Str. (length),Raman1,ROA1".split(',')
    bar_keys = "iri emang dip rot vosc vrot losc lrot raman1 roa1".split(' ')
    
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Bars extraction")
        tk.Grid.rowconfigure(self, 6, weight=1)
        tk.Grid.columnconfigure(self, 2, weight=1)
        ttk.Label(self, text="Chose bars you wish to extract:").grid(
            column=0, row=0, columnspan=2, sticky='w', padx=5, pady=5)
        positions = [(c,r) for r in range(1,6) for c in range(2)]
        self.vars = [tk.BooleanVar() for _ in self.bar_keys]
        for v, k, n, (c, r) in zip(self.vars, self.bar_keys, self.bar_names,
                                   positions):
            b = ttk.Checkbutton(self, text=n, variable=v)
            b.grid(column=c, row=r, sticky='w', pady=2, padx=5)
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(column=0, row=6, columnspan=3, sticky='se', pady=5)
        tk.Grid.rowconfigure(buttons_frame, 0, weight=1)
        tk.Grid.columnconfigure(buttons_frame, 0, weight=1)
        b_cancel = ttk.Button(buttons_frame, text="Cancel", command=self.cancel_command)
        b_cancel.grid(column=0, row=0, sticky='se')
        b_ok = ttk.Button(buttons_frame, text="OK", command=self.ok_command)
        b_ok.grid(column=1, row=0, sticky='se', padx=5)
        
    def ok_command(self):
        vals = [v.get() for v in self.vars]
        query = [b for b, v in zip(self.bar_keys, vals) if v]
        if query:
            self.destroy()
            self.master.execute_extract_bars(query)
        else:
            messagebox.showinfo("Nothing choosen!",
                "You must chose which bars you want to extract.")
            self.focus_set()
            
    def cancel_command(self):
        self.destroy()
        
        
class ExportPopup(Popup):

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Export...")
        self.labels = 'Energies Bars Spectra Averaged'.split(' ')
        self.vars = [tk.BooleanVar() for _ in self.labels]
        checks = [ttk.Checkbutton(self, text=l, variable=v)
                  for l, v in zip(self.labels, self.vars)]
        for n, check in enumerate(checks):
            check.grid(column=0, row=n, pady=2, padx=5, sticky='nw')
        checks[0].configure(state = 'normal' if
            self.master.parent.tslr.energies else 'disabled')
        checks[1].configure(state = 'normal' if
            self.master.parent.tslr.bars else 'disabled')
        checks[2].configure(state = 'normal' if
            self.master.parent.tslr.spectra else 'disabled')
        checks[3].configure(state = 'normal' if
            self.master.parent.tslr.spectra else 'disabled')
        self.vars[0].set(True if self.master.parent.tslr.energies else False)
        self.vars[1].set(True if self.master.parent.tslr.bars else False)
        self.vars[2].set(True if self.master.parent.tslr.spectra else False)
        self.vars[3].set(True if self.master.parent.tslr.spectra else False)
        self.protocol("WM_DELETE_WINDOW", self.cancel_command)
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(column=0, row=4, pady=2, sticky='se')
        b_cancel = ttk.Button(buttons_frame, text="Cancel", command=self.cancel_command)
        b_cancel.grid(column=0, row=0, sticky='se')
        b_ok = ttk.Button(buttons_frame, text="OK", command=self.ok_command)
        b_ok.grid(column=1, row=0, padx=5, sticky='se')
        tk.Grid.rowconfigure(self, 4, weight=1)
        tk.Grid.columnconfigure(self, 0, weight=1)
        self.query = []
        
    def ok_command(self):
        vals = [v.get() for v in self.vars]
        logger.debug(vals)
        if any(vals):
            self.destroy()
        else:
            messagebox.showinfo("Nothing choosen!",
                "You must chose what you want to extract.")
            self.focus_set()
            
    def cancel_command(self):
        self.vars = []
        self.destroy()
        
    def get_query(self):
        self.wait_window()
        self.query = [thing.lower() for thing, var
                      in zip(self.labels, self.vars) if var.get()]
        logger.debug(self.query)
        return self.query


######################
###   CHECK_TREE   ###
######################
        
        
class BoxVar(tk.BooleanVar):
    
    def __init__(self, box, *args, **kwargs):
        self.box = box
        super().__init__(*args, **kwargs)
        super().set(True)
        
    def set(self, value):
        # set is not called by tkinter when checkbutton is clicked
        super().set(value)
        if value:
            self.box.tree.item(self.box.index, tags=())
        else:
            self.box.tree.item(self.box.index, tags='discarded')

        
class Checkbox(ttk.Checkbutton):
    def __init__(self, master, tree, index, *args, **kwargs):
        self.frame = ttk.Frame(master, width=17, height=20)
        self.tree = tree
        self.index = index
        self.var = BoxVar(self)
        kwargs['variable'] = self.var
        super().__init__(self.frame, *args, command=self.clicked, **kwargs)
        self.frame.pack_propagate(False)
        self.frame.grid_propagate(False)
        self.grid(column=0, row=0)
        
    def clicked(self):
        self.tree.click_all(index=self.index, value=self.var.get())
        logger.debug('box index: {}'.format(self.index))
        #self.tree.selection_set(str(self.index))
        

class CheckTree(ttk.Treeview):
    trees = dict()

    def __init__(self, master, name, parent_tab=None, **kwargs):
        CheckTree.trees[name] = self
        self.frame = ttk.Frame(master)
        self.parent_tab = parent_tab
        super().__init__(self.frame, **kwargs)
        self.grid(column=0, row=0, rowspan=2, columnspan=2, sticky='nwse')
        tk.Grid.columnconfigure(self.frame, 1, weight=1)
        tk.Grid.rowconfigure(self.frame, 1, weight=1)
        self.vsb = ttk.Scrollbar(self.frame, orient='vertical', command=self.on_bar)
        self.vsb.grid(column=2, row=0, rowspan=2, sticky='nse')
        
        self.tag_configure('discarded', foreground='gray')

        #Sort button
        but_frame = ttk.Frame(self.frame, height=24, width=17)
        but_frame.grid(column=0, row=0)
        but_frame.grid_propagate(False)
        tk.Grid.columnconfigure(but_frame, 0, weight=1)
        tk.Grid.rowconfigure(but_frame, 0, weight=1)
        style = ttk.Style()
        style.configure('sorting.TButton',
            borderwidth=5,
            highlightthickness=1,
            relief='flat')
        self.but_sort = ttk.Button(but_frame, style='sorting.TButton',
            command=self._sort_button)
        self.but_sort.grid(column=0, row=0, sticky='nwes')
        
        #Boxes
        self.canvas = tk.Canvas(self.frame, width=17, borderwidth=0, 
                             background="#ffffff", highlightthickness=0)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.grid(column=0, row=1, sticky='ns')
        self.boxes_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0,0), window=self.boxes_frame, anchor="nw", 
                                  tags="boxes_frame")
        
        self.boxes_frame.bind("<Configure>", self.onFrameConfigure)
        self.configure(yscrollcommand=self.yscroll)
        self.boxes = OrderedDict()

    @property
    def blade(self):
        return [box.var.get() for box in self.boxes.values()]

    @property
    def dummy(self):
        ls = [self.item(i)['text'] for i in self.get_children()]
        ls = sorted(ls)
        dummy = tesliper.datawork.Data('dummy', filenames = ls)
        dummy.trimmer.set(self.blade)
        return dummy
    
    def _sort_button(self, reverse=True):
        ls = [(b.var.get(), b.index) for b in self.boxes.values()]
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

    def onFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def yscroll(self, *args):
        logger.debug(args)
        self.canvas.yview_moveto(args[0])
        logger.debug(self.canvas.yview())
        
    def _insert(self, parent='', index=tk.END, iid=None, **kw):
        box = Checkbox(self.boxes_frame, self, index=len(self.boxes))
        box.frame.grid(column=0, row=box.index)
        self.boxes[box.index] = box
        return super().insert(parent, index, iid=str(box.index), **kw)

    def insert(self, parent='', index=tk.END, iid=None, *kw):
        for tree in CheckTree.trees.values():
            tree._insert(parent=parent, index=index, iid=iid, **kw)
        
    def on_bar(self, *args):
        self.yview(*args)
        # logger.debug(args)
        # logger.debug(self.canvas.yview())

    def click_all(self, index, value):
        # this solution is somewhat redundant
        # (evaluets set(value) on clicked tree box as well)
        # for now will work only on same size trees
        for tree in CheckTree.trees.values():
            tree.boxes[index].var.set(value)
            tree.refresh()

    def refresh(self):
        pass


class EnergiesView(CheckTree):
    def __init__(self, master, parent_tab=None, **kwargs):
        kwargs['columns'] = 'ten ent gib scf zpe imag stoich'.split(' ')
        super().__init__(master, 'energies', parent_tab=parent_tab, **kwargs)
        
        # Columns
        for cid, text in zip('#0 stoich imag ten ent gib scf zpe'.split(' '),
                             'Filenames, Stoichiometry, Imag, Thermal, '
                             'Enthalpy, Gibbs, SCF, Zero-Point'.split(', ')):
            if not cid in ('#0', 'stoich', 'imag'):
                    self.column(cid, width=20, anchor='e')
            self.heading(cid, text=text)
        self.column('#0', width=100)
        self.column('stoich', width=100)
        self.column('imag', width=40, anchor='center', stretch=False)

    def refresh(self):
        # TO DO: implement this based on table_view_update from main.Conformers
        pass


class ConformersOverview(CheckTree):
    def __init__(self, master, parent_tab=None, **kwargs):
        kwargs['columns'] = 'en ir vcd uv ecd ram roa'.split(' ')
        super().__init__(master, 'main', parent_tab=parent_tab, **kwargs)

        # Columns
        self.column('#0', width=300, stretch=False)
        self.heading('#0', text='Filenames')
        for cid, text in zip('en ir vcd uv ecd ram roa'.split(' '),
                             'EN IR VCD UV ECD RAM ROA'.split(' ')):
            self.column(cid, width=35, anchor='center', stretch=False)
            self.heading(cid, text=text)

    @classmethod
    def test_populate(cls, master, num=30):
        import string, random
        new = cls(master, columns=('b'))
        new.heading('b', text='afasdgf')
        new.heading('#0', text='asdgasdfg')
        gen = (''.join(random.choices(string.ascii_lowercase, k=7)) for x in range(num))
        for x, bla in enumerate(gen):
            new.insert(text=bla + ' ' + str(x), values=[x])
        return (new)


class MaxLevelFilter:

    def __init__(self, max_level):
        self.max_level = max_level

    def filter(self, record):
        return record.levelno <= self.max_level


class ShortExcFormatter(lgg.Formatter):

    def format(self, record):
        record = copy(record)
        record.exc_text = ''
        return super().format(record)

    def formatException(self, ei):
        output = ''
        return output

