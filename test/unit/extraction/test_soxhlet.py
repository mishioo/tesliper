import builtins
import os
from unittest import mock
from tesliper.extraction import soxhlet as sx
import pytest


@pytest.fixture
def lsdir():
    with mock.patch(
        "tesliper.extraction.soxhlet.os.listdir",
        return_value="a.out b.out b.gjf".split(" "),
    ) as lsdir:
        yield lsdir


@pytest.fixture
def sox():
    yield sx.Soxhlet()


def test_path_default(sox):
    assert sox.path == os.getcwd()


def test_path_non_existing_path(sox, monkeypatch):
    monkeypatch.setattr(sx.os.path, "isdir", mock.Mock(return_value=False))
    with pytest.raises(FileNotFoundError):
        sox.path = "\\path\\doesnt\\exist"
    sx.os.path.isdir.assert_called()


def test_path_ok(lsdir, sox, monkeypatch):
    monkeypatch.setattr(sx.os.path, "isdir", mock.Mock(return_value=True))
    sox.path = "\\path\\is\\ok"
    assert "\\path\\is\\ok" == sox.path
    sx.os.path.isdir.assert_called()
    lsdir.assert_called_with("\\path\\is\\ok")
    assert "a.out b.out b.gjf".split(" ") == sox.files


def test_filter_files_no_extension(sox):
    with pytest.raises(ValueError):
        sox.filter_files()


@pytest.mark.usefixtures("lsdir")
def test_filter_files(sox):
    assert "a.out b.out".split(" ") == sox.filter_files(".out")
    assert ["b.gjf"] == sox.filter_files(".gjf")


def test_filter_files_empty(sox):
    assert [] == sox.filter_files(".log")


@pytest.mark.usefixtures("lsdir")
def test_guess_extension(sox):
    assert ".out" == sox.guess_extension()
    sox.files = "a.log b.log b.gjf".split(" ")
    assert ".log" == sox.guess_extension()


def test_guess_extension_mixed(sox):
    sox.files = "a.out b.log b.gjf".split(" ")
    with pytest.raises(ValueError):
        sox.guess_extension()


def test_guess_extension_missing(sox):
    sox.files = "b.gjf".split(" ")
    with pytest.raises(TypeError):
        sox.guess_extension()


def test_output_files(sox):
    sox.guess_extension = mock.Mock(return_value=".out")
    sox.filter_files = mock.Mock(return_value=["a.out", "b.out"])
    assert ["a.out", "b.out"] == sox.output_files
    sox.guess_extension.assert_called()
    sox.filter_files.assert_called_with(".out")


@pytest.mark.usefixtures("lsdir")
def test_files(sox):
    assert "a.out b.out b.gjf".split(" ") == sox.files


@pytest.fixture
def output(monkeypatch):
    mocked = mock.PropertyMock(return_value=["a.out", "b.out"])
    monkeypatch.setattr(sx.Soxhlet, "output_files", mocked)
    return mocked


def test_extract_iter(monkeypatch, output):
    sox = sx.Soxhlet()
    parser = mock.Mock(parse=mock.Mock(return_value={}))
    sox.parser = parser
    with monkeypatch.context() as monkey:
        monkey.setattr(builtins, "open", mock.mock_open())
        out = dict(sox.extract_iter())
    assert {"a.out": {}, "b.out": {}} == out
    output.assert_called()
    parser.parse.assert_called()
    assert 2 == parser.parse.call_count
