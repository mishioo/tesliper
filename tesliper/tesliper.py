###################
###   IMPORTS   ###
###################

import os
import logging as lgg
import numpy as np

from . import glassware as gw
from . import datawork as dw
from . import extraction as ex
from . import writer as wr
from .extraction import gaussian_parser as gp

############################
###   GLOBAL VARIABLES   ###
############################

__author__ = "Michał M. Więcław"
__version__ = "0.7.0"
    
    
##################
###   LOGGER   ###
##################

logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)

mainhandler = lgg.StreamHandler()
mainhandler.setLevel(lgg.DEBUG)
mainhandler.setFormatter(lgg.Formatter(
            '%(levelname)s:%(name)s:%(funcName)s - %(message)s'))

loggers = [logger, dw.logger, ex.logger, wr.logger, gw.logger, gp.logger]
for lgr in loggers: lgr.addHandler(mainhandler)


###################
###   CLASSES   ###
###################

class Tesliper:
    """
    TO DO
    -----
    Finish saving functionality.
    Add trimming support.
    Supplement docstrings.
    ? separate spectra types ?
    ? make it inherit mapping ?
    """
    
    standard_parameters = {
        'vibra': {'hwhm': 6,
                  'start': 800,
                  'stop': 2900,
                  'step': 2,
                  'fitting': dw.lorentzian},
        'electr': {'hwhm': 0.35,
                   'start': 150,
                   'stop': 800,
                   'step': 1,
                   'fitting': dw.gaussian}
        }
    units = gw.Spectra.units

    def __init__(self, input_dir=None, output_dir=None, wanted_files=None):
        """
        Parameters
        ----------
        input_dir : str or path-like object, optional
            Path to directory containing files for extraction.
        output_dir : str or path-like object, optional
            Path to directory for output files.
        wanted_files : list, optional
            List filenames representing wanted files.
        """
        self.molecules = gw.Molecules()
        self.soxhlet = None
        self.wanted_files = wanted_files
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.spectra = dict()
        self.set_standard_parameters()
        self.writer = wr.Writer(self)
        
    @property
    def energies(self):
        keys = 'zpe ent ten gib scf'.split(' ')
        return {k: self.molecules.arrayed(k) for k in keys}

    @property
    def spectral(self):
        # TO DO: expand with other spectral data
        keys = 'dip rot vosc vrot losc lrot raman1 roa1'.split(' ')
        return {k: self.molecules.arrayed(k) for k in keys}

    @property
    def bars(self):
        # TO DO: put proper keys here
        keys = 'zpe ent ten gib scf'.split(' ')
        return {k: self.molecules.arrayed(k) for k in keys}
        
    @property
    def wanted_files(self):
        return self.__wanted_files
        
    @wanted_files.setter
    def wanted_files(self, wanted_files):
        self.__wanted_files = wanted_files
        if self.soxhlet is not None:
            self.soxhlet.wanted_files = wanted_files
            logger.info("New list of wanted_files established.")

    def set_standard_parameters(self):
        self.parameters = {
            'vibra': self.standard_parameters['vibra'].copy(),
            'electr': self.standard_parameters['electr'].copy()
            }
        
    def update(self, *args, **kwargs):
        self.molecules.update(*args, **kwargs)
        # raise TypeError("Tesliper instance can not be updated with "
        #                 "type {}".format(type(value)))

    @property
    def input_dir(self):
        return self.__input_dir
        
    @input_dir.setter
    def input_dir(self, path=None):
        if path is not None:
            path = os.path.normpath(path)
            if not os.path.isdir(path):
                raise FileNotFoundError(
                    "Invalid path or directory not found: {}".format(path)
                )
            self.soxhlet = ex.Soxhlet(path, self.wanted_files)
            logger.info('Current working directory is: {}'.format(path))
        self.__input_dir = path
        
    @property
    def output_dir(self):
        return self.__output_dir
        
    @output_dir.setter
    def output_dir(self, path=None):
        if path is not None:
            path = os.path.normpath(path)
            os.makedirs(path, exist_ok=True)
            logger.info('Current output directory is: {}'.format(path))
        self.__output_dir = path

    def extract(self, path=None):
        soxhlet = ex.Soxhlet(path, self.wanted_files) if path else self.soxhlet
        data = soxhlet.extract()
        self.update(data)
        return data
    
    def smart_extract(self, deep_search=True, with_load=True):
        #TO DO: add deep search and loading
        soxhlet = self.soxhlet
        args = soxhlet.parse_command()
        return self.extract(*args)
        pass
        
    def smart_calculate(self, average=True):
        # TO DO: do it
        pass
                
    def load_bars(self, path=None, spectra_type=None):
        soxhlet = ex.Soxhlet(path) if path else self.soxhlet
        data = soxhlet.load_bars(spectra_type)
        self.update(data)
        return data
        
    def load_populations(self, path=None):
        soxhlet = ex.Soxhlet(path) if path else self.soxhlet
        data = soxhlet.load_popul()
        self.update(data)
        return data
        
    def load_spectra(self, path=None):
        soxhlet = ex.Soxhlet(path) if path else self.soxhlet
        data = soxhlet.load_spectra()
        self.update(data)
        return data
    
    def load_settings(self, path=None, spectra_type=None):
        # TO DO: remove soxhlet.spectra_type dependence
        soxhlet = ex.Soxhlet(path) if path else self.soxhlet
        spectra_type = spectra_type if spectra_type else \
            soxhlet.spectra_type
        settings = soxhlet.load_settings()
        self.settings[spectra_type].update(settings)
        return self.settings
        
    def calculate_single_spectrum(self, spectra_name, conformer, start=None,
                                  stop=None, step=None, hwhm=None,
                                  fitting=None):
        bar = self.molecules[conformer][gw.default_spectra_bars[spectra_name]]
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
            bars = self.spectral.values()
        else:
            # convert to spectra name if bar name passed
            bar_names = gw.default_spectra_bars
            query = [bar_names[v] if v in bar_names else v for v in args]
            query = set(query)  # ensure no duplicates
            bar_names, bars = zip(
                *[(k, v) for k, v in self.spectral.items() if k in query])
            unknown = query - set(self.spectral.keys())
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
                        
    def export_energies(self, format='txt'):
        self.writer.save_output(self.output_dir, 'energies', format)
        
    def export_bars(self, format='txt'):
        self.writer.save_output(self.output_dir, 'bars', format)
                
    def export_spectra(self, format='txt'):
        self.writer.save_output(self.output_dir, 'spectra', format)
                
    def export_averaged(self, format='txt'):
        self.writer.save_output(self.output_dir, 'averaged', format)
        