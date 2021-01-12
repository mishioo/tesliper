from pathlib import Path

import pytest

from tesliper import Tesliper, Spectra
from tesliper.glassware import SingleSpectrum
from tesliper.writing.serializer import ArchiveWriter, ArchiveLoader

fixtures_dir = Path(__file__).parent.parent / "fixtures"

empty = Tesliper()
with_args = Tesliper(
    input_dir=fixtures_dir,
    output_dir=fixtures_dir,
    wanted_files=["one_file.out", "two_file.out"],
)
with_mols = Tesliper(input_dir=fixtures_dir, wanted_files=["meoh-1.out", "meoh-2.out"],)
with_mols.extract()
with_spectra = Tesliper()
with_spectra.spectra["ir"] = Spectra(
    genre="ir",
    values=[[0.3, 0.2, 10, 300, 2], [0.5, 0.8, 12, 150, 5]],
    abscissa=[10, 20, 30, 40, 50],
    width=5,
    fitting="gaussian",
    scaling=2.0,
    offset=70,
    filenames=["meoh-1.out", "meoh-2.out"],
)
with_spectra.averaged["ir"] = SingleSpectrum(
    "ir",
    [0.3, 0.2, 10, 300, 2],
    [10, 20, 30, 40, 50],
    width=5,
    fitting="gaussian",
    scaling=3.5,
    offset=15,
    filenames=["meoh-1.out", "meoh-2.out"],
    averaged_by="gib",
)


@pytest.mark.parametrize("tesliper", [empty, with_args, with_mols, with_spectra])
def test_serialization(tmp_path, tesliper):
    path = tmp_path / "archive.tslr"
    writer = ArchiveWriter(destination=path)
    writer.write(tesliper)
    loader = ArchiveLoader(source=path)
    resurected = loader.load()
    assert resurected.input_dir == tesliper.input_dir
    assert resurected.output_dir == tesliper.output_dir
    assert resurected.wanted_files == tesliper.wanted_files
    assert (
        resurected.molecules.allow_data_inconsistency
        == tesliper.molecules.allow_data_inconsistency
    )
    assert resurected.molecules.filenames == tesliper.molecules.filenames
    assert resurected.molecules.kept == tesliper.molecules.kept
    assert resurected.molecules == tesliper.molecules
    # check if all attributes are identical, including numpy arrays
    for genre, spc in resurected.spectra.items():
        for key, value in spc.__dict__.items():
            try:
                assert value == tesliper.spectra[genre].__dict__[key]
            except ValueError:
                assert (value == tesliper.spectra[genre].__dict__[key]).all()
    for genre, spc in resurected.averaged.items():
        for key, value in spc.__dict__.items():
            try:
                assert value == tesliper.averaged[genre].__dict__[key]
            except ValueError:
                assert (value == tesliper.averaged[genre].__dict__[key]).all()
