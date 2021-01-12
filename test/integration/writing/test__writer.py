from pathlib import Path

import pytest

from tesliper.writing import SerialWriter


def test_serial_writer_iter_handles(tmp_path):
    wrt = SerialWriter(destination=tmp_path, mode="w")
    wrt.extension = "ext"
    names = ["a.out", "b.out"]
    handles = wrt._iter_handles(names, "grn")
    oldh, h = None, None
    for num, name in enumerate(names):
        oldh, h = h, next(handles)
        assert oldh is None or oldh.closed
        assert not h.closed
        # genre not used by default filename template
        assert f"{name[:-4]}.ext" == Path(h.name).name
    try:
        next(handles)
    except StopIteration:
        assert h.closed
    else:
        pytest.fail("file handle should be closed")
