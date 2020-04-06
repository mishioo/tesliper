# IMPORTS
import logging as lgg
import openpyxl as oxl
from itertools import zip_longest

from ._writer import Writer


# LOGGER

logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
class XlsxWriter(Writer):
    def write(self, data):
        data = self.distribute_data(data)
        if data["energies"]:
            file = self.destination.joinpath("distribution.xlsx")
            self.energies(
                file,
                data["energies"],
                frequencies=data["frequencies"],
                stoichiometry=data["stoichiometry"],
                corrections=data["corrections"].values(),
            )
        if data["vibra"]:
            file = self.destination.joinpath("bars.vibra.xlsx")
            self.bars(file, band=data["frequencies"], bars=data["vibra"])
        if data["electr"]:
            file = self.destination.joinpath("bars.electr.xlsx")
            self.bars(file, band=data["wavelengths"], bars=data["electr"])
        if data["other_bars"]:
            # TO DO
            pass
        if data["spectra"]:
            file = self.destination.joinpath("spectra.xlsx")
            self.spectra(file, data["spectra"])
        if data["single"]:
            file = self.destination.joinpath("averaged_spectra.xlsx")
            self.single_spectrum(file, data["single"])
        if data["other"]:
            # TODO
            pass

    def energies(
        self, filename, energies, frequencies=None, stoichiometry=None, corrections=None
    ):
        """Writes detailed information from multiple Energies objects to
         single xlsx file.

        Parameters
        ----------
        filename: string
            path to file
        energies: list of glassware.Energies
            Energies objects that is to be exported
        frequencies: glassware.DataArray, optional
            DataArray object containing frequencies
        stoichiometry: glassware.InfoArray, optional
            InfoArray object containing stoichiometry information
        corrections: list of glassware.DataArray
            DataArray objects containing energies corrections"""
        wb = oxl.Workbook()
        ws = wb.active
        ens_no = len(energies)
        ws.title = "Collective overview"
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
        # data = self.ts.energies
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
            ws.column_dimensions[column[0].column].width = width
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
                ws.column_dimensions[column[0].column].width = width
        wb.save(self.destination.joinpath(filename))
        logger.info("Energies export to xlsx files done.")

    def bars(self, filename, band, bars):
        """Writes Bars objects to xlsx file (one sheet for each conformer).

        Parameters
        ----------
        filename: string
            path to file
        band: glassware.Bars
            object containing information about band at which transitions occur;
            it should be frequencies for vibrational data and wavelengths or
            excitation energies for electronic data
        bars: list of glassware.Bars
            Bars objects that are to be serialized; all should contain
            information for the same conformers"""
        # TODO: sort on sheets by type of DataArray class (GroundState, ExitedState...)
        wb = oxl.Workbook()
        wb.remove(wb.active)
        bars = [band] + bars
        genres = [bar.genre for bar in bars]
        headers = [self._header[genre] for genre in genres]
        widths = [max(len(h), 10) for h in headers]
        fmts = [self._excel_formats[genre] for genre in genres]
        values = list(zip(*[bar.values for bar in bars]))
        for fname, values_ in zip(bars[0].filenames, values):
            ws = wb.create_sheet(fname)
            ws.append(headers)
            ws.freeze_panes = "B2"
            for column, width in zip(ws.columns, widths):
                ws.column_dimensions[column[0].column].width = width
            for col_num, (vals, fmt) in enumerate(zip(values_, fmts)):
                for row_num, v in enumerate(vals):
                    cell = ws.cell(row=row_num + 2, column=col_num + 1)
                    cell.value = v
                    cell.number_format = fmt
        wb.save(self.destination.joinpath(filename))
        logger.info("Bars export to xlsx files done.")

    def spectra(self, filename, spectra):
        wb = oxl.Workbook()
        del wb["Sheet"]
        for spectra_ in spectra:
            ws = wb.create_sheet()
            ws.title = spectra_.genre
            ws.freeze_panes = "B2"
            A0 = spectra_.units["x"]
            ws.append([A0] + list(spectra_.filenames))
            title = (
                f"{spectra_.genre} calculated with peak width = "
                f'{spectra_.width} {spectra_.units["width"]} and '
                f"{spectra_.fitting} fitting, shown as "
                f'{spectra_.units["x"]} vs. {spectra_.units["y"]}'
            )
            ws["A1"].comment = oxl.comments.Comment(title, "Tesliper")
            for line in zip(spectra_.x, *spectra_.y):
                ws.append(line)
        wb.save(self.destination.joinpath(filename))
        logger.info("Spectra export to xlsx file done.")

    def single_spectrum(self, filename, spectra):
        # TODO: add comment as in txt export
        # TODO: think how to do it
        wb = oxl.Workbook()
        del wb["Sheet"]
        for spc in spectra:
            ws = wb.create_sheet()
            ws.title = spc.genre + "_" + spc.averaged_by
            for row in zip(spc.x, spc.y):
                ws.append(row)
            wb.save(self.destination.joinpath(filename))
        logger.info("Spectrum export to xlsx files done.")
