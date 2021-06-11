import builtins
from pathlib import Path
from unittest import mock
from tesliper.extraction import soxhlet as sx
import pytest


@pytest.fixture
def files():
    return [Path(p) for p in "a.out b.out b.gjf".split()]


@pytest.fixture
def out_files(files):
    return [f for f in files if f.suffix == ".out"]


@pytest.fixture
def lsdir(files):
    with mock.patch.multiple(
        "tesliper.extraction.soxhlet.Path",
        iterdir=mock.Mock(return_value=files),
        is_file=mock.Mock(return_value=True),
    ):
        yield


@pytest.fixture
def sox(lsdir):
    yield sx.Soxhlet()


def test_path_default(sox):
    assert sox.path == Path().resolve()


def test_path_non_existing_path(sox, monkeypatch):
    monkeypatch.setattr(sx.Path, "is_dir", mock.Mock(return_value=False))
    with pytest.raises(FileNotFoundError):
        sox.path = "\\path\\doesnt\\exist"
    sx.Path.is_dir.assert_called()


def test_path_ok(sox, files, monkeypatch):
    monkeypatch.setattr(sx.Path, "is_dir", mock.Mock(return_value=True))
    path = "\\path\\is\\ok"
    sox.path = path
    assert Path(path).resolve() == sox.path
    sx.Path.is_dir.assert_called()
    assert files == sox.all_files


def test_filter_files_no_extension(sox):
    with pytest.raises(ValueError):
        sox.filter_files()


def test_filter_files(sox, out_files):
    assert out_files == sox.filter_files(".out")
    assert [Path("b.gjf")] == sox.filter_files(".gjf")


def test_filter_files_empty(sox):
    assert [] == sox.filter_files(".log")


@pytest.fixture
def log_all_files():
    return [Path(p) for p in "a.log b.log b.gjf".split()]


def test_guess_extension(sox, log_all_files, monkeypatch):
    assert ".out" == sox.guess_extension()


@pytest.fixture
def mixed_files():
    return [Path(p) for p in "a.out b.log b.gjf".split()]


def test_guess_extension_mixed(sox, mixed_files, monkeypatch):
    monkeypatch.setattr(sx.Path, "iterdir", mock.Mock(return_value=mixed_files))
    with pytest.raises(ValueError):
        sox.guess_extension()


def test_guess_extension_missing(sox, monkeypatch):
    monkeypatch.setattr(sx.Path, "iterdir", mock.Mock(return_value=[Path("b.gjf")]))
    with pytest.raises(FileNotFoundError):
        sox.guess_extension()


def test_output_files(sox, out_files, monkeypatch):
    monkeypatch.setattr(sx.Soxhlet, "guess_extension", mock.Mock(return_value=".out"))
    monkeypatch.setattr(sx.Soxhlet, "filter_files", mock.Mock(return_value=out_files))
    assert out_files == sox.output_files
    sox.guess_extension.assert_called()
    sox.filter_files.assert_called_with(".out")


def test_all_files(sox, files):
    assert files == sox.all_files


@pytest.fixture
def output(monkeypatch, out_files):
    mocked = mock.PropertyMock(return_value=out_files)
    monkeypatch.setattr(sx.Soxhlet, "output_files", mocked)
    return mocked


def test_extract_iter(sox, monkeypatch, output):
    monkeypatch.setattr(sx.Path, "open", mock.mock_open())
    monkeypatch.setattr(sox, "parser", mock.Mock(parse=mock.Mock(return_value={})))
    out = dict(sox.extract_iter())
    assert {"a": {}, "b": {}} == out
    output.assert_called()
    sox.parser.parse.assert_called()
    assert 2 == sox.parser.parse.call_count
