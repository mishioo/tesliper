# IMPORTS
import logging as lgg
from pathlib import Path
from typing import Sequence, Optional, Union, Iterable

import openpyxl as oxl
from itertools import zip_longest

from ._writer import Writer
from ..glassware.arrays import Energies, Bars, InfoArray, FloatArray, DataArray
from ..glassware.spectra import Spectra, SingleSpectrum


# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
class XlsxWriter(Writer):
    def __init__(self, destination: Union[str, Path], mode: str = "x"):
        super().__init__(destination=destination, mode=mode)
        if self.mode == "a":
            self.workbook = oxl.load_workbook(self.destination)
        else:
            self.workbook = oxl.Workbook()
            self.workbook.remove(self.workbook.active)

    def energies(
        self,
        energies: Sequence[Energies],
        frequencies: Optional[DataArray] = None,
        stoichiometry: Optional[InfoArray] = None,
        corrections: Sequence[FloatArray] = None,
    ):
        """Writes detailed information from multiple Energies objects to
         single xlsx file.

        Parameters
        ----------
        energies: list of glassware.Energies
            Energies objects that is to be exported
        frequencies: glassware.DataArray, optional
            DataArray object containing frequencies
        stoichiometry: glassware.InfoArray, optional
            InfoArray object containing stoichiometry information
        corrections: list of glassware.DataArray
            DataArray objects containing energies corrections"""
        wb = self.workbook
        ws = wb.create_sheet(title="Collective overview")
        ens_no = len(energies)
        headers = ["Gaussian output file", "Populations / %", "Energies / hartree"]
        headers += ["Imag"] if frequencies is not None else []
        headers += ["Stoichiometry"] if stoichiometry is not None else []
        cells = [
            "A1",
            "B1",
            f"{chr(66+ens_no)}1",
            f"{chr(66+2*ens_no)}1",
            f"{chr(67+2*ens_no)}1",
        ]
        for header, cell in zip(headers, cells):
            ws[cell] = header
        names = [self._header[en.genre] for en in energies]
        ws.append([""] + names + names)
        ws.merge_cells("A1:A2")
        ws.merge_cells(f"B1:{chr(65+ens_no)}1")
        ws.merge_cells(f"{chr(66+ens_no)}1:{chr(65+2*ens_no)}1")
        if frequencies is not None or stoichiometry is not None:
            ws.merge_cells(f"{chr(66+2*ens_no)}1:{chr(66+2*ens_no)}2")
        if frequencies is not None and stoichiometry is not None:
            ws.merge_cells(f"{chr(67+2*ens_no)}1:{chr(67+2*ens_no)}2")
        ws.freeze_panes = "A3"
        filenames = energies[0].filenames
        fmts = (
            ["0"]
            + ["0.00%"] * len(energies)
            + ["0." + "0" * (8 if en.genre == "scf" else 6) for en in energies]
            + ["0", "0"]
        )
        values = [en.values for en in energies]
        populs = [en.populations for en in energies]
        imag = frequencies.imaginary if frequencies is not None else []
        stoich = stoichiometry.values if stoichiometry is not None else []
        rows = zip_longest(filenames, *populs, *values, imag, stoich)
        for row_num, values in enumerate(rows):
            filtered_values = ((f, v) for f, v in zip(fmts, values) if v is not None)
            for col_num, (fmt, value) in enumerate(filtered_values):
                cell = ws.cell(row=row_num + 3, column=col_num + 1)
                cell.value = value
                cell.number_format = fmt
        # set cells width
        widths = [0] + [10] * ens_no + [16] * ens_no
        widths += [6] if frequencies is not None else []
        widths += [0] if stoichiometry is not None else []
        for column, width in zip(ws.columns, widths):
            if not width:
                width = max(len(str(cell.value)) for cell in column) + 2
            column_letter = oxl.utils.get_column_letter(column[0].column)
            ws.column_dimensions[column_letter].width = width
        # proceed to write detailed info on separate sheet for each energy
        corrs = {c.genre[:3]: c for c in corrections} if corrections is not None else {}
        for en in energies:
            genre = en.genre
            corr = corrs.get(genre, None)
            fmts = (
                ["0", "0.00%"]
                + ["0.0000"] * 2
                + ["0.00000000" if genre == "scf" else "0.000000"] * 2
            )
            ws = wb.create_sheet(title=self._header[genre])
            ws.freeze_panes = "A2"
            header = [
                "Gaussian output file",
                "Population / %",
                "Min. B. Factor",
                "DE / (kcal/mol)",
                "Energy / Hartree",
            ]
            header += ["Correction / Hartree"] if corr is not None else []
            ws.append(header)
            corr = corr.values if corr is not None else []
            rows = zip_longest(
                en.filenames, en.populations, en.min_factors, en.deltas, en.values, corr
            )
            for row_num, values in enumerate(rows):
                filtered_values = (
                    (f, v) for f, v in zip(fmts, values) if v is not None
                )
                for col_num, (fmt, value) in enumerate(filtered_values):
                    cell = ws.cell(row=row_num + 2, column=col_num + 1)
                    cell.value = value
                    cell.number_format = fmt
            # set cells width
            widths = [0, 15, 14, 15, 16, 19]
            for column, width in zip(ws.columns, widths):
                if not width:
                    width = max(len(str(cell.value)) for cell in column) + 2
                column_letter = oxl.utils.get_column_letter(column[0].column)
                ws.column_dimensions[column_letter].width = width
        wb.save(self.destination)
        logger.info("Energies export to xlsx files done.")

    def bars(self, band: Bars, bars: Iterable[Bars]):
        """Writes Bars objects to xlsx file (one sheet for each conformer).

        Parameters
        ----------
        band: glassware.Bars
            object containing information about band at which transitions occur;
            it should be frequencies for vibrational data and wavelengths or
            excitation energies for electronic data
        bars: list of glassware.Bars
            Bars objects that are to be serialized; all should contain
            information for the same conformers"""
        # TODO: sort on sheets by type of DataArray class (GroundState, ExitedState...)
        wb = self.workbook
        bars = [band] + list(bars)
        genres = [bar.genre for bar in bars]
        headers = [self._header[genre] for genre in genres]
        widths = [max(len(h), 10) for h in headers]
        fmts = [self._excel_formats[genre] for genre in genres]
        values = list(zip(*[bar.values for bar in bars]))
        for fname, values_ in zip(bars[0].filenames, values):
            ws = wb.create_sheet(title=fname)
            ws.append(headers)
            ws.freeze_panes = "B2"
            for column, width in zip(ws.columns, widths):
                column_letter = oxl.utils.get_column_letter(column[0].column)
                ws.column_dimensions[column_letter].width = width
            for col_num, (vals, fmt) in enumerate(zip(values_, fmts)):
                for row_num, v in enumerate(vals):
                    cell = ws.cell(row=row_num + 2, column=col_num + 1)
                    cell.value = v
                    cell.number_format = fmt
        wb.save(self.destination)
        logger.info("Bars export to xlsx files done.")

    def spectra(self, spectra: Spectra):
        wb = self.workbook
        ws = wb.create_sheet(title=spectra.genre)
        ws.freeze_panes = "B2"
        A0 = spectra.units["x"]
        ws.append([A0] + list(spectra.filenames))
        title = (
            f"{spectra.genre} calculated with peak width = "
            f'{spectra.width} {spectra.units["width"]} and '
            f"{spectra.fitting} fitting, shown as "
            f'{spectra.units["x"]} vs. {spectra.units["y"]}'
        )
        ws["A1"].comment = oxl.comments.Comment(title, "Tesliper")
        for line in zip(spectra.x, *spectra.y):
            ws.append(line)
        wb.save(self.destination)
        logger.info("Spectra export to xlsx file done.")

    def single_spectrum(self, spectrum: SingleSpectrum):
        # TODO: add comment as in txt export
        wb = self.workbook
        ws = wb.create_sheet(title=f"{spectrum.genre}_{spectrum.averaged_by}")
        ws.append([spectrum.units["x"], spectrum.units["y"]])
        for row in zip(spectrum.x, spectrum.y):
            ws.append(row)
        wb.save(self.destination)
        logger.info("Spectrum export to xlsx files done.")
