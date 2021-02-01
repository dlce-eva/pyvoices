"""

"""
import datetime

from clldutils.clilib import PathType

from pyvoices.doculect import Doculect


def register(parser):
    parser.add_argument('input', type=PathType(type='dir'))
    parser.add_argument(
        '--concept-tier',
        default='Rfc-Form',
        help="Name of the tier in the Praat TextGrid file which contains concept labels.")
    parser.add_argument(
        '--concept-column',
        default='English Translation',
        help="Name of the column in the Excel transcriptions file which contains concept labels.")


def run(args):
    d = Doculect(args.input)
    chunkdir = d.dir / 'chunks'
    if not chunkdir.exists():
        chunkdir.mkdir()

    intervalByConcept = {i.label: i for i in d.praat_textgrid.tierDict[args.concept_tier].entryList}
    count = 0
    for t in d.iter_transcriptions():
        transcription = list(t.values())[0]
        concept = t[args.concept_column]
        if not concept:
            continue  # pragma: no cover
        if concept in intervalByConcept:
            # We can match a transcription to a lable in the Praat file, ...
            interval = intervalByConcept[concept]
            # .. so we can cut out the corresponding audio chunk ...
            audio_chunk = d.audio[interval.start * 1000:interval.end * 1000]
            # ... make it smooth around the edges ...
            audio_chunk.fade_in(5)
            audio_chunk.fade_out(5)
            # ... and make the amplitude match that of the whole audio file:
            audio_chunk.apply_gain(d.audio.dBFS - audio_chunk.dBFS)
            md = {
                'artist': 'Vanuatu Voices',
                'title': '{}: {}'.format(interval.label, transcription),
                'album': d.id,
                'date': datetime.date.today().isoformat(),
                'genre': 'Speech'}
            save(chunkdir, interval, audio_chunk, md, 'wav')
            save(chunkdir, interval, audio_chunk, md, 'mp3', bitrate="128k")
            save(chunkdir, interval, audio_chunk, md, 'ogg', bitrate="128k")
            count += 1
        else:
            args.log.warning('no interval for concept: "{}"'.format(concept))
    args.log.info('created soundfiles for {} concepts in {}'.format(count, chunkdir))


def save(d, interval, chunk, tags, format, **kw):
    chunk.export(str(d / '{}.{}'.format(interval.label, format)), tags=tags, format=format, **kw)
