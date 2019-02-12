import csv
import numpy as np
import logging as lgg


logger = lgg.getLogger(__name__)


class SpectraParser:

    def parse(self, filename, delimiter=None, xcolumn=0, ycolumn=1):
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
            of data type 'float'

        TO DO
        -----
        add type checking of passed file, consider those:
            https://github.com/audreyr/binaryornot
            https://eli.thegreenplace.net/2011/10/19/perls-guess-if-file-is-text-or-binary-implemented-in-python/
        add csv and binary files support"""
        if filename.endswith(('.txt', '.xy')):
            spc = self.parse_txt(filename, delimiter, xcolumn, ycolumn)
        elif filename.endswith('.csv'):
            spc = self.parse_csv(filename, delimiter, xcolumn, ycolumn)
        else:
            spc = self.parse_spc(filename)
        return spc

    def parse_txt(self, file, delimiter=None, xcolumn=0, ycolumn=1):
        """Loads spectral data from txt file to numpy.array.

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
        with open(file, 'r') as txtfile:
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
            for lineno, line in enumerate(txtfile, start=lineno+1):
                values = [v.strip() for v in line.split(delimiter) if v]
                arr.append(
                    tuple(map(float, (values[xcolumn], values[ycolumn])))
                )
        return np.array(list(zip(*arr)))

    def parse_csv(self, file, delimiter=',', xcolumn=0, ycolumn=1):
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
        arr = []
        with open(file, newline='') as csvfile:
            dialect = csv.Sniffer().sniff(
                csvfile.read(1024), delimiters=delimiter
            )
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

        Rises
        -----
        NotImplementedError
            Whenever called, as this functionality is not implemented yet."""

        raise NotImplementedError("Parsing spc files is not implemented yet.")
