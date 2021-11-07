# IMPORTS
import logging as lgg
import os
from pathlib import Path
from typing import (
    Callable,
    Dict,
    Generator,
    Iterable,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from . import datawork as dw
from . import extraction as ex
from . import glassware as gw
from . import writing as wr
from .datawork.spectra import FittingFunctionType, Number

# GLOBAL VARIABLES
__author__ = "Michał M. Więcław"
__version__ = "0.7.4"

_DEVELOPMENT = "ENV" in os.environ and os.environ["ENV"] == "prod"


# LOGGER
logger = lgg.getLogger(__name__)

mainhandler = lgg.StreamHandler()
mainhandler.setLevel(lgg.DEBUG)
mainhandler.setFormatter(
    lgg.Formatter("%(levelname)s:%(name)s:%(funcName)s - %(message)s")
)

logger.setLevel(lgg.DEBUG if _DEVELOPMENT else lgg.WARNING)
logger.addHandler(mainhandler)

_activities_types = Union[
    gw.VibrationalActivities,
    gw.ScatteringActivities,
    gw.ElectronicActivities,
]


# CLASSES
class Tesliper:
    """
    TO DO
    -----
    Add trimming support.
    Supplement docstrings.
    ? separate spectra types ?
    ? make it inherit mapping ?
    """

    _standard_parameters = {
        "vibrational": {
            "width": 6,
            "start": 800,
            "stop": 2900,
            "step": 2,
            "fitting": dw.lorentzian,
        },
        "electronic": {
            "width": 0.35,
            "start": 150,
            "stop": 800,
            "step": 1,
            "fitting": dw.gaussian,
        },
    }
    _standard_parameters["scattering"] = _standard_parameters["vibrational"].copy()
    # TODO: introduce more sophisticated parameters proxy that enables using
    #       same or different params for genres of same type (e.g. "ir" and "vcd")

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
        self.conformers = gw.Conformers()
        self.wanted_files = wanted_files
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.spectra = dict()
        self.averaged = dict()
        self.parameters = self.standard_parameters

    def __getitem__(self, item):
        try:
            return self.conformers.arrayed(item)
        except ValueError:
            raise KeyError(f"Unknown genre '{item}'.")

    def clear(self):
        """Remove all data from the instance."""
        self.conformers.clear()
        self.wanted_files = []
        self.input_dir = ""
        self.output_dir = ""
        self.spectra = dict()
        self.averaged = dict()
        self.parameters = self.standard_parameters

    @property
    def energies(self) -> Dict[str, gw.Energies]:
        """Data for each energies' genre as `Energies` data array.
        Returned dictionary is of form {"genre": `Energies`} for each of the genres:
        "scf", "zpe", "ten", "ent", and "gib". If no values are available for
        a specific genre, an empty `Energies` array is produced as corresponding
        dictionary value.

        >>> tslr = Tesliper()
        >>> tslr.energies
        {
            "scf": Energies(genre="scf", ...),
            "zpe": Energies(genre="zpe", ...),
            "ten": Energies(genre="ten", ...),
            "ent": Energies(genre="ent", ...),
            "gib": Energies(genre="gib", ...),
        }

        Returns
        -------
        dict
            Dictionary with genre names as keys and `Energies` data arrays as values.
        """
        keys = gw.Energies.associated_genres
        return {k: self.conformers.arrayed(k) for k in keys}

    @property
    def activities(self) -> Dict[str, _activities_types]:
        """Data for default activities used to calculate spectra as appropriate
        `SpectralActivities` subclass.
        Returned dictionary is of form {"genre": `SpectralActivities`} for each of the
        genres: "dip", "rot", "vosc", "vrot", "raman1", and "roa1". If no values are
        available for a specific genre, an empty data array is produced as corresponding
        dictionary value.

        >>> tslr = Tesliper()
        >>> tslr.activities
        {
            "dip": VibrationalActivities(genre="dip", ...),
            "rot": VibrationalActivities(genre="rot", ...),
            "vosc": ElectronicActivities(genre="vosc", ...),
            "vrot": ElectronicActivities(genre="vrot", ...),
            "raman1": ScatteringActivities(genre="raman1", ...),
            "roa1": ScatteringActivities(genre="roa1", ...),
        }

        Returns
        -------
        dict
            Dictionary with genre names as keys and `SpectralActivities`
            data arrays as values.
        """
        keys = dw.DEFAULT_ACTIVITIES.values()
        return {k: self.conformers.arrayed(k) for k in keys}

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
    def standard_parameters(self) -> Dict[str, Dict[str, Union[int, float, Callable]]]:
        """Default parameters for spectra calculation for each spectra type
        (vibrational, electronic, and scattering). This returns a dictionary,
        but in fact it is a convenience, read-only attribute,
        modifying it will have no persisting effect.
        """
        return {key: params.copy() for key, params in self._standard_parameters.items()}

    def update(self, other=None, **kwargs):
        """Update stored conformers with given data.

        Works like `dict.update`, but if key is already present, it updates
        dictionary associated with given key rather than assigning new value.
        Keys of dictionary passed as positional parameter (or additional keyword
        arguments given) should be conformers' identifiers and its values should be
        dictionaries of {"genre": values} for those conformers.

        Please note, that values of status genres like 'optimization_completed'
        and 'normal_termination' will be updated as well for such key,
        if are present in given new values.

        >>> tslr.conformers
        Conformers([('one', {'scf': -100, 'stoichiometry': 'CH4'})])
        >>> tslr.update(
        ...     {'one': {'scf': 97}, 'two': {'scf': 82, 'stoichiometry': 'CH4'}}
        ... )
        >>> tslr.conformers
        Conformers([
            ('one', {'scf': 97, 'stoichiometry': 'CH4'}),
            ('two', {'scf': 82, 'stoichiometry': 'CH4'}),
        ])
        """
        self.conformers.update(other, **kwargs)

    @property
    def input_dir(self) -> Path:
        """Directory, from which files should be read."""
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
        """Directory, to which generated files should be written."""
        return self.__output_dir

    @output_dir.setter
    def output_dir(self, path: Union[Path, str] = "."):
        path = Path(path).resolve()
        path.mkdir(exist_ok=True)
        logger.info("Current output directory is: {}".format(path))
        self.__output_dir = path

    def extract_iterate(
        self,
        path: Optional[Union[str, Path]] = None,
        wanted_files: Optional[Iterable[str]] = None,
    ) -> Generator[Tuple[str, dict], None, None]:
        """Extracts data from chosen Gaussian output files present in given directory
        and yields data for each conformer found.

        Uses `Tesliper.input_dir` as source directory and `Tesliper.wanted_files`
        list of chosen files if these are not explicitly given as 'path' and
        'wanted_files' parameters.

        It is important to note that extracted data is yielded as dictionary BEFORE
        updating known conformers in underlying `Conformers` instance, so all changes
        introduced to this data will be persistent.

        Parameters
        ----------
        path : str or pathlib.Path, optional
            Path to directory, from which Gaussian files should be read.
            If not given or is `None`, `Tesliper.output_dir` will be used.
        wanted_files : list of str, optional
            Filenames (without a file extension) of conformers that should be extracted.
            If not given or is `None`, `Tesliper.wanted_files` will be used.
            If `Tesliper.wanted_files` is also `None`, all found Gaussian output files
            will be parsed.

        Yields
        ------
        tuple
            Two item tuple with name of parsed file as first and extracted
            data as second item, for each Gaussian output file parsed.
        """
        soxhlet = ex.Soxhlet(path or self.input_dir, wanted_files or self.wanted_files)
        for file, data in soxhlet.extract_iter():
            self.update(((file, data),))
            yield file, data

    def extract(
        self,
        path: Optional[Union[str, Path]] = None,
        wanted_files: Optional[Iterable[str]] = None,
    ):
        """Extracts data from chosen Gaussian output files present in given directory.

        Uses `Tesliper.input_dir` as source directory and `Tesliper.wanted_files`
        list of chosen files if these are not explicitly given as 'path' and
        'wanted_files' parameters.

        Parameters
        ----------
        path : str or pathlib.Path, optional
            Path to directory, from which Gaussian files should be read.
            If not given or is `None`, `Tesliper.output_dir` will be used.
        wanted_files : list of str, optional
            Filenames (without a file extension) of conformers that should be extracted.
            If not given or is `None`, `Tesliper.wanted_files` will be used.
        """
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

    def _calc_spc_with_settings(
        self, activities: gw.SpectralActivities, settings: dict
    ) -> gw.Spectra:
        """Helper method fot calculating spectra."""
        sett = self.parameters[activities.spectra_type].copy()
        sett.update(settings)
        return activities.calculate_spectra(**sett)

    def calculate_single_spectrum(
        self,
        genre: str,
        conformer: str,
        start: Number = None,
        stop: Number = None,
        step: Number = None,
        width: Number = None,
        fitting: FittingFunctionType = None,
    ) -> gw.SingleSpectrum:
        # TODO: add error handling when no data for requested spectrum
        try:
            bar_name = dw.DEFAULT_ACTIVITIES[genre]
        except KeyError:
            bar_name = genre
        with self.conformers.trimmed_to([conformer]) as confs:
            bar = confs.arrayed(bar_name)
        sett_from_args = {
            k: v
            for k, v in zip(
                ("start", "stop", "step", "width", "fitting"),
                (start, stop, step, width, fitting),
            )
            if v is not None
        }
        spc = self._calc_spc_with_settings(bar, sett_from_args)
        # TODO: maybe Spectra class should provide such conversion ?
        return gw.SingleSpectrum(
            spc.genre,
            spc.values[0],
            spc.abscissa,
            spc.width,
            spc.fitting,
            scaling=spc.scaling,
            offset=spc.offset,
            filenames=spc.filenames,
        )

    def calculate_spectra(
        self,
        genres: Iterable[str] = (),
        start: Number = None,
        stop: Number = None,
        step: Number = None,
        width: Number = None,
        fitting: FittingFunctionType = None,
    ):
        if not genres:
            bars = self.activities.values()
        else:
            # convert to spectra name if bar name passed
            default_act = dw.DEFAULT_ACTIVITIES
            genres = genres.split() if isinstance(genres, str) else genres
            query = [default_act[v] if v in default_act else v for v in genres]
            query_set = set(query)  # ensure no duplicates
            bars = (self[g] for g in query_set)
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
            spectra = self._calc_spc_with_settings(bar, sett_from_args)
            if spectra:
                output[bar.spectra_name] = spectra
            else:
                # should empty spectra be included in output?
                logger.warning(
                    f"No data for {bar.spectra_name} calculation; "
                    f"appropriate data is not available or was trimmed off."
                )
        self.spectra.update(output)
        return output

    def get_averaged_spectrum(self, spectrum: str, energy: str) -> gw.SingleSpectrum:
        spectra = self.spectra[spectrum]
        with self.conformers.trimmed_to(spectra.filenames):
            en = self.conformers.arrayed(energy)
        output = spectra.average(en)
        return output

    def average_spectra(self) -> Dict[str, gw.SingleSpectrum]:
        for genre, spectra in self.spectra.items():
            with self.conformers.trimmed_to(spectra.filenames):
                for energies in self.energies.values():
                    av = spectra.average(energies)
                    self.averaged[(genre, energies.genre)] = av
        return self.averaged

    # TODO: supplement docstrings
    def export_data(self, genres: Sequence[str], fmt: str = "txt", mode: str = "x"):
        """Saves specified data genres to disk in given file format.

        File formats available by default are: "txt", "csv", "xlsx", "gjf". Note that
        not all formats may are compatible with every genre (e.g. only "geometry"
        genre may be exported fo .gjf format). In such case genres unsupported
        by given format are ignored.

        Files produced are written to `Tesliper.output_dir` directory with filenames
        automatically generated using adequate genre's name and conformers' identifiers.
        In case of "xlsx" format only one file is produced and different data genres are
        written to separate sheets.

        Parameters
        ----------
        genres : list of str
            List of genre names, that will be saved to disk.
        fmt : str
            File format of output files, defaults to "txt".
        mode : str
            Specifies how writing to file should be handled. May be one of:
            "a" (append to existing file), "x" (only write if file doesn't exist yet),
            "w" (overwrite file if it already exists). Defaults to "x".
        """
        wrt = wr.writer(fmt=fmt, destination=self.output_dir, mode=mode)
        data = [self[g] for g in genres]
        if any(isinstance(arr, gw.arrays._VibData) for arr in data):
            data += [self["freq"]]
        if any(isinstance(arr, (gw.ElectronicData, gw.Transitions)) for arr in data):
            data += [self["wavelen"]]
        wrt.write(data)

    def export_energies(self, fmt: str = "txt", mode: str = "x"):
        """Saves energies and population data to disk in given file format.

        File formats available by default are: "txt", "csv", "xlsx".
        Files produced are written to `Tesliper.output_dir` directory with filenames
        automatically generated using adequate genre's name and conformers' identifiers.
        In case of "xlsx" format only one file is produced and different data genres are
        written to separate sheets.

        Parameters
        ----------
        fmt : str
            File format of output files, defaults to "txt".
        mode : str
            Specifies how writing to file should be handled. May be one of:
            "a" (append to existing file), "x" (only write if file doesn't exist yet),
            "w" (overwrite file if it already exists). Defaults to "x".
        """
        wrt = wr.writer(fmt=fmt, destination=self.output_dir, mode=mode)
        energies = [e for e in self.energies.values() if e]
        corrections = (self[f"{e.genre}corr"] for e in energies if e.genre != "scf")
        frequencies = self["freq"]
        stoichiometry = self["stoichiometry"]
        wrt.write(data=[*energies, frequencies, stoichiometry, *corrections])

    # TODO: separate to vibrational and electronic ?
    def export_spectral_data(self, fmt: str = "txt", mode: str = "x"):
        """Saves unprocessed spectral data to disk in given file format.

        File formats available by default are: "txt", "csv", "xlsx".
        Files produced are written to `Tesliper.output_dir` directory with filenames
        automatically generated using adequate genre's name and conformers' identifiers.
        In case of "xlsx" format only one file is produced and different data genres are
        written to separate sheets.

        Parameters
        ----------
        fmt : str
            File format of output files, defaults to "txt".
        mode : str
            Specifies how writing to file should be handled. May be one of:
            "a" (append to existing file), "x" (only write if file doesn't exist yet),
            "w" (overwrite file if it already exists). Defaults to "x".
        """
        wrt = wr.writer(fmt=fmt, destination=self.output_dir, mode=mode)
        bands = [self["freq"], self["wavelen"]]
        genres = (
            *gw.VibrationalData.associated_genres,
            *gw.ElectronicData.associated_genres,
            *gw.ScatteringData.associated_genres,
        )
        data = [self[g] for g in genres if g] + [b for b in bands if b]
        wrt.write(data)

    # TODO: separate to vibrational and electronic ?
    def export_activities(self, fmt: str = "txt", mode: str = "x"):
        """Saves unprocessed spectral activities to disk in given file format.

        File formats available by default are: "txt", "csv", "xlsx".
        Files produced are written to `Tesliper.output_dir` directory with filenames
        automatically generated using adequate genre's name and conformers' identifiers.
        In case of "xlsx" format only one file is produced and different data genres are
        written to separate sheets.

        Parameters
        ----------
        fmt : str
            File format of output files, defaults to "txt".
        mode : str
            Specifies how writing to file should be handled. May be one of:
            "a" (append to existing file), "x" (only write if file doesn't exist yet),
            "w" (overwrite file if it already exists). Defaults to "x".
        """
        wrt = wr.writer(fmt=fmt, destination=self.output_dir, mode=mode)
        bands = [self["freq"], self["wavelen"]]
        genres = (
            *gw.VibrationalActivities.associated_genres,
            *gw.ElectronicActivities.associated_genres,
            *gw.ScatteringActivities.associated_genres,
        )
        data = [self[g] for g in genres if g] + [b for b in bands if b]
        wrt.write(data)

    def export_spectra(self, fmt: str = "txt", mode: str = "x"):
        """Saves spectra calculated previously to disk in given file format.

        File formats available by default are: "txt", "csv", "xlsx".
        Files produced are written to `Tesliper.output_dir` directory with filenames
        automatically generated using adequate genre's name and conformers' identifiers.
        In case of "xlsx" format only one file is produced and different data genres are
        written to separate sheets.

        Parameters
        ----------
        fmt : str
            File format of output files, defaults to "txt".
        mode : str
            Specifies how writing to file should be handled. May be one of:
            "a" (append to existing file), "x" (only write if file doesn't exist yet),
            "w" (overwrite file if it already exists). Defaults to "x".
        """
        wrt = wr.writer(fmt=fmt, destination=self.output_dir, mode=mode)
        data = [s for s in self.spectra.values() if s]
        wrt.write(data)

    def export_averaged(self, fmt: str = "txt", mode: str = "x"):
        """Saves spectra calculated and averaged previously to disk
        in given file format.

        File formats available by default are: "txt", "csv", "xlsx".
        Files produced are written to `Tesliper.output_dir` directory with filenames
        automatically generated using adequate genre's name and conformers' identifiers.
        In case of "xlsx" format only one file is produced and different data genres are
        written to separate sheets.

        Parameters
        ----------
        fmt : str
            File format of output files, defaults to "txt".
        mode : str
            Specifies how writing to file should be handled. May be one of:
            "a" (append to existing file), "x" (only write if file doesn't exist yet),
            "w" (overwrite file if it already exists). Defaults to "x".
        """
        wrt = wr.writer(fmt=fmt, destination=self.output_dir, mode=mode)
        data = [s for s in self.averaged.values() if s]
        wrt.write(data)

    def export_job_file(
        self,
        fmt: str = "gjf",
        mode: str = "x",
        route: str = "# hf 3-21g",
        link0: Optional[dict] = None,
        comment: str = "No information provided.",
        post_spec: str = "",
    ):
        """Saves conformers to disk as job files for quantum chemistry software
        in given file format.

        Currently only "gjf" format is provided, used by Gaussian software.
        Files produced are written to `Tesliper.output_dir` directory with filenames
        automatically generated using conformers' identifiers.

        Parameters
        ----------
        fmt : str
            File format of output files, defaults to "gjf".
        mode : str
            Specifies how writing to file should be handled. May be one of:
            "a" (append to existing file), "x" (only write if file doesn't exist yet),
            "w" (overwrite file if it already exists). Defaults to "x".
        route : str
            List of space-separated keywords specifying calculations directives
            for Gaussian software.
        link0 : dict
            Dictionary with link0 commands, where key is command's name and value is
            str with parameters. For any non-parametric link0 command value is not
            important (may be `None`), key's presence is enough to record, that it was
            requested.
        comment : str
            Contents of title section, i.e. a comment about the calculations.
        post_spec : str
            Anything that should be placed after conformers geometry specification.
            Will be writen to file as given.
        """
        wrt = wr.writer(
            fmt=fmt,
            destination=self.output_dir,
            mode=mode,
            link0=link0,
            route=route,
            comment=comment,
            post_spec=post_spec,
        )
        wrt.geometry(
            geometry=self["geometry"],
            multiplicity=self["multiplicity"],
            charge=self["charge"],
        )

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
