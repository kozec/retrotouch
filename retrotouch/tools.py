#!/usr/bin/env python2
"""
RetroTouch - tools

Various stuff that I don't care to fit anywhere else.
"""
from __future__ import unicode_literals

import logging

log = logging.getLogger("tools.py")
_ = lambda x : x

LOG_FORMAT				= "%(levelname)s %(name)-13s %(message)s"

def init_logging(prefix="", suffix=""):
	"""
	Initializes logging, sets custom logging format and adds one
	logging level with name and method to call.
	
	prefix and suffix arguments can be used to modify log level prefixes.
	"""
	logging.basicConfig(format=LOG_FORMAT)
	logging.getLogger()
	# Rename levels
	logging.addLevelName(10, prefix + "D" + suffix)	# Debug
	logging.addLevelName(20, prefix + "I" + suffix)	# Info
	logging.addLevelName(30, prefix + "W" + suffix)	# Warning
	logging.addLevelName(40, prefix + "E" + suffix)	# Error
	# Create additional, "verbose" level
	logging.addLevelName(15, prefix + "V" + suffix)	# Verbose
	# Add 'logging.verbose' method
	def verbose(self, msg, *args, **kwargs):
		return self.log(15, msg, *args, **kwargs)
	logging.Logger.verbose = verbose
	# Wrap Logger._log in something that can handle utf-8 exceptions
	old_log = logging.Logger._log
	def _log(self, level, msg, args, exc_info=None, extra=None):
		args = tuple([
			(str(c).decode("utf-8") if type(c) is str else c)
			for c in args
		])
		msg = msg if type(msg) is unicode else str(msg).decode("utf-8")
		old_log(self, level, msg, args, exc_info, extra)
	logging.Logger._log = _log


def set_logging_level(verbose, debug):
	""" Sets logging level """
	logger = logging.getLogger()
	if debug:		# everything
		logger.setLevel(0)
	elif verbose:	# everything but debug
		logger.setLevel(11)
	else:			# INFO and worse
		logger.setLevel(20)
