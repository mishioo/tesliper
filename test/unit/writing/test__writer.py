from pathlib import Path
from unittest import mock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tesliper.writing import Writer, SerialWriter

normal_writers = [Writer]
serial_writers = [SerialWriter]
all_writers = [Writer, SerialWriter]


@pytest.fixture
def destination_is_dir(monkeypatch):
    monkeypatch.setattr(Path, "is_dir", lambda _: True)


@pytest.fixture
def destination_is_not_dir(monkeypatch):
    monkeypatch.setattr(Path, "is_dir", lambda _: False)


@pytest.fixture
def destination_is_file(monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda _: True)


@pytest.fixture
def destination_is_not_file(monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda _: False)


@pytest.fixture
def destination_exists(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda _: True)


@pytest.mark.usefixtures("destination_is_not_file", "destination_is_not_dir")
@pytest.fixture
def destination_doesnt_exists(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda _: False)


@pytest.mark.parametrize("writer_class", serial_writers)
@given(st.text())
def test_writer_mode_init(writer_class, mode):
    if mode not in ("a", "x", "w"):
        with pytest.raises(ValueError):
            writer_class(destination="", mode=mode)


@pytest.mark.usefixtures("destination_doesnt_exists")
@pytest.mark.parametrize("writer_class", normal_writers)
def test_writer_init_append_no_dest(writer_class):
    with pytest.raises(FileNotFoundError):
        writer_class(destination="", mode="a")


@pytest.mark.usefixtures("destination_doesnt_exists")
@pytest.mark.parametrize("writer_class", normal_writers)
def test_writer_init_overwrite_no_dest(writer_class, monkeypatch):
    parent_mock = mock.Mock()
    parent_mock.exists = mock.Mock(return_value=True)
    monkeypatch.setattr(Path, "parent", parent_mock)
    wrt = writer_class(destination="", mode="w")
    assert wrt.mode == "w"


@pytest.mark.usefixtures("destination_exists")
@pytest.mark.parametrize("writer_class", normal_writers)
def test_writer_init_overwrite(writer_class):
    wrt = writer_class(destination="", mode="w")
    assert wrt.mode == "w"


@pytest.mark.usefixtures("destination_exists")
@pytest.mark.parametrize("writer_class", normal_writers)
def test_writer_init_new_only_no_dest(writer_class):
    with pytest.raises(FileExistsError):
        writer_class(destination="", mode="x")


@pytest.mark.usefixtures("destination_is_not_dir")
@pytest.mark.parametrize("mode", ("a", "x", "w"))
@pytest.mark.parametrize("writer_class", serial_writers)
def test_serial_writer_init_no_dest(writer_class, mode):
    with pytest.raises(FileNotFoundError):
        writer_class(destination="", mode=mode)
