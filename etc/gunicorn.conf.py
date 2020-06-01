import multiprocessing

# Gunicorn configuration for pyCA user interface
#
# For details of the available optiuons see:
# https://docs.gunicorn.org/en/stable/settings.html#settings

# The socket to bind.
# This can be a TCP socket:
#   bind = "127.0.0.1:8000"
# …or a UNIX socket:
#   bind = "unix:/var/run/pyca/uisocket"
#
# Default: "127.0.0.1:8000"
#bind = "127.0.0.1:8000"

# The number of worker processes for handling requests.
# Default: 1
workers = multiprocessing.cpu_count()
