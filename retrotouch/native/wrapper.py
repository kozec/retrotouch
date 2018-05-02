#!/usr/bin/env python2
"""
RetroTouch - Wrapper

Wrapper around native c code
"""
import ctypes
import logging
log = logging.getLogger("Wrapper")

log_fn_t = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
LOG_LEVELS = [
	"debug",	# 0
	"info",		# 1
	"warn",		# 2
	"error",	# 3
]


class LibraryData(ctypes.Structure):
	_fields_ = [
		("parent",  ctypes.c_void_p),
		("respath", ctypes.c_char_p),
		("log_fn",  log_fn_t),
		("private", ctypes.c_void_p),
		("core", ctypes.c_void_p),
	]


class Wrapper:
	
	def __init__(self, respath, parent):
		self._lib = ctypes.CDLL("./libretrointerface.so")
		self._lib.rt_create.restype = ctypes.c_int
		self._lib.rt_check_error.restype = ctypes.c_char_p
		self._lib.rt_core_load.restype = ctypes.c_int
		self._lib.rt_get_game_loaded.restype = ctypes.c_int
		
		
		self.__libdata = LibraryData()
		self.__libdata.parent = ctypes.c_void_p(hash(parent))	# Weird hack to get c pointer to GTK widget
		self.__libdata.respath = ctypes.c_char_p(respath.encode("utf-8"))
		self.__libdata.log_fn = log_fn_t(self._log_fn)
		self.__libdata.private = None
		self._libdata = ctypes.byref(self.__libdata)
		assert 0 == self._lib.rt_create(self._libdata), "Failed to initialiaze native code"
	
	
	def _log_fn(self, tag, level, message):
		getattr(logging.getLogger(tag), LOG_LEVELS[min(level, len(LOG_LEVELS))])(message)
	
	
	def set_paused(self, paused):
		assert 0 == self._lib.rt_set_paused(self._libdata, ctypes.c_int(1 if paused else 0))
	
	
	def get_game_loaded(self):
		return self._lib.rt_get_game_loaded(self._libdata) == 1
	
	
	def load_core(self, filename):
		assert self._lib.rt_check_error(self._libdata) is None, "Error detected"
		assert 0 == self._lib.rt_core_load(self._libdata, ctypes.c_char_p(filename.encode("utf-8")))
	
	def load_game(self, filename):
		assert self._lib.rt_check_error(self._libdata) is None, "Error detected"
		assert 0 == self._lib.rt_game_load(self._libdata, ctypes.c_char_p(filename.encode("utf-8")))
