"""A tool for batch parsing files from specified directory."""
import logging as lgg
from pathlib import Path
from typing import Any, Generator, Iterable, List, Optional, Set, Tuple, Union

from .parser_base import _PARSERS

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
# TODO: Consider integration with gauopen interface: http://gaussian.com/interfacing/
# TODO: supplement class docstring
class Soxhlet:
    """A tool for data extraction from files in specific directory. Typical use:

    >>> s = Soxhlet('absolute/path_to/working/directory')
    >>> data = s.extract()
    """

    def __init__(
        self,
        path: Optional[Union[str, Path]] = None,
        purpose: str = "gaussian",
        wanted_files: Optional[Iterable[Union[str, Path]]] = None,
        extension: Optional[str] = None,
        recursive: bool = False,
    ):
        """
        Parameters
        ----------
        path : str or pathlib.Path
            String representing absolute path to directory containing files,
            which will be the subject of data extraction.
        purpose : str
            Determines which from registered parsers should be used for extraction.
            *purpose*\\s supported out-of-the-box are "gaussian", "spectra", and
            "parameters".
        wanted_files : list of str or pathlib.Path objects, optional
            List of files, that should be loaded for further extraction. If
            omitted, all output files present in directory will be processed.
        extension : str, optional
            A string representing file extension of output files, that should be
            parsed. If omitted, Soxhlet will try to resolve it based on
            contents of directory given in *path* parameter.
        recursive : bool
            If True, given *path* will be searched recursively, extracting data from
            subdirectories, otherwise subdirectories are ignored and only files
            placed directly in *path* will be parsed.

        Raises
        ------
        FileNotFoundError
            If path passed as argument to constructor doesn't exist
            or is not a directory.
        ValueError
            If no parser is registered for given *purpose*.
        """
        self.path = path
        self.wanted_files = wanted_files
        self.extension = extension
        self.recursive = recursive
        try:
            self.parser = _PARSERS[purpose]()
        except KeyError:
            raise ValueError(f"Unknown purpose: {purpose}.")

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
        """List of all files present in directory bounded to Soxhlet instance.
        If its *recursive* attribute is ``True``, also files from subdirectories
        are included."""
        iterable = self.path.iterdir() if not self.recursive else self.path.rglob("*")
        return [v for v in iterable if v.is_file()]

    @property
    def files(self):
        """List of all wanted files available in given directory. If wanted_files
        is not specified, evaluates to all files in said directory. If Soxhlet
        object's *recursive* attribute is ``True``, also files from subdirectories
        are included."""
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

        May also be set to ``None`` or other "falsy" value, in such case it is ignored.
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

        Filters file names in list associated with :class:`.Soxhlet` object
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
            If parameter *ext* is not given and attribute :attr:`.extension` in
            ``None``.
        """
        ext = ext if ext is not None else self.extension
        if ext is None:
            raise ValueError(
                "Parameter *ext* must be given if attribute *extension* is *None*."
            )
        filtered = [f for f in self.files if f.name.endswith(ext)]
        return filtered

    def guess_extension(self) -> str:
        """Tries to figure out which extension should be assumed.

        Looks for files, which names end with one of the extensions defined by currently
        used parser. Returns extension that matches as the only one. Raises an exception
        if extension cannot be easily guessed.

        Returns
        -------
        str
            The extension of files that are present in filenames list, which current
            parser can parse.

        Raises
        ------
        ValueError
            If more than one type of files declared by a current parser as possibly
            compatible is present in list of filenames.
        FileNotFoundError
            If none of files declared by a current parser as possibly compatible are
            present in list of filenames.
        TypeError
            If current parser does not declare any compatible file extensions.
        """
        if not self.parser.extensions:
            raise TypeError(
                f"Cannot guess extension: parser {type(self.parser).__name__} "
                "does not define any compatible extensions."
            )
        available = tuple(
            ext
            for ext in self.parser.extensions
            if any(f.name.endswith(ext) for f in self.all_files)
        )
        if len(available) > 1:
            raise ValueError(
                f"{', '.join(f'.{a}' for a in available)} files mixed in directory."
            )
        elif not available:
            raise FileNotFoundError(
                "Didn't found any of "
                f"{', '.join(f'.{e}' for e in self.parser.extensions)} files."
            )
        else:
            return available[0]

    def extract_iter(self) -> Generator[Tuple[str, dict], None, None]:
        """Extracts data from files associated with :class:`.Soxhlet` instance (*via*
        :attr:`.path` and :attr:`.wanted_files` attributes), using a current parser
        (determined by a *purpose* provided on :class:`.Soxhlet`'s instantiation).
        Implemented as generator. If Soxhlet instance's :attr:`.recursive` attribute is
        ``True``, also files from subdirectories are parsed.

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
            yield file.stem, data

    def extract(self) -> dict:
        """Extracts data from files associated with :class:`.Soxhlet` instance (*via*
        :attr:`.path` and :attr:`.wanted_files` attributes), using a current parser
        (determined by a *purpose* provided on :class:`.Soxhlet`'s instantiation). If
        :attr:`.Soxhlet.recursive` attribute is ``True``, also files from subdirectories
        are parsed.

        Returns
        ------
        dict of dicts
            dictionary of extracted data, with name of parsed file as key and
            data as value, for each file associated with Soxhlet instance.
        """
        return {f: d for f, d in self.extract_iter()}

    def parse_one(self, source: Union[str, Path]) -> Any:
        """Parse one file using current parser (determined by a *purpose* provided on
        :class:`.Soxhlet`'s instantiation) and return extracted data.

        Parameters
        ----------
        source : str or Path
            Path or Path-like object to a file. May be given as an absolute path or
            relative to the :attr:`.Soxhlet.path`.

        Returns
        -------
        any
            Data in a format that current parser provides.

        Raises
        ------
        FileNotFoundError
            If no *source* file is found.
        """
        appended = self.path / source
        if appended.is_file():
            path = appended
        elif Path(source).is_file():
            path = Path(source)
        else:
            raise FileNotFoundError(f"Cannot find such file: '{source}'.")
        return self.parser.parse(path)
