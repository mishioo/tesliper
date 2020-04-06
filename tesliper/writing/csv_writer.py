# IMPORTS
import csv
import logging as lgg
from itertools import zip_longest

from ._writer import Writer

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
class CsvWriter(Writer):
    def write(self, data):
        data = self.distribute_data(data)
        if data["energies"]:
            for en in data["energies"]:
                self.energies(
                    f"distribution.{en.genre}.csv",
                    en,
                    corrections=data["corrections"].get(en.genre),
                )
        if data["vibra"]:
            self.bars(band=data["frequencies"], bars=data["vibra"], interfix="vibra")
        if data["electr"]:
            self.bars(band=data["wavelengths"], bars=data["electr"], interfix="electr")
        if data["other_bars"]:
            # TO DO
            pass
        if data["spectra"]:
            for spc in data["spectra"]:
                self.spectra(spc, interfix=spc.genre)
        if data["single"]:
            for spc in data["single"]:
                interfix = f".{spc.averaged_by}" if spc.averaged_by else ""
                file = f"spectrum.{spc.genre+interfix}.csv"
                self.single_spectrum(file, spc)
        if data["other"]:
            # TO DO
            pass

    def energies(self, filename, energies, corrections=None, include_header=True):
        """Writes Energies object to csv file.

        Parameters
        ----------
        filename: string
            path to file
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
        with open(self.destination.joinpath(filename), "w", newline="") as file:
            csvwriter = csv.writer(file)
            if include_header:
                csvwriter.writerow(header)
            for row in rows:
                csvwriter.writerow(v for v in row if v is not None)
        logger.info("Energies export to csv files done.")

    def bars(self, band, bars, include_header=True, interfix=""):
        """Writes Bars objects to csv files (one for each conformer).

        Notes
        -----
        Filenames are generated in form of {conformer_name}[.{interfix}].csv

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
        interfix: string, optional
            string included in produced filenames, nothing is added if omitted
        """
        bars = [band] + bars
        headers = [self._header[bar.genre] for bar in bars]
        values = zip(*[bar.values for bar in bars])
        for fname, values_ in zip(bars[0].filenames, values):
            filename = (
                f"{'.'.join(fname.split('.')[:-1])}"
                f"{'.' if interfix else ''}{interfix}.csv"
            )
            path = self.destination.joinpath(filename)
            with open(path, "w", newline="") as file:
                csvwriter = csv.writer(file)
                if include_header:
                    csvwriter.writerow(headers)
                for row in zip(*values_):
                    csvwriter.writerow(row)
        logger.info("Bars export to csv files done.")

    def spectra(self, spectra, interfix="", include_header=True):
        abscissa = spectra.x
        for fnm, values in zip(spectra.filenames, spectra.y):
            filename = (
                f"{'.'.join(fnm.split('.')[:-1])}"
                f"{'.' if interfix else ''}{interfix}.csv"
            )
            file_path = self.destination.joinpath(filename)
            with open(file_path, "w", newline="") as file:
                csvwriter = csv.writer(file)
                if include_header:
                    # write header to file
                    pass
                for row in zip(abscissa, values):
                    csvwriter.writerow(row)
        logger.info("Spectra export to csv files done.")

    def single_spectrum(self, filename, spectrum):
        with open(self.destination.joinpath(filename), "w", newline="") as file_:
            csvwriter = csv.writer(file_)
            for row in zip(spectrum.x, spectrum.y):
                csvwriter.writerow(row)
        logger.info("Spectrum export to csv files done.")
