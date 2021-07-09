# IMPORTS
import logging as lgg
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from string import Template
from typing import (
    IO,
    Any,
    AnyStr,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from ..glassware.arrays import (
    Bars,
    DataArray,
    ElectronicBars,
    Energies,
    FloatArray,
    Geometry,
    InfoArray,
    IntegerArray,
    Transitions,
    VibrationalBars,
)
from ..glassware.spectra import SingleSpectrum, Spectra

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


_WRITERS: Dict[str, Type["Writer"]] = {}


def writer(fmt: str, destination, mode, **kwargs) -> "Writer":
    try:
        return _WRITERS[fmt](destination, mode, **kwargs)
    except KeyError:
        raise ValueError(f"Unknown file format: {fmt}.")


# CLASSES
class Writer(ABC):
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
    default_template = "${conf}.${ext}"

    @property
    @classmethod
    @abstractmethod
    def extension(cls) -> str:
        return ""

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _WRITERS[cls.extension] = cls

    def __init__(self, destination: Union[str, Path], mode: str = "x"):
        # TODO: unify subclasses __init__
        self.mode = mode
        self.destination = destination
        # TODO: make all handlers in subclasses use filename_template
        self.filename_template = self.default_template
        self._handle = None

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

    def check_file(self, file: Union[str, Path]) -> Path:
        file = Path(file)
        if not file.exists() and self.mode == "a":
            raise FileNotFoundError(
                "Mode 'a' was specified, but given file doesn't exist."
            )
        elif file.exists() and self.mode == "x":
            raise FileExistsError(
                "Mode 'x' was specified, but given file already exists."
            )
        elif not file.parent.exists():
            raise FileNotFoundError("Parent directory of specified file doesn't exist.")
        else:
            logger.debug(f"File {file} ok for writing.")
            return file

    @property
    def destination(self) -> Path:
        """pathlib.Path: Directory, to which generated files should be written.

        Raises
        ------
        FileNotFoundError
            If given destination doesn't exist or is not a directory.
        """
        return vars(self)["destination"]

    @destination.setter
    def destination(self, destination: Union[str, Path]) -> None:
        destination = Path(destination)
        if not destination.is_dir():
            raise FileNotFoundError(
                "Given destination doesn't exist or is not a directory."
            )
        vars(self)["destination"] = destination

    @staticmethod
    def distribute_data(data: List) -> Tuple[Dict[str, List], Dict[str, Any]]:
        """Sorts given data by genre category for use by specialized writing methods.

        Returns
        -------
        dict
            Dictionary with DataArray objects sorted by genre category.
            Available key: value pairs are:
                energies: List of Energies,
                vibrational: List of VibrationalBars,
                electronic: List of ElectronicBars,
                spectra: List of Spectra,
                single: List of SingleSpectrum,
                other: List of DataArray,
                corrections = dict of genre: FloatArray,
                frequencies = ElectronicBars or None,
                wavelenghts = VibrationalBars or None,
                stoichiometry = InfoArray or None
        """
        # TODO: correct docstring
        distr: Dict[str, List] = dict()
        extras: Dict[str, Any] = dict()
        for obj in data:
            if obj.genre.endswith("corr"):
                corrs = extras["corrections"] = extras.get("corrections", dict())
                corrs[obj.genre[:3]] = obj
            elif obj.genre == "freq":
                extras["frequencies"] = obj
            elif obj.genre == "wave":
                extras["wavelengths"] = obj
            elif obj.genre == "stoichiometry":
                extras["stoichiometry"] = obj
            elif obj.genre == "charge":
                extras["charge"] = obj
            elif obj.genre == "multiplicity":
                extras["multiplicity"] = obj
            else:
                name = type(obj).__name__.lower()
                values = distr[name] = distr.get(name, list())
                values.append(obj)
        return distr, extras

    @property
    def filename_template(self) -> Template:
        """string.Template: Template that will be used for generation of names of files
        produced by this object. It is stored as a `string.Template` object, if string
        is given instead, it will be converted. Only predefined identifiers may be used
        and they are as follows:
            ${conf} - name of the conformer;
            ${ext} - appropriate file extension, stored in `extension` class attribute;
            ${num} - number of the file according to internal counter;
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
            filename_template.substitute(conf="", ext="", num="", genre="")
        except ValueError as error:
            # TODO: add list of unexpected identifiers given
            raise ValueError("Unexpected identifiers given.") from error
        self._filename_template = filename_template

    @contextmanager
    def _get_handle(
        self, name: str, genre: str, num: int = 0, **kwargs
    ) -> Iterator[IO[AnyStr]]:
        """Helper method for creating files. Given additional kwargs will be passed to
        `open()` method. Implemented as context manager for use with `with` statement.

        Parameters
        ----------
        name: str
            value for `${conf}` placeholder in `filename_template`
        genre: str
            genre name for `${genre}` placeholder in `filename_template`
        num: int
            number for `${num}` placeholder in `filename_template`
        kwargs
            arguments for `Path.open()` used to open file

        Yields
        ------
        IO
            file handle, will be closed automatically after `with` statement exits
        """
        filename = self.filename_template.substitute(
            conf=name, ext=self.extension, num=num, genre=genre
        )
        file = self.check_file(self.destination.joinpath(filename))
        with file.open(self.mode, **kwargs) as handle:
            self._handle = handle
            yield handle

    def _iter_handles(
        self, filenames: Iterable[str], genre: str, **kwargs
    ) -> Iterator[IO[AnyStr]]:
        """Helper method for iteration over generated files. Given additional kwargs
        will be passed to `open()` method.

        Parameters
        ----------
        filenames: list of str
            list of source filenames, used as value for `${conf}` placeholder
            in `filename_template`
        genre: str
            genre name for `${genre}` placeholder in `filename_template`
        genre: str
            genre name for `${genre}` placeholder in `filename_template`
        kwargs
            arguments for `Path.open()` used to open file

        Yields
        ------
        TextIO
            file handle, will be closed automatically
        """
        for num, fnm in enumerate(filenames):
            filename = self.filename_template.substitute(
                conf=fnm, ext=self.extension, num=num, genre=genre
            )
            file = self.check_file(self.destination.joinpath(filename))
            with file.open(self.mode, **kwargs) as handle:
                yield handle

    def _energies_handler(self, data: List[Energies], extras: Dict[str, Any]) -> None:
        self.overview(
            data,
            frequencies=extras.get("frequencies"),
            stoichiometry=extras.get("stoichiometry"),
        )
        for en in data:
            self.energies(
                en, corrections=extras.get("corrections", dict()).get(en.genre)
            )

    def _vibrationalbars_handler(
        self, data: List[VibrationalBars], extras: Dict[str, Any]
    ) -> None:
        self.bars(band=extras["frequencies"], bars=data)

    def _electronicbars_handler(
        self, data: List[ElectronicBars], extras: Dict[str, Any]
    ) -> None:
        self.bars(band=extras["wavelengths"], bars=data)

    def _transitions_handler(
        self, data: List[Transitions], extras: Dict[str, Any]
    ) -> None:
        self.transitions(transitions=data, wavelengths=extras["wavelengths"])

    def _geometry_handler(self, data: List[Geometry], extras: Dict[str, Any]) -> None:
        self.geometry(
            data,
            charge=extras.get("charge"),
            multiplicity=extras.get("multiplicity"),
        )

    def _spectra_handler(self, data: List[Spectra], _extras) -> None:
        for spc in data:
            self.spectra(spc)

    def _singlespectrum_handler(self, data: List[SingleSpectrum], _extras) -> None:
        for spc in data:
            self.spectrum(spc)

    def write(self, data: List) -> None:
        distributed, extras = self.distribute_data(data)
        for name, data_ in distributed.items():
            try:
                handler = getattr(self, f"_{name}_handler")
                handler(data_, extras)
            except (NotImplementedError, AttributeError):
                logger.warning(f"{type(self)} does not handle '{name}' type data.")

    def overview(
        self,
        energies: Sequence[Energies],
        frequencies: Optional[DataArray] = None,
        stoichiometry: Optional[InfoArray] = None,
    ):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def energies(self, energies: Energies, corrections: Optional[FloatArray] = None):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def spectrum(self, spectrum: SingleSpectrum):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def bars(self, band: Bars, bars: List[Bars]):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def spectra(self, spectra: Spectra):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def transitions(
        self,
        transitions: Transitions,
        wavelengths: ElectronicBars,
        only_highest: bool = True,
    ):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def geometry(
        self,
        geometry: Geometry,
        charge: Optional[Union[IntegerArray, Sequence[int], int]] = None,
        multiplicity: Optional[Union[IntegerArray, Sequence[int], int]] = None,
    ):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")
