# IMPORTS
import csv
import logging as lgg
from itertools import zip_longest
from pathlib import Path
from string import Template
from typing import Union, List, Optional, Dict

from ._writer import Writer, SerialWriter
from ..glassware.spectra import SingleSpectrum, Spectra
from ..glassware.arrays import Energies, FloatArray, Bars

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


class _CsvMixin:
    """Mixin class for csv writers.

    This class takes care of setting up format of produced csv files.
    It should be used as a first base class to ensure proper cooperation with other
    base classes. It will pass all given *args and **kwargs to the next base class
    in MRO.

    Parameters
    ----------
    dialect: str or csv.Dialect
        Name of a dialect or csv.Dialect object, which will be used by csv.writer.
    fmtparams: dict, optional
        Additional formatting parameters for csv.writer to use.
        For list of valid parameters consult csv.Dialect documentation.
    include_header: bool, optional
        Determines if file should contain a header with column names, True by default.
    """

    _known_fmt_params = {
        "delimiter",
        "doublequote",
        "escapechar",
        "lineterminator",
        "quotechar",
        "quoting",
        "skipinitialspace",
        "strict",
    }

    def __init__(
        self,
        *args,
        dialect: Union[str, csv.Dialect] = "excel",
        fmtparams: Optional[Dict] = None,
        include_header: bool = True,
        **kwargs,
    ):
        self.dialect = dialect
        self.fmtparams = fmtparams or {}
        self.include_header = include_header
        super().__init__(*args, **kwargs)

    @property
    def dialect(self):
        """Name of a dialect (as string) or csv.Dialect object,
        which will be used by csv.writer.
        """
        return self._dialect

    @dialect.setter
    def dialect(self, dialect: Union[str, csv.Dialect]):
        self._dialect = (
            dialect if isinstance(dialect, csv.Dialect) else csv.get_dialect(dialect)
        )

    @property
    def fmtparams(self):
        """Dict of additional formatting parameters for csv.writer to use.
        For list of valid parameters consult csv.Dialect documentation.

        Raises
        ------
        TypeError
            if invalid parameter is given
        """
        return self._fmtparams

    @fmtparams.setter
    def fmtparams(self, params: Dict):
        for param in params.keys():
            if param not in self._known_fmt_params:
                raise TypeError(f"'{param}' is an invalid csv formatting parameter")
        self._fmtparams = params


# CLASSES
class CsvWriter(_CsvMixin, Writer):
    """Writes extracted data in .csv format form many conformers to one file.

    Parameters
    ----------
    destination: str or pathlib.Path
        Directory, to which generated files should be written.
    mode: str
        Specifies how writing to file should be handled. Should be one of characters:
         'a' (append to existing file), 'x' (only write if file doesn't exist yet),
         or 'w' (overwrite file if it already exists).
    include_header: bool, optional
        Determines if file should contain a header with column names, True by default.
    dialect: str or csv.Dialect
        Name of a dialect or csv.Dialect object, which will be used by underlying
        csv.writer.
    fmtparams: dict, optional
        Additional formatting parameters for underlying csv.writer to use.
        For list of valid parameters consult csv.Dialect documentation.
    """

    def __init__(
        self,
        destination: Union[str, Path],
        mode: str = "x",
        include_header: bool = True,
        dialect: Union[str, csv.Dialect] = "excel",
        **fmtparams,
    ):
        super().__init__(
            destination=destination,
            mode=mode,
            dialect=dialect,
            fmtparams=fmtparams,
            include_header=include_header,
        )

    def energies(
        self,
        energies: Energies,
        corrections: Optional[FloatArray] = None,
    ):
        """Writes Energies object to csv file. The output also contains derived values:
        populations, min_factors, deltas. Corrections are added only when explicitly
        given.

        Parameters
        ----------
        energies: glassware.Energies
            Energies objects that is to be serialized
        corrections: glassware.DataArray, optional
            DataArray objects containing energies corrections
        """
        header = ["Gaussian output file"]
        header += "population min_factor delta energy".split(" ")
        if corrections is not None:
            header += ["corrections"]
            corr = corrections.values
        else:
            corr = []
        rows = zip_longest(
            energies.filenames,
            energies.populations,
            energies.min_factors,
            energies.deltas,
            energies.values,
            corr,
        )
        with self.destination.open(self.mode, newline="") as handle:
            csvwriter = csv.writer(handle, dialect=self.dialect, **self.fmtparams)
            if self.include_header:
                csvwriter.writerow(header)
            for row in rows:
                csvwriter.writerow(v for v in row if v is not None)
        logger.info("Energies export to csv files done.")

    def spectrum(self, spectrum: SingleSpectrum):
        """Writes SingleSpectrum object to csv file.

        Parameters
        ----------
        spectrum: glassware.SingleSpectrum
            spectrum, that is to be serialized
        """
        with self.destination.open(self.mode, newline="") as handle:
            csvwriter = csv.writer(handle, dialect=self.dialect, **self.fmtparams)
            if self.include_header:
                csvwriter.writerow([spectrum.units["y"], spectrum.units["x"]])
            for row in zip(spectrum.x, spectrum.y):
                csvwriter.writerow(row)
        logger.info("Spectrum export to csv files done.")


class CsvSerialWriter(_CsvMixin, SerialWriter):
    """Writes extracted data in .csv format, generates separate file for
    each given conformer.

    Parameters
    ----------
    destination: str or pathlib.Path
        Directory, to which generated files should be written.
    mode: str
        Specifies how writing to file should be handled. Should be one of characters:
         'a' (append to existing file), 'x' (only write if file doesn't exist yet),
         or 'w' (overwrite file if it already exists).
    filename_template: str or string.Template
        Template for names of generated files, defaults to
        '${filename}.${genre}.${ext}'.
     include_header: bool, optional
        Determines if file should contain a header with column names, True by default.
    dialect: str or csv.Dialect
        Name of a dialect or csv.Dialect object, which will be used by underlying
        csv.writer.
    fmtparams: dict, optional
        Additional formatting parameters for underlying csv.writer to use.
        For list of valid parameters consult csv.Dialect documentation.
    """

    extension = "csv"

    def __init__(
        self,
        destination: Union[str, Path],
        mode: str = "x",
        filename_template: Union[str, Template] = "${filename}.${genre}.${ext}",
        include_header: bool = True,
        dialect: Union[str, csv.Dialect] = "excel",
        **fmtparams,
    ):
        super().__init__(
            destination=destination,
            mode=mode,
            filename_template=filename_template,
            dialect=dialect,
            fmtparams=fmtparams,
            include_header=include_header,
        )

    def bars(self, band: Bars, bars: List[Bars]):
        """Writes Bars objects to csv files (one file for each conformer).

        Parameters
        ----------
        band: glassware.Bars
            Object containing information about band at which transitions occur;
            it should be frequencies for vibrational data and wavelengths or
            excitation energies for electronic data.
        bars: list of glassware.Bars
            Bars objects that are to be serialized; all should contain
            information for the same set of conformers and correspond to given band.
        """
        bars = [band] + bars
        headers = [self._header[bar.genre] for bar in bars]
        values = zip(*[bar.values for bar in bars])
        for handle, values_ in zip(
            self._iter_handles(bars[0].filenames, band.genre, newline=""), values
        ):
            csvwriter = csv.writer(handle, dialect=self.dialect, **self.fmtparams)
            if self.include_header:
                csvwriter.writerow(headers)
            for row in zip(*values_):
                csvwriter.writerow(row)
        logger.info("Bars export to csv files done.")

    def spectra(self, spectra: Spectra):
        """Writes Spectra object to .csv files (one file for each conformer).

        Parameters
        ----------
        spectra: glassware.Spectra
            Spectra object, that is to be serialized.
        """
        abscissa = spectra.x
        header = [spectra.units["y"], spectra.units["x"]]
        for handle, values in zip(
            self._iter_handles(spectra.filenames, spectra.genre, newline=""), spectra.y
        ):
            csvwriter = csv.writer(handle, dialect=self.dialect, **self.fmtparams)
            if self.include_header:
                csvwriter.writerow(header)
            for row in zip(abscissa, values):
                csvwriter.writerow(row)
        logger.info("Spectra export to csv files done.")
