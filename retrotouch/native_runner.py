#!/usr/bin/env python2
"""
RetroTouch - Runner

Separate process not bound to any graphics toolkit with simple duty - run
and render libretro core as fast as possible.
"""
from __future__ import unicode_literals
from retrotouch.native.shared_data import SharedData
from retrotouch.data import CORE_CONFIG_OVERRIDE, CORE_CONFIG_DEFAULTS
from retrotouch.tools import load_core_config, save_core_config
from retrotouch.paths import get_share_path, get_data_path
from retrotouch.rpc import RPC
import sys, os, logging, ctypes
log = logging.getLogger("RRunner")


cb_log_t = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
cb_render_size_changed_t = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
cb_get_variable_t = ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_char_p)
cb_set_variable_t = ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p)
LOG_LEVELS = [
	"debug",	# 0
	"info",		# 1
	"warn",		# 2
	"error",	# 3
]


class LibraryData(ctypes.Structure):
	_fields_ = [
		("res_path", ctypes.c_char_p),
		("save_path", ctypes.c_char_p),
		("parent", ctypes.c_int),
		("window", ctypes.c_int),
		("cb_log",  cb_log_t),
		("cb_render_size_changed",  cb_render_size_changed_t),
		("cb_get_variable", cb_get_variable_t),
		("cb_set_variable", cb_set_variable_t),
		("variables_changed", ctypes.c_int),
		("shared_data", SharedData.get_c_type()),
		("private", ctypes.c_void_p),
		("core", ctypes.c_void_p),
	]


class Native:
	
	def __init__(self, parent, input_fname):
		self._lib = ctypes.CDLL("./libnative_runner.so")
		self._lib.rt_init.restype = ctypes.c_int
		self._lib.rt_check_saving_supported.restype = ctypes.c_int
		self._lib.rt_check_error.restype = ctypes.c_char_p
		self._lib.rt_core_load.restype = ctypes.c_int
		self._lib.rt_get_game_loaded.restype = ctypes.c_int
		
		self.paused = True
		self.shared_data = SharedData(input_fname, False)
		
		self.__libdata = LibraryData()
		self.__libdata.parent = parent
		self.__libdata.res_path = ctypes.c_char_p(get_share_path().encode("utf-8"))
		self.__libdata.save_path = ctypes.c_char_p(get_data_path().encode("utf-8"))
		self.__libdata.cb_log = cb_log_t(self._cb_log)
		self.__libdata.cb_render_size_changed = cb_render_size_changed_t(self.cb_render_size_changed)
		self.__libdata.cb_get_variable = cb_get_variable_t(self.cb_get_variable)
		self.__libdata.cb_set_variable = cb_set_variable_t(self.cb_set_variable)
		self.__libdata.variables_changed = 0
		self.__libdata.shared_data = self.shared_data.get_ptr()
		self.__libdata.private = None
		self._libdata = ctypes.byref(self.__libdata)
		
		assert 0 == self._lib.rt_init(self._libdata), "Failed to initialiaze native code"
		self.call("window_created", self.__libdata.window)
	
	def _cb_log(self, tag, level, message):
		getattr(logging.getLogger(tag), LOG_LEVELS[min(level, len(LOG_LEVELS))])(message)
	
	def check_saving_supported(self):
		return 1 == self._lib.rt_check_saving_supported(self._libdata)
	
	def step(self):
		self._lib.rt_step(self._libdata)
	
	def step_paused(self):
		self._lib.rt_step_paused(self._libdata)
	
	def set_paused(self, paused):
		if self.paused != paused:
			self.paused = paused
			self.call("paused_changed", paused)
			if paused:
				log.debug("Core paused")
			else:
				log.debug("Core resumed")
	
	def get_game_loaded(self):
		return self._lib.rt_get_game_loaded(self._libdata) == 1
	
	def config_changed(self, *a):
		self.__libdata.variables_changed = 1
	
	def load_core(self, filename):
		assert self._lib.rt_check_error(self._libdata) is None, "Error detected"
		assert 0 == self._lib.rt_core_load(self._libdata, ctypes.c_char_p(filename.encode("utf-8")))
	
	def set_vsync(self, enabled):
		assert 0 == self._lib.rt_vsync_enable(self._libdata, ctypes.c_int(enabled))
	
	def set_screen_size(self, width, height):
		self._lib.rt_set_screen_size(self._libdata, ctypes.c_int(width), ctypes.c_int(height))
	
	def set_background_color(self, r, g, b):
		self._lib.rt_set_background_color(self._libdata, ctypes.c_float(r), ctypes.c_float(g), ctypes.c_float(b))
	
	
	def ping(self, *a, **b):
		pass
	
	def load_game(self, filename):
		assert self._lib.rt_check_error(self._libdata) is None, "Error detected"
		assert 0 == self._lib.rt_game_load(self._libdata, ctypes.c_char_p(filename.encode("utf-8")))
	
	def save_state(self, filename):
		assert 0 == self._lib.rt_save_state(self._libdata, ctypes.c_char_p(filename.encode("utf-8")))
		self.call("on_state_saved", filename)
	
	def load_state(self, filename):
		assert 0 == self._lib.rt_load_state(self._libdata, ctypes.c_char_p(filename.encode("utf-8")))
	
	def save_screenshot(self, filename):
		assert 0 == self._lib.rt_save_screenshot(self._libdata, ctypes.c_char_p(filename.encode("utf-8")))
	
	def save_both(self, prefix, ext_state, ext_screenshot):
		state = "%s.%s" % (prefix, ext_state)
		screenshot = "%s.%s" % (prefix, ext_screenshot)
		assert 0 == self._lib.rt_save_state(self._libdata, ctypes.c_char_p(state.encode("utf-8")))
		if 0 != self._lib.rt_save_screenshot(self._libdata, ctypes.c_char_p(screenshot.encode("utf-8"))):
			log.warning("Failed to save screenshot (game saved with no problems)")
		self.call("on_state_saved", state)


class RetroRunner(Native, RPC):	
	def __init__(self, read_fd, write_fd, input_fname, parent, core, game):
		RPC.__init__(self, read_fd, write_fd)
		Native.__init__(self, parent, input_fname)
		self.config = load_core_config(core) or {}
		self.load_core(core)
		self.load_game(game)
	
	def config_changed(self, *a):
		self.config = load_core_config(core) or self.config
		Native.config_changed(self)
	
	def cb_render_size_changed(self, width, height):
		self.call("render_size_changed", width, height)
	
	def cb_get_variable(self, key):
		key = key.decode("utf-8")
		if key in CORE_CONFIG_OVERRIDE:
			return CORE_CONFIG_OVERRIDE[key].encode("utf-8")
		elif key in self.config:
			return str(self.config[key]).encode("utf-8")
		else:
			return None
	
	def cb_set_variable(self, key, options):
		key = key.decode("utf-8")
		try:
			description, values = options.decode("utf-8").split("; ")
			options = values.split("|")
			value = options[0]
			self.call("add_variable", key, description, options)
		except Exception, e:
			log.exception(e)
			return
		if key not in self.config:
			if key in CORE_CONFIG_OVERRIDE:
				self.config[key] = CORE_CONFIG_OVERRIDE[key]
			elif key in CORE_CONFIG_DEFAULTS:
				self.config[key] = CORE_CONFIG_DEFAULTS[key]
			else:
				self.config[key] = value
	
	def run(self):
		while True:
			if self.paused:
				self.select(0.1)
				self.step_paused()
			else:
				self.select()
				self.step()


if __name__ == "__main__":
	try:
		core, game = sys.argv[1:]
		read_fd = long(os.environ.get("RT_RUNNER_READ_FD", "0"))
		write_fd = long(os.environ.get("RT_RUNNER_WRITE_FD", "1"))
		window_id = long(os.environ.get("RT_RUNNER_WINDOW_ID", "0"))
		r, g, b = [ float(x) for x in os.environ.get("RT_BACKGROUND_COLOR", "0").split(" ") ]
		input_fname = os.environ.get("RT_RUNNER_SHM_FILENAME", "/dev/null")
	except ValueError:
		print >>sys.stderr, "You should not be running this script directly."
		print >>sys.stderr, ""
		print >>sys.stderr, "But if you absolutelly must, arguments are:"
		print >>sys.stderr, "	%s core game" % (sys.argv[0],)
		print >>sys.stderr, "Required env.variables:"
		print >>sys.stderr, "	RT_RUNNER_READ_FD"
		print >>sys.stderr, "	RT_RUNNER_WRITE_FD"
		print >>sys.stderr, "	RT_RUNNER_WINDOW_ID"
		print >>sys.stderr, "	RT_RUNNER_SHM_FILENAME"
		print >>sys.stderr, "	RT_BACKGROUND_COLOR (r g b, space separated, floats)"
		sys.exit(1)
	
	from retrotouch.tools import init_logging, set_logging_level
	init_logging()
	set_logging_level(True, True)
	
	n = RetroRunner(int(read_fd), int(write_fd), input_fname,
						int(window_id), core, game)
	n.set_background_color(float(r), float(g), float(b))
	n.set_paused(False)
	save_core_config(core, n.config)
	if n.check_saving_supported():
		n.call("saving_supported")
	
	n.run()
