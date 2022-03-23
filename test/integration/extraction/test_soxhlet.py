from pathlib import Path
from unittest.mock import patch

from tesliper import extraction as ex

fixtures_dir = Path(__file__).parent.parent / "fixtures"


def test_abnormal_termination_warning():
    with patch.object(ex.soxhlet.logger, "warning") as warning:
        sox = ex.Soxhlet(fixtures_dir, wanted_files=["fal-input-error"])
        data = sox.extract()
        assert not data["fal-input-error"]["normal_termination"]
        assert warning.called


def test_normal_termination_no_warning():
    with patch.object(ex.soxhlet.logger, "warning") as warning:
        sox = ex.Soxhlet(fixtures_dir, wanted_files=["fal-freq"])
        _ = sox.extract()
        assert not warning.called
