"""
Functionality to curate the data collected for one language variety, or doculect.

Processing status of the "raw" data is infered from the existence of derived artefacts.
"""
import pathlib
import collections

import pydub
import pympi
import praatio.tgio
import openpyxl
from clldutils.misc import lazyproperty


def case_insensitive_glob_pattern(pattern):
    def either(c):
        return '[%s%s]' % (c.lower(), c.upper()) if c.isalpha() else c
    return ''.join(map(either, pattern))


class Doculect:
    def __init__(self, d):
        self.dir = pathlib.Path(d)

    def _path(self, ext):
        p = '*.' + case_insensitive_glob_pattern(ext)
        try:
            return list(self.dir.glob(p))[0]
        except:
            raise ValueError(p)

    @property
    def id(self):
        return self._path('wav').stem

    @lazyproperty
    def audio(self):
        return pydub.AudioSegment.from_wav(self._path('wav'))

    @lazyproperty
    def praat_textgrid(self):
        try:
            p = self._path('TextGrid')
        except ValueError:
            # Need to convert eaf to TextGrid
            assert self._path('eaf')
            eaf = pympi.Eaf(str(self._path('eaf')))
            p = self.dir / '{}.TextGrid'.format(self.id)
            eaf.to_textgrid().to_file(str(p))
        return praatio.tgio.openTextgrid(p)

    def iter_transcriptions(self, concept_tier='English'):
        try:
            p = self._path('xlsx')
        except ValueError:
            # No xlsx transcriptions file: seed one with the concept labels from praat:
            p = self.dir / '{}.xlsx'.format(self.id)
            wb = openpyxl.Workbook()
            wb.active.append([self.id, concept_tier])
            seen = set()
            for t in self.praat_textgrid.tierDict[concept_tier].entryList:
                if t.label and t.label not in seen:
                    wb.active.append(['', t.label])
                    seen.add(t.label)
            wb.save(p)
        header = None
        wb = openpyxl.load_workbook(p, data_only=True)
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
