"""

"""
import datetime
from pydub.effects import normalize

from clldutils.clilib import PathType

from pyvoices.doculect import Doculect


# should each audio chunk be normalized so that any sound file has the same loadness?
NORMALIZE = True
# if normalization is desired specify the headroom in dB
NORMALIZE_HEADROOM = 4.
# chunk interval offset in milliseconds
INTERVAL_OFFSET = 50
# fade in/out time in milliseconds
FADE_TIME = 50


# FIXME: Also spit out a CLDF Wordlist? an EDICTOR Wordlist?
#ID>-----ALIGNMENT>------CLASSES>COGID>--COGIDS>-COGNACY>CONCEPT>DOCULECT>-------DUPLICATES>-----FORM>---IPA>----LANGID>-LANGUAGE_NAME>--MORPHEMES>------NUMBERS>PROSTRINGS>-----SONARS>-TOKENS>-VALUE>--WEIGHTS>NOTE
#1>------n a ʔ o t>------NAHUT>--3>------4>------emcimade>-------ABOVE>--Karo_Arara>-----0>------naʔot>--naʔot>--36>-----Karo (Arara)>---ABOVE>--36.N.C 36.A.V 36.H.C 36.U.V 36.T.c>-----AXBYN>--4 7 1 7 1>------n a ʔ o t>------naʔot>--2.0 1.5 1.75 1.3 0.8>---


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

    audio = get_mono_channel(d.audio)  # FIXME: pass in channel number from args!
    intervalByConcept = {i.label: i for i in d.praat_textgrid.tierDict[args.concept_tier].entryList}
    count = 0
    for t in d.iter_transcriptions(
            concept_tier=args.concept_tier, concept_column=args.concept_column):
        transcription = list(t.values())[0]
        concept = t[args.concept_column]
        if not concept:
            continue  # pragma: no cover
        if concept in intervalByConcept:
            # We can match a transcription to a lable in the Praat file, ...
            interval = intervalByConcept[concept]
            # ... so we can cut out the corresponding audio chunk
            audio_chunk = audio[
                interval.start * 1000 - INTERVAL_OFFSET:interval.end * 1000 + INTERVAL_OFFSET]
            if NORMALIZE:
                # normalize it with headroom
                audio_chunk = normalize(audio_chunk, NORMALIZE_HEADROOM)
            # fade in and out
            audio_chunk = audio_chunk.fade_in(duration=FADE_TIME).fade_out(duration=FADE_TIME)
            md = {
                'artist': 'Vanuatu Voices',
                'title': '{}: {}'.format(interval.label, transcription),
                'album': d.id,
                'date': datetime.date.today().isoformat(),
                'genre': 'Speech'}
            save(chunkdir, interval, audio_chunk, md, 'wav', codec="copy")
            save(chunkdir, interval, audio_chunk, md, 'mp3', bitrate="128k")
            save(chunkdir, interval, audio_chunk, md, 'ogg', bitrate="128k")
            count += 1
        else:
            args.log.warning('no interval for concept: "{}"'.format(concept))
    #
    # FIXME: do we have to write the filenames to the xslx?
    #
    args.log.info('created soundfiles for {} concepts in {}'.format(count, chunkdir))


def get_mono_channel(audio, channel=1):
    assert 0 < channel <= audio.channels
    if audio.channels > 1:
        return audio.split_to_mono()[channel - 1]
    return audio


def save(d, interval, chunk, tags, format, **kw):
    chunk.export(str(d / '{}.{}'.format(interval.label, format)), tags=tags, format=format, **kw)
