import shutil
import pathlib

import pytest


@pytest.fixture
def doculect_dir(tmp_path):
    d = tmp_path / 'doculect'
    shutil.copytree(pathlib.Path(__file__).parent / 'doculect', d)
    return d
