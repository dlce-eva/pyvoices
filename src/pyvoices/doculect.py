"""
Functionality to curate the data collected for one language variety, or doculect.

Processing status of the "raw" data is inferred from the existence of derived artefacts.
"""
import logging
import pathlib
import functools
import collections
from collections.abc import Generator
import dataclasses
from typing import Any, Optional, Union

import pydub
import pympi
import praatio.textgrid
from praatio.utilities.constants import Interval
import openpyxl


class Doculect:
    """
    Data for a doculect is organized in a directory containing (eventually) 4 files:
    - an audio file in WAV format (extension .wav)
    - a corresponding ELAN file (extension .eaf)
    - a Praat TextGrid file with the annotations from one tier in ELAN (extension .TextGrid)
    - an Excel sheet mapping concept labels to transcriptions (extension .xlsx)
    """
    def __init__(self, d: Union[str, pathlib.Path]):
        self.dir = pathlib.Path(d)
        self._eaf_tier_name: Optional[str] = None
        self._eaf_tier_names: list[str] = []

    def _path(self, ext: str) -> pathlib.Path:
        pattern = '*.' + ''.join(f'[{c.lower()}{c.upper()}]' if c.isalpha() else c for c in ext)
        try:
            return [p for p in self.dir.glob(pattern) if not p.name.startswith('~$')][0]
        except Exception as e:  # pragma: no cover
            raise ValueError(pattern) from e

    @property
    def id(self) -> str:
        """We take the stem of the WAV file as identifier."""
        return self._path('wav').stem

    @property
    def eaf_tier_name(self) -> Optional[str]:
        return self._eaf_tier_name

    @property
    def eaf_tier_names(self) -> list[str]:
        return self._eaf_tier_names

    @functools.cached_property
    def audio(self) -> pydub.AudioSegment:
        return pydub.AudioSegment.from_wav(self._path('wav'))

    @functools.cached_property
    def praat_textgrid(self) -> praatio.textgrid.Textgrid:
        try:
            p = self._path('TextGrid')
        except ValueError:
            # Need to convert eaf to TextGrid
            assert self._path('eaf')
            eaf = pympi.Eaf(str(self._path('eaf')))
            tier_names = list(eaf.get_tier_names())
            # If only one tier is found take this otherwise print out all available to rerun it
            if len(tier_names) == 1:
                self._eaf_tier_name = tier_names[0]
            else:
                self._eaf_tier_names = tier_names
            p = self.dir / f'{self.id}.TextGrid'
            eaf.to_textgrid().to_file(str(p))
        return praatio.textgrid.openTextgrid(str(p), includeEmptyIntervals=False)

    def intervals(self, concept_tier: str) -> 'Intervals':
        return Intervals.from_textgrid(self.praat_textgrid, concept_tier)

    def to_raw_dir(self):
        pass

    def iter_transcriptions(
            self,
            concept_tier: str = 'Rfc-Form',
            concept_column: str = 'English Translation',
    ) -> Generator[collections.OrderedDict[str, Any], None, None]:
        try:
            p = self._path('xlsx')
        except ValueError:
            # No xlsx transcriptions file: seed one with the concept labels from praat:
            p = self.dir / f'{self.id}.xlsx'
            wb = openpyxl.Workbook()
            wb.active.append([self.id, concept_column])
            seen = set()
            for t in self.praat_textgrid._tierDict[concept_tier].entries:  # pylint: disable=W0212
                if t.label and t.label not in seen:
                    wb.active.append(['', t.label])
                    seen.add(t.label)
            wb.save(p)
        header = None
        wb = openpyxl.load_workbook(p, data_only=True)
        for sname in wb.sheetnames:
            sheet = wb[sname]
            for i, row in enumerate(sheet.rows):
                row = ["" if col.value is None else f'{col.value}'.strip() for col in row]
                if i == 0:
                    header = row
                else:
                    assert header
                    yield collections.OrderedDict(zip(header, row))
            break


@dataclasses.dataclass
class Intervals:
    """Access to the information about intervals read from TextGrid."""
    by_concept: dict[str, list[Interval]] = dataclasses.field(
        default_factory=lambda: collections.defaultdict(list))
    # We map the name of already created chunks to the number of times they have been created in
    # order to be able to create unique filenames.
    existing_chunks: dict[str, int] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_textgrid(cls, textgrid, concept_tier: str) -> 'Intervals':
        """Initialize with the data from a TextGrid file."""
        res = cls()
        for i in textgrid._tierDict[concept_tier].entries:  # pylint: disable=W0212
            res.by_concept[i.label.strip()].append(i)
        return res

    def get(self, concept: str, label: str = '') -> tuple[Optional[Interval], str]:
        """Get the matching interval for the occurrence of concept."""
        if concept in self.existing_chunks:
            self.existing_chunks[concept] += 1
            idx = f'___{self.existing_chunks[concept]}'
        else:
            self.existing_chunks[concept] = 1
            idx = ''

        # We can match a transcription to a label in the Praat file, ...
        try:
            interval = self.by_concept[concept][self.existing_chunks[concept] - 1]
        except IndexError:
            return None, idx
        if label:
            interval = Interval(interval.start, interval.end, label)
        return interval, idx

    def info(self, log: logging.Logger):
        """Log information about the occurrence of concepts in TextGrid and Excel."""
        for c, intervals in self.by_concept.items():
            if c in self.existing_chunks:
                if len(intervals) != self.existing_chunks[c]:
                    log.warning('check occurrences of %s in TextGrid and XLSX', c)
                elif len(intervals) > 1:
                    log.info('duplicates for %s', c)
            else:
                log.info('found %s in TextGrid but not in XLSX', c)
