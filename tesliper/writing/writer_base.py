"""Interface for witing data to disk.

This module contains :func:`.writer` factory function that enables to dynamically create
a writer object that's responsible for saving data in a desired output format.
:func:`.writer` instantiates a subclass of :class:`WriterBase`, an Abstract Base Class
also defined here. :class:`WriterBase` provides an interface for all serial data writers
(objects that export conformers' data to multiple files) used by ``tesliper``.

:class:`WriterBase` expects it's subclasses to provide an *extention* class attribute,
which is used as an extension of files produced by this particular writer, and also as
an identifier for the output format, used by the :func:`.writer` factory function.
``tesliper`` is shipped with four such writers: :class:`.TxtWriter` for writting to .txt
files, :class:`.CsvWriter` for writting in CSV format, :class:`.XlsxWriter` for
creating Excel files, and :class:`.GjfWriter` for preparing Gaussian input files.

You may want to export your data to other file formats - in such case you will need to
implement your own writer. To do this, subclass :class:`WriterBase`, provide it's
*extension* as mentioned above, and implement writing methods for data you intend to
support in your writer. The table below lists these methods, along with a brief
description and :class:`.DataArray`-like object, for which the method will be called by
writer's :meth:`~.WriterBase.write` method.

.. list-table:: Methods used by default to write certain data
    :header-rows: 1

    * - Writer's Method
      - Description
      - Associated array
    * - :meth:`~.WriterBase.overview`
      - General information about conformers: energies, imaginary frequencies,
        stoichiometry.
      - :class:`.Energies`
    * - :meth:`~.WriterBase.energies`
      - Detailed information about conformers' relative energy,
        including calculated populations
      - :class:`.Energies`
    * - :meth:`~.WriterBase.single_spectrum`
      - A spectrum - calculated for single conformer or averaged.
      - :class:`.SingleSpectrum`
    * - :meth:`~.WriterBase.spectral_data`
      - Data related to spectral activity, but not convertible to spectra.
      - :class:`.SpectralData`
    * - :meth:`~.WriterBase.spectral_activities`
      - Data that may be used to simulate conformers' spectra.
      - :class:`.SpectralActivities`
    * - :meth:`~.WriterBase.spectra`
      - Spectra for multiple conformers.
      - :class:`.Spectra`
    * - :meth:`~.WriterBase.transitions`
      - Electronic transitions from ground to excited state, contributing to each band.
      - :class:`.Transitions`
    * - :meth:`~.WriterBase.geometry`
      - Geometry (positions of atoms in space) of conformers.
      - :class:`.Geometry`

.. note::

    These methods are not abstract methods, but will still raise a
    ``NotImplementedError`` if called. This is to let you omit implementation of methods
    you don't need or wouldn't make sense for the particular format and still provide an
    abstract interface. ``tesliper`` takes advantage of this in it's implementation of
    :class:`.GjfWriter`, which only implements :meth:`~.GjfWriter.geometry` method,
    because export of, e.g. a calculated spectrum as a Gaussian output would be
    pointless.

Writer object decides which of these methods to call based on the type of each
:class:`.DataArray`-like object passed to the :meth:`~.WriterBase.write` method. For
some of them, it also passes additional :class:`.DataArray`-like objects, referred to as
*extras*, e.g. correspomding :class:`.Bands` for spectral data. See documentation for
particular method to learn, which of its parameters are mandatory, which are optional,
and which should expect ``None`` as a possible value of *extra*.

When implementing one of these methods in your writer, you should take care of opening
and closing file files, formatting data you export, and writing to the file. For the
first part you may use one of the helper methods that provide a ready-to-use file
handles: :meth:`~.WriterBase._iter_handles` for writing to many files in batch or
:meth:`~.WriterBase._get_handle` for writing to one file only. Both require a template
that will be used to generate filename for produced files. To learn more about how these
templates are handled by ``tesliper``, see :meth:`~.WriterBase.make_name` documentation.

As mentioned before, writer object uses type of the :class:`.DataArray`-like object (or,
more precisely, a name of its class) to decide which method to use for writing to disk.
If you introduce a new subclass of :class:`.DataArray` for handling some genres, you
will need to tell the Writer class, how it should handle these new objects. This is done
by implementing a custom handler method. It's name should begin with an underscore,
followed by the name of your subclass in lower case, followed by "_handler". Also, it
should take two parameters: *data* and *extras*. First one is a list of instances of
your subclass, second one is a dictionary of special-case genres, both retrieved from
arguments given to :meth:`~.WriterBase.write` method (for details on which genres as
treated as special cases, see :meth:`~.WriterBase.distribute_data`). Handler is
responsible for calling appropriate writing method with arguments it needs.

Here is an example: let's assume you have implemented a custom :class:`.DataArray`
subclass for "ldip" and "lrot" genres with some additional functionality, but you'd like
``tesliper`` to treat it as the original :class:`.ElectronicActivities` class for
purposes of writing to disk.

.. code-block:: python

    class LengthActivities(ElectronicActivities):
        associated_genres = ("ldip", "lrot")
        ...  # custom functionality implemented here

    class UpdatedTxtWriter(TxtWriter):
        extension = "txt"

        def _lengthactivities_handler(self, data, extras):
            # written like ``ElectronicActivities``, so just delegate to its handler
            self._electronicactivities_handler(data, extras)

If you'd like to treat this new subclass differently, then you should provide a custom
writting method for this kind of data:

.. code-block:: python

    class UpdatedTxtWriter(TxtWriter):
        extension = "txt"

        def length_activities(
            self,
            band: Bands,
            data: List[LengthActivities],
            name_template: Union[str, Template] = "${conf}.${cat}-${det}.${ext}",
        ):
            # we will use ``_iter_handles`` method for opening/closing files
            template_params = {"genre": band.genre, "cat": "activity", "det": "length"}
            handles = self._iter_handles(band.filenames, name_template, template_params)
            # we will iterate conformer by conformer
            values = zip(*[arr.values for arr in data])
            for values, handle in zip(values, handles):
                ...  # writting logic

        def _lengthactivities_handler(self, data, extras):
            self.length_activities(band=extras["wavelengths"], data=data)

In both cases ``UpdatedTxtWriter`` will be picked by the :func:`.writer` instead of the
original :class:`.TxtWriter`, thanks to the automatic registration done by the base
class :class:`.WriterBase `.

.. warning::

    If ``extension = "txt"`` line would be omitted in the ``UpdatedTxtWriter``
    definition, it would be picked by the :func:`.writer` for "txt" format anyway,
    because ``extension``'s value would be inherited from :class:`.TxtWriter`.
    If you want to prevent this, provide a different ``extension`` class attribute.
    If your custom writer should still use the same extension as one of the default
    writers, provide ``extension`` also as an instance-level attribute:

    .. code-block:: python

        class UpdatedTxtWriter(TxtWriter):
            extension = ""  # do not register
            
            def __init__(self, destination, mode):
                super().__init__(destination, mode)
                self.extension = "txt"  # use in generated filenames
"""
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


_WRITERS: Dict[str, Type["WriterBase"]] = {}


def writer(
    fmt: str, destination: Union[str, Path], mode: str = "x", **kwargs
) -> "WriterBase":
    """Factory function that returns concrete implementation of :class:`.WriterBase`
    subclass, most recently defined for export to *fmt* file format.

    Parameters
    ----------
    fmt : str
        File format, to which export will be done.
    destination : Union[str, Path]
        Path to file or direcotry, to which export will be done.
    mode : str
        Specifies how writing to file should be handled. Should be one of
        characters: "a" (append to existing file), "x" (only write if file doesn't
        exist yet), or "w" (overwrite file if it already exists). Defaults to "x".
    kwargs
        Any additional keword arguments will be passed as-is to the constructor of the
        retrieved :class:`.WriterBase` subclass.

    Returns
    -------
    WriterBase
        Initialized :class:`.WriterBase` subclass most recently defined for export to
        *fmt* file format.

    Raises
    ------
    ValueError
        If :class:`.WriterBase` subclass for export to *fmt* file format was not
        defined.
    """
    try:
        return _WRITERS[fmt](destination, mode, **kwargs)
    except KeyError:
        message = f"Unknown file format: {fmt}."
        if fmt.startswith(".") and fmt[1:] in _WRITERS:
            message += f" Did you mean '{fmt[1]}'?"
        raise ValueError(message)


# CLASSES
class WriterBase(ABC):
    """Base class for writers that handle export process based on genre of exported
    data.
    
    Subclasses should provide an :attr:`.extension` class-level attribute and writting
    methods that subclass intend to support (see below). Value of :attr:`.extension`
    will be used to register subclass as a default writer for export to files that this
    value indicates ("txt", "csv", *etc.*). Not providing value for this attribute
    results in a ``TypeError`` exception. If subclass should not be registered, use
    an empty string as the attribute's value.

    :class:`.WriterBase` provides a :meth:`.write` method for writing arbitrary
    :class:`.DataArray`-like objects to disk. It dispatches those objects to appropriate
    writing methods based on their type. Those writing methods are:

        | :meth:`.overview`,
        | :meth:`.energies`,
        | :meth:`.single_spectrum`,
        | :meth:`.spectral_data`,
        | :meth:`.spectral_activities`,
        | :meth:`.spectra`,
        | :meth:`.transitions`,
        | :meth:`.geometry`.

    To learn more about implementing custom writers, see their documentation and
    :mod:`.writer_base` documentation or :ref:`extend` section.
    """

    _header = dict(
        zpecorr="Zero-point Corr.",
        tencorr="Thermal Corr.",
        stoichiometry="Stoichiometry",
        entcorr="Enthalpy Corr.",
        geometry="Geometry",
        optimization_completed="Optimized",
        input_geom="Input Geom.",
        command="Command",
        multiplicity="Multiplicity",
        transitions="Transitions",
        cpu_time="CPU Time",
        gibcorr="Gibbs Corr.",
        charge="Charge",
        normal_termination="Termination",
        filenames="Filename",
        freq="Frequencies",
        mass="Red. masses",
        frc="Frc consts",
        ramanactiv="Raman Activ",
        depolarp="Depolar (P)",
        depolaru="Depolar (U)",
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
        zpecorr="{:> 10.4f}",
        tencorr="{:> 10.4f}",
        entcorr="{:> 10.4f}",
        gibcorr="{:> 10.4f}",
        stoichiometry="{}",
        geometry="{}",
        optimization_completed="{}",
        input_geom="{}",
        command="{}",
        multiplicity="{:^ 12d}",
        charge="{:^ 6d}",
        transitions="{}",
        cpu_time="{}",
        normal_termination="{}",
        filenames="{}",
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
        ramanactiv="{:> 10.4f}",
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
        zpecorr="0.0000",
        tencorr="0.0000",
        entcorr="0.0000",
        gibcorr="0.0000",
        multiplicity="{0",
        charge="0",
        stoichiometry="",
        geometry="",
        optimization_completed="",
        input_geom="",
        command="",
        transitions="",
        cpu_time="",
        normal_termination="",
        filenames="",
        freq="0.0000",
        mass="0.0000",
        frc="0.0000",
        ramanactiv="0.0000",
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
    """Default order, in which energy-related data is written to files."""

    # TODO: add support for generic FloatArray and InfoArray

    @property
    @classmethod
    @abstractmethod
    def extension(cls) -> str:
        """Identifier of this writer, indicating the format of files generated,
        and a default extension of those files used by the :meth:`.make_name` method.

        Returns
        -------
        str
            Default extension of files generated by this writer and it's identifier.
        """
        return ""

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # TODO: ignore empty strings
        _WRITERS[cls.extension] = cls

    def __init__(self, destination: Union[str, Path], mode: str = "x"):
        """
        Parameters
        ----------
        destination: str or pathlib.Path
            Directory, to which generated files should be written.
        mode: str
            Specifies how writing to file should be handled. Should be one of
            characters: 'a' (append to existing file), 'x' (only write if file doesn't
            exist yet), or 'w' (overwrite file if it already exists).
        """
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
            Dictionary with :class:`.DataArray`-like objects, sorted by their type.
            Each {key: value} pair is {name of the type in lowercase format:
            list of :class:`.DataArray` objects of this type}.
        extras : dict
            Spacial-case genres: extra information used by some writer methods
            when exporting data. Available {key: value} pairs (if given in *data*) are:

            | corrections: dict of {"energy genre": :class:`.FloatArray`},
            | frequencies: :class:`.Bands`,
            | wavelengths: :class:`.Bands`,
            | excitation: :class:`.Bands`,
            | stoichiometry: :class:`.InfoArray`,
            | charge: :class:`.IntegerArray`,
            | multiplicity: :class:`.IntegerArray`
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
        ``"${identifier}"`` where "identifier" is the name of identifier.
        Available names and their meaning are:

        | ``${ext}`` - appropriate file extension
        | ``${conf}`` - name of the conformer
        | ``${num}`` - number of the file according to internal counter
        | ``${genre}`` - genre of exported data
        | ``${cat}`` - category of produced output
        | ``${det}`` - category-specific detail

        The ``${ext}`` identifier is filled with the value of Writers :attr:`.extension`
        attribute if not explicitly given as parameter to this method's call. Values for
        other identifiers should be provided by the caller.

        Parameters
        ----------
        template : str or string.Template
            Template that will be used to generate filenames. It should contain only
            known identifiers, listed above.
        conf : str
            value for ``${conf}`` identifier, defaults to empty string.
        num : str or int
            value for ``${str}`` identifier, defaults to empty string.
        genre : str
            value for ``${genre}`` identifier, defaults to empty string.
        cat : str
            value for ``${cat}`` identifier, defaults to empty string.
        det : str
            value for ``${det}`` identifier, defaults to empty string.
        ext : str
            value for ``${ext}`` identifier, defaults to empty string.

        Raises
        ------
        ValueError
            If given template or string contains any unexpected identifiers.

        Examples
        --------
        Must be first subclassed and instantiated:

        >>> class MyWriter(WriterBase):
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
        """  # TODO: update examples
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
        :meth:`Path.open` method. Implemented as context manager for use with ``with``
        statement.

        Parameters
        ----------
        template : str or string.Template
            Template that will be used to generate filenames.
        template_params : dict
            Dictionary of {identifier: value} for `.make_name` method.
        open_params : dict, optional
            Arguments for :meth:`Path.open` used to open file.

        Yields
        ------
        IO
            file handle, will be closed automatically after ``with`` statement exits
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
        will be passed to :meth:`Path.open` method.

        Parameters
        ----------
        filenames: list of str
            list of source filenames, used as value for `${conf}` placeholder
            in *name_template*
        template_params : dict
            Dictionary of {identifier: value} for `.make_name` method.
        open_params : dict, optional
            arguments for :meth:`Path.open` used to open file.

        Yields
        ------
        TextIO
            file handle, will be closed automatically on next iteration
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
                "Got multiple *Transitions* objects, but can write contents "
                "of only one such object for .write() call."
            )
        self.transitions(transitions=data[0], wavelengths=extras["wavelengths"])

    def _geometry_handler(self, data: List[Geometry], extras: Dict[str, Any]) -> None:
        if len(data) > 1:
            raise ValueError(
                "Got multiple *Geometry* objects, but can write contents "
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
        """Writes :class:`.DataArray`-like objects to disk, decides how to write them
        based on the type of each object. If some types of given objects are not
        supported by this writer, data of this type is ignored and a warning is emitted.

        Parameters
        ----------
        data : List
            :class:`.DataArray`-like objects that should be written to disk.
        """
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
        frequencies: Optional[Bands] = None,
        stoichiometry: Optional[InfoArray] = None,
        name_template: Union[str, Template] = "",
    ):
        """Intercafe for generating an overview of known conformers: values of energies,
        number of imaginary frequencies, and stoichiometry for each conformer. Evoked
        when handling :class:`.Energies` objects.

        Parameters
        ----------
        energies
            List of objects representing different energies genres for each conformer.
            Mandatory in custom implementation.
        frequencies
            :class:`.Bands` of "freq" genre, with list of frequencies for each
            conformer. Mandatory in custom implementation. May be ``None`` when method
            evoked by handler.
        stoichiometry
            Stoichiometry of each conformer. Mandatory in custom implementation. May be
            ``None`` when method evoked by handler.
        name_template
            Template that defines naming scheme for files generated by this method.
            May be omitted in custom implementation.

        Raises
        ------
        NotImplementedError
            Whenever called, this is an interface that should not be used directly.
        """
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def energies(
        self,
        energies: Energies,
        corrections: Optional[FloatArray] = None,
        name_template: Union[str, Template] = "",
    ):
        """Interface for writing energies values, and optionally their corrections.
        Evoked when handling :class:`.Energies` objects.

        Parameters
        ----------
        energies
            Conformers' energies. Mandatory in custom implementation.
        corrections
            Correction of energies values. Mandatory in custom implementation.
            May be ``None`` when method evoked by handler.
        name_template
            Template that defines naming scheme for files generated by this method.
            May be omitted in custom implementation.

        Raises
        ------
        NotImplementedError
            Whenever called, this is an interface that should not be used directly.
        """
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def single_spectrum(
        self, spectrum: SingleSpectrum, name_template: Union[str, Template] = ""
    ):
        """Interface for writing a single spectrum to disk: calculated for one conformer
        or averaged. Evoked when handling :class:`.SingleSpectrum` objects.

        Parameters
        ----------
        spectrum
            Single calculated spectrum. Mandatory in custom implementation.
        name_template
            Template that defines naming scheme for files generated by this method.
            May be omitted in custom implementation.
        
        Raises
        ------
        NotImplementedError
            Whenever called, this is an interface that should not be used directly.
        """
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def spectral_data(
        self,
        band: Bands,
        data: List[SpectralData],
        name_template: Union[str, Template] = "",
    ):
        """Interface for writing multiple objects with spectral data that is not a
        spectral activity (cannot be converted to signal intensity). Evoked when
        handling one of the: :class:`.VibrationalData`, :class:`.ElectronicData`,
        :class:`.ScatteringData` objects.

        Parameters
        ----------
        band
            Band at which transitions occur for each conformer.
            Mandatory in custom implementation.
        data
            List of objects representing different spectral data genres (but not
            spectral activities). Mandatory in custom implementation.
        name_template
            Template that defines naming scheme for files generated by this method.
            May be omitted in custom implementation.
        
        Raises
        ------
        NotImplementedError
            Whenever called, this is an interface that should not be used directly.
        """
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def spectral_activities(
        self,
        band: Bands,
        data: List[SpectralActivities],
        name_template: Union[str, Template] = "",
    ):
        """Interface for writing multiple objects with spectral activities (data that
        may be converted to signal intensity). Evoked when handling one of the:
        :class:`.VibrationalActivities`, :class:`.ElectronicActivities`,
        :class:`.ScatteringActivities` objects.

        Parameters
        ----------
        band
            Band at which transitions occur for each conformer.
            Mandatory in custom implementation.
        data
            List of objects representing different spectral activities genres.
            Mandatory in custom implementation.
        name_template
            Template that defines naming scheme for files generated by this method.
            May be omitted in custom implementation.
        
        Raises
        ------
        NotImplementedError
            Whenever called, this is an interface that should not be used directly.
        """
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def spectra(self, spectra: Spectra, name_template: Union[str, Template] = ""):
        """Interface for writing a set of spectra of one type calculated for many
        conformers. Evoked when handling :class:`.Spectra` objects.

        Parameters
        ----------
        spectra
            Spectra of one type calculated for multiple conformers.
            Mandatory in custom implementation.
        name_template
            Template that defines naming scheme for files generated by this method.
            May be omitted in custom implementation.
        
        Raises
        ------
        NotImplementedError
            Whenever called, this is an interface that should not be used directly.
        """
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def transitions(
        self,
        transitions: Transitions,
        wavelengths: Bands,
        only_highest: bool = True,
        name_template: Union[str, Template] = "",
    ):
        """Interface for writing single object with electronic transitions data.
        Evoked when handling :class:`.Transitions` objects.

        Parameters
        ----------
        transitions
            List of objects representing different spectral data genres (but not
            spectral_activities). Mandatory in custom implementation.
        wavelengths
            Wavelengths at which transitions occur for each conformer.
            Mandatory in custom implementation.
        only_highest
            Boolean flag indicating if all transitions should be written to disk or only
            these transition that contributes the most for each wavelength/
            May be omitted in custom implementation.
        name_template
            Template that defines naming scheme for files generated by this method.
            May be omitted in custom implementation.

        Raises
        ------
        NotImplementedError
            Whenever called, this is an interface that should not be used directly.
        """
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")

    def geometry(
        self,
        geometry: Geometry,
        charge: Optional[Union[IntegerArray, Sequence[int], int]] = None,
        multiplicity: Optional[Union[IntegerArray, Sequence[int], int]] = None,
        name_template: Union[str, Template] = "",
    ):
        """Interface for writing single object with geometry of each conformer.
        Evoked when handling :class:`.Geometry` objects.

        Parameters
        ----------
        geometry
            Positions of atoms in each conformer. Mandatory in custom implementation.
        charge
            Value of each structure's charge. Mandatory in custom implementation.
        multiplicity
            Value of each structure's multiplicity. Mandatory in custom implementation.
        name_template
            Template that defines naming scheme for files generated by this method.
            May be omitted in custom implementation.

        Raises
        ------
        NotImplementedError
            Whenever called, this is an interface that should not be used directly.
        """
        raise NotImplementedError(f"Class {type(self)} does not implement this method.")
