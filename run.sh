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
[ -h libretro_runner.so ] || ln -s build/lib.linux-x86_64-2.7/libretro_runner.so .

# Execute
if [ x"$1" == x"-d" ] ; then
	(echo "run scripts/retrotouch" ; echo "bt") | gdb python2
else
	# python2 'retrotouch/retro_runner.py' "$@"
	python2 'scripts/retrotouch' "$@"
fi
