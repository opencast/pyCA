Record Using GStreamer
======================

GStreamer is a good alternative to FFmpeg when it comes to media recording.
The easiest way of leveraging GStreamer is by using ``gst-launch`` for starting  the recording
and pyCA's process signaling for stopping the recording process.

To tell pyCA to send a SIGTERM once it's time to end the recording, set:

.. code-block:: ini

    sigterm_time = 0

The following command then is an example of how to record a video4linux2 device using GStreamer:

.. code-block:: bash

    gst-launch-1.0 -e \
        v4l2src device=/dev/video16 \
        ! videoconvert \
        ! x264enc speed-preset=faster qp-min=30 \
        ! matroskamux \
        ! filesink location={{dir}}/{{name}}.mkv
