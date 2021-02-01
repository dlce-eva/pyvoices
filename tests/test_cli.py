import os

import pydub.utils

from pyvoices.__main__ import main


def test_chunk(doculect_dir, mocker):
    if 'CI' in os.environ:
        mocker.patch('pyvoices.commands.chunk.save', mocker.Mock())
    main(['chunk', str(doculect_dir)])
    res = doculect_dir.joinpath('chunks', 'new_moon.mp3')
    if 'CI' not in os.environ:
        assert res.exists()
        assert pydub.utils.mediainfo(res)['TAG']['album'] == 'doculect'

