import pathlib
import collections

import pydub
import praatio.tgio
import openpyxl
from clldutils.misc import lazyproperty


class Doculect:
    def __init__(self, d):
        self.dir = pathlib.Path(d)

    def _path(self, ext):
        return list(self.dir.glob('*.' + ext))[0]

    @property
    def id(self):
        return self._path('xlsx').stem

    @lazyproperty
    def audio(self):
        return pydub.AudioSegment.from_wav(self._path('wav'))

    @lazyproperty
    def praat_textgrid(self):
        return praatio.tgio.openTextgrid(self._path('TextGrid'))

    def iter_transcriptions(self):
        wb = openpyxl.load_workbook(self._path('xlsx'), data_only=True)
        header = None
        for sname in wb.sheetnames:
            sheet = wb[sname]
            for i, row in enumerate(sheet.rows):
                row = ["" if col.value is None else '{0}'.format(col.value).strip() for col in row]
                if i == 0:
                    header = row
                else:
                    assert header
                    yield collections.OrderedDict(zip(header, row))
            break
