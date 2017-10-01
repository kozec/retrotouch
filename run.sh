#!/bin/bash

# Ensure correct cwd
cd "$(dirname "$0")"

# Set PATH
SCRIPTS="$(pwd)/scripts"
export PATH="$SCRIPTS":"$PATH"
export PYTHONPATH=".":"$PYTHONPATH"
export SHARED="$(pwd)"

# Execute
# lldb python2 -- 'scripts/retrotouch' $@
python2 'scripts/retrotouch' $@
