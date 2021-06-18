# IMPORTS
import os
import logging as lgg
from pathlib import Path
from typing import Union, Iterable, Optional, Set

import numpy as np

from . import glassware as gw
from . import datawork as dw
from . import extraction as ex
from . import writing as wr


# GLOBAL VARIABLES
__author__ = "Michał M. Więcław"
__version__ = "0.7.4"
_DEVELOPMENT = False


# LOGGER
logger = lgg.getLogger(__name__)

mainhandler = lgg.StreamHandler()
mainhandler.setLevel(lgg.DEBUG)
mainhandler.setFormatter(
    lgg.Formatter("%(levelname)s:%(name)s:%(funcName)s - %(message)s")
)

logger.setLevel(lgg.DEBUG if _DEVELOPMENT else lgg.WARNING)
logger.addHandler(mainhandler)


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
        "vibra": {
            "width": 6,
            "start": 800,
            "stop": 2900,
            "step": 2,
            "fitting": dw.lorentzian,
        },
        "electr": {
            "width": 0.35,
            "start": 150,
            "stop": 800,
            "step": 1,
            "fitting": dw.gaussian,
        },
    }
    _standard_parameters["scatt"] = _standard_parameters["vibra"]

    def __init__(self, input_dir=".", output_dir=".", wanted_files=None):
        """
        Parameters
        ----------
        input_dir : str or path-like object, optional
            Path to directory containing files for extraction, defaults to current
            working directory.
        output_dir : str or path-like object, optional
            Path to directory for output files, defaults to current working directory.
        wanted_files : list, optional
            List filenames representing wanted files.
        """
        self.molecules = gw.Molecules()
        self.writers = {
            "txt": wr.TxtWriter,
            "xlsx": wr.XlsxWriter,
            "csv": wr.CsvWriter,
        }
        self.wanted_files = wanted_files
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.spectra = dict()
        self.averaged = dict()
        self.parameters = self.standard_parameters
        self.same_vibrational_parameters = False
        self.same_electronic_parameters = False
        self.same_scattering_parameters = False

    def __getitem__(self, item):
        try:
            return self.molecules.arrayed(item)
        except ValueError:
            raise KeyError(f"Unknown genre '{item}'.")

    @property
    def energies(self):
        keys = "zpe ent ten gib scf".split(" ")
        return {k: self.molecules.arrayed(k) for k in keys}

    @property
    def spectral(self):
        # TO DO: expand with other spectral data
        keys = "dip rot vosc vrot losc lrot raman1 roa1".split(" ")
        return {k: self.molecules.arrayed(k) for k in keys}

    @property
    def bars(self):
        # TO DO: put proper keys here
        keys = "dip rot vosc vrot raman1 roa1".split(" ")
        return {k: self.molecules.arrayed(k) for k in keys}

    @property
    def wanted_files(self) -> Optional[Set[str]]:
        """Set of files that are desired for data extraction, stored as filenames
        without an extension. Any iterable of strings or Path objects is transformed
        to this form.

        >>> tslr = Tesliper()
        >>> tslr.wanted_files = [Path("./dir/file_one.out"), Path("./dir/file_two.out")]
        >>> tslr.wanted_files
        {"file_one", "file_two"}

        May also be set to `None` or other "falsy" value, in such case it is ignored.
        """
        # TODO: reuse Soxhlet.wanted_files property
        return self._wanted_files

    @wanted_files.setter
    def wanted_files(self, files: Optional[Iterable[Union[str, Path]]]):
        self._wanted_files = None if not files else {Path(f).stem for f in files}

    @property
    def standard_parameters(self):
        return {key: params.copy() for key, params in self._standard_parameters.items()}

    def update(self, *args, **kwargs):
        self.molecules.update(*args, **kwargs)
        # raise TypeError("Tesliper instance can not be updated with "
        #                 "type {}".format(type(value)))

    @property
    def input_dir(self) -> Path:
        return self.__input_dir

    @input_dir.setter
    def input_dir(self, path: Union[Path, str] = "."):
        path = Path(path).resolve()
        if not path.is_dir():
            raise FileNotFoundError(
                "Invalid path or directory not found: {}".format(path)
            )
        logger.info("Current working directory is: {}".format(path))
        self.__input_dir = path

    @property
    def output_dir(self) -> Path:
        return self.__output_dir

    @output_dir.setter
    def output_dir(self, path: Union[Path, str] = "."):
        path = Path(path).resolve()
        path.mkdir(exist_ok=True)
        logger.info("Current output directory is: {}".format(path))
        self.__output_dir = path

    def extract_iterate(self, path=None, wanted_files=None):
        soxhlet = ex.Soxhlet(path or self.input_dir, wanted_files or self.wanted_files)
        for file, data in soxhlet.extract_iter():
            self.update(((file, data),))
            yield file, data

    def extract(self, path=None, wanted_files=None):
        for f, d in self.extract_iterate(path, wanted_files):
            _ = f, d

    def smart_extract(self, deep_search=True):
        # TODO: should also parse settings
        soxhlet = ex.Soxhlet(self.input_dir, self.wanted_files, recursive=deep_search)
        for file, data in soxhlet.extract_iter():
            self.update(((file, data),))

    def smart_calculate(self, average=True):
        # TODO: implement it
        pass

    def load_settings(self, path=None, spectra_type=None):
        # TODO: remove soxhlet.spectra_type dependence
        soxhlet = ex.Soxhlet(path or self.input_dir)
        spectra_type = spectra_type if spectra_type else soxhlet.spectra_type
        settings = soxhlet.load_settings()
        self.settings[spectra_type].update(settings)
        return self.settings

    def calculate_single_spectrum(
        self,
        spectra_name,
        conformer,
        start=None,
        stop=None,
        step=None,
        width=None,
        fitting=None,
    ):
        # TO DO: add error handling when no data for requested spectrum
        bar_name = gw.default_spectra_bars[spectra_name]
        is_excited = spectra_name.lower() in ("uv", "ecd")
        conformer = self.molecules[conformer]
        values = conformer[bar_name]
        freqs = 1e7 / conformer["wave"] if is_excited else conformer["freq"]
        inten = dw.calculate_intensities(bar_name, values, freqs)
        sett_from_args = {
            k: v
            for k, v in zip(
                ("start", "stop", "step", "width", "fitting"),
                (start, stop, step, width, fitting),
            )
            if v is not None
        }
        sett = self.parameters[gw.Bars.spectra_type_ref[spectra_name]].copy()
        sett.update(sett_from_args)
        start, stop, step = [sett.pop(k) for k in ("start", "stop", "step")]
        abscissa = np.arange(start, stop, step)
        if not is_excited:
            converted = sett
            converted["abscissa"] = abscissa
        else:
            converted = dict(
                width=sett["width"] / 1.23984e-4,
                fitting=sett["fitting"],
                abscissa=1e7 / abscissa,
            )
        spc = dw.calculate_spectra([freqs], [inten], **converted)
        spc = gw.Spectra(
            spectra_name.lower(),
            conformer,
            spc[0],
            abscissa,
            width,
            fitting.__name__,
            check_sizes=False,
        )
        return spc

    def calculate_spectra(
        self, genres=(), start=None, stop=None, step=None, width=None, fitting=None
    ):
        if not genres:
            bars = self.bars.values()
        else:
            # convert to spectra name if bar name passed
            bar_names = gw.default_spectra_bars
            genres = genres.split() if isinstance(genres, str) else genres
            query = [bar_names[v] if v in bar_names else v for v in genres]
            query_set = set(query)  # ensure no duplicates
            bar_names, bars = zip(
                *[(k, v) for k, v in self.spectral.items() if k in query_set]
            )
            unknown = query_set - set(self.spectral.keys())
            # TO DO: change it to handle custom bars
            if unknown:
                info = (
                    "No other requests provided."
                    if not bar_names
                    else f"Will proceed using only those bars: {bar_names}"
                )
                msg = f"Don't have those bar types: {unknown}. {info}"
                logger.warning(msg)
        sett_from_args = {
            k: v
            for k, v in zip(
                ("start", "stop", "step", "width", "fitting"),
                (start, stop, step, width, fitting),
            )
            if v is not None
        }
        output = {}
        for bar in bars:
            sett = self.parameters[bar.spectra_type].copy()
            sett.update(sett_from_args)
            spectra = bar.calculate_spectra(**sett)
            if spectra:
                output[bar.spectra_name] = spectra
            else:
                # should empty spectra be included in output?
                logger.warning(
                    f"No data for {bar.spectra_name} calculation; "
                    f"appropriate data is not available or was filtered out."
                )
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
        return self.averaged

    def export_data(self, genres, dest="", fmt="txt"):
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
            raise ValueError("No destination provided.")
        try:
            writer_class = self.writers[fmt]
        except KeyError:
            raise ValueError(f"Invalid file format: {fmt}")
        writer = writer_class(dest)
        data = [self[g] for g in genres]
        writer.write(data)

    def export_energies(self, dest="", fmt="txt"):
        dest = dest if dest else self.output_dir
        if not dest:
            raise ValueError("No destination provided.")
        try:
            writer_class = self.writers[fmt]
        except KeyError:
            raise ValueError(f"Invalid file format: {fmt}")
        writer = writer_class(dest)
        energies = [e for e in self.energies.values() if e]
        corrections = (self[f"{e.genre}corr"] for e in energies if e.genre != "scf")
        frequencies = self["freq"]
        stoichiometry = self["stoichiometry"]
        writer.write(data=[*energies, frequencies, stoichiometry, *corrections])

    def export_bars(self, dest="", fmt="txt"):
        dest = dest if dest else self.output_dir
        if not dest:
            raise ValueError("No destination provided.")
        try:
            writer_class = self.writers[fmt]
        except KeyError:
            raise ValueError(f"Invalid file format: {fmt}")
        writer = writer_class(dest)
        bands = [self["freq"], self["wave"]]
        data = [b for b in self.spectral.values() if b] + [b for b in bands if b]
        writer.write(data)

    def export_spectra(self, dest="", fmt="txt"):
        dest = dest if dest else self.output_dir
        if not dest:
            raise ValueError("No destination provided.")
        try:
            writer_class = self.writers[fmt]
        except KeyError:
            raise ValueError(f"Invalid file format: {fmt}")
        writer = writer_class(dest)
        data = [s for s in self.spectra.values() if s]
        writer.write(data)

    def export_averaged(self, dest="", fmt="txt"):
        dest = dest if dest else self.output_dir
        if not dest:
            raise ValueError("No destination provided.")
        try:
            writer_class = self.writers[fmt]
        except KeyError:
            raise ValueError(f"Invalid file format: {fmt}")
        writer = writer_class(dest)
        data = [s for s in self.averaged.values() if s]
        writer.write(data)

    def serialize(self, filename: str = ".tslr", mode: str = "x") -> None:
        """Serialize instance of Tesliper object to a file in `self.output_dir`.

        Parameters
        ----------
        filename: str
            Name of the file, to which content will be written. Defaults to ".tslr".
        mode: str
            Specifies how writing to file should be handled.
            Should be one of characters: "x" or "w".
            "x" - only write if file doesn't exist yet;
            "w" - overwrite file if it already exists.
            Defaults to "x".

        Raises
        ------
        ValueError
            If given any other `mode` than "x" or "w".

        Notes
        -----
        If `self.output_dir` is `None`, current working directory is assumed.
        """
        path = self.output_dir / filename
        if mode not in {"x", "w"}:
            raise ValueError(
                f"'{mode}' is not a valid mode for serializing Tesliper object. "
                f"It should be 'x' or 'w'."
            )
        writer = wr.ArchiveWriter(destination=path, mode=mode)
        writer.write(self)

    @classmethod
    def load(cls, source: Union[Path, str]) -> "Tesliper":
        """Load serialized Tesliper object from given file.

        Parameters
        ----------
        source: pathlib.Path or str
            Path to the file with serialized Tesliper object.

        Returns
        -------
        Tesliper
            New instance of Tesliper class containing data read from the file.
        """
        path = Path(source)
        loader = wr.ArchiveLoader(source=path)
        return loader.load()
