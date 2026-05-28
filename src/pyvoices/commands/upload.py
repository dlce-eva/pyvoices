"""
Work in progress

Upload soundfiles to CDSTAR

Reads from raw/csv/<lg-id>/audio/
"""
import pathlib

from cdstarcat import Catalog
from pycdstar.media import File
from clldutils.clilib import PathType


def register(parser):
    parser.add_argument('catalog', type=PathType(type='file'))

    # raw/csv for AmazonianVoices, raw/data for VanuatuVoices
    parser.add_argument('data-dir', type=PathType(type='dir'))

    parser.add_argument('collection')  # infer from a cldfbench dir?


def run(args):
    from os import environ

    with Catalog(
            args.catalog,
            cdstar_url=environ['CDSTAR_URL'],
            cdstar_user=environ['CDSTAR_USER'],
            cdstar_pwd=environ['CDSTAR_PWD']
    ) as cat:
        done = {obj.metadata['name'] for obj in cat}
        upload_all(args.collection, args.data_dir, cat, done)
        print(len(list(cat)))


class Wav(File):
    """
    We package all three bitstreams created by `cldfbench download` in one CDSTAR object.
    """
    def add_bitstreams(self):
        res = []
        for suffix in ['mp3', 'ogg']:
            p = self.path.parent / '{}.{}'.format(self.path.stem, suffix)
            assert p.exists()
            res.append(File(p, name=p.name, type='soundfile'))
        return res


def upload_all(source, cat, done):
    i = 0
    for lgdir in sorted(source.iterdir(), key=lambda p: p.stem):
        if not lgdir.is_dir():
            continue
        if not lgdir.joinpath('audio').exists():
            continue
        print(lgdir)
        for wav in sorted(lgdir.joinpath('audio').glob('*.wav'), key=lambda p: p.stem):
            if wav.stem not in done:
                for _, _, obj in cat.create(
                    wav,
                    lambda p: {
                        "collection": "amazonianvoices",
                        "name": p.stem,
                        "type": "soundfile"
                    },
                    object_class=Wav
                ):
                    i += 1
                    if i >= 200:
                        return
