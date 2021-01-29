import os

import pydub.utils

from pyvoices.__main__ import main


def test_chunk(doculect_dir):
    if 'CI' not in os.environ:
        main(['chunk', str(doculect_dir)])
        res = doculect_dir.joinpath('chunks', 'new_moon.mp3')
        assert res.exists()
        assert pydub.utils.mediainfo(res)['TAG']['album'] == 'doculect'
