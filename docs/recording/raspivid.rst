Recording Raspberry Pi Camera Module
====================================

The Raspberry Pi comes with camera modules in various qualities:

- `Camera Module V2`_
- `Raspberry Pi High Quality Camera`_
- `Pi NoIR Camera V2`_

To record from these modules a special tool called ``raspivid`` can be used.


Shell Script
------------

While you could configure the command directly, it is very error-prone due to shell functionality being used which is not directly available in pyCA.
Thus, it is best to write a minimal shell script which you run from pyCA which
executes the necessary commands.

A basic recording script (``rec.sh``) could look like this:

.. code-block:: bash

    #!/bin/sh

    TIME="$1"
    OUTFILE="$2"

    # recrdging command

Make sure the file is executable by running::

    chmod +x rec.sh

Finally, configgure pyCA to use this new script for recording::

    command = '/path/to/run.sh {{time}} {{dir}}/{{name}}.mkv'


Recording Commands
------------------

Record from the camera module using raspivid, pipe the video into FFmpeg and directly mux it with audio
from an ALSA source:

.. code-block:: bash

    #!/bin/sh

    TIME="$1"
    OUTFILE="$2"

    raspivid -t ${TIME}000 -w 1280 -h 720 -b 2000000 -fps 30 -n -awb fluorescent -sa -10 -br 60 -co 50 -o - | \
       ffmpeg -ac 2 -f alsa -ar 16000 -i plughw:1  -r 30 -i pipe:0 -filter:a aresample=async=1 \
       -c:a flac -c:v copy -t 300 "${OUTFILE}"

Record from the camera module using raspivid and in parallel, record from an ALSA source using arecord. Mux
both files together afterwards using FLAC for audio encoding:

.. code-block:: bash

    #!/bin/sh

    TIME="$1"
    OUTFILE="$2"

    set -eu

    raspivid -t ${TIME}000 -w 1280 -h 720 -b 2000000 -fps 30 -n -awb fluorescent -sa -10 -br 60 -co 50 -o v.h264 | \
       arecord -D plug:default -f S16_LE -c 1 -r 16000 -d 300 a.wav
    ffmpeg -i a.wav -r 30 -i v.h264 -filter:a aresample=async=1 -c:a flac -c:v copy "${OUTFILE}"

The second options puts less stress on the system while recording since the reconding commands run separately.
But this also means that the recording command will continue for sometime after the actual recording is finished.
This means that you need some time before you can start the next recording.


.. _Camera Module V2: https://www.raspberrypi.org/products/camera-module-v2/
.. _Raspberry Pi High Quality Camera: https://www.raspberrypi.org/products/raspberry-pi-high-quality-camera/
.. _Pi NoIR Camera V2: https://www.raspberrypi.org/products/pi-noir-camera-v2/
