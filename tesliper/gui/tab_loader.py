###################
###   IMPORTS   ###
###################

import os
import logging as lgg
from collections import namedtuple
import tkinter as tk
import tkinter.ttk as ttk

from tkinter import messagebox
from tkinter.filedialog import askdirectory, askopenfilenames

from . import components as guicom
from .. import tesliper

_DEVELOPEMENT = False


###################
###   CLASSES   ###
###################

class Loader(ttk.Frame):

    def __init__(self, parent):
        """
        TO DO
        -----
        don't allow energy extraction if already extracted
        """
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky='nwse')
        tk.Grid.columnconfigure(self, 2, weight=1)
        tk.Grid.rowconfigure(self, 5, weight=1)
        self.bind('<FocusIn>', lambda e: self.update_overview_values())

        # Extract data
        extract_frame = ttk.LabelFrame(self, text='Extract data...')
        extract_frame.grid(column=0, row=0, columnspan=2, sticky='nwe')
        tk.Grid.columnconfigure(extract_frame, 0, weight=1)
        self.b_auto_extract = ttk.Button(
            extract_frame, text='Choose folder', command=self.from_dir
        )
        self.b_auto_extract.grid(column=0, row=0, sticky='nwe')
        self.b_man_extract = ttk.Button(
            extract_frame, text='Choose files', command=self.man_extract
        )
        self.b_man_extract.grid(column=0, row=1, sticky='nwe')

        # Session control
        buttons_frame = ttk.LabelFrame(self, text="Session control", width=90)
        buttons_frame.grid(column=0, row=1, columnspan=2, sticky='nwe')
        tk.Grid.columnconfigure(buttons_frame, (0, 1), weight=1)
        self.b_clear_session = ttk.Button(
            buttons_frame, text='Clear session', command=self.parent.new_session
        )
        self.b_clear_session.grid(column=0, row=2, sticky='nwe')
        guicom.WgtStateChanger.either.append(self.b_clear_session)

        self.b_calc = ttk.Button(
            buttons_frame, text='Auto calculate', command=self.not_impl
        )
        self.b_calc.grid(column=0, row=0, sticky='nwe')
        guicom.WgtStateChanger.bars.append(self.b_calc)

        self.b_text_export = ttk.Button(
            buttons_frame, text='Export as .txt', command=self.save_text
        )
        self.b_text_export.grid(column=1, row=0, sticky='nwe')
        self.b_excel_export = ttk.Button(
            buttons_frame, text='Export as .xls', command=self.save_excel
        )
        self.b_excel_export.grid(column=1, row=1, sticky='nwe')
        self.b_csv_export = ttk.Button(
            buttons_frame, text='Export as .csv', command=self.save_csv
        )
        self.b_csv_export.grid(column=1, row=2, sticky='nwe')
        guicom.WgtStateChanger.either.extend(
            [self.b_text_export, self.b_excel_export, self.b_csv_export]
        )

        # Overview control
        # TO DO: consider switching to three buttons: 'include', 'exclude',
        # 'limit to', or similar
        self.overview_control_frame = ttk.Labelframe(
            self, text="Overview control", width=90
        )
        self.overview_control_frame.grid(
            column=0, row=2, columnspan=2, sticky='nswe'
        )
        tk.Grid.columnconfigure(self.overview_control_frame, 4, weight=1)
        overview_vars = namedtuple('overview', ['checked', 'all', 'button'])
        self.overview_funcs = dict(
            file=lambda mol, max_len: True,
            en=lambda mol, max_len: 'gib' in mol,
            ir=lambda mol, max_len: 'dip' in mol,
            vcd=lambda mol, max_len: 'rot' in mol,
            uv=lambda mol, max_len: 'vosc' in mol,
            ecd=lambda mol, max_len: 'vrot' in mol,
            ram=lambda mol, max_len: 'raman1' in mol,
            roa=lambda mol, max_len: 'roa1' in mol,
            incompl=lambda mol, max_len: mol,
            term=lambda mol, max_len: mol['notmal_termination'],
            opt=lambda mol, max_len: 'optimization_completed' in mol
                                     and not mol['optimization_completed'],
            imag=lambda mol, max_len: 'freq' in mol and
                                      any([f < 0 for f in mol['freq']])
        )
        self.overview_control_ref = {
            k: v for k, v in zip(
                'file en ir vcd uv ecd ram roa incompl term opt '
                'imag'.split(' '),
                'command gib dip rot vosc vrot raman1 roa1 command '
                'normal_termination optimization_completed freq'.split(' ')
            )
        }
        self.overview_control = dict()
        for i, (name, key) in enumerate(zip(
                'Files Energy IR VCD UV ECD Raman ROA Incompl. Errors '
                'Unopt. Imag.Freq.'.split(' '),
                'file en ir vcd uv ecd ram roa incompl term '
                'opt imag'.split(' ')
        )):
            tk.Label(
                self.overview_control_frame, text=name, anchor='w'
            ).grid(column=0, row=i)
            var_checked = tk.IntVar(value=0)
            tk.Label(
                self.overview_control_frame, textvariable=var_checked,
                bd=0, width=3
            ).grid(column=1, row=i)
            tk.Label(
                self.overview_control_frame, text='/', bd=0
            ).grid(column=2, row=i)
            var_all = tk.IntVar(value=0)
            tk.Label(
                self.overview_control_frame, textvariable=var_all, bd=0, width=3
            ).grid(column=3, row=i)
            butt = ttk.Button(
                self.overview_control_frame, text='check',
                command=lambda key=key: self.un_check(key, True)
            )
            butt.grid(column=4, row=i, sticky='ne')
            guicom.WgtStateChanger.either.append(butt)
            self.overview_control[key] = overview_vars(
                var_checked, var_all, butt
            )

        # keep unchecked
        self.keep_unchecked_frame = ttk.LabelFrame(
            self, text='Keep unchecked?'
        )
        self.keep_unchecked_frame.grid(
            column=0, row=3, columnspan=2, sticky='nswe'
        )
        self.kept_vars = {
            k: tk.BooleanVar() for k
            in 'error unopt imag stoich incompl'.split(' ')
        }
        self.kept_buttons = {
            k: ttk.Checkbutton(
                self.keep_unchecked_frame, text=text, variable=var,
                command=lambda k=k: self.discard(k)
            ) for (k, var), text in zip(
                self.kept_vars.items(),
                ['Error termination', 'Unoptimised', 'Imaginary frequencies',
                 'Non-matching stoichiometry', 'Incomplete entries']
            )
        }
        for n, (key, var) in enumerate(self.kept_vars.items()):
            var.set(True)
            self.kept_buttons[key].grid(column=0, row=n, sticky='nw')

        # Conformers Overview
        self.label_overview = ttk.LabelFrame(self, text='Conformers Overview')
        self.label_overview.grid(
            column=2, row=0, columnspan=3, rowspan=6, sticky='nwse'
        )
        self.overview = None
        tk.Grid.rowconfigure(self.label_overview, 0, weight=1)
        tk.Grid.columnconfigure(self.label_overview, 0, weight=1)

    def un_check(self, key, keep):
        mols = self.parent.tslr.molecules
        condition = self.overview_funcs[key]
        overview = self.overview
        max_len = 0 if not key == 'incompl' else mols._max_len
        for n, mol in enumerate(mols.values()):
            if condition(mol, max_len):
                overview.boxes[str(n)].var.set(keep)
        self.discard_not_kept()
        self.update_overview_values()
        self.overview_control[key][2].configure(
            text='check' if not keep else 'uncheck',
            command=lambda key=key, keep=keep: self.un_check(key, not keep)
        )

    @property
    def kept_funcs(self):
        return dict(
            error=self.parent.tslr.molecules.trim_non_normal_termination,
            unopt=self.parent.tslr.molecules.trim_not_optimized,
            imag=self.parent.tslr.molecules.trim_imaginary_frequencies,
            stoich=self.parent.tslr.molecules.trim_non_matching_stoichiometry,
            incompl=self.parent.tslr.molecules.trim_incomplete
        )

    def not_impl(self):
        messagebox.showinfo(
            "Sorry!",
            "We are sorry, but this function is not implemented yet."
        )

    def get_save_output(self):
        popup = guicom.ExportPopup(self, width='220', height='130')
        query = popup.get_query()
        return query

    @guicom.Feedback('Saving...')
    def execute_save_command(self, output, format):
        self.parent.tslr.writer.save_output(output, format)

    @guicom.Feedback('Saving...')
    def save(self):
        pass

    def save_text(self):
        output = self.get_save_output()
        if not output:
            return
        self.execute_save_command(output, format='txt')

    def save_excel(self):
        output = self.get_save_output()
        if not output:
            return
        self.execute_save_command(output, format='xlsx')

    def save_csv(self):
        output = self.get_save_output()
        if not output:
            return
        self.execute_save_command(output, format='csv')

    @guicom.WgtStateChanger
    def clear_session(self):
        if self.parent.tslr:
            pop = messagebox.askokcancel(
                message='Are you sure you want to start new session? Any '
                        'unsaved changes will be lost!',
                title='New session', icon='warning', default='cancel')
            if pop:
                if self.parent.tslr:
                    self.parent.tslr = None
                if self.parent.conf_tab.conf_list:
                    self.parent.conf_tab.conf_list.destroy()
                    self.parent.conf_tab.conf_list = None
                    self.parent.conf_tab.established = False
                if self.parent.spectra_tab.ax:
                    self.parent.spectra_tab.figure.delaxes(
                        self.parent.spectra_tab.ax)
                    self.parent.spectra_tab.ax = None
                    self.parent.spectra_tab.canvas.show()
            else:
                return False
        self.parent.logger.info('\nStarting new session...')
        return True

    def from_dir(self):
        # TO DO: add messagebox when output files not found
        work_dir = askdirectory()
        if not work_dir:
            return
        self.extract(path=work_dir)

    def man_extract(self):
        files = askopenfilenames(
            filetypes=[("gaussian output", ("*.log", "*.out")),
                       ("log files", "*.log"), ("out files", "*.out"),
                       ("all files", "*.*")],
            defaultextension='.log'
        )
        if not files:
            return
        path = os.path.split(files[0])[0]
        filenames = list(map(lambda p: os.path.split(p)[1], files))
        self.extract(path, filenames)

    @guicom.Feedback('Extracting...')
    def extract(self, path, wanted_files=None):
        tslr = self.parent.tslr
        overview = self.overview
        for file, data in tslr.extract_iterate(path, wanted_files):
            overview.insert('', tk.END, text=file)
        # self.parent.conf_tab.conf_list.refresh()
        self.set_overview_values()
        self.discard_not_kept()
        self.update_overview_values()

    def set_overview_values(self):
        values = {k: 0 for k in self.overview_control.keys()}
        longest = 0
        for num, (file, mol) in enumerate(self.parent.tslr.molecules.items()):
            for key in values.keys():
                if key == 'file':
                    values[key] += 1
                elif key == 'term':
                    values[key] += not mol['normal_termination']
                elif key == 'incompl':
                    length = len(mol)
                    if length > longest:
                        values[key] = num
                        longest = length
                    elif length < longest:
                        values[key] += 1
                    else:
                        pass
                elif key == 'opt':
                    if 'optimization_completed' in mol:
                        values[key] += not mol['optimization_completed']
                elif key == 'imag':
                    if 'freq' in mol:
                        freqs = self.parent.tslr.molecules[file]['freq']
                        imag = (freqs < 0).sum()
                        values[key] += imag
                elif key == 'ir':
                    values[key] += 'dip' in mol
                elif key == 'vcd':
                    values[key] += 'rot' in mol
                elif key == 'uv':
                    values[key] += 'vosc' in mol
                elif key == 'ecd':
                    values[key] += 'vrot' in mol
                elif key == 'ram':
                    values[key] += 'raman1' in mol
                elif key == 'roa':
                    values[key] += 'roa1' in mol
                elif key == 'en':
                    values[key] += 'gib' in mol
                else:
                    continue
        for key, value in values.items():
            self.overview_control[key][1].set(value)

    def update_overview_values(self):
        if not self.parent.tslr.molecules:
            for key in self.overview_control_ref.keys():
                var = self.overview_control[key][0]
                var.set(0)
            return
        for key, value in self.overview_control_ref.items():
            arr = self.parent.tslr.molecules.arrayed(value)
            var = self.overview_control[key][0]
            if key == 'file':
                value = len(arr.values)
            elif key == 'term':
                value = (arr.values == 0).sum()
            elif key == 'incompl':
                mols = self.parent.tslr.molecules
                value = 0
                longest = max(
                    len(mol) for mol in mols.values()
                )
                for kept, mol in zip(mols.kept, mols.values()):
                    if kept and len(mol) < longest:
                        value += 1
            elif key == 'opt':
                value = (arr.values == 0).sum()
            elif key == 'imag':
                value = int(arr.imaginary.sum())
            else:
                value = len(arr.values)
            var.set(value)

    def discard(self, key):
        if self.kept_vars[key].get():
            self.kept_funcs[key]()
            for box, kept in zip(self.overview.boxes.values(),
                                 self.parent.tslr.molecules.kept):
                box.var.set(kept)
        self.update_overview_values()

    def discard_not_kept(self):
        for key, var in self.kept_vars.items():
            if var.get():
                self.kept_funcs[key]()
        for box, kept in zip(self.overview.boxes.values(),
                             self.parent.tslr.molecules.kept):
            box.var.set(kept)

    @guicom.Feedback('Calculating populations...')
    def calc_popul(self):
        self.parent.tslr.calculate_populations()

    @guicom.Feedback('Calculating spectra...')
    def calc_spectra(self):
        self.parent.tslr.calculate_spectra()

    @guicom.Feedback('Averaging spectra...')
    def calc_average(self):
        tslr = self.parent.tslr
        for spc in tslr.spectra.values():
            averaged = [spc.average(en) for en in tslr.energies.values()]

    def get_wanted_bars(self):
        popup = guicom.BarsPopup(self, width='250', height='190')
