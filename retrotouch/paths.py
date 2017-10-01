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
	Usually "/usr/share/scc" or $SCC_SHARED if program is being started from
	script extracted from source tarball
	"""
	if "SHARED" in os.environ:
		return os.environ["SHARED"]
	if os.path.exists("/usr/local/share/scc/"):
		return "/usr/local/share/scc/"
	return "/usr/share/scc/"
