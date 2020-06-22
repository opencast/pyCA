Configure PyCA as System Service
================================

This is the recommended way of running PyCA in production.
If you install the Debian or RPM packages, this is what is pre-configured.


Services
--------

PyCA is internally split into multiple separate services.
The idea is that if an error occurs in one part, it does not effect the other parts.
For example, let's say that there is a bug in the web interface.
It would be bad if that one would crash, killing a recording which is running in parallel.
Separating these services tries to prevent things like that.

Separate services are currently:

- `capture` – Taking care of recording events
- `ingest` – Uploading recordings to Opencast
- `schedule` – Synchronize scheduled events with Opencast
- `agentstate` – Updating the overall agent state in Opencast
- `ui` – The web interface


Systemd
-------

To automatically start all these services
and to ensure services are restarted if necessary,
we recommend using systemd.

Example systemd unit files, corresponding to the services above, are available in ``init/systemd``.
These unit files start and manage all pyCA services separately.

Remember to increase the ``WatchdogSec`` parameter in the ``pyca-schedule.service`` unit file
if you modify the ``update_frequency`` setting in pyCA.
It is recommended to set it at least twice as long as the ``update_frequency``.
