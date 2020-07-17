Record Using FFmpeg
===================

FFmpeg is a powerful tool to record all types of audio and video material.
The following command show how to record:

- Video from a video4linux2 device like a webcam
- Audio from Pulseaudio

.. code-block:: bash

    ffmpeg -nostats \
        -f pulse -i default \
        -f v4l2 -video_size 1280x720 -input_format yuyv422 -framerate 30 -i /dev/video0 \
        -t {{time}}
        -c:v libx264 -preset medium -pix_fmt yuv420p -movflags faststart \
        -c:a aac \
        {{dir}}/{{name}}.mp4


Recording Network Streams
-------------------------

FFmpeg can also be used to capture network streams e.g. from network cameras.
The following command shows how to capture from a network camera via RTSP.

.. code-block:: bash

    ffmpeg -nostats \
        -rtsp_transport tcp \
        -i rtsp://10.10.97.108:554/hdmi \
        -t {{time}} \
        -c copy -f mp4 \
        {{dir}}/{{name}}.mp4
