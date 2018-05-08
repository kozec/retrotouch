#!/usr/bin/env python2
"""
SC-Controller - Paths

Methods in this module are used to determine stuff like where user data is stored,
where sccdaemon can be executed from and similar.

This is gui-only thing, as sccdaemon doesn't really need to load anything what
python can't handle.
All this is needed since I want to have entire thing installable, runnable
from source tarball *and* debugable in working folder.
"""
import os


def get_share_path():
	"""
	Returns directory where shared files are kept.
	Usually "/usr/share/retrotouch" or $SHARED if program is being started from
	script extracted from source tarball
	"""
	if "SHARED" in os.environ:
		return os.environ["SHARED"]
	if os.path.exists("/usr/local/share/retrotouch/"):
		return "/usr/local/share/retrotouch/"
	return "/usr/share/retrotouch/"


def get_config_path():
	"""
	Returns configuration directory.
	~/.config/retrotouch under normal conditions.
	"""
	confdir = os.path.expanduser("~/.config")
	if "XDG_CONFIG_HOME" in os.environ:
		confdir = os.environ['XDG_CONFIG_HOME']
	return os.path.join(confdir, "retrotouch")


def get_data_path():
	"""
	Returns directory for user data that is not configuration.
	RetroTouch stores game saves there.
	~/.local/share/retrotouch under normal conditions.
	"""
	confdir = os.path.expanduser("~/.local/share")
	if "XDG_DATA_HOME" in os.environ:
		confdir = os.environ['XDG_DATA_HOME']
	return os.path.join(confdir, "retrotouch")
