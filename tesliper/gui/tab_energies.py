###################
###   IMPORTS   ###
###################

import logging as lgg
import tkinter as tk
import tkinter.ttk as ttk

from functools import reduce
from itertools import zip_longest, cycle

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
        tk.Grid.rowconfigure(self, 0, weight=1)
        tk.Grid.columnconfigure(self, 0, weight=1)

        self.overview = ttk.LabelFrame(self, text='Conformers overview')
        self.overview.grid(column=0, row=0, columnspan=6, sticky='nwse')
        tk.Grid.rowconfigure(self.overview, 0, weight=1)
        tk.Grid.columnconfigure(self.overview, 0, weight=1)
        self.conf_list = None
        self.make_new_conf_list()

        b_select = ttk.Button(self, text='Select all', command=self.select_all)
        b_select.grid(column=0, row=1)
        b_disselect = ttk.Button(
            self, text='Disselect all',
            command=self.disselect_all)
        b_disselect.grid(column=0, row=2)
        # ttk.Button(self, text='Refresh', command=self.refresh).grid(column=3, row=2, sticky='swe')
        ttk.Label(self, text='Show:').grid(column=2, row=1, sticky='sw')
        self.show_var = tk.StringVar()
        show_values = ('Energy /Hartree', 'Delta /(kcal/mol)',
                       'Min. Boltzmann factor', 'Population/%')
        show_id = ('values', 'deltas', 'min_factor', 'populations')
        self.show_ref = {k: v for k, v in zip(show_values, show_id)}
        self.show_combo = ttk.Combobox(self, textvariable=self.show_var,
                                       values=show_values, state='readonly')
        self.show_combo.bind('<<ComboboxSelected>>', self.show_combo_sel)
        self.show_combo.grid(column=2, row=2)

        # filter
        filter_frame = ttk.LabelFrame(self, text='Filter')
        filter_frame.grid(column=1, row=1, rowspan=2)
        ttk.Label(filter_frame, text='Lower limit').grid(column=0, row=0)
        ttk.Label(filter_frame, text='Upper limit').grid(column=0, row=1)
        self.lower_var = tk.StringVar()
        self.upper_var = tk.StringVar()
        lentry = ttk.Entry(filter_frame, textvariable=self.lower_var, validate='key',
                           validatecommand=self.parent.validate_entry)
        lentry.grid(column=1, row=0)
        lentry.bind('<FocusOut>',
                    lambda e, var=self.lower_var: self.parent.entry_out_validation(var)
                    )
        uentry = ttk.Entry(filter_frame, textvariable=self.upper_var, validate='key',
                           validatecommand=self.parent.validate_entry)
        uentry.grid(column=1, row=1)
        uentry.bind('<FocusOut>',
                    lambda e, var=self.upper_var: self.parent.entry_out_validation(var)
                    )
        self.en_filter_var = tk.StringVar()
        filter_values = 'Thermal Enthalpy Gibbs SCF Zero-Point'.split(' ')
        filter_id = 'ten ent gib scf zpe'.split(' ')
        self.filter_ref = {k: v for k, v in zip(filter_values, filter_id)}
        self.filter_combo = ttk.Combobox(
            filter_frame, textvariable=self.en_filter_var,
            values=filter_values, state='readonly'
        )
        self.filter_combo.grid(column=3, row=0)
        self.filter_combo.bind('<<ComboboxSelected>>', self.set_upper_and_lower)

        b_filter = ttk.Button(filter_frame, text='Filter by energy type', command=self.filter_energy)
        b_filter.grid(column=3, row=1)
        check_frame = ttk.Frame(filter_frame)
        check_frame.grid(column=4, row=0, rowspan=2)
        var_stoich = tk.BooleanVar()
        var_stoich.set(True)
        self.check_stoich = ttk.Checkbutton(
            check_frame, text='Discard non-matching stoichiometry',
            variable=var_stoich, command=self.update)
        self.check_stoich.grid(column=4, row=0, sticky='w')
        self.check_stoich.var = var_stoich
        var_imag = tk.BooleanVar()
        var_imag.set(True)
        self.check_imag = ttk.Checkbutton(
            check_frame, text='Discard imaginary frequencies',
            variable=var_imag, command=self.update)
        self.check_imag.grid(column=4, row=1, sticky='w')
        self.check_imag.var = var_imag
        var_missing = tk.BooleanVar()
        var_missing.set(True)
        self.check_missing = ttk.Checkbutton(
            check_frame, text='Discard excessive conformers',
            variable=var_missing, command=self.update)
        self.check_missing.grid(column=4, row=2, sticky='w')
        self.check_missing.var = var_missing

        self.established = False

        # b_stoich = ttk.Button(filter_frame, text='Non-matching\nstoichiometry', command=self.filter_stoich)
        # b_stoich.grid(column=4, row=0, rowspan=2)
        # b_imag = ttk.Button(filter_frame, text='Imaginary\nfrequencies', command=self.filter_imag)
        # b_imag.grid(column=5, row=0, rowspan=2)
        guicom.WgtStateChanger.energies.extend(
            [b_select, b_disselect, self.show_combo, lentry, uentry,
             self.filter_combo, self.check_stoich, self.check_imag,
             self.check_missing]
            # b_filter, b_stoich, b_imag]
        )

    def make_new_conf_list(self):
        self.conf_list = guicom.EnergiesView(self.overview, parent_tab=self)
        self.conf_list.frame.grid(column=0, row=0, sticky='nswe')

    def establish(self):
        self.make_new_conf_list()
        en = self.parent.tslr.energies.scf.full
        for num, (fnm, stoich) in enumerate(zip_longest(en.filenames, en.stoich)):
            self.conf_list.insert('', 'end', text=fnm)
            self.conf_list.set(num, column='stoich', value=stoich)
        # frame = ttk.Frame(self.conf_list.frame, height=15, width=17)
        # frame.grid(column=0, row=2, sticky='sw')
        # frame.grid_propagate(False)
        self.show_combo.set('Energy /Hartree')
        self.filter_combo.set('Thermal')
        self.update('values')
        self.show_imag()
        self.established = True

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

    def refresh(self):
        self.parent.logger.debug('conf_tab.refresh called.')
        self.set_energies_blade()
        self.table_view_update()

    def set_energies_blade(self):
        dummy = self.conf_list.dummy
        for en in self.energies.values():
            en.trimmer.match(dummy)

    def set_blade(self, blade):
        for box, value in zip(self.conf_list.boxes.values().values(), blade):
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
        self.parent.logger.debug('lower limit: {}\nupper limit: {}'.format(lower, upper))
        energy = self.filter_ref[self.en_filter_var.get()]
        values = iter(getattr(self.energies[energy], self.showing))
        self.parent.logger.debug('energy: {}\nshowing: {}'.format(energy, self.showing))
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
                self.parent.logger.debug('value: {}, setting {}'.format(value, new))
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
            self.parent.logger.warning("Can't show optimised conformers "
                                       "imaginary frequencies count: no appropiate data found. "
                                       "Please keep 'Discard imaginary frequencies' option unchecked."
                                       )
            self.check_imag.var.set(False)
        else:
            # self.set_blade([not value.sum(0) for value in imag])
            for box, value in zip(self.conf_list.boxes.values(), imag):
                if value.sum(0): box.var.set(False)

    def unify_data(self):
        stencil = None if not self.established else self._dummy
        self.parent.tslr.unify_data(stencil=stencil)
        if stencil is not None:
            for box, value in zip(self.conf_list.boxes.values(), self.energies.scf.trimmer.blade):
                box.var.set(1 if value else 0)
            # need to check value this way
            # because tkinter doesn't understand numpy.bool_ type

    def show_combo_sel(self, event):
        self.parent.logger.debug('Show combobox selected.')
        self.table_view_update()

    def show_imag(self):
        bar = 'iri' if 'iri' in self.parent.tslr.bars else 'ir'
        try:
            bar = self.parent.tslr.bars[bar].full
            imag = bar.imag
            stoich = bar.stoich
        except KeyError:
            imag = []
            stoich = []
        for num, (imag_val, stoich_val) in enumerate(zip(imag, stoich)):
            self.parent.conf_tab.conf_list.set(num, column='imag', value=imag_val.sum(0))
            # self.parent.conf_tab.conf_list.set(num, column='stoich', value=stoich_val)

    def update(self, show=None):
        if self.check_imag.var.get(): self.filter_imag()
        if self.check_stoich.var.get(): self.filter_stoich()
        if self.check_missing.var.get(): self.unify_data()
        if (self.blade == self.energies.scf.trimmer.blade).all():
            self.parent.logger.debug(
                'Energies blades not matchnig internal blade. ' 
                'Will call set_energies_blade.')
            self.set_energies_blade()
        self.table_view_update(show)

    def table_view_update(self, show=None):
        show = show if show else self.showing
        self.parent.logger.debug('Going to update by showing {}.'.format(show))
        e_keys = 'ten ent gib scf zpe'.split(' ')
        formats = dict(
            values=lambda v: '{:.6f}'.format(v),
            deltas=lambda v: '{:.4f}'.format(v),
            min_factor=lambda v: '{:.4f}'.format(v),
            populations=lambda v: '{:.4f}'.format(v * 100)
        )
        scope = 'full' if show == 'values' else 'trimmed'
        en_get_attr = lambda e, scope, show: reduce(
            lambda obj, attr: getattr(obj, attr), (e, scope, show), self.energies
        )
        trimmed = zip(*[en_get_attr(e, scope, show) for e in e_keys])
        what_to_show = self.blade if show != 'values' else (True for __ in self.blade)
        for index, kept in enumerate(what_to_show):
            values = ['--' for _ in range(5)] if not kept else map(formats[show], next(trimmed))
            for energy, value in zip(e_keys, values):
                self.parent.conf_tab.conf_list.set(index, column=energy, value=value)
        self.set_upper_and_lower()

