"""Data export to CSV format."""
import csv
import logging as lgg
from contextlib import contextmanager
from itertools import repeat, zip_longest
from pathlib import Path
from string import Template
from typing import IO, Any, AnyStr, Dict, Iterable, Iterator, List, Optional, Union

import numpy as np

from ..glassware.arrays import (
    Bands,
    Energies,
    FloatArray,
    SpectralActivities,
    SpectralData,
    Transitions,
)
from ..glassware.spectra import SingleSpectrum, Spectra
from ._writer import Writer

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
    """Writes extracted or calculated data to .csv format files."""

    extension = "csv"

    def __init__(
        self,
        destination: Union[str, Path],
        mode: str = "x",
        include_header: bool = True,
        dialect: Union[str, csv.Dialect] = "excel",
        **fmtparams,
    ):
        """
        Parameters
        ----------
        destination: str or pathlib.Path
            Directory, to which generated files should be written.
        mode: str
            Specifies how writing to file should be handled. Should be one of
            characters: 'a' (append to existing file), 'x' (only write if file doesn't
            exist yet), or 'w' (overwrite file if it already exists).
        include_header: bool, optional
            Determines if file should contain a header with column names, ``True`` by
            default.
        dialect: str or csv.Dialect
            Name of a dialect or :class:`csv.Dialect` object, which will be used by
            underlying :class:`csv.writer`.
        fmtparams: dict, optional
            Additional formatting parameters for underlying csv.writer to use.
            For list of valid parameters consult :class:`csv.Dialect` documentation.
        """
        super().__init__(
            destination=destination,
            mode=mode,
            dialect=dialect,
            fmtparams=fmtparams,
            include_header=include_header,
        )

    @contextmanager
    def _get_handle(
        self,
        template: Union[str, Template],
        template_params: dict,
        open_params: Optional[dict] = None,
    ) -> Iterator[IO[AnyStr]]:
        open_params = open_params or {"newline": ""}
        with super()._get_handle(template, template_params, open_params) as handle:
            yield handle

    def _iter_handles(
        self,
        filenames: Iterable[str],
        template: Union[str, Template],
        template_params: dict,
        open_params: Optional[dict] = None,
    ) -> Iterator[IO[AnyStr]]:
        open_params = open_params or {"newline": ""}
        yield from super()._iter_handles(
            filenames, template, template_params, open_params
        )

    def energies(
        self,
        energies: Energies,
        corrections: Optional[FloatArray] = None,
        name_template: Union[str, Template] = "distribution-${genre}.${ext}",
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
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.
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
        template_params = {
            "conf": "multiple",
            "genre": energies.genre,
            "cat": "populations",
        }
        with self._get_handle(name_template, template_params) as handle:
            csvwriter = csv.writer(handle, dialect=self.dialect, **self.fmtparams)
            if self.include_header:
                csvwriter.writerow(header)
            for row in rows:
                csvwriter.writerow(v for v in row if v is not None)
        logger.info("Energies export to csv files done.")

    def _energies_handler(self, data: List[Energies], extras: Dict[str, Any]) -> None:
        # TODO: return to Writer's implementation when `.overview()` added to this class
        for en in data:
            self.energies(
                en, corrections=extras.get("corrections", dict()).get(en.genre)
            )

    def single_spectrum(
        self,
        spectrum: SingleSpectrum,
        name_template: Union[str, Template] = "${cat}.${genre}-${det}.${ext}",
    ):
        """Writes SingleSpectrum object to csv file.

        Parameters
        ----------
        spectrum: glassware.SingleSpectrum
            spectrum, that is to be serialized
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.
        """
        template_params = {
            "genre": spectrum.genre,
            "cat": "spectrum",
            "det": spectrum.averaged_by,
        }
        with self._get_handle(name_template, template_params) as handle:
            csvwriter = csv.writer(handle, dialect=self.dialect, **self.fmtparams)
            if self.include_header:
                csvwriter.writerow([spectrum.units["y"], spectrum.units["x"]])
            for row in zip(spectrum.x, spectrum.y):
                csvwriter.writerow(row)
        logger.info("Spectrum export to csv files done.")

    def spectral_activities(
        self,
        band: SpectralActivities,
        data: List[SpectralActivities],
        name_template: Union[str, Template] = "${conf}.${cat}-${genre}.${ext}",
    ):
        """Writes SpectralActivities objects to csv files (one file for each conformer).

        Parameters
        ----------
        band: glassware.SpectralActivities
            Object containing information about band at which transitions occur;
            it should be frequencies for vibrational data and wavelengths or
            excitation energies for electronic data.
        data: list of glassware.SpectralActivities
            SpectralActivities objects that are to be serialized; all should contain
            information for the same set of conformers and correspond to given band.
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.
        """
        self._spectral(
            band=band,
            data=data,
            name_template=name_template,
            category="activities",
        )

    def spectral_data(
        self,
        band: SpectralData,
        data: List[SpectralData],
        name_template: Union[str, Template] = "${conf}.${cat}-${genre}.${ext}",
    ):
        """Writes SpectralData objects to csv files (one file for each conformer).

        Parameters
        ----------
        band: glassware.SpectralData
            Object containing information about band at which transitions occur;
            it should be frequencies for vibrational data and wavelengths or
            excitation energies for electronic data.
        data: list of glassware.SpectralData
            SpectralData objects that are to be serialized; all should contain
            information for the same set of conformers and correspond to given band.
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.
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
        """Writes SpectralData objects to csv files (one file for each conformer).

        Parameters
        ----------
        band: glassware.SpectralData
            Object containing information about band at which transitions occur;
            it should be frequencies for vibrational data and wavelengths or
            excitation energies for electronic data.
        data: list of glassware.SpectralData
            SpectralData objects that are to be serialized; all should contain
            information for the same set of conformers and correspond to given band.
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.
        category : str
            category of exported data genres
        """
        data = [band] + data
        headers = [self._header[bar.genre] for bar in data]
        values = zip(*[bar.values for bar in data])
        template_params = {"genre": band.genre, "cat": category}
        for handle, values_ in zip(
            self._iter_handles(band.filenames, name_template, template_params),
            values,
        ):
            csvwriter = csv.writer(handle, dialect=self.dialect, **self.fmtparams)
            if self.include_header:
                csvwriter.writerow(headers)
            for row in zip(*values_):
                csvwriter.writerow(row)
        logger.info(f"{category.title()} export to csv files done.")

    def spectra(
        self,
        spectra: Spectra,
        name_template: Union[str, Template] = "${conf}.${genre}.${ext}",
    ):
        """Writes Spectra object to .csv files (one file for each conformer).

        Parameters
        ----------
        spectra: glassware.Spectra
            Spectra object, that is to be serialized.
        name_template : str or string.Template
            Template that will be used to generate filenames. Refer to
            :meth:`.make_name` documentation for details on supported placeholders.
        """
        abscissa = spectra.x
        header = [spectra.units["y"], spectra.units["x"]]
        template_params = {"genre": spectra.genre, "cat": "spectra"}
        for handle, values in zip(
            self._iter_handles(spectra.filenames, name_template, template_params),
            spectra.y,
        ):
            csvwriter = csv.writer(handle, dialect=self.dialect, **self.fmtparams)
            if self.include_header:
                csvwriter.writerow(header)
            for row in zip(abscissa, values):
                csvwriter.writerow(row)
        logger.info("Spectra export to csv files done.")

    def transitions(
        self,
        transitions: Transitions,
        wavelengths: Bands,
        only_highest=True,
        name_template: Union[str, Template] = "${conf}.${cat}-${det}.${ext}",
    ):
        """Writes electronic transitions data to CSV files (one for each conformer).

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
        header = ["wavelength/nm", "ground", "excited", "coefficient", "contribution"]
        template_params = {
            "genre": transitions.genre,
            "cat": "transitions",
            "det": "highest" if only_highest else "all",
        }
        for handle, grounds, exciteds, values, contribs, bands in zip(
            self._iter_handles(transitions.filenames, name_template, template_params),
            *transtions_data,
            wavelengths.wavelen,
        ):
            csvwriter = csv.writer(handle, dialect=self.dialect, **self.fmtparams)
            if self.include_header:
                csvwriter.writerow(header)
            for g, e, v, c, b in zip(grounds, exciteds, values, contribs, bands):
                try:
                    listed = [
                        d
                        for d in zip(repeat(b), g, e, v, c)
                        # omit entry if any value is masked
                        if all(x is not np.ma.masked for x in d)
                    ]
                except TypeError:
                    # transition_data is transitions.highest_contribution
                    listed = [(b, g, e, v, c)]
                for data in listed:
                    csvwriter.writerow(data)
