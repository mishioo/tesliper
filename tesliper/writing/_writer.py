# IMPORTS
import logging as lgg
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from string import Formatter, Template
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
    Bands,
    DataArray,
    ElectronicActivities,
    ElectronicData,
    Energies,
    FloatArray,
    Geometry,
    InfoArray,
    IntegerArray,
    ScatteringActivities,
    ScatteringData,
    SpectralActivities,
    SpectralData,
    Transitions,
    VibrationalActivities,
    VibrationalData,
)
from ..glassware.spectra import SingleSpectrum, Spectra

# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


_WRITERS: Dict[str, Type["Writer"]] = {}


def writer(fmt: str, destination, mode="x", **kwargs) -> "Writer":
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
        # TODO: add missing headers
        freq="Frequencies",
        mass="Red. masses",
        frc="Frc consts",
        raman="Raman Activ",
        depolarp=r"Depolar (P)",
        depolaru=r"Depolar (U)",
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
        vdip="Dip. (velo)",
        ldip="Dip. (length)",
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
        ir="{:> .4e}",
        vcd="{:> .4e}",
        uv="{:> .4e}",
        ecd="{:> .4e}",
        raman="{:> .4e}",
        roa="{:> .4e}",
        rot="{:> 10.4f}",
        dip="{:> 10.4f}",
        roa1="{:> 10.4f}",
        raman1="{:> 10.4f}",
        vrot="{:> 10.4f}",
        lrot="{:> 10.4f}",
        vosc="{:> 10.4f}",
        losc="{:> 10.4f}",
        vdip="{:> 10.4f}",
        ldip="{:> 10.4f}",
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
        vdip="0.0000",
        ldip="0.0000",
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
    # TODO: add support for generic FloatArray and InfoArray

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
        self.mode = mode
        self.destination = destination
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
        distr : dict
            Dictionary with DataArray objects sorted by their type.
            Each {key: value} pair is {name of the type in lowercase format:
            list of DataArray objects of this type}.
        extras : dict
            Spacial-case genres: extra information used by some writer methods
            when exporting data. Available {key: value} pairs (if given in `data`) are:
                corrections: dict of {energy genre: FloatArray},
                frequencies: Bands,
                wavelengths: Bands,
                excitation: Bands,
                stoichiometry: InfoArray,
                charge: IntegerArray,
                multiplicity: IntegerArray
        """
        distr: Dict[str, List] = dict()
        extras: Dict[str, Any] = dict()
        for obj in data:
            if obj.genre.endswith("corr"):
                corrs = extras["corrections"] = extras.get("corrections", dict())
                corrs[obj.genre[:3]] = obj
            elif obj.genre == "freq":
                extras["frequencies"] = obj
            elif obj.genre == "wavelen":
                extras["wavelengths"] = obj
            elif obj.genre == "ex_en":
                extras["excitation"] = obj
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

    def make_name(
        self,
        template: Union[str, Template],
        conf: str = "",
        num: Union[str, int] = "",
        genre: str = "",
        cat: str = "",
        det: str = "",
        ext: str = "",
    ) -> str:
        """Create filename using given template and given or global values
        for known identifiers. The identifier should be used in the template as
        "${identifier}" where "identifier" is the name of identifier.
        Available names and their meaning are:
            ${ext} - appropriate file extension;
            ${conf} - name of the conformer;
            ${num} - number of the file according to internal counter;
            ${genre} - genre of exported data;
            ${cat} - category of produced output;
            ${det} - category-specific detail.
        The ${ext} identifier is filled with the value of Writers `extension` attribute
        if not explicitly given as parameter to this method's call. Default values
        for other identifiers are just empty strings.

        Parameters
        ----------
        template : str or string.Template
            Template that will be used to generate filenames. It should contain only
            known identifiers, listed above.
        conf : str
            value for ${conf} identifier, defaults to empty string.
        num : str or int
            value for ${str} identifier, defaults to empty string.
        genre : str
            value for ${genre} identifier, defaults to empty string.
        cat : str
            value for ${cat} identifier, defaults to empty string.
        det : str
            value for ${det} identifier, defaults to empty string.
        ext : str
            value for ${ext} identifier, defaults to empty string.

        Raises
        ------
        ValueError
            If given template or string contains any unexpected identifiers.

        Examples
        --------
        Must be first subclassed and instantiated:
        >>> class MyWriter(Writer):
        >>>     extension = "foo"
        >>> wrt = MyWriter("/path/to/some/directory/")

        >>> wrt.make_name(template="somefile.${ext}")
        "somefile.foo"
        >>> wrt.make_name(template="${conf}.${ext}")
        ".foo"  # conf is empty string by default
        >>> wrt.make_name(template="${conf}.${ext}", conf="")
        "conformer.foo"
        >>> wrt.make_name(template="Unknown_identifier_${bla}.${ext}")
        Traceback (most recent call last):
        ValueError: Unexpected identifiers given: bla.
        """
        if isinstance(template, str):
            template = Template(template)
        try:
            return template.substitute(
                conf=conf,
                ext=ext or self.extension,
                num=num,
                genre=genre,
                cat=cat,
                det=det,
            )
        except KeyError as error:
            known = {"conf", "ext", "num", "genre", "cat", "det"}
            # second element of each tuple returned is identifier's name
            ids = {parsed[1] for parsed in Formatter().parse(template.template)}
            raise ValueError(f"Unexpected identifiers given: {ids-known}.") from error

    @contextmanager
    def _get_handle(
        self,
        template: Union[str, Template],
        template_params: dict,
        open_params: Optional[dict] = None,
    ) -> Iterator[IO[AnyStr]]:
        """Helper method for creating files. Given additional kwargs will be passed to
        `open()` method. Implemented as context manager for use with `with` statement.

        Parameters
        ----------
        template : str or string.Template
            Template that will be used to generate filenames.
        template_params : dict
            Dictionary of {identifier: value} for `.make_name` method.
        open_params : dict, optional
            Arguments for `Path.open()` used to open file.

        Yields
        ------
        IO
            file handle, will be closed automatically after `with` statement exits
        """
        open_params = open_params or {}  # empty dict by default
        filename = self.make_name(template=template, **template_params)
        file = self.check_file(self.destination.joinpath(filename))
        with file.open(self.mode, **open_params) as handle:
            self._handle = handle
            yield handle

    def _iter_handles(
        self,
        filenames: Iterable[str],
        template: Union[str, Template],
        template_params: dict,
        open_params: Optional[dict] = None,
    ) -> Iterator[IO[AnyStr]]:
        """Helper method for iteration over generated files. Given additional kwargs
        will be passed to `open()` method.

        Parameters
        ----------
        filenames: list of str
            list of source filenames, used as value for `${conf}` placeholder
            in `name_template`
        template_params : dict
            Dictionary of {identifier: value} for `.make_name` method.
        open_params : dict, optional
            arguments for `Path.open()` used to open file.

        Yields
        ------
        TextIO
            file handle, will be closed automatically
        """
        open_params = open_params or {}  # empty dict by default
        for num, fnm in enumerate(filenames):
            template_params.update({"conf": fnm, "num": num})
            filename = self.make_name(template=template, **template_params)
            file = self.check_file(self.destination.joinpath(filename))
            with file.open(self.mode, **open_params) as handle:
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

    def _vibrationalactivities_handler(
        self, data: List[VibrationalActivities], extras: Dict[str, Any]
    ) -> None:
        self.spectral_activities(band=extras["frequencies"], data=data)

    def _scatteringactivities_handler(
        self, data: List[ScatteringActivities], extras: Dict[str, Any]
    ) -> None:
        self.spectral_activities(band=extras["frequencies"], data=data)

    def _electronicactivities_handler(
        self, data: List[ElectronicActivities], extras: Dict[str, Any]
    ) -> None:
        self.spectral_activities(band=extras["wavelengths"], data=data)

    def _vibrationaldata_handler(
        self, data: List[VibrationalData], extras: Dict[str, Any]
    ) -> None:
        self.spectral_data(band=extras["frequencies"], data=data)

    def _scatteringdata_handler(
        self, data: List[ScatteringData], extras: Dict[str, Any]
    ) -> None:
        self.spectral_data(band=extras["frequencies"], data=data)

    def _electronicdata_handler(
        self, data: List[ElectronicData], extras: Dict[str, Any]
    ) -> None:
        self.spectral_data(band=extras["wavelengths"], data=data)

    def _transitions_handler(
        self, data: List[Transitions], extras: Dict[str, Any]
    ) -> None:
        if len(data) > 1:
            raise ValueError(
                "Got multiple `Transitions` objects, but can write contents "
                "of only one such object for .write() call."
            )
        self.transitions(transitions=data[0], wavelengths=extras["wavelengths"])

    def _geometry_handler(self, data: List[Geometry], extras: Dict[str, Any]) -> None:
        if len(data) > 1:
            raise ValueError(
                "Got multiple `Geometry` objects, but can write contents "
                "of only one such object for .write() call."
            )
        self.geometry(
            data[0],
            charge=extras.get("charge"),
            multiplicity=extras.get("multiplicity"),
        )

    def _spectra_handler(self, data: List[Spectra], _extras) -> None:
        for spc in data:
            self.spectra(spc)

    def _singlespectrum_handler(self, data: List[SingleSpectrum], _extras) -> None:
        for spc in data:
            self.single_spectrum(spc)

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
        name_template: Union[str, Template] = "",
    ):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def energies(
        self,
        energies: Energies,
        corrections: Optional[FloatArray] = None,
        name_template: Union[str, Template] = "",
    ):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def single_spectrum(
        self, spectrum: SingleSpectrum, name_template: Union[str, Template] = ""
    ):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def spectral_data(
        self,
        band: SpectralData,
        data: List[SpectralData],
        name_template: Union[str, Template] = "",
    ):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def spectral_activities(
        self,
        band: SpectralActivities,
        data: List[SpectralActivities],
        name_template: Union[str, Template] = "",
    ):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def spectra(self, spectra: Spectra, name_template: Union[str, Template] = ""):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def transitions(
        self,
        transitions: Transitions,
        wavelengths: Bands,
        only_highest: bool = True,
        name_template: Union[str, Template] = "",
    ):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def geometry(
        self,
        geometry: Geometry,
        charge: Optional[Union[IntegerArray, Sequence[int], int]] = None,
        multiplicity: Optional[Union[IntegerArray, Sequence[int], int]] = None,
        name_template: Union[str, Template] = "",
    ):
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")
