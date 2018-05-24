#!/bin/sh
source /reg/g/pcds/pyps/mfx/dev/mfx/mfxenv.sh
SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
python "$SCRIPTPATH"/take_pedestal.py "$@"
