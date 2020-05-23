#!/bin/sh

npm run build
exec python -m pyca ${1+"$@"}
