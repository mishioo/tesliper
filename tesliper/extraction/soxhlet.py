# IMPORTS
import csv
import os
import logging as lgg
import multiprocessing as mp
import threading as th
import queue

from collections import defaultdict
from io import StringIO

from . import gaussian_parser
from . import spectra_parser

# TO DO
# correct load_bars, load_popul, load_spectra, load_settings methods


# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# FUNCTIONS
def _process_file(filename, file_location, parser, lock):
    """A worker for data extraction. This functionality is delegated
    to this function outside of `Soxhlet` class for easier implementation
    of parallel processing via `multiprocessing` module.

    Parameters
    ----------
    filename : str
        Name of the file.
    file_location : str
        Location of files that should be parsed.
    parser : object
        Object used for parsing, should implement `parse` method.
    lock : multiprocessing.Lock

    Returns
    -------
    tuple
        Two item tuple with name of parsed file as first and extracted
        data as second item, for each file associated with Soxhlet instance.
    """
    lock.acquire()
    strio = None
    logger.debug(f"Starting file {filename} extraction in process {os.getpid()}")
    try:
        with open(os.path.join(file_location, filename)) as handle:
            strio = StringIO(handle.read())
    except FileNotFoundError:
        logger.warning(f"File {filename} not found.")
    finally:
        lock.release()
    strio = strio if strio is not None else StringIO("")
    data = parser.parse(strio)
    logger.debug(f"File {filename} done.")
    return filename, data


def _error_callback(error):
    logger.error(f"One of sub-processes failed. {type(error).__name__}: {error}.")
    raise error


# CLASSES
class Soxhlet:
    """A tool for data extraction from files in specific directory. Typical
    use:

    >>> s = Soxhlet('absolute/path_to/working/directory')
    >>> data = s.extract()

    Attributes
    ----------
    path: str
        Path of directory bounded to Soxhlet instance.
    files: list
        List of files present in directory bounded to Soxhlet instance.
    output_files
    bar_files

    TO DO
    -----
    correct load_bars, load_popul, load_spectrs, load_settings, from_dict methods
    """

    WORKERS = mp.cpu_count()
    TIMEOUT = 1

    def __init__(self, path=None, wanted_files=None, extension=None):
        """Initialization of Soxhlet object.

        Parameters
        ----------
        path: str
            String representing absolute path to directory containing files,
            which will be the subject of data extraction.
        wanted_files: list, optional
            List of files, that should be loaded for further extraction. If
            omitted, all files present in directory will be taken.
        extension: str
            String representing file extension of output files, that are to be
            parsed. If omitted, Soxhlet will try to resolve it based on
            contents of directory pointed by path.

        Raises
        ------
        FileNotFoundError
            If path passed as argument to constructor doesn't exist.
        """
        self.path = path
        self.files = os.listdir(path)
        self.wanted_files = wanted_files
        self.extension = extension
        self.parser = gaussian_parser.GaussianParser()
        self.spectra_parser = spectra_parser.SpectraParser()
        self._queue = mp.Queue()
        self._pool = None

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        if value is None:
            self._path = os.getcwd()
        elif not os.path.isdir(value):
            raise FileNotFoundError(f"Path not found: {value}")
        else:
            self.files = os.listdir(value)
            self._path = value

    @property
    def output_files(self):
        """List of (sorted by file name) gaussian output files from files
        list associated with Soxhlet instance.
        """
        try:
            ext = (
                self.extension if self.extension is not None else self.guess_extension()
            )
            gf = sorted(self.filter_files(ext))
        except ValueError:
            gf = []
        return gf

    @property
    def bar_files(self):
        """List of (sorted by file name) *.bar files from files list
        associated with Soxhlet instance.
        """
        try:
            ext = ".bar"
            bar = sorted(self.filter_files(ext))
        except ValueError:
            bar = []
        return bar

    def filter_files(self, ext=None):
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
        files = self.wanted_files if self.wanted_files else self.files
        try:
            filtered = [f for f in files if f.endswith(ext)]
        except TypeError as error:
            raise ValueError(
                "Parameter `ext` must be given if attribute `extension` is None."
            ) from error
        return filtered

    def guess_extension(self):
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
        TypeError
            If neither *.log nor *.out files are present in list of filenames.

        TO DO
        -----
        add support for other extensions when new parsers implemented
        """
        files = self.wanted_files if self.wanted_files else self.files
        logs, outs = (any(f.endswith(ext) for f in files) for ext in (".log", ".out"))
        if outs and logs:
            raise ValueError(".log and .out files mixed in directory.")
        elif not outs and not logs:
            raise TypeError("Didn't found any .log or .out files.")
        else:
            return ".log" if logs else ".out"

    def mp_extract_iter(self):
        """Extracts data from gaussian files associated with Soxhlet instance
        in parallel manner. Implemented as generator.

        This method uses `multiprocessing` module to process multiple files at once,
        allowing for faster execution on machines with multi-core processors. Maximum
        number of sub-processes spawned is defined by `Soxhlet.WORKERS` and by default
        is equal to `multiprocessing.cpu_count()`.

        Notes
        -----
        When `Soxhlet.WORKERS` is set to 1 (one), files are processed sequentially
        without spawning new processes.

        Extracted data is awaited for maximum of `Soxhlet.TIMEOUT` seconds (5 seconds
        by default). If parsed files are very big, this time might need to be extended.

        `Soxhlet.WORKERS` and `Soxhlet.TIMEOUT` are accessed as an instance attributes,
        so they may be changed locally - only for specific instance of Soxhlet object -
        by setting their values on this instance (e.g. `soxhlet_instance.WORKERS`).

        When using this method in your code, please make sure to follow programming
        guidelines for `multiprocessing` module. Especially make sure to include
        `if __name__ == '__main__':` ward in your main script.

        Yields
        ------
        tuple
            Two item tuple with name of parsed file as first and extracted
            data as second item, for each file associated with Soxhlet instance.

        Raises
        ------
        ValueError:
            If `Soxhlet.WORKERS` is set to less than 1 (one) or is not a whole number.
        """
        # TODO: optimise this for real-life examples;
        #       currently doesn't produce reliable effects
        if self.WORKERS < 1:
            raise ValueError("Number of `Soxhlet.WORKERS` must be greater than zero.")
        elif self.WORKERS != int(self.WORKERS):
            raise ValueError("Number of `Soxhlet.WORKERS` must be a whole number.")
        elif self.WORKERS == 1:
            yield from self.extract_iter()
        else:
            logger.debug(
                f"Starting parallel processing. Main process pid: {os.getpid()}"
            )
            manager = mp.Manager()
            lock = manager.Lock()
            self._pool = pool = mp.Pool(self.WORKERS)
            for file in self.output_files:
                logger.debug(f"Scheduling file '{file}' extraction.")
                pool.apply_async(
                    _process_file,
                    (file, self.path, self.parser, lock),
                    callback=self._queue.put,
                    error_callback=_error_callback,
                )
            pool.close()
            for _ in self.output_files:
                try:
                    values = self._queue.get(timeout=self.TIMEOUT)
                    logger.debug(f"Values from file {values[0]} retrieved.")
                    yield values
                except queue.Empty:
                    logger.warning(
                        f"Timeout = {self.TIMEOUT}s for data extraction reached. "
                        f"Extend maximum waiting time by modifying `Soxhlet.TIMEOUT` "
                        f"or run extraction in non-parallel manner by setting "
                        f"`Soxlet.WORKERS` to 1 (one)."
                    )
                    break
            pool.join()
            manager.shutdown()

    def extract_iter(self):
        """Extracts data from gaussian files associated with Soxhlet instance.
        Implemented as generator.

        Yields
        ------
        tuple
            Two item tuple with name of parsed file as first and extracted
            data as second item, for each file associated with Soxhlet instance.
        """
        logger.debug("Starting sequential processing.")
        for file in self.output_files:
            logger.debug(f"Starting file {file} extraction.")
            with open(os.path.join(self.path, file)) as handle:
                data = self.parser.parse(handle)
            logger.debug(f"File {file} done.")
            yield file, data

    def extract(self):
        """Extracts data from gaussian files associated with Soxhlet instance.
        This is essentially just a wrapper over `extract_iter`, that returns the whole
        set of data at once.

        Returns
        ------
        dict of dicts
            dictionary of extracted data, with name of parsed file as key and
            data as value, for each file associated with Soxhlet instance.
        """
        return {f: d for f, d in self.extract_iter()}

    def load_bars(self, spectra_type=None):
        """Parses *.bar files associated with object and loads spectral data
        previously extracted from gaussian output files.

        Parameters
        ----------
        spectra_type : str, optional
            Type of spectra which is to extract; valid values are
            'vibra', 'electr' or '' (if spectrum is not present
            in gaussian output files); if omitted, spectra_type
            associated with object is used.

        Returns
        -------
        dict
            Dictionary with extracted spectral data.

        TO DO
        -----
        Make sure Transitions not needed.
        Rewrite to match current keys handling
        remove self.spectra_type dependence
        """
        spectra_type = spectra_type if spectra_type else self.spectra_type
        no = len(self.bar_files)
        # Create empty dict with list of empty lists as default value.
        output = defaultdict(lambda: [[] for _ in range(no)])
        keys = (
            "freq dip rot vemang".split(" ")
            if spectra_type == "vibra"
            else "wave vosc srot losc lrot energy eemang".split(" ")
        )
        for num, bar in enumerate(self.bar_files):
            with open(os.path.join(self.path, bar), newline="") as handle:
                header = handle.readline()
                del header
                col_names = handle.readline()
                if "Transition" in col_names and "eemang" in keys:
                    keys = keys[:-1]
                reader = csv.reader(handle, delimiter="\t")
                for row in reader:
                    # For each row in *.bar file copy value to corresponding
                    # position in prepared output dict
                    for k, v in zip(keys, row):
                        # output[value type][file position in sorted list]
                        output[k][num].append(float(v))
        return self.from_dict(output)

    def load_popul(self):
        """Parses BoltzmanDistribution.txt file associated with object and
        loads conformers' energies previously extracted from gaussian output
        files and calculated populations.

        Returns
        -------
        dict
            Dictionary with extracted data.
        """
        keys = (
            "filenames scfp entp gibp scfd entd gibd scf ent gib imag "
            "stoich".split(" ")
        )
        output = defaultdict(list)
        with open(os.path.join(self.path, "BoltzmanDistribution.txt")) as blz:
            header1 = blz.readline()
            header2 = blz.readline()
            del header1, header2
            for row in blz.readlines():
                for k, v in zip(keys, self.extractor["popul"](row)):
                    try:
                        v = float(v)
                    except ValueError:
                        if "%" in v:
                            v = float(v[:-1]) / 100
                    output[k].append(v)
        return self.from_dict(output)

    def load_settings(self):
        """Parses Setup.txt file associated with object and returns dict with
        extracted values. Prefers Setup.txt file over *Setup.txt files.

        Returns
        -------
        dict
            Dictionary eith extracted settings data.

        Raises
        ------
        FileNotFoundError
            If no or multiple setup.txt files found.
        """
        try:
            f = open("Setup.txt", "r")
        except FileNotFoundError:
            fls = [file.endswith("Setup.txt") for file in self.files]
            if len(fls) != 1:
                raise FileNotFoundError("No or multiple setup files in directory.")
            else:
                f = open(fls[0], "r")
        sett = self.extractor["settings"](f)
        f.close()
        return sett

    def load_spectrum(self, filename):
        # TO DO: add support for .spc and .csv files
        # TO DO: add docstring
        appended = os.path.join(self.path, filename)
        if os.path.isfile(appended):
            path = appended
        elif os.path.isfile(filename):
            path = filename
        else:
            raise FileNotFoundError(f"Cannot find such file: '{filename}'.")
        spectrum = self.spectra_parser.parse(path)
        return spectrum
