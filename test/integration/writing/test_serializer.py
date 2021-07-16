import copy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tesliper import Spectra, Tesliper
from tesliper.glassware import SingleSpectrum
from tesliper.writing.serializer import ArchiveLoader, ArchiveWriter

fixtures_dir = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def wanted_files():
    return ["meoh-1.out", "meoh-2.out"]


@pytest.fixture
def empty():
    return Tesliper()


@pytest.fixture
def tesliper(tmp_path, wanted_files):
    return Tesliper(
        input_dir=fixtures_dir, output_dir=tmp_path, wanted_files=wanted_files
    )


@pytest.fixture
def inconsistent(tesliper):
    tesliper.allow_data_inconsistency = True
    return tesliper


@pytest.fixture
def extracted(tesliper):
    tesliper.extract()
    return tesliper


@pytest.fixture
def trimmed(extracted):
    extracted.conformers.kept = [False, True]
    return extracted


@pytest.fixture
def with_spectra(extracted):
    extracted.spectra["ir"] = Spectra(
        genre="ir",
        values=[[0.3, 0.2, 10, 300, 2], [0.5, 0.8, 12, 150, 5]],
        abscissa=[10, 20, 30, 40, 50],
        width=5,
        fitting="gaussian",
        scaling=2.0,
        offset=70,
        filenames=["meoh-1.out", "meoh-2.out"],
    )
    return extracted


@pytest.fixture
def with_averaged(empty):
    empty.averaged["ir"] = SingleSpectrum(
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
    return empty


def resurect(tesliper, path):
    file = path / "archive.tslr"
    writer = ArchiveWriter(destination=file)
    writer.write(tesliper)
    loader = ArchiveLoader(source=file)
    return loader.load()


@given(blade=st.lists(st.booleans(), min_size=2, max_size=2))
def test_serialization_kept(blade):
    tslr = Tesliper(
        input_dir=fixtures_dir,
        wanted_files=["meoh-1.out", "meoh-2.out"],
    )
    tslr.extract()
    with TemporaryDirectory() as temppath:
        with tslr.conformers.trimmed_to(blade):
            resurected = resurect(tslr, Path(temppath))
            assert resurected.conformers.kept == tslr.conformers.kept


def test_serialization_init_params_empty(tmp_path, empty):
    resurected = resurect(empty, tmp_path)
    assert resurected.input_dir == empty.input_dir
    assert resurected.output_dir == empty.output_dir
    assert resurected.wanted_files == empty.wanted_files


def test_serialization_init_params(tmp_path, tesliper):
    resurected = resurect(tesliper, tmp_path)
    assert resurected.input_dir == tesliper.input_dir
    assert resurected.output_dir == tesliper.output_dir
    assert resurected.wanted_files == tesliper.wanted_files


def test_serialization_inconsistent(tmp_path, inconsistent):
    resurected = resurect(inconsistent, tmp_path)
    assert (
        resurected.conformers.allow_data_inconsistency
        == inconsistent.conformers.allow_data_inconsistency
    )


def test_serialization_extracted(tmp_path, extracted):
    resurected = resurect(extracted, tmp_path)
    assert resurected.conformers == extracted.conformers
    assert resurected.conformers.filenames == extracted.conformers.filenames


def test_serialization(tmp_path, trimmed):
    resurected = resurect(trimmed, tmp_path)
    assert resurected.conformers.kept == trimmed.conformers.kept
    assert resurected.conformers == trimmed.conformers


def test_serialization_spectra(with_spectra, tmp_path):
    resurected = resurect(with_spectra, tmp_path)
    for genre, spc in resurected.spectra.items():
        for key, value in spc.__dict__.items():
            try:
                assert value == with_spectra.spectra[genre].__dict__[key]
            except ValueError:
                assert (value == with_spectra.spectra[genre].__dict__[key]).all()


def test_serialization_averaged(with_averaged, tmp_path):
    resurected = resurect(with_averaged, tmp_path)
    for genre, spc in resurected.averaged.items():
        for key, value in spc.__dict__.items():
            try:
                assert value == with_averaged.averaged[genre].__dict__[key]
            except ValueError:
                assert (value == with_averaged.averaged[genre].__dict__[key]).all()
