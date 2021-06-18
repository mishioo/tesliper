import zipfile
from pathlib import Path
import json
from json.decoder import JSONArray
from json.scanner import py_make_scanner
from typing import Union, List, Dict, Any

from ._writer import Writer
from ..glassware import Molecules, Spectra, SingleSpectrum
from .. import datawork as dw
import tesliper  # absolute import to solve problem of circular imports


class ArchiveWriter(Writer):
    """Class for serialization of Tesliper objects.

    Structure of the produced archive:
    .
    ├───arguments: {input_dir=str, output_dir=str, wanted_files=[str]}
    ├───parameters: {"vibra": {params}, "electr": {params}}
    ├───molecules
    │   ├───arguments: {"allow_data_inconsistency": bool}
    │   ├───filenames: [str]
    │   ├───kept: [bool]
    │   └───data
    │       ├───filename_1: {genre=str: data}
    |       ...
    │       └───filename_N: {genre=str: data}
    └───spectra
        ├───experimental: {genre=str: SingleSpectrum}
        ├───calculated: {genre=str: Spectra}
        └───averaged: {genre=str: SingleSpectrum}
    """

    def __init__(
        self, destination: Union[str, Path], mode: str = "x", encoding: str = "utf-8"
    ):
        super().__init__(destination=destination, mode=mode)
        self.encoding = encoding
        self.root = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def open(self):
        self.root = zipfile.ZipFile(self.destination, mode=self.mode)
        return self

    def close(self):
        self.root.close()

    def write(self, obj: "tesliper.Tesliper"):
        with self:
            self._write_arguments(obj.input_dir, obj.output_dir, obj.wanted_files)
            self._write_parameters(obj.parameters)
            self._write_molecules(obj.molecules)
            # self._write_experimental(tesliper.experimental)  # not supported yet
            for spc in obj.averaged.values():
                self._write_averaged(spc)
            for spc in obj.spectra.values():
                self._write_calculated(spc)

    def _write_arguments(
        self,
        input_dir: Union[Path, str] = None,
        output_dir: Union[Path, str] = None,
        wanted_files: List[str] = None,
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
        for params in parameters.values():
            params["fitting"] = params["fitting"].__name__
        with self.root.open("parameters.json", mode="w") as handle:
            handle.write(self.jsonencode(to_write))

    def _write_molecules(self, molecules: Molecules):
        self._write_molecules_arguments(
            allow_data_inconsistency=molecules.allow_data_inconsistency
        )
        self._write_filenames(molecules.filenames)
        self._write_kept(molecules.kept)
        for filename in molecules.filenames:
            self._write_mol(filename=filename, mol=molecules[filename])

    def _write_molecules_arguments(self, allow_data_inconsistency: bool):
        with self.root.open("molecules/arguments.json", mode="w") as handle:
            handle.write(
                self.jsonencode({"allow_data_inconsistency": allow_data_inconsistency})
            )

    def _write_filenames(self, filenames: List[str]):
        with self.root.open("molecules/filenames.json", mode="w") as handle:
            handle.write(self.jsonencode(filenames))

    def _write_mol(self, filename: str, mol: dict):
        with self.root.open(f"molecules/data/{filename}.json", mode="w") as handle:
            handle.write(self.jsonencode(mol))

    def _write_kept(self, kept: List[bool]):
        with self.root.open("molecules/kept.json", mode="w") as handle:
            handle.write(self.jsonencode(kept))

    def _write_experimental(self, spectra: Dict[str, SingleSpectrum]):
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
        path = f"spectra/averaged/{spectrum.genre}.json"
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
            filenames = self._load("molecules/filenames.json")
            mols = (
                (
                    name,
                    self.jsondecode(
                        self.root.read(f"molecules/data/{name}.json"),
                        cls=ConformerDecoder,
                    ),
                )
                for name in filenames
            )  # iterator producing key-value pairs
            tslr.molecules = Molecules(mols, **self._load("molecules/arguments.json"))
            for file in self.root.namelist():
                if "experimental" in file:
                    ...  # not implemented yet
                elif "calculated" in file:
                    params = self._load(file)
                    tslr.spectra[params["genre"]] = Spectra(**params)
                elif "averaged" in file:
                    params = self._load(file)
                    tslr.averaged[params["genre"]] = SingleSpectrum(**params)
        return tslr

    def _load(self, dest):
        return self.jsondecode(self.root.read(dest))

    def _load_parameters(self):
        params = self._load("parameters.json")
        params["vibra"]["fitting"] = getattr(dw, params["vibra"]["fitting"])
        params["electr"]["fitting"] = getattr(dw, params["electr"]["fitting"])
        return params

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
