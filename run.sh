#!/bin/bash

# Ensure correct cwd
cd "$(dirname "$0")"

# Set PATH
SCRIPTS="$(pwd)/scripts"
export PATH="$SCRIPTS":"$PATH"
export PYTHONPATH=".":"$PYTHONPATH"
export SHARED="$(pwd)/resources"

# Build libs
python2 setup.py build || exit 1
[ -h libretrointerface.so ] || ln -s build/lib.linux-x86_64-2.7/libretrointerface.so .

# Execute
# (echo "run scripts/retrotouch" ; echo "bt") | gdb python2
python2 'scripts/retrotouch' $@
