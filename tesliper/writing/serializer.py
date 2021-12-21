"""Serialization and deserialization of :class:`.Tesliper` objects."""
import json
import logging
import zipfile
from json.decoder import JSONArray
from json.scanner import py_make_scanner
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union

import tesliper  # absolute import to solve problem of circular imports
from tesliper import datawork as dw
from tesliper.glassware import Conformers, SingleSpectrum, Spectra

logger = logging.getLogger(__name__)


class ArchiveWriter:
    """Class for serialization of Tesliper objects.

    Structure of the produced archive::

        .
        ├───arguments: {input_dir=str, output_dir=str, wanted_files=[str]}
        ├───parameters: {"ir": {params}, ..., "roa": {params}}
        ├───conformers
        │   ├───arguments: {"allow_data_inconsistency": bool}
        │   ├───filenames: [str]
        │   ├───kept: [bool]
        │   └───data
        │       ├───filename_1: {genre=str: data}
        |       ...
        │       └───filename_N: {genre=str: data}
        └───spectra
            ├───experimental  # not implemented yet
            ├───calculated
            │   ├───spectra_genre_1: {attr_name: Spectra.attr}
            |   ...
            │   └───spectra_genre_N: {attr_name: Spectra.attr}
            └───averaged
                ├───spectra_genre_1-energies-genre-1: {attr_name: SingleSpectrum.attr}
                ...
                └───spectra_genre_N-energies-genre-N: {attr_name: SingleSpectrum.attr}
    """

    def __init__(
        self, destination: Union[str, Path], mode: str = "x", encoding: str = "utf-8"
    ):
        """
        Parameters
        ----------
        destination : Union[str, Path]
            Path to target file.
        mode : str, optional
            Specifies how writing to file should be handled. Should be one of
            characters: 'a' (append to existing file), 'x' (only write if file doesn't
            exist yet), or 'w' (overwrite file if it already exists). Defaults to "x".
        encoding : str, optional
            Encoding of the output, by default "utf-8"
        """
        self.mode = mode
        self.destination = destination
        self.encoding = encoding
        self.root = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

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
        if not destination.exists() and self.mode == "a":
            raise FileNotFoundError(
                "Mode 'a' was specified, but given file doesn't exist."
            )
        elif destination.exists() and self.mode == "x":
            raise FileExistsError(
                "Mode 'x' was specified, but given file already exists."
            )
        elif not destination.parent.exists():
            raise FileNotFoundError("Parent directory of specified file doesn't exist.")
        else:
            logger.debug(f"File {destination} ok for writing.")
        vars(self)["destination"] = destination

    def open(self):
        self.root = zipfile.ZipFile(self.destination, mode=self.mode)
        return self

    def close(self):
        self.root.close()

    def write(self, obj: "tesliper.Tesliper"):
        with self:
            self._write_arguments(obj.input_dir, obj.output_dir, obj.wanted_files)
            self._write_parameters(obj.parameters)
            self._write_conformers(obj.conformers)
            # self._write_experimental(tesliper.experimental)  # not supported yet
            for spc in obj.averaged.values():
                self._write_averaged(spc)
            for spc in obj.spectra.values():
                self._write_calculated(spc)

    def _write_arguments(
        self,
        input_dir: Union[Path, str] = None,
        output_dir: Union[Path, str] = None,
        wanted_files: Iterable[str] = None,
    ):
        with self.root.open("arguments.json", mode="w") as handle:
            handle.write(
                self.jsonencode(
                    {
                        "input_dir": str(input_dir) if input_dir else None,
                        "output_dir": str(output_dir) if output_dir else None,
                        "wanted_files": list(wanted_files) if wanted_files else None,
                    }
                )
            )

    def _write_parameters(self, parameters: dict):
        # TODO: Implement more universal way of serializing fitting
        #       this won't deserialize custom fitting functions
        to_write = {key: params.copy() for key, params in parameters.items()}
        for params in to_write.values():
            params["fitting"] = params["fitting"].__name__
        with self.root.open("parameters.json", mode="w") as handle:
            handle.write(self.jsonencode(to_write))

    def _write_conformers(self, conformers: Conformers):
        self._write_conformers_arguments(
            allow_data_inconsistency=conformers.allow_data_inconsistency
        )
        self._write_filenames(conformers.filenames)
        self._write_kept(conformers.kept)
        for filename in conformers.filenames:
            self._write_mol(filename=filename, mol=conformers[filename])

    def _write_conformers_arguments(self, allow_data_inconsistency: bool):
        with self.root.open("conformers/arguments.json", mode="w") as handle:
            handle.write(
                self.jsonencode({"allow_data_inconsistency": allow_data_inconsistency})
            )

    def _write_filenames(self, filenames: List[str]):
        with self.root.open("conformers/filenames.json", mode="w") as handle:
            handle.write(self.jsonencode(filenames))

    def _write_mol(self, filename: str, mol: dict):
        with self.root.open(f"conformers/data/{filename}.json", mode="w") as handle:
            handle.write(self.jsonencode(mol))

    def _write_kept(self, kept: List[bool]):
        with self.root.open("conformers/kept.json", mode="w") as handle:
            handle.write(self.jsonencode(kept))

    def _write_experimental(self, spectra: Dict[str, SingleSpectrum]):
        # TODO: implement this
        raise NotImplementedError
        # "spectra/experimental.json"

    def _write_calculated(self, spectra: Spectra):
        path = f"spectra/calculated/{spectra.genre}.json"
        with self.root.open(path, mode="w") as handle:
            handle.write(
                self.jsonencode(
                    {
                        "genre": spectra.genre,
                        "filenames": spectra.filenames.tolist(),
                        "values": spectra.values.tolist(),
                        "abscissa": spectra.abscissa.tolist(),
                        "width": spectra.width,
                        "fitting": spectra.fitting,
                        "scaling": spectra.scaling,
                        "offset": spectra.offset,
                        "allow_data_inconsistency": spectra.allow_data_inconsistency,
                    }
                )
            )

    def _write_averaged(self, spectrum: SingleSpectrum):
        path = f"spectra/averaged/{spectrum.genre}-{spectrum.averaged_by}.json"
        with self.root.open(path, mode="w") as handle:
            handle.write(
                self.jsonencode(
                    {
                        "genre": spectrum.genre,
                        "filenames": spectrum.filenames.tolist(),
                        "values": spectrum.values.tolist(),
                        "abscissa": spectrum.abscissa.tolist(),
                        "width": spectrum.width,
                        "fitting": spectrum.fitting,
                        "scaling": spectrum.scaling,
                        "offset": spectrum.offset,
                        "averaged_by": spectrum.averaged_by,
                    }
                )
            )

    def jsonencode(
        self,
        obj: Any,
        *,
        skipkeys=False,
        ensure_ascii=True,
        check_circular=True,
        allow_nan=True,
        cls=None,
        indent=None,
        separators=None,
        default=None,
        sort_keys=False,
        **kw,
    ) -> bytes:
        """json.dumps wrapper, that encodes JSON produced."""
        return json.dumps(
            obj,
            skipkeys=skipkeys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            cls=cls,
            indent=indent,
            separators=separators,
            default=default,
            sort_keys=sort_keys,
            **kw,
        ).encode(self.encoding)


class ConformerDecoder(json.JSONDecoder):
    """JSONDecoder subclass, that transforms all inner lists into tuples."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        in_array = False

        def parse_array(*_args, **_kwargs):
            nonlocal in_array
            if not in_array:
                in_array = True
                values, end = JSONArray(*_args, **_kwargs)
                in_array = False
            else:
                values, end = JSONArray(*_args, **_kwargs)
                values = tuple(values)
            return values, end

        self.parse_array = parse_array
        self.scan_once = py_make_scanner(self)


class ArchiveLoader:
    """Class for deserialization of Tesliper objects."""

    def __init__(self, source: Union[str, Path], encoding: str = "utf-8"):
        """
        Parameters
        ----------
        source : Union[str, Path]
            Path to the source file.
        encoding : str, optional
            Source file encoding, by default "utf-8".
        """
        self.source = source
        self.encoding = encoding
        self.root = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def open(self):
        self.root = zipfile.ZipFile(self.source, mode="r")
        return self

    def close(self):
        self.root.close()

    @property
    def source(self) -> Path:
        """pathlib.Path: File, from which data should read.

        Notes
        -----
        If str given, it will be converted to pathlib.Path.

        Raises
        ------
        FileNotFoundError
            If given destination doesn't exist.
        """
        return self._destination

    @source.setter
    def source(self, destination: Union[str, Path]) -> None:
        destination = Path(destination)
        if not destination.exists():
            raise FileNotFoundError("Given destination doesn't exist.")
        self._destination = destination

    def load(self) -> "tesliper.Tesliper":
        with self:
            tslr = tesliper.Tesliper(**self._load("arguments.json"))
            tslr.parameters = self._load_parameters()
            filenames = self._load("conformers/filenames.json")
            mols = (
                (
                    name,
                    self.jsondecode(
                        self.root.read(f"conformers/data/{name}.json"),
                        cls=ConformerDecoder,
                    ),
                )
                for name in filenames
            )  # iterator producing key-value pairs
            tslr.conformers = Conformers(
                mols, **self._load("conformers/arguments.json")
            )
            tslr.conformers.kept = self._load("conformers/kept.json")
            for file in self.root.namelist():
                if "experimental" in file:
                    # TODO: implement this
                    ...  # not implemented yet
                elif "calculated" in file:
                    params = self._load(file)
                    tslr.spectra[params["genre"]] = Spectra(**params)
                elif "averaged" in file:
                    params = self._load(file)
                    tslr.averaged[
                        (params["genre"], params["averaged_by"])
                    ] = SingleSpectrum(**params)
        return tslr

    def _load(self, dest):
        return self.jsondecode(self.root.read(dest))

    def _load_parameters(self):
        parameters = self._load("parameters.json")
        for params in parameters.values():
            params["fitting"] = getattr(dw, params["fitting"])
        return parameters

    def jsondecode(
        self,
        string: bytes,
        *,
        cls=None,
        object_hook=None,
        parse_float=None,
        parse_int=None,
        parse_constant=None,
        object_pairs_hook=None,
        **kw,
    ) -> Any:
        """json.loads wrapper, that decodes bytes before parsing as JSON."""
        return json.loads(
            string.decode(self.encoding),
            cls=cls,
            object_hook=object_hook,
            parse_float=parse_float,
            parse_int=parse_int,
            parse_constant=parse_constant,
            object_pairs_hook=object_pairs_hook,
            **kw,
        )
