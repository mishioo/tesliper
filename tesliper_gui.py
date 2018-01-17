from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox
from tkinter.filedialog import askdirectory, askopenfilename
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from threading import Thread

from tesliper import Tesliper

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
        self.gui.main_tab.progtext.set(self.progbar)
        self.gui.main_tab.progbar.start()
        self.gui.spectra_tab.progbar.start()
        return_value = self.target(*self.args, **self.kwargs)
        self.gui.main_tab.progbar.stop()
        self.gui.spectra_tab.progbar.stop()
        self.gui.main_tab.progtext.set('Idle.')
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
            print(self.progbar)
            other.parent.thread.start()
        return wrapper


class Loader(Frame):
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky=(N,W,S,E))
        Grid.columnconfigure(self, 3, weight=1)
        Grid.rowconfigure(self, 10, weight=1)
        
        #New session
        self.label_new = Labelframe(self, text='New session')
        self.label_new.grid(column=0, row=0, rowspan=3, sticky=N)
        Button(self.label_new, text='From dir', command=self.from_dir).grid(column=0, row=0)
        Button(self.label_new, text='From files', command=self.not_impl).grid(column=0, row=1)
        
        #Smart
        self.label_smart = Labelframe(self, text='Smart')
        self.label_smart.grid(column=0, row=3, rowspan=4, sticky=N)
        Button(self.label_smart, text='Extract', command=self.not_impl).grid(column=0, row=0)
        Button(self.label_smart, text='Calculate', command=self.not_impl).grid(column=0, row=1)
        Button(self.label_smart, text='Save', command=self.not_impl).grid(column=0, row=2)

        #Extract
        self.label_extr = Labelframe(self, text='Extract')
        self.label_extr.grid(column=0, row=7, rowspan=3, sticky=N)
        Button(self.label_extr, text='Energies', command=self.extract_energies).grid(column=0, row=0)
        Button(self.label_extr, text='Bars').grid(column=0, row=1)

        #Calculate
        self.label_calc = Labelframe(self, text='Calculate')
        self.label_calc.grid(column=1, row=0, rowspan=4, sticky=N)
        Button(self.label_calc, text='Populations', command=self.calc_popul).grid(column=0, row=0)
        Button(self.label_calc, text='Spectra').grid(column=0, row=1)
        Button(self.label_calc, text='Average').grid(column=0, row=2)

        #Load
        self.label_load = Labelframe(self, text='Load')
        self.label_load.grid(column=1, row=4, rowspan=5, sticky=N)
        Button(self.label_load, text='Populations').grid(column=0, row=0)
        Button(self.label_load, text='Bars').grid(column=0, row=1)
        Button(self.label_load, text='Spectra').grid(column=0, row=2)
        Button(self.label_load, text='Settings').grid(column=0, row=3)
        
        #Work dir
        Label(self, text='Work dir').grid(column=2, row=0)
        self.work_dir = StringVar()
        self.work_dir.set('Not specified.')
        self.work_entry = Entry(self, textvariable=self.work_dir, state='readonly')
        self.work_entry.grid(column=3, row=0, columnspan=2, sticky=(W,E))
        Button(self, text="Change").grid(column=4, row=0, sticky=E)
        
        #Output dir
        Label(self, text='Output dir').grid(column=2, row=1)
        self.out_dir = StringVar()
        self.out_dir.set('Not specified.')
        self.out_entry = Entry(self, textvariable=self.out_dir, state='readonly')
        self.out_entry.grid(column=3, row=1, columnspan=2, sticky=(W,E))
        Button(self, text="Change").grid(column=4, row=1, sticky=E)
        
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
        self.parent.tslr = Tesliper(new_dir)
        self.work_dir.set(new_dir)
        self.out_dir.set(self.parent.tslr.output_dir)
        self.tslr_dependent_change_state('normal')
        
    def from_files(self):
        pass
        
                
    @GUIFeedback('Extracting...')  
    def extract_energies(self):
        self.parent.tslr.extract('energies')
    
    @GUIFeedback('Extracting...')  
    def extract_bars(self):
        self.parent.tslr.extract()
     
    @GUIFeedback('Calculating populations...')
    def calc_popul(self):
        self.parent.tslr.calculate_populations()

    def tslr_dependent_change_state(self, state):
        widgets = (
            (widget, parent)
            for parent in self.grid_slaves()
            for widget in parent.grid_slaves()
            )
        for widget, parent in widgets:
            name = parent['text']
            con1 = name in 'Calculate Smart Load Extract'.split(' ')
            con2 = isinstance(widget, Button)
            if con1 and con2:
                widget.config(state=state)
        for widget in self.grid_slaves():
            if isinstance(widget, Button):
                widget.config(state=state)

class Spectra(Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky=(N,W,S,E))
        Grid.columnconfigure(self, 2, weight=1)
        Grid.rowconfigure(self, 8, weight=1)

        #Spectra type
        s_type = Labelframe(self, text="Spectra type:")
        s_type.grid(column=0, row=0)
        self.s_type = StringVar()
        names = 'IR UV Raman IR/VCD UV/ECD Raman/ROA'.split(' ')
        values = 'ir uv ra vcd ecd roa'.split(' ')
        positions = [(c,r) for c in range(2) for r in range(3)]
        for n, v, (c, r) in zip(names, values, positions):
            Radiobutton(s_type, text=n, variable=s_type, value=v).grid(column=c, row=r, sticky=W)
        
        #Settings
        sett = Labelframe(self, text="Settings:")
        sett.grid(column=0, row=1)
        for no, name in enumerate('Start Stop Step HWHM'.split(' ')):
            Label(sett, text=name).grid(column=0, row=no)
            var = StringVar()
            setattr(self, name.lower(), var)
            entry = Entry(sett, textvariable=var, width=10)
            entry.grid(column=1, row=no)
            unit = StringVar()
            unit.set('cm-1')
            setattr(self, '{}_unit'.format(name).lower(), unit)
            label = Label(sett, textvariable=unit)
            label.grid(column=2, row=no)
        Label(sett, text='Fitting').grid(column=0, row=4)
        self.fitting = StringVar()
        fit = Combobox(sett, textvariable=self.fitting, width=13)
        fit.grid(column=1, row=4, columnspan=2)
        fit['values'] = ('lorentzian', 'gaussian')
        
        #Calculation Mode
        self.mode = StringVar()
        Radiobutton(self, text='Average by:', variable=self.mode, value='average').grid(column=0, row=2, sticky=W)
        Radiobutton(self, text='Single file:', variable=self.mode, value='single').grid(column=0, row=4, sticky=W)
        Radiobutton(self, text='Stack by overview', variable=self.mode, value='stack').grid(column=0, row=6, sticky=W)
        
        self.average = StringVar()
        self.average_box = Combobox(self, textvariable=self.average)
        self.average_box.grid(column=0, row=3)
        self.average_box['values'] = ()
        self.single = StringVar()
        self.single_box = Combobox(self, textvariable=self.single)
        self.single_box.grid(column=0, row=5)
        self.single_box['values'] = ()

        #Recalculate
        Button(self, text='Recalculate').grid(column=0, row=7)
        
        #Progress bar
        lab = Label(self, textvariable=parent.main_tab.progtext, anchor=W, foreground='gray')
        lab.grid(column=0, row=8, sticky=(S,W))
        self.progbar = Progressbar(self, orient=HORIZONTAL, mode='indeterminate')
        self.progbar.grid(column=0, row=9, sticky=(S,W,E))
        
        #Spectrum
        specta_view = Labelframe(self, text='Spectra view')
        specta_view.grid(column=1, row=0, rowspan=10, sticky=(N,S,W,E))
        self.figure = Figure()
        self.canvas = FigureCanvasTkAgg(self.figure, master=specta_view)
        self.canvas.show()
        self.canvas.get_tk_widget().grid(column=0, row=0, sticky=(N,S,W,E))

class Conformers(Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky=(N,W,S,E))
        Grid.rowconfigure(self, 0, weight=1)
        Grid.columnconfigure(self, 0, weight=1)
        
        self.overview = Labelframe(self, text='Conformers overview')
        self.overview.grid(column=0, row=0, columnspan=6, sticky=(N,W,S,E))
        #Button(self.overview, text='bla').grid(column=0, row=0)
        
        Button(self, text='Recalculate').grid(column=0, row=2, sticky=(S,W))

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
