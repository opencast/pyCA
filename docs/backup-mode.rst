Backup Mode
===========

By setting ``backup_mode = True`` in the configuration file, PyCA will go into a backup mode.
This means that neither will the capture agent register itself at Opencast,
nor try to ingest any of the recorded media
or set the capture state.

This is useful if the CA shall be used as backup in case a regular capture agent fails to record.
Just match the name of the pyCA to that of the regular capture agent.
