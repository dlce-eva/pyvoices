"""

"""
import collections
import datetime
from pydub.effects import normalize
from praatio.utilities.constants import Interval

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

exported_chunks = dict()

# FIXME: Also spit out a CLDF Wordlist? an EDICTOR Wordlist?
# ID>-----ALIGNMENT>------CLASSES>COGID>--COGIDS>-COGNACY>CONCEPT>DOCULECT>-------DUPLICATES
# >-----FORM>---IPA>----LANGID>-LANGUAGE_NAME>--MORPHEMES>------NUMBERS>PROSTRINGS>-----SONARS
# >-TOKENS>-VALUE>--WEIGHTS>NOTE
# 1>------n a ʔ o t>------NAHUT>--3>------4>------emcimade>-------ABOVE>--Karo_Arara>-----0
# >------naʔot>--naʔot>--36>-----Karo (Arara)>---ABOVE>--36.N.C 36.A.V 36.H.C 36.U.V 36.T.c
# >-----AXBYN>--4 7 1 7 1>------n a ʔ o t>------naʔot>--2.0 1.5 1.75 1.3 0.8>---


def register(parser):
    parser.add_argument('input', type=PathType(type='dir'))
    parser.add_argument(
        '--album',
        default='Voices',
        help="Name of the album stored in the metadata.")
    parser.add_argument(
        '--concept-tier',
        default='Rfc-Form',
        help="Name of the tier in the Praat TextGrid file which contains concept labels.")
    parser.add_argument(
        '--concept-column',
        default='English Translation',
        help="Name of the column in the Excel transcriptions file which contains concept labels.")
    parser.add_argument(
        '--concept-map-column',
        default=None,
        help="Name of the column in the Excel transcriptions file which contains concept labels \
              used in the TextGrid file but differs from the general concept column.")


def run(args):
    d = Doculect(args.input)
    chunkdir = d.dir / 'chunks'
    if not chunkdir.exists():
        chunkdir.mkdir()

    textgrid = d.praat_textgrid

    if d.eaf_tier_name is not None:
        args.log.info('TextGrid file was created, this tier name will be used: {}'.format(
                      d._eaf_tier_name))
        concept_tier = d.eaf_tier_name
    elif args.concept_tier in d.eaf_tier_names or args.concept_tier in textgrid._tierDict:
        concept_tier = args.concept_tier
    else:
        args.log.info('TextGrid file was created, these tier names were found:\n{}'.format(
                      ', '.join(d._eaf_tier_names)))
        return

    intervalByConcept = collections.defaultdict(list)

    for i in textgrid._tierDict[concept_tier].entries:
        intervalByConcept[i.label.strip()].append(i)

    is_mapped = False
    if args.concept_map_column is None:
        concept_column = args.concept_column
    else:
        is_mapped = True
        concept_column = args.concept_map_column

    audio = get_mono_channel(d.audio)  # FIXME: pass in channel number faderom args!

    count = 0
    for t in d.iter_transcriptions(concept_tier=concept_tier, concept_column=concept_column):

        transcription = list(t.values())[0].strip()
        if is_mapped:
            concept = t[args.concept_map_column].strip()
        else:
            concept = t[args.concept_column].strip()
        if not concept:
            continue  # pragma: no cover

        if concept in intervalByConcept:

            if concept in exported_chunks:
                exported_chunks[concept] += 1
                idx = '___{}'.format(exported_chunks[concept])
                args.log.info('duplicates for {}'.format(concept))
            else:
                exported_chunks[concept] = 1
                idx = ''
            cpt_idx = exported_chunks[concept] - 1

            # We can match a transcription to a label in the Praat file, ...
            try:
                interval = intervalByConcept[concept][cpt_idx]
            except IndexError:
                args.log.error('check occurrences of concept {}'.format(concept))
                return
            if is_mapped:
                interval = Interval(interval.start, interval.end, t[args.concept_column].strip())
            # ... so we can cut out the corresponding audio chunk
            audio_chunk = audio[
                interval.start * 1000 - INTERVAL_OFFSET:interval.end * 1000 + INTERVAL_OFFSET]
            if NORMALIZE:
                # normalize it with headroom
                audio_chunk = normalize(audio_chunk, NORMALIZE_HEADROOM)
            # fade in and out
            audio_chunk = audio_chunk.fade_in(duration=FADE_TIME).fade_out(duration=FADE_TIME)
            md = {
                'artist': args.album,
                'title': '{}{}: {}'.format(interval.label, idx, transcription),
                'album': d.id,
                'date': datetime.date.today().isoformat(),
                'genre': 'Speech'}
            save(chunkdir, interval, idx, audio_chunk, md, 'wav', codec="copy")
            save(chunkdir, interval, idx, audio_chunk, md, 'mp3', bitrate="128k")
            save(chunkdir, interval, idx, audio_chunk, md, 'ogg', bitrate="128k")
            count += 1
        else:
            args.log.warning('no interval for concept: "{}"'.format(concept))
    #
    # FIXME: do we have to write the filenames to the xslx?
    #
    args.log.info('created soundfiles for {} concepts in {} of {} TextGrid intervals'.format(
                  count, chunkdir, len(textgrid._tierDict[concept_tier].entries)))

    for c in intervalByConcept:
        if c in exported_chunks:
            if len(intervalByConcept[c]) != exported_chunks[c]:
                args.log.warning('check occurrances of {} in TextGrid and XLSX'.format(c))
        else:
            args.log.info('found {} in TextGrid but not in XLSX'.format(c))


def get_mono_channel(audio, channel=1):
    assert 0 < channel <= audio.channels
    if audio.channels > 1:
        return audio.split_to_mono()[channel - 1]
    return audio


def save(d, interval, idx, chunk, tags, format, **kw):
    fn = interval.label.strip().replace('/', '_or_')
    chunk.export(str(d / '{}{}.{}'.format(fn, idx, format)), tags=tags, format=format, **kw)
