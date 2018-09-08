###################
###   IMPORTS   ###
###################

import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

from functools import reduce
from itertools import cycle

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

        frame = ttk.Frame(self, width=200)  # left frame
        frame.grid(column=0, row=0)
        tk.Grid.columnconfigure(frame, 0, weight=1)
        # control frame
        control_frame = ttk.LabelFrame(frame, text='Overview control')
        control_frame.grid(column=0, row=0, sticky='nwe')
        tk.Grid.columnconfigure(control_frame, 0, weight=1)

        b_select = ttk.Button(control_frame, text='Select all',
                              command=self.select_all)
        b_select.grid(column=0, row=0, sticky='nwe')
        b_disselect = ttk.Button(
            control_frame, text='Disselect all',
            command=self.disselect_all)
        b_disselect.grid(column=0, row=1, sticky='nwe')
        ttk.Label(frame, text='Show:').grid(
            column=0, row=2, columnspan=2, sticky='nw'
        )
        self.show_var = tk.StringVar()
        show_values = ('Energy /Hartree', 'Delta /(kcal/mol)',
                       'Min. Boltzmann factor', 'Population /%')
        show_id = ('values', 'deltas', 'min_factor', 'populations')
        self.show_ref = {k: v for k, v in zip(show_values, show_id)}
        self.show_combo = ttk.Combobox(
            frame, textvariable=self.show_var,
            values=show_values, state='readonly', width=21
        )
        self.show_combo.bind('<<ComboboxSelected>>', self.show_combo_sel)
        self.show_combo.grid(column=0, row=3, sticky='nwe')

        # filter
        filter_frame = ttk.LabelFrame(frame, text='Filter')
        filter_frame.grid(column=0, row=1, columnspan=2, sticky='nwe')
        tk.Grid.columnconfigure(filter_frame, 1, weight=1)
        ttk.Label(filter_frame, text='Lower limit').grid(column=0, row=0)
        ttk.Label(filter_frame, text='Upper limit').grid(column=0, row=1)
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

        b_filter = ttk.Button(filter_frame, text='Filter',
                              command=self.filter_energy)
        b_filter.grid(column=0, row=3, columnspan=2, sticky='nwe')
        self.show_combo.set('Energy /Hartree')
        self.filter_combo.set('Thermal')

        # can't make it work other way
        dummy = ttk.Frame(frame, width=185)
        dummy.grid(column=0, row=5)
        dummy.grid_propagate(False)

        self.established = False

        guicom.WgtStateChanger.energies.extend(
            [b_select, b_disselect, b_filter, self.show_combo, lentry, uentry,
             self.filter_combo]
        )

    def establish(self):
        self.show_combo.set('Energy /Hartree')
        self.filter_combo.set('Thermal')
        self.established = True

    def update_conf_list(self):
        en = self.parent.tslr.molecules.arrayed('gib', full=True)
        children = self.conf_list.owned_children
        for num, fnm in enumerate(en.filenames):
            if fnm not in children:
                self.conf_list.insert('', 'end', text=fnm)
        if not self.established:
            self.establish()
        self.conf_list.refresh()

    @property
    def energies(self):
        return reduce(
            lambda obj, attr: getattr(obj, attr, None),
            ('tslr', 'energies'), self.parent)

    @property
    def showing(self):
        return self.show_ref[self.show_var.get()]

    def select_all(self):
        self.set_blade(cycle([True]))
        self.set_energies_blade()
        self.update()

    def disselect_all(self):
        self.set_blade(cycle([False]))
        self.set_energies_blade()
        self.update()

    def set_energies_blade(self):
        dummy = self.conf_list.dummy
        for en in self.energies.values():
            en.trimmer.match(dummy)

    def set_blade(self, blade):
        for box, value in zip(self.conf_list.boxes.values(), blade):
            box.var.set(1 if value else 0)
            # need to check value this way
            # because tkinter doesn't understand numpy.bool_ type

    def set_upper_and_lower(self, event=None):
        energy = self.filter_ref[self.en_filter_var.get()]
        arr = getattr(self.energies[energy], self.showing)
        factor = 100 if self.showing == 'populations' else 1
        try:
            lower, upper = arr.min(), arr.max()
        except ValueError:
            lower, upper = 0, 0
        else:
            if self.showing == 'populations':
                n = 2
            elif self.showing == 'values':
                n = 6
            else:
                n = 4
            lower, upper = map(lambda v: '{:.{}f}'.format(v * factor, n),
                               (lower - 1e-6 if lower != 0 else 0,
                                upper + 1e-6 if upper != 0 else 0))
        finally:
            self.lower_var.set(lower)
            self.upper_var.set(upper)

    def filter_energy(self):
        lower = float(self.lower_var.get())
        upper = float(self.upper_var.get())
        self.parent.logger.debug(
            'lower limit: {}\nupper limit: {}'.format(lower, upper))
        energy = self.filter_ref[self.en_filter_var.get()]
        values = iter(getattr(self.energies[energy], self.showing))
        self.parent.logger.debug(
            'energy: {}\nshowing: {}'.format(energy, self.showing))
        factor = 100 if self.showing == 'populations' else 1
        # must init new_blade with Falses for sake of already discarded
        # new_blade = np.zeros_like(energy.trimmer.blade)
        # iter_new = np.nditer(new_blade, op_flags=['readwrite'])
        # for box, new in zip(self.conf_list.boxes.values(), iter_new):
        #    if box.var.get():
        # must iterate through trimmed object to get correct values
        # so should get next value only if conformer not suppressed
        #        value = next(values)
        #        new[...] = False if not lower <= value * factor <= upper else True
        new_blade = []
        for box in self.conf_list.boxes.values():
            if box.var.get():
                value = next(values)
                new = False if not lower <= value * factor <= upper else True
                self.parent.logger.debug(
                    'value: {}, setting {}'.format(value, new))
            else:
                new = False
                self.parent.logger.debug('no value, setting {}'.format(new))
            new_blade.append(new)
        for en in self.energies.values():
            en.trimmer.set(new_blade)
        self.set_blade(new_blade)
        self.table_view_update()

    def filter_stoich(self):
        for en in self.energies.values():
            en.trimm_by_stoich()
        for box, kept in zip(self.conf_list.boxes.values(), en.trimmer.blade):
            if not kept: box.var.set(False)
            # need to check kept value this way
            # because tkinter doesn't understand numpy.bool_ type

    def filter_imag(self):
        try:
            imag = self.parent.tslr.bars.iri.full.imag
        except AttributeError:
            self.parent.logger.warning(
                "Can't show optimised conformers "
                "imaginary frequencies count: no appropiate data found. "
                "Please keep 'Discard imaginary frequencies' option unchecked."
            )
            self.check_imag.var.set(False)
        else:
            # self.set_blade([not value.sum(0) for value in imag])
            for box, value in zip(self.conf_list.boxes.values(), imag):
                if value.sum(0): box.var.set(False)

    def show_combo_sel(self, event):
        self.parent.logger.debug('Show combobox selected.')
        self.conf_list.refresh()

    def update(self, show=None):
        if self.check_imag.var.get(): self.filter_imag()
        if self.check_stoich.var.get(): self.filter_stoich()
        if self.check_missing.var.get(): self.unify_data()
        if (self.blade == self.energies.scf.trimmer.blade).all():
            self.parent.logger.debug(
                'Energies blades not matching internal blade. '
                'Will call set_energies_blade.')
            self.set_energies_blade()
        self.table_view_update(show)
