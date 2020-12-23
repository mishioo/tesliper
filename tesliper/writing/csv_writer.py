# IMPORTS
import csv
import logging as lgg
from itertools import zip_longest
from pathlib import Path
from string import Template
from typing import Union, List, Optional

from ._writer import Writer, SerialWriter
from ..glassware.spectra import SingleSpectrum, Spectra
from ..glassware.arrays import Energies, FloatArray, Bars

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
class CsvWriter(Writer):
    def __init__(
        self,
        destination: Union[str, Path],
        mode: str = "x",
        dialect: Union[str, csv.Dialect] = "excel",
        **fmtparams,
    ):
        super().__init__(destination=destination, mode=mode)
        self.dialect = (
            dialect if isinstance(dialect, csv.Dialect) else csv.get_dialect(dialect)
        )
        self.fmtparams = fmtparams

    def energies(
        self,
        energies: Energies,
        corrections: Optional[FloatArray] = None,
        include_header: bool = True,
    ):
        """Writes Energies object to csv file.

        Parameters
        ----------
        energies: glassware.Energies
            Energies objects that is to be serialized
        corrections: glassware.DataArray, optional
            DataArray objects containing energies corrections
        include_header: bool, optional
            determines if file should contain a header with column names,
            True by default"""
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
        with self.destination.open(self.mode) as handle:
            csvwriter = csv.writer(handle, dialect=self.dialect, **self.fmtparams)
            if include_header:
                csvwriter.writerow(header)
            for row in rows:
                csvwriter.writerow(v for v in row if v is not None)
        logger.info("Energies export to csv files done.")

    def spectrum(self, spectrum: SingleSpectrum, include_header: bool = True):
        with self.destination.open(self.mode, newline="") as handle:
            csvwriter = csv.writer(handle, dialect=self.dialect, **self.fmtparams)
            if include_header:
                csvwriter.writerow([spectrum.units['y'], spectrum.units['x']])
            for row in zip(spectrum.x, spectrum.y):
                csvwriter.writerow(row)
        logger.info("Spectrum export to csv files done.")


class CsvSerialWriter(SerialWriter):
    extension = "csv"

    def __init__(
        self,
        destination: Union[str, Path],
        mode: str = "x",
        filename_template: Union[str, Template] = "${filename}.${genre}.${ext}",
        dialect: Union[str, csv.Dialect] = "excel",
        **fmtparams,
    ):
        super().__init__(
            destination=destination, mode=mode, filename_template=filename_template
        )
        self.dialect = (
            dialect if isinstance(dialect, csv.Dialect) else csv.get_dialect(dialect)
        )
        self.fmtparams = fmtparams

    def bars(self, band: Bars, bars: List[Bars], include_header: bool = True):
        """Writes Bars objects to csv files (one for each conformer).

        Parameters
        ----------
        band: glassware.Bars
            object containing information about band at which transitions occur;
            it should be frequencies for vibrational data and wavelengths or
            excitation energies for electronic data
        bars: list of glassware.Bars
            Bars objects that are to be serialized; all should contain
            information for the same conformers
        include_header: bool, optional
            determines if file should contain a header with column names,
            True by default,
        """
        bars = [band] + bars
        headers = [self._header[bar.genre] for bar in bars]
        values = zip(*[bar.values for bar in bars])
        for handle, values_ in zip(
            self._iter_handles(bars[0].filenames, band.genre), values
        ):
            csvwriter = csv.writer(handle, dialect=self.dialect, **self.fmtparams)
            if include_header:
                csvwriter.writerow(headers)
            for row in zip(*values_):
                csvwriter.writerow(row)
        logger.info("Bars export to csv files done.")

    def spectra(self, spectra: Spectra, include_header: bool = True):
        abscissa = spectra.x
        header = [spectra.units['y'], spectra.units['x']]
        for handle, values in zip(
            self._iter_handles(spectra.filenames, spectra.genre), spectra.y
        ):
            csvwriter = csv.writer(handle, dialect=self.dialect, **self.fmtparams)
            if include_header:
                csvwriter.writerow(header)
            for row in zip(abscissa, values):
                csvwriter.writerow(row)
        logger.info("Spectra export to csv files done.")
