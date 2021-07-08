# IMPORTS
import logging as lgg
from pathlib import Path
from string import Template
from typing import Any, Dict, Iterable, TextIO, Union

from ..glassware.arrays import (
    Bars,
    DataArray,
    Energies,
    ExcitedStateBars,
    GroundStateBars,
)
from ..glassware.spectra import SingleSpectrum, Spectra

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
class Writer:
    """Base class for writers, that produce single file from multiple conformers.

    Parameters
    ----------
    destination: str or pathlib.Path
        File, to which generated files should be written.
    mode: str
        Specifies how writing to file should be handled. Should be one of characters:
         "a" (append to existing file); "x" (only write if file does'nt exist yet);
         or "w" (overwrite file if it already exists). Defaults to "x".

    Attributes
    ----------
    destination
    mode
    """

    _header = dict(
        freq="Frequencies",
        mass="Red. masses",
        frc="Frc consts",
        raman="Raman Activ",
        depolarp=r"Depolar \(P\)",
        depolaru=r"Depolar \(U\)",
        ramact="RamAct",
        depp="Dep-P",
        depu="Dep-U",
        alpha2="Alpha2",
        beta2="Beta2",
        alphag="AlphaG",
        gamma2="Gamma2",
        delta2="Delta2",
        cid1="CID1",
        raman2="Raman2",
        roa2="ROA2",
        cid2="CID2",
        raman3="Raman3",
        roa3="ROA3",
        cid3="CID3",
        rc180="RC180",
        rot="Rot. Str.",
        dip="Dip. Str.",
        roa1="ROA1",
        raman1="Raman1",
        ex_en="Excit. Energy",
        wavelen="Wavelength",
        vrot="Rot.(velo)",
        lrot="Rot. (len)",
        vosc="Osc.(velo)",
        losc="Osc. (len)",
        iri="IR Int.",
        emang="E-M Angle",
        eemang="E-M Angle",
        zpe="Zero-point",
        ten="Thermal",
        ent="Enthalpy",
        gib="Gibbs",
        scf="SCF",
    )

    _formatters = dict(
        rot="{:> 10.4f}",
        dip="{:> 10.4f}",
        roa1="{:> 10.4f}",
        raman1="{:> 10.4f}",
        vrot="{:> 10.4f}",
        lrot="{:> 10.4f}",
        vosc="{:> 10.4f}",
        losc="{:> 10.4f}",
        iri="{:> 10.4f}",
        emang="{:> 10.4f}",
        eemang="{:> 10.4f}",
        zpe="{:> 13.4f}",
        ten="{:> 13.4f}",
        ent="{:> 13.4f}",
        gib="{:> 13.4f}",
        scf="{:> 13.4f}",
        ex_en="{:> 13.4f}",
        freq="{:> 10.2f}",
        wavelen="{:> 10.2f}",
        mass="{:> 11.4f}",
        frc="{:> 10.4f}",
        raman="{:> 11.4f}",
        depolarp="{:> 11.4f}",
        depolaru="{:> 11.4f}",
        ramact="{:> 10.4f}",
        depp="{:> 9.4f}",
        depu="{:> 9.4f}",
        alpha2="{:> 9.4f}",
        beta2="{:> 9.4f}",
        alphag="{:> 9.4f}",
        gamma2="{:> 9.4f}",
        delta2="{:> 9.4f}",
        cid1="{:> 8.3f}",
        raman2="{:> 8.3f}",
        roa2="{:> 8.3f}",
        cid2="{:> 8.3f}",
        raman3="{:> 8.3f}",
        roa3="{:> 8.3f}",
        cid3="{:> 8.3f}",
        rc180="{:> 8.3f}",
    )

    _excel_formats = dict(
        freq="0.0000",
        mass="0.0000",
        frc="0.0000",
        raman="0.0000",
        depolarp="0.0000",
        depolaru="0.0000",
        ramact="0.0000",
        depp="0.0000",
        depu="0.0000",
        alpha2="0.0000",
        beta2="0.0000",
        alphag="0.0000",
        gamma2="0.0000",
        delta2="0.0000",
        cid1="0.000",
        raman2="0.000",
        roa2="0.000",
        cid2="0.000",
        raman3="0.000",
        roa3="0.000",
        cid3="0.000",
        rc180="0.000",
        rot="0.0000",
        dip="0.0000",
        roa1="0.000",
        raman1="0.000",
        ex_en="0.0000",
        wavelen="0.0000",
        vrot="0.0000",
        lrot="0.0000",
        vosc="0.0000",
        losc="0.0000",
        iri="0.0000",
        emang="0.0000",
        eemang="0.0000",
        zpe="0.000000",
        ten="0.000000",
        ent="0.000000",
        gib="0.000000",
        scf="0.00000000",
    )

    energies_order = "zpe ten ent gib scf".split(" ")

    def __init__(self, destination: Union[str, Path], mode: str = "x"):
        self.mode = mode
        self.destination = destination

    @property
    def mode(self):
        """Specifies how writing to file should be handled. Should be one of characters:
        "a", "x", or "w".
        "a" - append to existing file;
        "x" - only write if file doesn't exist yet;
        "w" - overwrite file if it already exists.

        Raises
        ------
        ValueError
            If given anything other than "a", "x", or "w".
        """
        return self._mode

    @mode.setter
    def mode(self, mode):
        if mode not in ("a", "x", "w"):
            raise ValueError("Mode should be 'a', 'x', or 'w'.")
        self._mode = mode

    @property
    def destination(self) -> Path:
        """pathlib.Path: File, to which data should be written.

        Notes
        -----
        If str given, it will be converted to pathlib.Path.

        Raises
        ------
        FileNotFoundError
            If mode 'a' was specified, but given destination doesn't exist.
        FileExistsError
            If mode 'x' was specified, but given destination already exists.
        """
        return self._destination

    @destination.setter
    def destination(self, destination: Union[str, Path]) -> None:
        destination = Path(destination)
        if not destination.exists() and self.mode == "a":
            raise FileNotFoundError(
                "Mode 'a' was specified, but given destination doesn't exist."
            )
        elif destination.exists() and self.mode == "x":
            raise FileExistsError(
                "Mode 'x' was specified, but given destination already exists."
            )
        elif not destination.parent.exists():
            raise FileNotFoundError("Parent directory of specified file doesn't exist.")
        self._destination = destination

    @staticmethod
    def distribute_data(data: Iterable[DataArray]) -> Dict:
        """Sorts given data by genre category for use by specialized writing methods.

        Parameters
        ----------
        data: Iterable of DataArray
            Iterable with DataArray objects to sort by genre category.

        Returns
        -------
        dict
            Dictionary with DataArray objects sorted by genre category.
            Available key: value pairs are:
                energies: List of Energies,
                vibra: List of GroundStateBars,
                electr: List of ExcitedStateBars,
                other_bars: List of Bars,
                spectra: List of Spectra,
                single: List of SingleSpectrum,
                other: List of DataArray,
                corrections = dict of genre: FloatArray,
                frequencies = ExcitedStateBars or None,
                wavelenghts = GroundStateBars or None,
                stoichiometry = InfoArray or None
        """
        distr = dict(
            energies=[],
            vibra=[],
            electr=[],
            other_bars=[],
            spectra=[],
            single=[],
            other=[],
            corrections={},
            frequencies=None,
            wavelengths=None,
            stoichiometry=None,
        )
        for obj in data:
            if isinstance(obj, Energies):
                distr["energies"].append(obj)
            elif obj.genre.endswith("corr"):
                distr["corrections"][obj.genre[:3]] = obj
            elif obj.genre == "freq":
                distr["frequencies"] = obj
            elif obj.genre == "wave":
                distr["wavelengths"] = obj
            elif obj.genre == "stoichiometry":
                distr["stoichiometry"] = obj
            elif isinstance(obj, GroundStateBars):
                distr["vibra"].append(obj)
            elif isinstance(obj, ExcitedStateBars):
                distr["electr"].append(obj)
            elif isinstance(obj, Bars):
                distr["other_bars"].append(obj)
            elif isinstance(obj, Spectra):
                distr["spectra"].append(obj)
            elif isinstance(obj, SingleSpectrum):
                distr["single"].append(obj)
            else:
                distr["other"].append(obj)
        return distr


class SerialWriter(Writer):
    """Base class for writers, that produce multiple files.

    Parameters
    ----------
    destination: str or pathlib.Path
        Directory, to which generated files should be written.
    filename_template: str or string.Template
        Template for names of generated files, defaults to  '${filename}.${ext}'.

    Attributes
    ----------
    destination
    mode
    filename_template

    Class Attributes
    ----------------
    extension: str
        Default extension of generated files.
    """

    extension = ""

    def __init__(
        self,
        destination: Union[str, Path],
        mode: str = "x",
        filename_template: Union[str, Template] = "${filename}.${ext}",
    ):
        super().__init__(destination, mode)
        self.filename_template = filename_template

    @property
    def destination(self) -> Path:
        """pathlib.Path: Directory, to which generated files should be written.

        Raises
        ------
        FileNotFoundError
            If given destination doesn't exist or is not a directory.
        """
        return self._destination

    @destination.setter
    def destination(self, destination: Union[str, Path]) -> None:
        destination = Path(destination)
        if not destination.is_dir():
            raise FileNotFoundError(
                "Given destination doesn't exist or is not a directory."
            )
        self._destination = destination

    @property
    def filename_template(self) -> Template:
        """string.Template: Template that will be used for generation of names of files
        produced by this object. It is stored as a `string.Template` object, if string
        is given instead, it will be converted. Only predefined identifiers may be used
        and they are as follows:
            ${filename} - base name of the file (without extension);
            ${ext} - appropriate file extension, stored in `extension` class attribute;
            ${num} - number of file according to internal counter;
            ${genre} - genre of exported data.

        Raises
        ------
        ValueError
            If given template or string contain any unexpected identifiers.
        """
        return self._filename_template

    @filename_template.setter
    def filename_template(self, filename_template: Union[str, Template]) -> None:
        if isinstance(filename_template, str):
            filename_template = Template(filename_template)
        try:
            filename_template.substitute(filename="", ext="", num="", genre="")
        except ValueError as error:
            # TODO: add list of unexpected identifiers given
            raise ValueError("Unexpected identifiers given.") from error
        self._filename_template = filename_template

    def _iter_handles(
        self, filenames: Iterable[str], genre: str, **kwargs
    ) -> (TextIO, Any):
        """Helper method for iteration over generated files. Given additional kwargs
        will be passed to `open()` method.

        Parameters
        ----------
        filenames: list of str
            list of source filenames
        genre: str
            genre name for filename_template

        Yields
        ------
        TextIO
            file handle, will be closed automatically
        any
            values corresponding to particular filename, given in `values` parameter
        """
        for num, fnm in enumerate(filenames):
            filename = self.filename_template.substitute(
                filename=Path(fnm).stem, ext=self.extension, num=num, genre=genre
            )
            with self.destination.joinpath(filename).open(
                self.mode, **kwargs
            ) as handle:
                yield handle
