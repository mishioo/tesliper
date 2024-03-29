import builtins
from pathlib import Path
from unittest import mock

import pytest

from tesliper.extraction import soxhlet as sx


@pytest.fixture
def files():
    return [Path(p) for p in "a.out b.out b.gjf setup.txt".split()]


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
    assert "out" == sox.guess_extension()


@pytest.fixture
def mixed_files():
    return [Path(p) for p in "a.out b.log b.gjf".split()]


def test_guess_extension_mixed(sox, mixed_files, monkeypatch):
    monkeypatch.setattr(sx.Path, "iterdir", mock.Mock(return_value=mixed_files))
    with pytest.raises(ValueError):
        sox.guess_extension()


def test_output_files_mixed(sox, mixed_files, monkeypatch):
    monkeypatch.setattr(sx.Path, "iterdir", mock.Mock(return_value=mixed_files))
    assert sox.output_files == []


def test_guess_extension_missing(sox, monkeypatch):
    monkeypatch.setattr(sx.Path, "iterdir", mock.Mock(return_value=[Path("b.gjf")]))
    with pytest.raises(FileNotFoundError):
        sox.guess_extension()


def test_output_files_missing(sox, monkeypatch):
    monkeypatch.setattr(sx.Path, "iterdir", mock.Mock(return_value=[Path("b.gjf")]))
    assert sox.output_files == []


def test_output_files_missing_explicit_ext(sox, monkeypatch):
    sox.extension = ".out"
    monkeypatch.setattr(sx.Path, "iterdir", mock.Mock(return_value=[Path("b.gjf")]))
    assert sox.output_files == []


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


@pytest.fixture
def files_tree(tmp_path):
    tree = [
        tmp_path / p
        for p in "a.out b.out b.gjf inner/setup.txt inner/c.out inner/c.gjf".split()
    ]
    for f in tree:
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("w") as h:
            h.write("")
    return tree


@pytest.fixture
def rsox(files_tree, tmp_path):
    return sx.Soxhlet(path=tmp_path, recursive=True)


def test_rsox_all_files(rsox, files_tree, tmp_path):
    assert set(rsox.all_files) == set(files_tree)


def test_rsox_output_files(rsox, tmp_path):
    assert set(rsox.output_files) == {
        tmp_path / p for p in "a.out b.out inner/c.out".split()
    }


def test_rsox_no_recursive_output_files(rsox, tmp_path):
    rsox.recursive = False
    assert set(rsox.output_files) == {tmp_path / p for p in "a.out b.out".split()}


def test_parse_one_found_in_path(sox, monkeypatch):
    monkeypatch.setattr(sox.parser, "parse", mock.Mock(side_effect=lambda x: x))
    assert sox.parse_one("setup.txt") == sox.path / "setup.txt"


def test_parse_one_absolute_path(sox, monkeypatch):
    # first is_file called for source appended to sx.path
    monkeypatch.setattr(sx.Path, "is_file", mock.Mock(side_effect=[False, True]))
    monkeypatch.setattr(sox.parser, "parse", mock.Mock(side_effect=lambda x: x))
    assert sox.parse_one("/some/path/setup.txt") == Path("/some/path/setup.txt")


def test_parse_one_file_not_found(sox, monkeypatch):
    monkeypatch.setattr(sx.Path, "is_file", mock.Mock(return_value=False))
    with pytest.raises(FileNotFoundError):
        sox.parse_one("setup.txt")
