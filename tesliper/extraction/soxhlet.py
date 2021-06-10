# IMPORTS
import logging as lgg
from pathlib import Path
import re
from typing import Union, Tuple, Generator, Optional, List, Iterable, Set
import numpy as np

from . import gaussian_parser
from . import spectra_parser


# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
# TODO: Consider integration with gauopen interface: http://gaussian.com/interfacing/
class Soxhlet:
    """A tool for data extraction from files in specific directory. Typical
    use:

    >>> s = Soxhlet('absolute/path_to/working/directory')
    >>> data = s.extract()

    Attributes
    ----------
    path: str
        Path of directory bounded to Soxhlet instance.
    files
    output_files
    bar_files
    """

    def __init__(self, path=None, wanted_files=None, extension=None):
        """Initialization of Soxhlet object.

        Parameters
        ----------
        path: str or pathlib.Path
            String representing absolute path to directory containing files,
            which will be the subject of data extraction.
        wanted_files: list of str or pathlib.Path objects, optional
            List of files, that should be loaded for further extraction. If
            omitted, all output files present in directory will be processed.
        extension: str
            A string representing file extension of output files, that should be
            parsed. If omitted, Soxhlet will try to resolve it based on
            contents of directory given in `path` parameter.

        Raises
        ------
        FileNotFoundError
            If path passed as argument to constructor doesn't exist.
        """
        self.path = path
        self.wanted_files = wanted_files
        self.extension = extension
        self.parser = gaussian_parser.GaussianParser()
        self.spectra_parser = spectra_parser.SpectraParser()

    @property
    def path(self) -> Path:
        return self._path

    @path.setter
    def path(self, value: Union[str, Path]):
        value = Path() if value is None else Path(value)
        if not value.is_dir():
            raise FileNotFoundError(f"Path not found: {value}")
        self._path = value.resolve()

    @property
    def all_files(self):
        """List of all files present in directory bounded to Soxhlet instance."""
        return [v for v in self.path.iterdir() if v.is_file()]

    @property
    def files(self):
        """List of all wanted files available in given directory. If wanted_files
        is not specified, evaluates to all files in said directory."""
        wanted_empty = not self.wanted_files
        return [
            f for f in self.all_files if wanted_empty or f.stem in self.wanted_files
        ]

    @property
    def wanted_files(self) -> Optional[Set[str]]:
        """Set of files that are desired for data extraction, stored as filenames
        without an extension. Any iterable of strings or Path objects is transformed
        to this form.

        >>> s = Soxhlet()
        >>> s.wanted_files = [Path("./dir/file_one.out"), Path("./dir/file_two.out")]
        >>> s.wanted_files
        {"file_one", "file_two"}

        May also be set to `None` or other "falsy" value, in such case it is ignored.
        """
        return self._wanted_files

    @wanted_files.setter
    def wanted_files(self, files: Optional[Iterable[Union[str, Path]]]):
        self._wanted_files = None if not files else {Path(f).stem for f in files}

    @property
    def output_files(self) -> List[Path]:
        """List of (sorted by file name) gaussian output files from files
        list associated with Soxhlet instance.
        """
        try:
            ext = self.extension if self.extension else self.guess_extension()
        except (ValueError, FileNotFoundError) as error:
            logger.warning(f"{error} Returning empty list.")
            return []
        try:
            gf = sorted(self.filter_files(ext))
        except ValueError:
            gf = []
        return gf

    def filter_files(self, ext: Optional[str] = None) -> List[Path]:
        """Filters files from filenames list.

        Function filters file names in list associated with Soxhlet object
        instance. It returns list of file names ending with provided ext
        string, representing file extension and starting with any of filenames
        associated with instance as wanted_files if those were provided.

        Parameters
        ----------
        ext : str
            Strings representing file extension.

        Returns
        -------
        list
            List of filtered filenames as strings.

        Raises
        ------
        ValueError
            If parameter `ext` is not given and attribute `extension` in None.
        """
        ext = ext if ext is not None else self.extension
        if ext is None:
            raise ValueError(
                "Parameter `ext` must be given if attribute `extension` is None."
            )
        filtered = [f for f in self.files if f.name.endswith(ext)]
        return filtered

    def guess_extension(self) -> str:
        """Checks list of file extensions in list of file names.

        Function checks for .log and .out files in passed list of file names.
        If both are present, it raises TypeError exception.
        If either is present, it raises ValueError exception.
        It returns string representing file extension present in files list.

        Returns
        -------
        str
            '.log' if *.log files are present in filenames list or '.out' if
            *.out files are present in filenames list.

        Raises
        ------
        ValueError
            If both *.log and *.out files are present in list of filenames.
        FileNotFoundError
            If neither *.log nor *.out files are present in list of filenames.

        TO DO
        -----
        add support for other extensions when new parsers implemented
        """
        logs, outs = (
            any(f.name.endswith(ext) for f in self.all_files)
            for ext in (".log", ".out")
        )
        if outs and logs:
            raise ValueError(".log and .out files mixed in directory.")
        elif not outs and not logs:
            raise FileNotFoundError("Didn't found any .log or .out files.")
        else:
            return ".log" if logs else ".out"

    def extract_iter(self) -> Generator[Tuple[str, dict], None, None]:
        """Extracts data from gaussian files associated with Soxhlet instance.
        Implemented as generator.

        Yields
        ------
        tuple
            Two item tuple with name of parsed file as first and extracted
            data as second item, for each file associated with Soxhlet instance.
        """
        for file in self.output_files:
            logger.debug(f"Starting extraction from file: {file}")
            with file.open() as handle:
                data = self.parser.parse(handle)
            logger.debug("file done.\n")
            yield file.name, data

    def extract(self) -> dict:
        """Extracts data from gaussian files associated with Soxhlet instance.

        Returns
        ------
        dict of dicts
            dictionary of extracted data, with name of parsed file as key and
            data as value, for each file associated with Soxhlet instance.
        """
        return {f: d for f, d in self.extract_iter()}

    def load_settings(self) -> dict:
        """Parses Setup.txt file associated with object and returns dict with
        extracted values. Prefers Setup.txt file over *Setup.txt files.
        Settings values should be placed one for line in this order: hwhm, start, stop,
        step, fitting. Anything beside a number and "lorentzian" or "gaussian" word
        is ignored.

        Returns
        -------
        dict
            Dictionary with extracted settings data.

        Raises
        ------
        FileNotFoundError
            If no or multiple setup.txt files found.

        """
        # TODO: make it use keys instead of order
        # TODO?: implement ConfigParser-based solution
        settings_file = self.path / "Setup.txt"
        if not settings_file.is_file():
            fls = [file for file in self.all_files if file.name.endswith("Setup.txt")]
            if len(fls) != 1:
                raise FileNotFoundError("No or multiple setup files in directory.")
            else:
                settings_file = self.path / fls[0]
        with settings_file.open() as f:
            text = f.read()
        regex = r"(-?\d+.?d\*|lorentzian|gaussian)"
        sett = re.findall(regex, text.lower())
        sett = {k: v for k, v in zip(("hwhm start stop step fitting".split(" "), sett))}
        f.close()
        return sett

    def load_spectrum(self, filename: Union[str, Path]) -> np.ndarray:
        # TO DO: add support for .spc and .csv files
        # TO DO: add docstring
        appended = self.path / filename
        if appended.is_file():
            path = appended
        elif Path(filename).is_file():
            path = Path(filename)
        else:
            raise FileNotFoundError(f"Cannot find such file: '{filename}'.")
        spectrum = self.spectra_parser.parse(path)
        return spectrum
