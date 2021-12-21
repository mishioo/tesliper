"""Parser for spectra files."""
import csv
import logging as lgg
from pathlib import Path
from typing import Optional, Union

import numpy as np

from .base_parser import Parser

logger = lgg.getLogger(__name__)


class SpectraParser(Parser):
    """Parser for files containing spectral data. It can parse .txt (in "x y" format)
    and .csv files, returning an numpy.ndarray with loaded spectrum. Parsing process
    may be customized by specifying what delimiter of values should be expected
    and in which column x- and y-values are, if there are more than 2 columns of data.
    If file contains any header, it is ignored.
    """

    def __init__(self):
        super().__init__()
        self.delimiter = None
        self.xcolumn = 0
        self.ycolumn = 1

    def parse(
        self,
        filename: Union[str, Path],
        delimiter: Optional[str] = None,
        xcolumn: int = 0,
        ycolumn: int = 1,
    ) -> np.ndarray:
        """Loads spectral data from file to numpy.array. Currently supports
        only .txt, .xy, and .csv files.

        Parameters
        ----------
        filename: str
            path to file containing spectral data
        delimiter: str, optional
            character used to delimit columns in file, defaults to whitespace
        xcolumn: int, optional
            column, that should be used as points on x axis,
            defaults to 0 (first column)
        ycolumn: int, optional
            column, that should be used as values on y axis,
            defaults to 1 (second column)

        Returns
        -------
        numpy.array
            two-dimensional numpy array ([[x-values], [y-values]])
            of data type ``float``"""
        # TODO: add type checking of passed file, consider those:
        #     https://github.com/audreyr/binaryornot
        #     https://eli.thegreenplace.net/2011/10/19/\
        #       perls-guess-if-file-is-text-or-binary-implemented-in-python/
        # TODO: add binary files support"""
        self.delimiter = delimiter
        self.xcolumn = xcolumn
        self.ycolumn = ycolumn
        filename = str(filename)
        self.workhorse(filename)  # figure out which method to use
        spc = self.workhorse(filename)  # actual parsing
        return spc

    def initial(self, filename: str):
        super().initial(filename)
        if self.workhorse is self.initial:
            raise ValueError(f"Don't know how to parse file {filename}")

    @Parser.state(trigger=r".+\.(?:txt|xy)$")
    def parse_txt(self, file: Path):
        """Loads spectral data from .txt or .xy file to numpy.array.

        Parameters
        ----------
        file: str
            path to file containing spectral data
        delimiter: str, optional
            character used to delimit columns in file, defaults to whitespace
        xcolumn: int, optional
            column, that should be used as points on x axis,
            defaults to 0 (first column)
        ycolumn: int, optional
            column, that should be used as values on y axis,
            defaults to 1 (second column)

        Returns
        -------
        numpy.array
            two-dimensional numpy array ([[x-values], [y-values]])
            of data type 'float'

        Rises
        -----
        ValueError
            if file passed was read to end, but no spectral data was found;
            this includes columns' numbers out of range and usage of
            inappropriate delimiter"""
        with open(file, "r") as txtfile:
            delimiter = self.delimiter
            xcolumn = self.xcolumn
            ycolumn = self.ycolumn
            line = txtfile.readline()
            lineno = 1
            search = True
            while line and search:
                try:
                    values = [v.strip() for v in line.split(delimiter) if v]
                    x, y = float(values[xcolumn]), float(values[ycolumn])
                    search = False
                except (ValueError, TypeError, IndexError) as error:
                    logger.debug(f"Line omitted due to {error}")
                    line = txtfile.readline()
                    lineno += 1
            if not line:
                raise ValueError(
                    f"No spectral data found in file's columns {xcolumn} "
                    f"and {ycolumn}."
                )
            arr = [(x, y)]
            for lineno, line in enumerate(txtfile, start=lineno + 1):
                values = [v.strip() for v in line.split(delimiter) if v]
                arr.append(tuple(map(float, (values[xcolumn], values[ycolumn]))))
        return np.array(list(zip(*arr)))

    @Parser.state(trigger=r".+\.csv$")
    def parse_csv(self, file: Path):
        """Loads spectral data from csv file to numpy.array.

        Parameters
        ----------
        file: str
            path to file containing spectral data
        delimiter: str, optional
            character used to delimit columns in file, defaults to ','
        xcolumn: int, optional
            column, that should be used as points on x axis,
            defaults to 0 (first column)
        ycolumn: int, optional
            column, that should be used as values on y axis,
            defaults to 1 (second column)

        Returns
        -------
        numpy.array
            two-dimensional numpy array ([[x-values], [y-values]])
            of data type 'float'"""
        delimiter = self.delimiter
        xcolumn = self.xcolumn
        ycolumn = self.ycolumn
        arr = []
        with open(file, newline="") as csvfile:
            dialect = csv.Sniffer().sniff(csvfile.read(1024), delimiters=delimiter)
            csvfile.seek(0)
            reader = csv.reader(csvfile, dialect)
            for line in reader:
                arr.append(tuple(map(float, (line[xcolumn], line[ycolumn]))))
        return np.array(list(zip(*arr)))

    def parse_spc(self, file):
        """Loads spectral data from spc file to numpy.array.

        Notes
        -----
        This method is not implemented yet, it will raise an error when called.

        Parameters
        ----------
        file: str
            path to file containing spectral data

        Returns
        -------
        numpy.array
            two-dimensional numpy array ([[x-values], [y-values]])
            of data type 'float'

        Raises
        ------
        NotImplementedError
            Whenever called, as this functionality is not implemented yet."""
        # TODO: add support for .spc files
        raise NotImplementedError("Parsing spc files is not implemented yet.")
