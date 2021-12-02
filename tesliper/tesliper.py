"""`tesliper` is a package for batch processing of Gaussian output files, focusing
on extraction and processing of data related to simulation of optical spectra.

Simulation of optical spectra of organic compounds becomes one of the routine tasks
for chemical analysts -- it is a necessary step in one of the increasingly popular
methods of establishing compound's absolute configuration. However, the process
of obtaining a simulated spectrum may be cumbersome, as it usually involves analysing
a large number of potentially stable conformers of the studied molecule.
`tesliper` was created to aid in such work.

Software offers a Python API and a graphical user interface (GUI), allowing for your
preferred style of interaction with the computer: visual or textual. It was designed
for working with multiple conformers of a compound, represented by a number of files
obtained from Gaussian quantum-chemical computations software. It allows to easily
exclude conformers that are not suitable for further analysis: erroneous,
not optimized, of higher energy or lower contribution than a user-given threshold.
It also implements an RMSD sieve, enabling one to filter out similar structures.
Finally, it lets you calculate theoretical IR, VCD, UV, ECD, Raman, and ROA spectra
for all conformers or as a population-weighted average and export obtained spectral
data in one of supported file formats: .txt, .csv, or .xlsx.

There are some conventions that are important to note:
- `tesliper` stores multiple data entries of various types for each conformer.
To prevent confusion with Python's data ``type`` and with data itself,
`tesliper` refers to specific kinds of data as "genres". Genres in code are represented
by specific strings, used as identifiers. To learn about data genres
known to `tesliper`, see documentation for `GaussianParser`, which lists them.
- `tesliper` identifies conformers using stem of an extracted file (i.e. its filename
without extension). When files with identical names are extracted in course of
subsequent `Tesliper.extract` calls or in recursive extraction using
``Tesliper.extract(recursive=True)``, they are treated as data for one conformer.
This enables to join data from subsequent calculations steps, e.g. geometry
optimization, vibrational spectra simulation, and electronic spectra simulation.
Please note that if specific data genre is available from more than one calculation
job, only recently extracted values will be stored.
- `tesliper` was designed to deal with multiple conformers of single molecule and may
not work properly when used to process data concerning different molecules (i.e.
having different number of atoms, different number of degrees of freedom, etc.).
If you want to use it for such purpose anyway, you may set
`Tesliper.conformers.allow_data_inconsistency` to ``True``. `tesliper` will then stop
complaining and try to do its best.
"""

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
__version__ = "0.8.1"

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
    """This class is a main access point to `tesliper`'s functionality. It allows you
    to extract data from specified files, provides a proxy to the trimming
    functionality, gives access to data in form of specialized arrays, enables you
    to calculate and average desired spectra, and provides an easy way to export data.

    Most basic use might look like this:
    >>> tslr = Tesliper()
    >>> tslr.extract()
    >>> tslr.calculate_spectra()
    >>> tslr.average_spectra()
    >>> tslr.export_averaged()
    This extracts data from files in the current working directory, calculates
    available spectra using standard parameters, averages them using available energy
    values, and exports to current working directory in .txt format.

    You can customize this process by specifying call parameters for used methods
    and modifying `Tesliper`'s configuration attributes:
    - to change source directory
    or location of exported files instantiate `Tesliper` object with `input_dir`
    and `output_dir` parameters specified, respectively. You can also set appropriate
    attributes on the instance directly.
    - To extract only selected files in `input_dir` use `wanted_files` init parameter.
    It should be given an iterable of filenames you want to parse. Again, you can
    also directly set an identically named attribute.
    - To change parameters used for calculation of spectra, modify appropriate entries
    of `parameters` attribute.
    - Use other export methods to export more data and specify `fmt` parameter
    in method's call to export to other file formats.

    >>> tslr = Tesliper(input_dir="./myjob/optimization/", output_dir="./myjob/output/")
    >>> tslr.wanted_files = ["one", "two", "three"]  # only files with this names
    >>> tslr.extract()  # use tslr.input_dir as source
    >>> tslr.extract(path="./myjob/vcd_sim/")  # use other input_dir
    >>> tslr.conformers.trim_not_optimized()  # trimming out unwanted conformers
    >>> tslr.parameters["vcd"].update({"start": 500, "stop": 2500, "width": 2})
    >>> tslr.calculate_spectra(genres=["vcd"])  # we want only VCD spectrum
    >>> tslr.average_spectra()
    >>> tslr.export_averaged(mode="w")  # overwrite previously exported files
    >>> tslr.export_activities(fmt="csv")  # save activities for analysis elsewhere
    >>> tslr.output_dir = "./myjob/ecd_sim/"
    >>> tslr.export_job_file(  # prepare files for next step of calculations
    ...     route="# td=(singlets,nstates=80) B3LYP/Def2TZVP"
    ... )

    When modifying `Tesliper.parameters` be cerfull to not delete any of the parameters.
    If you need to revert to standard parameters values, you can find them in
    `Tesliper.standard_parameters`.
    >>> tslr.parameters["ir"] = {
    ...     "start": 500, "stop": 2500, "width": 2
    ... }  # this will cause problems!
    >>> tslr.parameters = tslr.standard_parameters  # revert to default values

    Trimming functionality, used in previous example in
    `tslr.conformers.trim_not_optimized()`, allows you to filter out conformers that
    shouldn't be used in further processing and analysis. You can trim off conformers
    that were not optimized, contain imaginary frequencies, or have other unwanted
    qualities. Conformers with similar geometry may be discarded using an RMSD sieve.
    For more information about trimming, please refer to the documentation
    of `Conformers` class.

    For more exploratory analysis, `Tesliper` provides an easy way to access desired
    data as an instance of specialized `DataArray` class. Those objects implement
    a number of convenience methods for dealing with specific data genres. A more
    detailed information on `DataArray`s see `glassware.arrays` module documentation.
    To get data in this form use `array = tslr["genre"]` were `"genre"` is string with
    the name of desired data genre. For more control over instantiation of `DataArray`s
    you may use `Tesliper.conformers.arrayed` factory method.
    >>> energies = tslr["gib"]
    >>> energies.values
    array([-304.17061762, -304.17232455, -304.17186735])
    >>> energies.populations
    array([0.0921304 , 0.56174031, 0.3461293 ])
    >>> energies.full_name
    'Thermal Free Energy'

    Please note, that if some conformers do not provide values for a specific data
    genre, it will be ignored when retriving data for `DataArray` instantiation,
    regardles if it were trimmed off or not.
    >>> tslr = Tesliper()
    >>> tslr.conformers.update([
    >>> ...     ('one', {'gib': -304.17061762}),
    >>> ...     ('two', {'gib': -304.17232455}),
    >>> ...     ('three', {'gib': -304.17186735}),
    >>> ...     ('four', {})
    >>> ... ])
    >>> tslr.conformers.kept
    [True, True, True, True]
    >>> energies = tslr["gib"]
    >>> energies.filenames
    array(['one', 'two', 'three'], dtype='<U5')

    Parameters
    ----------
    input_dir : str or path-like object, optional
        Path to directory containing files for extraction, defaults to current
        working directory.
    output_dir : str or path-like object, optional
        Path to directory for output files, defaults to current working directory.
    wanted_files : list of str or list of Path, optional
        List of files or filenames representing wanted files. If not given, all
        files are considered wanted. File extensions are ignored.

    Attributes
    ----------
    conformers : Conformers
        Container for data extracted from Gaussian output files. It provides trimming
        functionality, enabling to filter out conformers of unwanted qualities.
    spectra : dict of str: Spectra
        Spectra calculated so far, using `Tesliper.calculate_spectra` method.
        Possible keys are spectra genres: "ir", "vcd", "uv", "ecd", "raman", and "roa".
        Values are `Spectra` instances with lastly calculated spetra of this genre.
    averaged : dict of str: (dict of str: float or callable)
        Spectra averaged using available energies genres, calculated with last call
        to `Tesliper.average_spectra` method. Keys are tuples of two strings: averaged
        spectra genre and energies genre used for averaging.
    parameters : dict of str: (dict of str: float or callable)
        Parameters for calculation of each type of spectra: "vibrational", "electronic",
        and "scattering". Avaliable parameters are:
            "start" - float ot int, the beginning of the spectral range,
            "stop" - float ot int, the end of the spectral range,
            "step" - float ot int, step of the abscissa,
            "width" - float ot int, width of the peak,
            "fitting" - callable, function used to simulate peaks as curves, preferably
                        one of `datawork.gaussian` or `datawork.lorentzian`.
        "start", "stop", and "step" expect its values to by in cm^-1 units for
        vibrational and scattering spectra, and nm units for electronic spectra.
        "width" expects its value to be in cm^-1 units for vibrational and scattering
        spectra, and eV units for electronic spectra.
    standard_parameters
    input_dir
    output_dir
    wanted_files
    energies
    activities
    """

    # TODO?: add proxy for trimming ?
    # TODO?: separate spectra types ?
    # TODO?: make it inherit mapping ?
    _standard_parameters = {
        "ir": {
            "width": 6,
            "start": 800,
            "stop": 2900,
            "step": 2,
            "fitting": dw.lorentzian,
        },
        "uv": {
            "width": 0.35,
            "start": 150,
            "stop": 800,
            "step": 1,
            "fitting": dw.gaussian,
        },
    }
    _standard_parameters["vcd"] = _standard_parameters["ir"].copy()
    _standard_parameters["raman"] = _standard_parameters["ir"].copy()
    _standard_parameters["roa"] = _standard_parameters["ir"].copy()
    _standard_parameters["ecd"] = _standard_parameters["uv"].copy()
    # TODO: introduce more sophisticated parameters proxy that enables using
    #       same or different params for genres of same type (e.g. "vibrational")

    def __init__(
        self,
        input_dir: str = ".",
        output_dir: str = ".",
        wanted_files: Optional[Iterable[Union[str, Path]]] = None,
    ):
        self.conformers = gw.Conformers()
        self.wanted_files = wanted_files
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.spectra = dict()
        self.averaged = dict()
        self.parameters = self.standard_parameters

    def __getitem__(self, item: str) -> gw.conformers.AnyArray:
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
        """Default parameters for spectra calculation for each spectra genre
        (ir, vcd, uv, ecd, raman, roa). This returns a dictionary,
        but in fact it is a convenience, read-only attribute,
        modifying it will have no persisting effect.
        """
        return {key: params.copy() for key, params in self._standard_parameters.items()}

    def update(self, other: Optional[Dict[str, dict]] = None, **kwargs):
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
        extension: Optional[str] = None,
        recursive: bool = False,
    ) -> Generator[Tuple[str, dict], None, None]:
        """Extracts data from chosen Gaussian output files present in given directory
        and yields data for each conformer found.

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
            If `Tesliper.wanted_files` is also `None`, all found Gaussian output files
            will be parsed.
        extension : str, optional
            Only files with given extension will be parsed. If omitted, Tesliper will
            try to guess the extension from contents of input directory.
        recursive : bool
            If `True`, also subdirectories are searched for files to parse, otherwise
            subdirectories are ignored. Defaults to `False`.

        Yields
        ------
        tuple
            Two item tuple with name of parsed file as first and extracted
            data as second item, for each Gaussian output file parsed.
        """
        soxhlet = ex.Soxhlet(
            path or self.input_dir,
            wanted_files or self.wanted_files,
            extension=extension,
            recursive=recursive,
        )
        for file, data in soxhlet.extract_iter():
            self.update(((file, data),))
            yield file, data

    def extract(
        self,
        path: Optional[Union[str, Path]] = None,
        wanted_files: Optional[Iterable[str]] = None,
        extension: Optional[str] = None,
        recursive: bool = False,
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
        extension : str, optional
            Only files with given extension will be parsed. If omitted, Tesliper will
            try to guess the extension from contents of input directory.
        recursive : bool
            If `True`, also subdirectories are searched for files to parse, otherwise
            subdirectories are ignored. Defaults to `False`.
        """
        for f, d in self.extract_iterate(path, wanted_files, extension, recursive):
            _ = f, d

    def load_parameters(
        self,
        path: Optional[Union[str, Path]] = None,
        spectra_genre: Optional[str] = None,
    ) -> dict:
        """Load calculation parameters from a file.

        Parameters
        ----------
        path : str or pathlib.Path, optional
            Path to the file with desired parameters specification. If omitted,
            Tesliper will try to find appropriate file in the default input directory.
        spectra_genre : str, optional
            Genre of spectra that loaded parameters concerns. If given, should be one of
            "ir", "vcd", "uv", "ecd", "raman", or "roa" -- parameters for that
            spectra will be updated with loaded values. Otherwise no update
            is done, only parsed data is returned.

        Returns
        -------
        dict
            Parameters read from the file.

        Notes
        -----
        For information on supported format of parameters configuration file, please
        refer to `ParametersParser` documentation.
        """
        soxhlet = ex.Soxhlet(path or self.input_dir)
        settings = soxhlet.load_parameters()
        if spectra_genre is not None:
            self.parameters[spectra_genre].update(settings)
        return settings

    def calculate_single_spectrum(
        self,
        genre: str,
        conformer: Union[str, int],
        start: Number = None,
        stop: Number = None,
        step: Number = None,
        width: Number = None,
        fitting: FittingFunctionType = None,
    ) -> gw.SingleSpectrum:
        """Calculates spectrum for requested conformer.

        'start', 'stop', 'step', 'width', and 'fitting' parameters, if given, will
        be used instead of the parameters stored in `Tesliper.parameters` attribute.
        'start', 'stop', and 'step' values will be interpreted as cm^-1 for vibrational
        or scattering spectra/activities and as nm for electronic ones.
        Similarly, 'width' will be interpreted as cm^-1 or eV. If not given, values
        stored in appropriate `Tesliper.parameters` are used.

        Parameters
        ----------
        genre : str
            Spectra genre (or related spectral activities genre) that should
            be calculated. If given spectral activity genre, this genre will be used
            to calculate spectra instead of the default activities.
        conformer : str or int
            Conformer, specified as it's identifier or it's index, for which
            spectrum should be calculated.
        start : int or float, optional
            Number representing start of spectral range.
        stop : int or float, optional
            Number representing end of spectral range.
        step : int or float, optional
            Number representing step of spectral range.
        width : int or float, optional
            Number representing half width of maximum peak height.
        fitting : function, optional
            Function, which takes spectral data, freqs, abscissa, width as parameters
            and returns numpy.array of calculated, non-corrected spectrum points.
            Basically one of `datawork.gaussian` or `datawork.lorentzian`.

        Returns
        -------
        SingleSpectrum
            Calculated spectrum.
        """
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
        sett = self.parameters[bar.spectra_name].copy()
        sett.update(sett_from_args)
        spc = bar.calculate_spectra(**sett)
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

    def calculate_spectra(self, genres: Iterable[str] = ()) -> Dict[str, gw.Spectra]:
        """Calculates spectra for each requested genre using parameters stored
        in `Tesliper.parameters` attribute.

        Parameters
        ----------
        genres : iterable of str
            List of spectra genres (or related spectral activities genres) that should
            be calculated. If given spectral activity genre, this genre will be used
            to calculate spectra instead of the default activities. If given empty
            sequence (default), all available spectra will be calculated using default
            activities.

        Returns
        -------
        dict of str: Spectra
            Dictionary with calculated spectra genres as keys and `Spectra` objects
            as values.
        """
        if not genres:
            # use default genres, ignoring empty
            bars = (v for v in self.activities.values() if v)
        else:
            # convert to spectra name if bar name passed
            default_act = dw.DEFAULT_ACTIVITIES
            genres = genres.split() if isinstance(genres, str) else genres
            query = [default_act[v] if v in default_act else v for v in genres]
            query_set = set(query)  # ensure no duplicates
            bars = (self[g] for g in query_set)
        output = {}
        for bar in bars:
            spectra = bar.calculate_spectra(**self.parameters[bar.spectra_name])
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
        """Average previously calculated spectra using populations derived from
        specified energies.

        Parameters
        ----------
        spectrum : str
            Genre of spectrum that should be averaged. This spectrum should be
            previously calculated using `Tesliper.calculate_spectra` method.
        energy : str
            Genre of energies, that should be used to calculate populations
            of conformers. These populations will be used as weights for averaging.

        Returns
        -------
        SingleSpectrum
            Calculated averaged spectrum.
        """
        # TODO: add fallback if spectra was nat calculated yet
        spectra = self.spectra[spectrum]
        with self.conformers.trimmed_to(spectra.filenames):
            en = self.conformers.arrayed(energy)
        output = spectra.average(en)
        return output

    def average_spectra(self) -> Dict[Tuple[str, str], gw.SingleSpectrum]:
        """For each previously calculated spectra (stored in `Tesliper.spectra`
         attribute) calculate it's average using population derived from each available
         energies genre.

        Returns
        -------
        dict
            Averaged spectrum for each previously calculated spectra and energies known
            as a dictionary. It's keys are tuples of genres used for averaging
            and values are `SingleSpectrum` instances (so this dictionary is of form
            {tuple("spectra", "energies"): `SingleSpectrum`}).
        """
        for genre, spectra in self.spectra.items():
            with self.conformers.trimmed_to(spectra.filenames):
                for energies in self.energies.values():
                    if energies:
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
        data = (self[g] for g in genres)
        data = [d for d in data if d]  # ignore empty DataArrays
        data += [b for b in bands if b]
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
        data = (self[g] for g in genres)
        data = [d for d in data if d]  # ignore empty DataArrays
        data += [b for b in bands if b]
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
            Will be written to file as given.
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
