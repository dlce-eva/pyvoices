"""
The chunk command expects
- a wav file of an elicitation session
- the corresponding ELAN file with form chunks marked with concept labels in a tier
- transcriptions for the concept labels in an EXCEL sheet

Running `voices chunk` on a directory containing these files results in creation of
- a TextGrid file, containing the data of the selected ELAN tier
- a directory `chunks` containing audio files named using the concept labels
"""
import pathlib
import datetime

from pydub import AudioSegment
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
        args.log.info(
            'TextGrid file was created, this tier name will be used: %s',
            d._eaf_tier_name)  # pylint: disable=W0212
        concept_tier = d.eaf_tier_name
    elif any((
            args.concept_tier in d.eaf_tier_names,
            args.concept_tier in textgrid._tierDict)):  # pylint: disable=W0212
        concept_tier = args.concept_tier
    else:
        args.log.info(
            'TextGrid file was created, these tier names were found:\n%s',
            ', '.join(d._eaf_tier_names))  # pylint: disable=W0212
        return

    is_mapped = False
    if args.concept_map_column is None:
        concept_column = args.concept_column
    else:
        is_mapped = True
        concept_column = args.concept_map_column

    intervals = d.intervals(concept_tier)
    audio = get_mono_channel(d.audio)  # FIXME: pass in channel number faderom args!
    count = 0
    for t in d.iter_transcriptions(concept_tier=concept_tier, concept_column=concept_column):
        if is_mapped:
            concept = t[args.concept_map_column].strip()
        else:
            concept = t[args.concept_column].strip()
        if not concept:
            continue  # pragma: no cover

        if concept not in intervals.by_concept:
            args.log.warning('no interval for concept: "%s"', concept)
            continue

        interval, idx = intervals.get(concept, t[args.concept_column].strip())
        if interval is None:
            args.log.error('check occurrences of concept %s', concept)
            return

        # ... so we can cut out the corresponding audio chunk
        chunk(
            audio,
            interval,
            chunkdir,
            idx,
            {
                'artist': args.album,
                'album': d.id,
                'title': f'{interval.label}{idx}: {list(t.values())[0].strip()}'})
        count += 1

    #
    # FIXME: do we have to write the filenames to the xslx?
    #
    args.log.info(
        'created soundfiles for %s concepts in %s of %s TextGrid intervals',
        count, chunkdir, len(textgrid._tierDict[concept_tier].entries))  # pylint: disable=W0212
    intervals.info(args.log)


def chunk(
        audio: AudioSegment,
        interval: Interval,
        chunkdir: pathlib.Path,
        idx: str,
        md_: dict[str, str],
):
    """Chunk the audio and write chunks in three formats to disk."""
    audio_chunk = audio[
        interval.start * 1000 - INTERVAL_OFFSET:interval.end * 1000 + INTERVAL_OFFSET]
    if NORMALIZE:
        # normalize it with headroom
        audio_chunk = normalize(audio_chunk, NORMALIZE_HEADROOM)
    # fade in and out
    audio_chunk = audio_chunk.fade_in(duration=FADE_TIME).fade_out(duration=FADE_TIME)
    md = {'date': datetime.date.today().isoformat(), 'genre': 'Speech'}
    md.update(md_)
    for fmt, kw in [
            ('wav', {'codec': "copy"}), ('mp3', {'bitrate': "128k"}), ('ogg', {'bitrate': "128k"})]:
        fn = interval.label.strip().replace('/', '_or_')
        audio_chunk.export(str(chunkdir / f'{fn}{idx}.{fmt}'), tags=md, format=fmt, **kw)


def get_mono_channel(audio: AudioSegment, channel: int = 1) -> AudioSegment:
    """Split to mono."""
    assert 0 < channel <= audio.channels
    if audio.channels > 1:
        return audio.split_to_mono()[channel - 1]
    return audio
