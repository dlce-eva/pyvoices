"""
Work in progress

Package data for one doculect into a format as expected as raw data in lexibank/*voices

Aggregates data from multiple elicitation sessions or conceptlists.

Reads concept matches from prompts/*.csv

Reads from single/
- the four different wordlists per language are merged
- chunks are selected if matched to etc/concepts.csv
- chunks are renamed to <language>_<concept>

Writes to per-language subdirectories of packaged/
- languages.csv: language metadata
- data.csv: transcriptions
- chunks/: soundfiles
"""
import shutil
import pathlib
import collections

from csvw.dsv import reader, UnicodeWriter


def package(source, target, concepts, lg):
    glang = lg.get('glang')
    with UnicodeWriter(target / 'languages.csv') as w:
        w.writerow('ORG_LG_NAME,ID,Name,Glottocode,Glottolog_Name,ISO639P3code,Macroarea,Latitude,Longitude,Family,Island,IsProto,Source,LongName'.split(','))
        w.writerow([
            target.name,
            target.name,
            lg['name'],
            lg['glottocode'],
            glang.name if glang else None,
            glang.iso if glang else None,
            glang.macroareas[0].name if glang else None,
            lg['latitude'],
            lg['longitude'],
            'Austronesian',
            'Santo',
            False,
            'Rangelov' + lg['year'],
            None
        ])

    chunks = target / 'chunks'
    if not chunks.exists():
        chunks.mkdir()

    with UnicodeWriter(target / 'data.csv') as w:
        w.writerow([target.name, 'English Translation'])

        for wldir in source.iterdir():
            if wldir.name in concepts:
                for row in reader(wldir / 'transcriptions.csv', dicts=True):
                    if row['id'] in concepts[wldir.name]:
                        for suffix in {'mp3', 'wav', 'ogg'}:
                            shutil.copy(
                                wldir / 'chunks' / '{}.{}'.format(row['id'], suffix),
                                chunks / '{}_{}.{}'.format(
                                    source.name, concepts[wldir.name][row['id']], suffix))
                        w.writerow([row['transcription'], concepts[wldir.name][row['id']]])

def package_all(source, target, concepts, langs):
    for lgdir in source.iterdir():
        if lgdir.is_dir():
            tdir = target / lgdir.name
            if not tdir.exists():
                tdir.mkdir()
            package(lgdir, tdir, concepts, langs[lgdir.name])


def run(args):
    from pyglottolog import Glottolog

    glottolog = Glottolog('../../glottolog/glottolog')
    langs = {r['id']: r for r in reader('languages.csv', dicts=True)}
    for v in langs.values():
        if v['glottocode']:
            v['glang'] = glottolog.languoid(v['glottocode'])

    concepts = collections.defaultdict(dict)
    for p in pathlib.Path('prompts').glob('*.csv'):
        for row in reader(p, dicts=True):
            if row['id']:  # The prompted concept could be matched to a concept in etc/concepts.csv.
                concepts[p.stem][row['lid']] = row['id']
                if p.stem == 'kinship' and row['kinship_code']:
                    concepts[p.stem][row['kinship_code']] = row['id']

    package_all(pathlib.Path('single'), pathlib.Path('packaged'), concepts, langs)
