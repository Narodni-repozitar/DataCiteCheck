#!/bin/bash

SD=$(dirname "$0")
V="$SD/.venv"

if [ ! -d  "$V" ] ; then
    python -m venv "$V"
    "$V/bin/pip" install -U setuptools pip wheel
    "$V/bin/pip" install -e "$SD"
fi

"$V/bin/python" "$SD/main.py" $@

