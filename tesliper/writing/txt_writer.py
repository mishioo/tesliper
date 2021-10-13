# IMPORTS
import logging as lgg
from itertools import zip_longest
from string import Template
from typing import List, Optional, Sequence, Union

import numpy as np

from ..glassware.arrays import (
    ElectronicData,
    Energies,
    FloatArray,
    InfoArray,
    SpectralData,
    Transitions,
    VibrationalData,
)
from ..glassware.spectra import SingleSpectrum, Spectra
from ._writer import Writer

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
class TxtWriter(Writer):
    """Writes extracted data in .txt format form many conformers to one file.

    Parameters
    ----------
    destination: str or pathlib.Path
        Directory, to which generated files should be written.
    mode: str
        Specifies how writing to file should be handled. Should be one of characters:
         'a' (append to existing file), 'x' (only write if file doesn't exist yet),
         or 'w' (overwrite file if it already exists).
    """

    extension = "txt"
    default_template: Union[str, Template] = "${conf}.${genre}.${ext}"

    def overview(
        self,
        energies: Sequence[Energies],
        frequencies: Optional[VibrationalData] = None,
        stoichiometry: Optional[InfoArray] = None,
    ):
        """Writes essential information from multiple Energies objects to
         single txt file.

         Notes
         -----
         All Energy objects given should contain information for the same set of files.

        Parameters
        ----------
        energies: list of glassware.Energies
            Energies objects that is to be exported
        frequencies: glassware.DataArray, optional
            DataArray object containing frequencies, needed for imaginary
            frequencies count
        stoichiometry: glassware.InfoArray, optional
            InfoArray object containing stoichiometry information
        """
        filenames = energies[0].filenames
        imaginary = [] if frequencies is None else frequencies.imaginary
        stoichiometry = [] if stoichiometry is None else stoichiometry.values
        # find the longest string to figure out padding
        max_fnm = max(np.vectorize(len)(filenames).max(), 20)
        try:
            max_stoich = max(np.vectorize(len)(stoichiometry).max(), 13)
        except ValueError:
            max_stoich = 0
        # values should be in shape (file, genre)
        values = np.array([en.values for en in energies]).T
        # populations in percent
        popul = np.array([en.populations * 100 for en in energies]).T
        names = [self._header[en.genre] for en in energies]
        population_widths = [max(8, len(n)) for n in names]
        population_header = "  ".join(
            [f"{n:<{w}}" for n, w in zip(names, population_widths)]
        )
        energies_widths = [14 if n == "SCF" else 12 for n in names]
        energies_header = "  ".join(
            [f"{n:<{w}}" for n, w in zip(names, energies_widths)]
        )
        names_line = [" " * max_fnm, population_header, energies_header]
        names_line += ["    "] if frequencies is not None else []
        names_line += ["             "] if max_stoich else []
        names_line = " | ".join(names_line)
        precisions = [8 if n == "SCF" else 6 for n in names]
        header = [
            f"{'Gaussian output file':<{max_fnm}}",
            f"{'Population / %':^{len(population_header)}}",
            f"{'Energy / Hartree':^{len(energies_header)}}",
        ]
        header += ["Imag"] if frequencies is not None else []
        header += [f"{'Stoichiometry':<{max_stoich}}"] if max_stoich else []
        header = " | ".join(header)
        line_format = (
            f"{{:<{max_fnm}}} | {{}} | {{}}"
            f"{' | {:^ 4}' if frequencies is not None else '{}'}"
            f"{f' | {{:<{max_stoich}}}' if max_stoich else '{}'}\n"
        )
        with self._get_handle("overwiew", "general") as file:
            file.write(header + "\n")
            file.write(names_line + "\n")
            file.write("-" * len(header) + "\n")
            rows = zip_longest(
                filenames, values, popul, imaginary, stoichiometry, fillvalue=""
            )
            for fnm, vals, pops, imag, stoich in rows:
                p_line = "  ".join(
                    [f"{p:>{w}.4f}" for p, w in zip(pops, population_widths)]
                )
                v_line = "  ".join(
                    [
                        f"{v:> {w}.{p}f}"
                        for v, w, p in zip(vals, energies_widths, precisions)
                    ]
                )
                line = line_format.format(fnm, p_line, v_line, imag, stoich)
                file.write(line)
        logger.info("Energies collective export to text file done.")

    def energies(self, energies: Energies, corrections: Optional[FloatArray] = None):
        """Writes Energies object to txt file.

        Parameters
        ----------
        energies: glassware.Energies
            Energies object that is to be serialized
        corrections: glassware.DataArray, optional
            DataArray object, containing energies corrections"""
        max_fnm = max(np.vectorize(len)(energies.filenames).max(), 20)
        header = [f"{'Gaussian output file':<{max_fnm}}"]
        header += ["Population/%", "Min.B.Factor", "DE/(kcal/mol)", "Energy/Hartree"]
        header += ["Corr/Hartree"] if corrections is not None else []
        header = " | ".join(header)
        align = ("<", ">", ">", ">", ">", ">")
        width = (max_fnm, 12, 12, 13, 14, 12)
        corrections = corrections.values if corrections is not None else []
        fmt = (
            "",
            ".4f",
            ".4f",
            ".4f",
            ".8f" if energies.genre == "scf" else ".6f",
            "f",
        )
        rows = zip_longest(
            energies.filenames,
            energies.populations * 100,
            energies.min_factors,
            energies.deltas,
            energies.values,
            corrections,
            fillvalue=None,
        )
        with self._get_handle("populations", energies.genre) as file:
            file.write(header + "\n")
            file.write("-" * len(header) + "\n")
            for row in rows:
                new_row = [
                    f"{v:{a}{w}{f}}"
                    for v, a, w, f in zip(row, align, width, fmt)
                    if v is not None
                ]
                file.write(" | ".join(new_row) + "\n")
        logger.info("Energies separate export to text files done.")

    def single_spectrum(self, spectrum: SingleSpectrum):
        """Writes SingleSpectrum object to txt file.

        Parameters
        ----------
        spectrum: glassware.SingleSpectrum
            spectrum, that is to be serialized
        """
        title = (
            f"{spectrum.genre} calculated with peak width = "
            f'{spectrum.width} {spectrum.units["width"]} and '
            f'{spectrum.fitting} fitting, shown as {spectrum.units["x"]} '
            f'vs. {spectrum.units["y"]}'
        )
        with self._get_handle("spectrum", spectrum.genre) as file:
            file.write(title + "\n")
            if spectrum.averaged_by:
                file.write(
                    f"{len(spectrum.filenames)} conformers averaged base on"
                    f" {self._header[spectrum.averaged_by]}\n"
                )
            file.write(
                "\n".join(
                    f"{int(x):> 7.2f}\t{y: > 10.4f}"
                    for x, y in zip(spectrum.x, spectrum.y)
                )
            )
        logger.info("Spectrum export to text files done.")

    def spectral_data(self, band: SpectralData, data: List[SpectralData]):
        """Writes SpectralData objects to txt files (one for each conformer).

        Parameters
        ----------
        band: glassware.SpectralData
            object containing information about band at which transitions occur;
            it should be frequencies for vibrational data and wavelengths or
            excitation energies for electronic data
        data: list of glassware.SpectralData
            SpectralData objects that are to be serialized; all should contain
            information for the same conformers
        """
        data = [band] + data
        genres = [bar.genre for bar in data]
        headers = [self._header[genre] for genre in genres]
        widths = [self._formatters[genre][4:-4] for genre in genres]
        formatted = [f"{h: <{w}}" for h, w in zip(headers, widths)]
        values = zip(*[bar.values for bar in data])
        for handle, values_ in zip(
            self._iter_handles(data[0].filenames, band.genre), values
        ):
            handle.write("\t".join(formatted))
            handle.write("\n")
            for vals in zip(*values_):
                line = "\t".join(
                    self._formatters[g].format(v) for v, g in zip(vals, genres)
                )
                handle.write(line + "\n")
        logger.info("SpectralData export to text files done.")

    def spectra(self, spectra: Spectra):
        """Writes Spectra object to text files (one for each conformer).

        Parameters
        ----------
        spectra: glassware.Spectra
            Spectra object, that is to be serialized
        """
        abscissa = spectra.x
        title = (
            f"{spectra.genre} calculated with peak width = {spectra.width}"
            f' {spectra.units["width"]} and {spectra.fitting} '
            f'fitting, shown as {spectra.units["x"]} vs. '
            f'{spectra.units["y"]}'
        )
        for handle, values in zip(
            self._iter_handles(spectra.filenames, spectra.genre), spectra.y
        ):
            handle.write(title + "\n")
            handle.write(
                "\n".join(f"{int(a):>4d}\t{v: .4f}" for a, v in zip(abscissa, values))
            )
        logger.info("Spectra export to text files done.")

    def transitions(
        self, transitions: Transitions, wavelengths: ElectronicData, only_highest=True
    ):
        """Writes electronic transitions data to text files (one for each conformer).

        Parameters
        ----------
        transitions : glassware.Transitions
            Electronic transitions data that should be serialized.
        wavelengths : glassware.ElectronicData
            Object containing information about wavelength at which transitions occur.
        only_highest : bool
            Specifies if only transition of highest contribution to given band should
            be reported. If `False` all transition are saved to file.
            Defaults to `True`.
        """
        transtions_data = (
            transitions.highest_contribution
            if only_highest
            else (
                transitions.ground,
                transitions.excited,
                transitions.values,
                transitions.contribution,
            )
        )
        contrib_text = "of highest contribution" if only_highest else "contributing"
        title = f"Electronic transitions {contrib_text} to each band."
        legend = "wavelength: ground -> excited, coefficient, contribution"
        transition_entry = "{:>6d} -> {:<7d} {:> 11.5f} {:>12.0%}\n"
        for handle, grounds, exciteds, values, contribs, bands in zip(
            self._iter_handles(transitions.filenames, transitions.genre),
            *transtions_data,
            wavelengths.wavelen,
        ):
            handle.write(title + "\n")
            handle.write(legend + "\n\n")
            for g, e, v, c, b in zip(grounds, exciteds, values, contribs, bands):
                try:
                    listed = [
                        transition_entry.format(*d)
                        for d in zip(g, e, v, c)
                        # omit entry if any value is masked
                        if all(x is not np.ma.masked for x in d)
                    ]
                    listed = (" " * 12).join(listed)
                except TypeError:
                    # transition_data is transitions.highest_contribution
                    listed = transition_entry.format(g, e, v, c)
                handle.write(f"  {b:> 7.2f} nm: {listed}")
