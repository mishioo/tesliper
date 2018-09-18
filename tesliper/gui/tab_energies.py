###################
###   IMPORTS   ###
###################

import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

from functools import reduce

from . import components as guicom

_DEVELOPEMENT = False


###################
###   CLASSES   ###
###################


class Conformers(ttk.Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.grid(column=0, row=0, sticky='nwse')
        tk.Grid.rowconfigure(self, 5, weight=1)
        tk.Grid.columnconfigure(self, 2, weight=1)

        self.overview = ttk.LabelFrame(self, text='Conformers overview')
        self.overview.grid(column=2, row=0, rowspan=6, sticky='nwse')
        tk.Grid.rowconfigure(self.overview, 0, weight=1)
        tk.Grid.columnconfigure(self.overview, 0, weight=1)
        self.conf_list = None  # obj is created in main.TesliperApp.new_session
        self.bind('<FocusIn>', self.refresh)

        frame = ttk.Frame(self, width=200)  # left frame
        frame.grid(column=0, row=0)
        tk.Grid.columnconfigure(frame, 0, weight=1)
        # control frame
        control_frame = ttk.LabelFrame(frame, text='Overview control')
        control_frame.grid(column=0, row=0, columnspan=2, sticky='nwe')
        tk.Grid.columnconfigure(control_frame, 0, weight=1)

        b_select = ttk.Button(control_frame, text='Select all',
                              command=self.select_all)
        b_select.grid(column=0, row=0, sticky='nwe')
        b_disselect = ttk.Button(
            control_frame, text='Disselect all',
            command=self.disselect_all)
        b_disselect.grid(column=0, row=1, sticky='nwe')
        ttk.Label(frame, text='Show:').grid(column=0, row=2, sticky='nw')
        self.show_var = tk.StringVar()
        show_values = ('Energy /Hartree', 'Delta /(kcal/mol)',
                       'Min. Boltzmann factor', 'Population /%')
        show_id = ('values', 'deltas', 'min_factor', 'populations')
        self.show_ref = {k: v for k, v in zip(show_values, show_id)}
        self.show_combo = ttk.Combobox(
            frame, textvariable=self.show_var,
            values=show_values, state='readonly'  # , width=21
        )
        self.show_combo.bind('<<ComboboxSelected>>', self.refresh)
        self.show_combo.grid(column=1, row=2, sticky='nwe')

        # filter
        filter_frame = ttk.LabelFrame(frame, text='Energies range')
        filter_frame.grid(column=0, row=1, columnspan=2, sticky='nwe')
        tk.Grid.columnconfigure(filter_frame, 1, weight=1)
        ttk.Label(filter_frame, text='Minimum').grid(column=0, row=0)
        ttk.Label(filter_frame, text='Maximum').grid(column=0, row=1)
        ttk.Label(filter_frame, text='Energy type').grid(column=0, row=2)
        self.lower_var = tk.StringVar()
        self.upper_var = tk.StringVar()
        lentry = ttk.Entry(filter_frame, textvariable=self.lower_var,
                           width=15, validate='key',
                           validatecommand=self.parent.validate_entry)
        lentry.grid(column=1, row=0, sticky='ne')
        lentry.bind(
            '<FocusOut>',
            lambda e, var=self.lower_var: self.parent.entry_out_validation(var)
        )
        uentry = ttk.Entry(filter_frame, textvariable=self.upper_var,
                           width=15, validate='key',
                           validatecommand=self.parent.validate_entry)
        uentry.grid(column=1, row=1, sticky='ne')
        uentry.bind(
            '<FocusOut>',
            lambda e, var=self.upper_var: self.parent.entry_out_validation(var)
        )
        self.en_filter_var = tk.StringVar()
        filter_values = 'Thermal Enthalpy Gibbs SCF Zero-Point'.split(' ')
        filter_id = 'ten ent gib scf zpe'.split(' ')
        self.filter_ref = {k: v for k, v in zip(filter_values, filter_id)}
        self.filter_combo = ttk.Combobox(
            filter_frame, textvariable=self.en_filter_var,
            values=filter_values, state='readonly', width=12
        )
        self.filter_combo.grid(column=1, row=2, sticky='ne')
        self.filter_combo.bind('<<ComboboxSelected>>', self.set_upper_and_lower)

        b_filter = ttk.Button(filter_frame, text='Limit to...',
                              command=self.filter_energy)
        b_filter.grid(column=0, row=3, columnspan=2, sticky='nwe')
        self.show_combo.set('Energy /Hartree')
        self.filter_combo.set('Thermal')

        # can't make it work other way
        # dummy = ttk.Frame(frame, width=185)
        # dummy.grid(column=0, row=5)
        # dummy.grid_propagate(False)

        self.established = False

        guicom.WgtStateChanger.energies.extend(
            [b_select, b_disselect, b_filter, self.show_combo, lentry, uentry,
             self.filter_combo]
        )

    def establish(self):
        self.show_combo.set('Energy /Hartree')
        self.filter_combo.set('Thermal')
        self.established = True

    @property
    def energies(self):
        return reduce(
            lambda obj, attr: getattr(obj, attr, None),
            ('tslr', 'energies'), self.parent)

    @property
    def showing(self):
        return self.show_ref[self.show_var.get()]

    def discard_lacking_energies(self):
        if not self.parent.main_tab.kept_vars['incompl'].get():
            self.parent.logger.info(
                'Any conformers without energy data will be discarded.'
            )
            boxes = self.conf_list.trees['main'].boxes
            for num, mol in enumerate(self.parent.tslr.molecules.values()):
                if 'gib' not in mol:
                    boxes[str(num)].var.set(False)

    def refresh(self, event=None):
        self.conf_list.refresh()
        self.set_upper_and_lower()

    def select_all(self):
        for box in self.conf_list.boxes.values():
            box.var.set(True)
        self.parent.main_tab.discard_not_kept()
        self.discard_lacking_energies()
        self.refresh()

    def disselect_all(self):
        for box in self.conf_list.boxes.values():
            box.var.set(False)
        self.refresh()

    def set_upper_and_lower(self, event=None):
        energy = self.filter_ref[self.en_filter_var.get()]
        arr = getattr(self.energies[energy], self.showing)
        factor = 100 if self.showing == 'populations' else 1
        try:
            lower, upper = arr.min(), arr.max()
        except ValueError:
            lower, upper = 0, 0
        else:
            if self.showing == 'values':
                n = 6
            else:
                n = 4
            lower, upper = map(lambda v: '{:.{}f}'.format(v * factor, n),
                               (lower, upper))
        finally:
            self.lower_var.set(lower)
            self.upper_var.set(upper)

    def filter_energy(self):
        energy = self.filter_ref[self.en_filter_var.get()]
        factor = 1e-2 if self.showing == 'populations' else 1
        lower = float(self.lower_var.get()) * factor
        upper = float(self.upper_var.get()) * factor
        self.parent.tslr.molecules.trim_to_range(
            energy, minimum=lower, maximum=upper, attribute=self.showing
        )
        for box, kept in zip(self.conf_list.trees['main'].boxes.values(),
                             self.parent.tslr.molecules.kept):
            box.var.set(kept)
        self.conf_list.refresh()
