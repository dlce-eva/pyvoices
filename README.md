# pyvoices

python package supporting data curation for "* Voices"-like data.

Currently, `pyvoices` depends on `pydub`, which in turn depends on Python's `audioop` module.
The latter was removed in Python 3.13. Thus, `pyvoices` currently requires 3.9 <= Python <= 3.12.
