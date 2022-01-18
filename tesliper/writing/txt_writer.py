"""Data export to text files."""
import logging as lgg
from itertools import zip_longest
from string import Template
from typing import List, Optional, Sequence, Union

import numpy as np

from ..glassware.arrays import (
    Bands,
    Energies,
    FloatArray,
    InfoArray,
    SpectralActivities,
    SpectralData,
    Transitions,
)
from ..glassware.spectra import SingleSpectrum, Spectra
from .writer_base import WriterBase, _GenericArray

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
class TxtWriter(WriterBase):
    """Writes extracted or calculated data to .txt format files."""

    extension = "txt"

    def generic(
        self,
        data: List[_GenericArray],
        name_template: Union[str, Template] = "${cat}.${det}.${ext}",
    ):
        """Writes generic data from multiple :class:`.DataArray`-like objects to a
        single file. Said objects should provide a single value for each conformer.

        Parameters
        ----------
        data
            :class:`.DataArray` objects that are to be exported.
        name_template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.
        """
        genres = [arr.genre for arr in data]
        headers = ["Gaussian output file"] + [self._header[genre] for genre in genres]
        formatters = [
            self._formatters[g] if g in self._formatters else "{}" for g in genres
        ]
        values = [arr.values for arr in data]
        formatted = [[f.format(v) for v in vs] for f, vs in zip(formatters, values)]
        lines = list(zip(data[0].filenames, *formatted))
        widths = [max([len(v) for v in vs]) for vs in zip(headers, *lines)]
        types = [type(arr).__name__.lower().replace("array", "") for arr in data]
        detail = "various" if len(set(types)) > 1 else types[0]
        genre = "misc" if len(genres) > 1 else genres[0]
        template_params = {
            "cat": "generic",
            "conf": "multiple",
            "det": detail,
            "genre": genre,
        }
        headers_line = "   ".join([f"{e:<{w}}" for e, w in zip(headers, widths)])
        side = ["<"] + [">"] * len(genres)
        with self._get_handle(name_template, template_params) as handle:
            handle.write(headers_line + "\n")
            handle.write("-" * len(headers_line) + "\n")
            for line in lines:
                handle.write(
                    "   ".join([f"{e:{s}{w}}" for e, s, w in zip(line, side, widths)])
                )
                handle.write("\n")

    def overview(
        self,
        energies: Sequence[Energies],
        frequencies: Optional[Bands] = None,
        stoichiometry: Optional[InfoArray] = None,
        name_template: Union[str, Template] = "${cat}.${ext}",
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
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.
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
        template_params = {"cat": "overview", "conf": "multiple"}
        with self._get_handle(name_template, template_params) as file:
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

    def energies(
        self,
        energies: Energies,
        corrections: Optional[FloatArray] = None,
        name_template: Union[str, Template] = "distribution-${genre}.${ext}",
    ):
        """Writes Energies object to txt file.

        Parameters
        ----------
        energies: glassware.Energies
            Energies object that is to be serialized
        corrections: glassware.DataArray, optional
            DataArray object, containing energies corrections
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.
        """
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
        template_params = {
            "conf": "multiple",
            "genre": energies.genre,
            "cat": "populations",
        }
        with self._get_handle(name_template, template_params) as file:
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

    def single_spectrum(
        self,
        spectrum: SingleSpectrum,
        name_template: Union[str, Template] = "${cat}.${genre}-${det}.${ext}",
    ):
        """Writes SingleSpectrum object to txt file.

        Parameters
        ----------
        spectrum: glassware.SingleSpectrum
            spectrum, that is to be serialized
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.
        """
        title = (
            f"{spectrum.genre} calculated with peak width = "
            f'{spectrum.width} {spectrum.units["width"]} and '
            f'{spectrum.fitting} fitting, shown as {spectrum.units["x"]} '
            f'vs. {spectrum.units["y"]}'
        )
        template_params = {
            "genre": spectrum.genre,
            "cat": "spectrum",
            "det": spectrum.averaged_by,
        }
        with self._get_handle(name_template, template_params) as file:
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

    def spectral_activities(
        self,
        band: SpectralActivities,
        data: List[SpectralActivities],
        name_template: Union[str, Template] = "${conf}.${cat}-${det}.${ext}",
    ):
        """Writes SpectralActivities objects to txt files (one for each conformer).

        Parameters
        ----------
        band: glassware.SpectralActivities
            object containing information about band at which transitions occur;
            it should be frequencies for vibrational data and wavelengths or
            excitation energies for electronic data
        data: list of glassware.SpectralActivities
            SpectralActivities objects that are to be serialized; all should contain
            information for the same conformers. Assumes that all *data*'s elements have
            the same *spectra_type*, which is passed to the *name_template* as "det".
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.

        Raises
        ------
        ValueError
            if *data* is an empty sequence
        """
        self._spectral(
            band=band,
            data=data,
            name_template=name_template,
            category="activities",
        )

    def spectral_data(
        self,
        band: SpectralActivities,
        data: List[SpectralData],
        name_template: Union[str, Template] = "${conf}.${cat}-${det}.${ext}",
    ):
        """Writes SpectralData objects to txt files (one for each conformer).

        Parameters
        ----------
        band: glassware.SpectralData
            object containing information about band at which transitions occur;
            it should be frequencies for vibrational data and wavelengths or
            excitation energies for electronic data
        data: list of glassware.SpectralData
            SpectralData objects that are to be serialized; all should contain
            information for the same conformers. Assumes that all *data*'s elements have
            the same *spectra_type*, which is passed to the *name_template* as "det".
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.

        Raises
        ------
        ValueError
            if *data* is an empty sequence
        """
        self._spectral(
            band=band, data=data, name_template=name_template, category="data"
        )

    def _spectral(
        self,
        band: SpectralActivities,
        data: Union[List[SpectralData], List[SpectralActivities]],
        name_template: Union[str, Template],
        category: str,
    ):
        """Writes SpectralData objects to txt files (one for each conformer).

        Parameters
        ----------
        band: glassware.SpectralData
            object containing information about band at which transitions occur;
            it should be frequencies for vibrational data and wavelengths or
            excitation energies for electronic data
        data: list of glassware.SpectralData
            SpectralData objects that are to be serialized; all should contain
            information for the same conformers. Assumes that all *data*'s elements have
            the same *spectra_type*, which is passed to the *name_template* as "det".
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.
        category : str
            category of exported data genres

        Raises
        ------
        ValueError
            if *data* is an empty sequence
        """
        try:
            spectra_type = data[0].spectra_type
        except IndexError:
            raise ValueError("No data to export.")
        data = [band] + data
        genres = [bar.genre for bar in data]
        headers = [self._header[genre] for genre in genres]
        widths = [self._formatters[genre][4:-4] for genre in genres]
        formatted = [f"{h: <{w}}" for h, w in zip(headers, widths)]
        values = zip(*[bar.values for bar in data])
        template_params = {"genre": band.genre, "cat": category, "det": spectra_type}
        for values_, handle in zip(
            values,
            self._iter_handles(band.filenames, name_template, template_params),
        ):
            handle.write("\t".join(formatted))
            handle.write("\n")
            for vals in zip(*values_):
                line = "\t".join(
                    self._formatters[g].format(v) for v, g in zip(vals, genres)
                )
                handle.write(line + "\n")
        logger.info(f"{category.title()} export to text files done.")

    def spectra(
        self,
        spectra: Spectra,
        name_template: Union[str, Template] = "${conf}.${genre}.${ext}",
    ):
        """Writes Spectra object to text files (one for each conformer).

        Parameters
        ----------
        spectra: glassware.Spectra
            Spectra object, that is to be serialized
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.
        """
        abscissa = spectra.x
        title = (
            f"{spectra.genre} calculated with peak width = {spectra.width}"
            f' {spectra.units["width"]} and {spectra.fitting} '
            f'fitting, shown as {spectra.units["x"]} vs. '
            f'{spectra.units["y"]}'
        )
        template_params = {
            "genre": spectra.genre,
            "cat": "spectra",
            "det": spectra.spectra_type,
        }
        abscissa_genre = "wavelen" if spectra.spectra_type == "electronic" else "freq"
        values_template = "\t".join(
            (self._formatters[abscissa_genre], self._formatters[spectra.genre])
        )
        for values, handle in zip(
            spectra.y,
            self._iter_handles(spectra.filenames, name_template, template_params),
        ):
            handle.write(title + "\n")
            handle.write(
                "\n".join(
                    values_template.format(a, v) for a, v in zip(abscissa, values)
                )
            )
        logger.info("Spectra export to text files done.")

    def transitions(
        self,
        transitions: Transitions,
        wavelengths: Bands,
        only_highest=True,
        name_template: Union[str, Template] = "${conf}.${cat}-${det}.${ext}",
    ):
        """Writes electronic transitions data to text files (one for each conformer).

        Parameters
        ----------
        transitions : glassware.Transitions
            Electronic transitions data that should be serialized.
        wavelengths : glassware.ElectronicActivities
            Object containing information about wavelength at which transitions occur.
        only_highest : bool
            Specifies if only transition of highest contribution to given band should
            be reported. If ``False`` all transition are saved to file.
            Defaults to ``True``.
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.

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
        template_params = {
            "genre": transitions.genre,
            "cat": "transitions",
            "det": "highest" if only_highest else "all",
        }
        for grounds, exciteds, values, contribs, bands, handle in zip(
            *transtions_data,
            wavelengths.wavelen,
            self._iter_handles(transitions.filenames, name_template, template_params),
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
