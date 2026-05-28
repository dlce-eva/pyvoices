import logging

from pyvoices.doculect import Doculect


def test_Doculect_iter_transcriptions(doculect_dir):
    doculect_dir.joinpath('doculect.xlsx').unlink()
    res = list(Doculect(doculect_dir).iter_transcriptions())
    assert res


def test_Doculect_intervals(doculect_dir, caplog):
    doculect_dir.joinpath('doculect.TextGrid').unlink()
    intervals = Doculect(doculect_dir).intervals('default')
    assert intervals.by_concept
    # new_moon   "dry season"

    interval, idx = intervals.get('new_moon')
    assert idx == ''
    assert interval.label == 'new_moon'
    interval, idx = intervals.get('new_moon', 'label')
    assert interval.label == 'label'
    assert idx == '___2'
    interval, _ = intervals.get('new_moon')
    assert interval is None

    with caplog.at_level(logging.INFO):
        intervals.info(logging.getLogger(__name__))
        messages = {rec.message for rec in caplog.records}
        assert any('check occurrences of new_moon' in msg for msg in messages)
        assert any('nonexisting' in msg for msg in messages)
