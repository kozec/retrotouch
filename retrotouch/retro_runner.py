#!/usr/bin/env python2
"""
RetroTouch - Runner

Separate process not bound to any graphics toolkit with simple duty - run
and render libretro core as fast as possible.
"""
from __future__ import unicode_literals
from retrotouch.paths import get_share_path
from retrotouch.rpc import RPC, prepare_mmap
import logging, ctypes, mmap, sys

cb_log_t = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
cb_render_size_changed_t = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
LOG_LEVELS = [
	"debug",	# 0
	"info",		# 1
	"warn",		# 2
	"error",	# 3
]


class LibraryData(ctypes.Structure):
	_fields_ = [
		("parent", ctypes.c_int),
		("respath", ctypes.c_char_p),
		("cb_log",  cb_log_t),
		("cb_render_size_changed",  cb_render_size_changed_t),
		("input_state", ctypes.POINTER(ctypes.c_uint)),
		("private", ctypes.c_void_p),
		("core", ctypes.c_void_p),
	]


class Native:
	
	def __init__(self, respath, parent, input_fname):
		self._lib = ctypes.CDLL("./libretro_runner.so")
		self._lib.rt_init.restype = ctypes.c_int
		self._lib.rt_check_error.restype = ctypes.c_char_p
		self._lib.rt_core_load.restype = ctypes.c_int
		self._lib.rt_get_game_loaded.restype = ctypes.c_int

		trash, self.input_mmap = prepare_mmap(input_fname)
		self.input_state = ctypes.c_uint.from_buffer(self.input_mmap)
		
		self.__libdata = LibraryData()
		self.__libdata.parent = parent
		self.__libdata.respath = ctypes.c_char_p(respath.encode("utf-8"))
		self.__libdata.cb_log = cb_log_t(self._cb_log)
		self.__libdata.cb_render_size_changed = cb_render_size_changed_t(self._cb_render_size_changed)
		self.__libdata.input_state = ctypes.POINTER(ctypes.c_uint)(self.input_state)
		self.__libdata.private = None
		self._libdata = ctypes.byref(self.__libdata)
		
		
		assert 0 == self._lib.rt_init(self._libdata), "Failed to initialiaze native code"
	
	
	def _cb_log(self, tag, level, message):
		getattr(logging.getLogger(tag), LOG_LEVELS[min(level, len(LOG_LEVELS))])(message)
	
	
	def _cb_render_size_changed(self, width, height):
		self.call("render_size_changed", width, height)
	
	
	def step(self):
		self._lib.rt_step(self._libdata)
	
	
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


class RetroRunner(Native, RPC):
	
	def __init__(self, respath, read_fd, write_fd, input_fname, parent, core, game):
		Native.__init__(self, respath, parent, input_fname)
		RPC.__init__(self, read_fd, write_fd)
		self.load_core(core)
		self.load_game(game)


if __name__ == "__main__":
	try:
		read_fd, write_fd, window_id, input_fname, core, game = sys.argv[1:]
	except ValueError:
		print >>sys.stderr, "You should not be running this script directly."
		sys.exit(1)
	
	from retrotouch.tools import init_logging, set_logging_level
	init_logging()
	set_logging_level(True, True)
	
	respath = get_share_path()
	n = RetroRunner(respath, int(read_fd), int(write_fd),
			input_fname, int(window_id), core, game)
	
	while True:
		n.select()
		n.step()
