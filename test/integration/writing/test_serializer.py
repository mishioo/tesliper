import copy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given
from hypothesis import strategies as st

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


def resurect(tesliper, path):
    writer = ArchiveWriter(destination=path)
    writer.write(tesliper)
    loader = ArchiveLoader(source=path)
    return loader.load()


@given(
    blade=st.lists(
        st.booleans(),
        min_size=len(with_mols.conformers),
        max_size=len(with_mols.conformers),
    )
)
def test_serialization_kept(blade):
    tslr = copy.deepcopy(with_mols)
    with TemporaryDirectory() as temppath:
        with tslr.conformers.trimmed_to(blade):
            resurected = resurect(tslr, Path(temppath) / "archive.tslr")
            assert resurected.conformers.kept == tslr.conformers.kept


@pytest.mark.parametrize("tesliper", [empty, with_args, with_mols, with_spectra])
def test_serialization(tmp_path, tesliper):
    resurected = resurect(tesliper, tmp_path / "archive.tslr")
    assert resurected.input_dir == tesliper.input_dir
    assert resurected.output_dir == tesliper.output_dir
    assert resurected.wanted_files == tesliper.wanted_files
    assert (
        resurected.conformers.allow_data_inconsistency
        == tesliper.conformers.allow_data_inconsistency
    )
    assert resurected.conformers.filenames == tesliper.conformers.filenames
    assert resurected.conformers.kept == tesliper.conformers.kept
    assert resurected.conformers == tesliper.conformers
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
