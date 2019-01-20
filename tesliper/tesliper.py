# IMPORTS
import os
import logging as lgg
import numpy as np

from . import glassware as gw
from . import datawork as dw
from . import extraction as ex
from . import writer as wr
from .extraction import gaussian_parser as gp


# GLOBAL VARIABLES
__author__ = "Michał M. Więcław"
__version__ = "0.7.0"
_DEVELOPMENT = False
    

# LOGGER
logger = lgg.getLogger(__name__)

mainhandler = lgg.StreamHandler()
mainhandler.setLevel(lgg.DEBUG)
mainhandler.setFormatter(lgg.Formatter(
            '%(levelname)s:%(name)s:%(funcName)s - %(message)s'))

loggers = [logger, dw.logger, ex.logger, wr.logger, gw.logger, gp.logger]
for lgr in loggers:
    lgr.setLevel(lgg.DEBUG if _DEVELOPMENT else lgg.WARNING)
    lgr.addHandler(mainhandler)


# CLASSES
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
    
    _standard_parameters = {
        'vibra': {'width': 6,
                  'start': 800,
                  'stop': 2900,
                  'step': 2,
                  'fitting': dw.lorentzian},
        'electr': {'width': 0.35,
                   'start': 150,
                   'stop': 800,
                   'step': 1,
                   'fitting': dw.gaussian}
        }

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
        self.writers = {fmt: Wrt() for fmt, Wrt in wr.Writer.writers.items()}
        self.soxhlet = None if input_dir is not None else ex.Soxhlet()
        self.wanted_files = wanted_files  # setter modifies self.soxhlet
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.spectra = dict()
        self.averaged = dict()
        self.parameters = self.standard_parameters

    def __getitem__(self, item):
        try:
            return self.molecules.arrayed(item)
        except ValueError:
            raise KeyError(f"Unknown genre '{item}'.")

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
        keys = 'dip rot vosc vrot raman1 roa1'.split(' ')
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

    @property
    def standard_parameters(self):
        return {
            'vibra': self._standard_parameters['vibra'].copy(),
            'electr': self._standard_parameters['electr'].copy()
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
            # self.writer.path = path  # depreciated
            logger.info('Current output directory is: {}'.format(path))
        self.__output_dir = path

    def extract_iterate(self, path=None, wanted_files=None):
        files = wanted_files or self.wanted_files
        soxhlet = ex.Soxhlet(path, files) if path else self.soxhlet
        for file, data in soxhlet.extract():
            self.update(((file, data),))
            yield file, data

    def extract(self, path=None, wanted_files=None):
        files = wanted_files or self.wanted_files
        soxhlet = ex.Soxhlet(path, files) if path else self.soxhlet
        for file, data in soxhlet.extract():
            self.update(((file, data),))
    
    def smart_extract(self, deep_search=True, with_load=True):
        #TO DO: add deep search and loading
        soxhlet = self.soxhlet
        args = soxhlet.parse_command()
        return self.extract(*args)

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
        
    def calculate_single_spectrum(
            self, spectra_name, conformer, start=None, stop=None, step=None,
            width=None, fitting=None
    ):
        # TO DO: add error handling when no data for requested spectrum
        bar_name = gw.default_spectra_bars[spectra_name]
        is_excited = spectra_name.lower() in ('uv', 'ecd')
        conformer = self.molecules[conformer]
        values = conformer[bar_name]
        freqs = 1e7 / conformer['wave'] if is_excited else conformer['freq']
        inten = dw.calculate_intensities(bar_name, values, freqs)
        sett_from_args = {
            k: v for k, v in zip(('start', 'stop', 'step', 'width', 'fitting'),
                                 (start, stop, step, width, fitting))
            if v is not None
            }
        sett = self.parameters[gw.Bars.spectra_type_ref[spectra_name]].copy()
        sett.update(sett_from_args)
        start, stop, step = [sett.pop(k) for k in ('start', 'stop', 'step')]
        abscissa = np.arange(start, stop, step)
        if not is_excited:
            converted = sett
            converted['abscissa'] = abscissa
        else:
            converted = dict(
                width=sett['width'] / 1.23984e-4,
                fitting=sett['fitting'],
                abscissa=1e7 / abscissa
            )
        spc = dw.calculate_spectra([freqs], [inten], **converted)
        spc = gw.Spectra(
            spectra_name.lower(), conformer, spc[0], abscissa, width,
            fitting.__name__, check_sizes=False
        )
        return spc
        
    def calculate_spectra(
            self, grnres=(), start=None, stop=None, step=None, width=None,
            fitting=None
    ):
        if not grnres:
            bars = self.bars.values()
        else:
            # convert to spectra name if bar name passed
            bar_names = gw.default_spectra_bars
            query = [bar_names[v] if v in bar_names else v for v in grnres]
            query = set(query)  # ensure no duplicates
            spectral = self.spectral
            bar_names, bars = zip(
                *[(k, v) for k, v in spectral.items() if k in query])
            unknown = query - set(spectral.keys())
            if unknown:
                info = "No other requests provided." if not bar_names else \
                       f"Will proceed using only those bars: {bar_names}"
                msg = f"Don't have those bar types: {unknown}. {info}"
                logger.warning(msg)
        sett_from_args = {
            k: v for k, v in zip(('start', 'stop', 'step', 'width', 'fitting'),
                                 (start, stop, step, width, fitting))
            if v is not None
            }
        output = {}
        for bar in bars:
            sett = self.parameters[bar.spectra_type].copy()
            sett.update(sett_from_args)
            spectra = bar.calculate_spectra(**sett)
            if spectra:
                output[bar.spectra_name] = spectra
        self.spectra.update(output)
        return output
        
    def get_averaged_spectrum(self, spectrum, energy):
        spectra = self.spectra[spectrum]
        with self.molecules.trimmed_to(spectra.filenames):
            en = self.molecules.arrayed(energy)
        output = spectra.average(en)
        return output

    def average_spectra(self):
        for genre, spectra in self.spectra.items():
            with self.molecules.trimmed_to(spectra.filenames):
                for energies in self.energies.values():
                    av = spectra.average(energies)
                    self.averaged[(genre, energies.genre)] = av

    def export_data(self, genres, dest='', fmt='txt'):
        """
        Parameters
        ----------
        genres: list of str
            list of genre names, that are to be saved to disc
        dest: str
            path to destination directory
        fmt: str
            format of output files

        TO DO
        -----
        add checking if freq/wave/ect. passed if needed
        """
        dest = dest if dest else self.output_dir
        if not dest:
            raise ValueError('No destination provided.')
        try:
            writer = self.writers[fmt]
        except KeyError:
            raise ValueError(f'Invalid file format: {fmt}')
        data = [self[g] for g in genres]
        writer.write(dest, data)

    def export_energies(self, dest='', fmt='txt'):
        dest = dest if dest else self.output_dir
        if not dest:
            raise ValueError('No destination provided.')
        try:
            writer = self.writers[fmt]
        except KeyError:
            raise ValueError(f'Invalid file format: {fmt}')
        energies = [e for e in self.energies.values() if e]
        corrections = (
            self[f'{e.genre}corr'] for e in energies if e.genre != 'scf'
        )
        frequencies = self['freq']
        stoichiometry = self['stoichiometry']
        writer.write(
            dest, data=[*energies, frequencies, stoichiometry, *corrections]
        )

    def export_bars(self, dest='', fmt='txt'):
        dest = dest if dest else self.output_dir
        if not dest:
            raise ValueError('No destination provided.')
        try:
            writer = self.writers[fmt]
        except KeyError:
            raise ValueError(f'Invalid file format: {fmt}')
        bands = [self['freq'], self['wave']]
        data = [b for b in self.spectral.values() if b] + \
               [b for b in bands if b]
        writer.write(dest, data)
                
    def export_spectra(self, dest='', fmt='txt'):
        dest = dest if dest else self.output_dir
        if not dest:
            raise ValueError('No destination provided.')
        try:
            writer = self.writers[fmt]
        except KeyError:
            raise ValueError(f'Invalid file format: {fmt}')
        data = [s for s in self.spectra.values() if s]
        writer.write(dest, data)
                
    def export_averaged(self, dest='', fmt='txt'):
        dest = dest if dest else self.output_dir
        if not dest:
            raise ValueError('No destination provided.')
        try:
            writer = self.writers[fmt]
        except KeyError:
            raise ValueError(f'Invalid file format: {fmt}')
        data = [s for s in self.averaged.values() if s]
        writer.write(dest, data)
