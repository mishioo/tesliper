###################
###   IMPORTS   ###
###################

import csv
import math
import os, re
import logging as lgg
import numpy as np

from collections.abc import MutableMapping
from collections import OrderedDict
from contextlib import contextmanager
from copy import copy
from itertools import chain, cycle

from . import datawork
from . import extraction
from . import writer

############################
###   GLOBAL VARIABLES   ###
############################

__author__ = "Michał M. Więcław"
__version__ = "0.6.4"
    
    
##################
###   LOGGER   ###
##################

logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)

mainhandler = lgg.StreamHandler()
mainhandler.setLevel(lgg.DEBUG)
mainhandler.setFormatter(lgg.Formatter(
            '%(levelname)s:%(name)s:%(funcName)s - %(message)s'))

loggers = [logger, datawork.logger, extraction.logger, writer.logger]
for lgr in loggers: lgr.addHandler(mainhandler)

###################
###   CLASSES   ###
###################

class DataHolder(MutableMapping):
    """Convenience dict-like holder for data objects. It enables accessing its
    values through standard dictionary syntax (holder['key']), as well as
    through attribute syntax (holder.key).
    """

    def __init__(self):
        self._storage = {}

    def __getitem__(self, key):
        return self._storage[key]
    
    def __setitem__(self, key, value):
        self._storage[key] = value
    
    def __delitem__(self, key):
        del self._storage[key]
    
    def __iter__(self):
        return iter(self._storage)
    
    def __len__(self):
        return len(self._storage)
        
    def __setattr__(self, name, value):
        if name == '_storage':
            return super().__setattr__(name, value)
        elif name in self._storage:
            self[name] = value
        else:
            super().__setattr__(name, value)

    def __getattribute__(self, name):
        if name == '_storage':
            return object.__getattribute__(self, name)
        elif name in self._storage:
            return self[name]
        else:
            return object.__getattribute__(self, name)
    
    @property
    def spectral(self):
        return {k: v for k, v in self.items() if k in \
                'dip rot vosc vrot losc lrot raman1 roa1'.split(' ')}


class Tesliper:
    """
    TO DO
    -----
    Finish saving functionality.
    Add trimming support.
    Supplement docstrings.
    ? separate spectra types ?
    """
    
    standard_parameters = {
        'vibra': {'hwhm': 6,
                  'start': 800,
                  'stop': 2900,
                  'step': 2,
                  'fitting': datawork.lorentzian},
        'electr': {'hwhm': 0.35,
                   'start': 150,
                   'stop': 800,
                   'step': 1,
                   'fitting': datawork.gaussian}
        }
    units = datawork.Spectra.units

    def __init__(self, input_dir=None, output_dir=None, wanted_files=None):
        # TO DO: make wanted_files setter to reflect changes after instantiation
        self.molecules = Molecules()
        self.wanted_files = wanted_files
        if input_dir or output_dir:
            self.change_dir(input_dir, output_dir)
        self.energies = DataHolder()
        self.bars = DataHolder()
        self.spectra = DataHolder()
        self.set_standard_parameters()
        self.writer = writer.Writer(self)

    @property
    def extracted(self):
        return dict((k, v) for k, v in
                    chain(self.bars.items(), self.energies.items()))

    def set_standard_parameters(self):
        self.parameters = {
            'vibra': self.standard_parameters['vibra'].copy(),
            'electr': self.standard_parameters['electr'].copy()
            }
        
    def update(self, *args, **kwargs):
        pairs = chain(*(d.items() for d in args), kwargs.items())
        for key, value in pairs:
            if isinstance(value, datawork.Energies):
                self.energies[key] = value
            elif isinstance(value, datawork.Bars):
                self.bars[key] = value
            elif isinstance(value, datawork.Spectra):
                self.spectra[key] = value
            else:
                raise TypeError("Tesliper instance can not be updated with "
                                "type {}".format(type(value)))
                                
    def change_dir(self, input_dir=None, output_dir=None):
        if not input_dir and not output_dir:
            raise TypeError("Tesliper.change_dir() requires at least one "
                            "argument: input_dir or output_dir.")
        input_dir, output_dir = map(
            lambda s: os.path.normpath(s) if s else None,
            (input_dir, output_dir)
            )
        for dir in input_dir, output_dir:
            if dir and not os.path.isdir(dir):
                raise FileNotFoundError(
                    "Invalid path or directory not found: {}"\
                    .format(dir)
                    )
        if input_dir:
            self.input_dir = input_dir
            self.soxhlet = extraction.Soxhlet(input_dir, self.wanted_files)
            logger.info('Current working directory is: {}'.format(input_dir))
        if output_dir:
            self.output_dir = output_dir
            logger.info('Current output directory is: {}'.format(output_dir))
        elif input_dir and not hasattr(self, 'output_dir'):
            output_dir = os.path.join(input_dir, 'tesliper_output')
            os.makedirs(output_dir, exist_ok=True)
            self.output_dir = output_dir
            logger.info('Current output directory is: {}'.format(output_dir))
        else:
            return

        
    def load_files(self, path=None):
        if path:
            self.soxhlet = extraction.Soxhlet(path)
            self.change_dir(path)
        else:
            self.soxhlet = extraction.Soxhlet(self.input_dir)
        return self.soxhlet
        
    def extract(self, *args, path=None):
        soxhlet = extraction.Soxhlet(path) if path else self.soxhlet
        data = soxhlet.extract(args)
        self.update(data)
        return data
    
    def smart_extract(self, deep_search=True, with_load=True):
        #TO DO: add deep search and loading
        soxhlet = self.soxhlet
        args = soxhlet.parse_command()
        return self.extract(*args)
        pass
        
    def smart_calculate(self, average=True):
        #TO DO: do it
        pass
                
    def load_bars(self, path=None, spectra_type=None):
        soxhlet = extraction.Soxhlet(path) if path else self.soxhlet
        data = soxhlet.load_bars(spectra_type)
        self.update(data)
        return data
        
    def load_populations(self, path=None):
        soxhlet = extraction.Soxhlet(path) if path else self.soxhlet
        data = soxhlet.load_popul()
        self.update(data)
        return self.data
        
    def load_spectra(self, path=None):
        soxhlet = extraction.Soxhlet(path) if path else self.soxhlet
        data = soxhlet.load_spectra()
        self.update(data)
        return data
    
    def load_settings(self, path=None, spectra_type=None):
        # TO DO: remove soxhlet.spectra_type dependence
        soxhlet = extraction.Soxhlet(path) if path else self.soxhlet
        spectra_type = spectra_type if spectra_type else \
            soxhlet.spectra_type
        settings = soxhlet.load_settings()
        self.settings[spectra_type].update(settings)
        return self.settings
        
    def calculate_single_spectrum(self, spectra_name, conformer, start=None,
                                  stop=None, step=None, hwhm=None,
                                  fitting=None):
        bar = self.bars[datawork.default_spectra_bars[spectra_name]][conformer]
        sett_from_args = {
            k: v for k, v in zip(('start', 'stop', 'step', 'hwhm', 'fitting'),
                                 (start, stop, step, hwhm, fitting))
            if v is not None
            }
        sett = self.parameters[bar.spectra_type].copy()
        sett.update(sett_from_args)
        spc = bar.calculate_spectra(**sett)
        return spc
        
    def calculate_spectra(self, *args, start=None, stop=None,
                          step=None, hwhm=None, fitting=None):
        if not args:
            bars = self.bars.spectral.values()
        else:
            #convert to spectra name if bar name passed
            bar_names = datawork.default_spectra_bars
            query = [bar_names[v] if v in bar_names else v for v in args]
            query = set(query) #ensure no duplicates
            bar_names, bars = zip(
                *[(k, v) for k, v in self.bars.spectral.items() if k in query])
            unknown = query - set(self.bars.spectral.keys())
            if unknown:
                info = "No other requests provided." if not bar_names else \
                       "Will proceed using only those bars: {}".format(bar_names)
                msg = "Don't have those bar types: {}. {}".format(unknown, info)
                logger.warning(msg)
        sett_from_args = {
            k: v for k, v in zip(('start', 'stop', 'step', 'hwhm', 'fitting'),
                                 (start, stop, step, hwhm, fitting))
            if v is not None
            }
        output = {}
        for bar in bars:
            sett = self.parameters[bar.spectra_type].copy()
            sett.update(sett_from_args)
            spc = bar.calculate_spectra(**sett)
            self.spectra[bar.spectra_name] = spc
            output[bar.spectra_name] = spc
        return output
        
    def get_averaged_spectrum(self, spectr, energy):
        output = self.spectra[spectr].average(self.energies[energy])
        return output
        
    def __unify_data(self, data, dummy, overriding):
        for dat in data:
            try:
                dummy.trimmer.unify(dat, overriding = overriding)
            except Exception:
                logger.warning(
                    'A problem occured during data unification. '\
                    'Make sure your file sets have any common filenames.',
                    exc_info=True)
                raise
        fnames = [dat.filenames for dat in data]
        #for fnm in fnames: print(fnm)
        if not all(x.shape == y.shape and (x == y).all() for x, y \
                   in zip(fnames[:-1], fnames[1:])):
            #raise
            self.__unify_data(data, dummy, overriding)

    def __get_data(self, data_type):
        data_type = data_type.lower()
        if not data_type or data_type == 'all':
            data = self.extracted
        elif data_type in ('e', 'energy', 'energies'):
            data = self.energies
        elif data_type in ('b', 'bar', 'bars'):
            data = self.bars
        else:
            raise ValueError('Unrecognised value of data_type parameter: '
                             '{}.'.format(data_type))
        return data
                             
    def unify_data(self, stencil=None, data_type='all'):
        data = self.__get_data(data_type).values()
        if not stencil:
            dat = next(iter(data))
            dummy = datawork.DataArray(type='dummy',
                                       filenames = dat.full.filenames)
        else:
            dummy = datawork.DataArray(type='dummy',
                                       filenames = stencil.full.filenames)
            dummy.trimmer.set(stencil.trimmer.blade)
        self.__unify_data(data, dummy,
            overriding = False if stencil is None else True)

    @contextmanager
    def unified_data(self, stencil=None, data_type='all'):
        data = self.__get_data(data_type)
        previous = [(key, value.trimmer.blade)
                    for key, value in data.items()]
        try:
            self.unify_data(stencil, data_type)
            yield data
        finally:
            for name, blade in previous:
                data[name].trimmer.set(blade)
                
    def export_energies(self, format='txt'):
        self.writer.save_output(self.output_dir, 'energies', format)
        
    def export_bars(self, format='txt'):
        self.writer.save_output(self.output_dir, 'bars', format)
                
    def export_spectra(self, format='txt'):
        self.writer.save_output(self.output_dir, 'spectra', format)
                
    def export_averaged(self, format='txt'):
        self.writer.save_output(self.output_dir, 'averaged', format)
        