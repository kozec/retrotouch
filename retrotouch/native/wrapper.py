#!/usr/bin/env python2
"""
RetroTouch - Wrapper

Wrapper around native c code
"""
from gi.repository import Gtk, Gio, GdkX11
from retrotouch.rpc import RPC, decode_call, decode_size
from retrotouch.native.shared_data import SharedData
from collections import OrderedDict
import os, logging, subprocess
log = logging.getLogger("Wrapper")


class Wrapper(RPC):
	GDB = False
	VALGRIND = False
	
	def __init__(self, app, parent, core, game):
		# Store variables
		self.app = app
		self.parent = parent
		self.core = core
		self.game = game
		self.window = None
		self.app.on_playpause_changed(paused=True)
		self.retro_config = OrderedDict()
		self.width, self.height = self.screen_size = self.render_size = 640, 480
		self.pads = []
		
		# Prepare GTK
		self.parent.realize()
		
		# Prepare RPC
		self.shared_data = SharedData()
		self.shared_data.input_state.buttons = 0
		self.shared_data.input_state.analogs = (0, 0, 0, 0)
		
		mine_rfd, his_wfd = os.pipe()
		his_rfd, mine_wfd = os.pipe()
		color = self.app.window.get_style_context().get_background_color(Gtk.StateFlags.NORMAL)
		RPC.__init__(self, mine_rfd, mine_wfd)
		
		# Setup environment
		env = dict(**os.environ)
		env['RT_RUNNER_READ_FD'] = str(his_rfd)
		env['RT_RUNNER_WRITE_FD'] = str(his_wfd)
		env['RT_RUNNER_WINDOW_ID'] = str(self.parent.get_window().get_xid())
		env['RT_BACKGROUND_COLOR'] = "%s %s %s" % (color.red, color.green, color.blue)
		env['RT_RUNNER_SHM_FILENAME'] = self.shared_data.get_filename()
		# Start native_runner
		if self.GDB:
			self.proc = subprocess.Popen([ "gdb", "python" ],
				env=env, stdin=subprocess.PIPE)
			print >>self.proc.stdin, " ".join([
				"run", "retrotouch/native_runner.py",
				"'%s'" % (self.core,) , "'%s'" % (self.game,),
			])
			print >>self.proc.stdin, "bt"
		elif self.VALGRIND:
			self.proc = subprocess.Popen([
				"valgrind",
				"--suppressions=resources/valgrind-python.supp",
				"--tool=memcheck",
				"python", "retrotouch/native_runner.py",
				self.core, self.game,
			], env=env) 
		else:
			self.proc = subprocess.Popen([
				"python", "retrotouch/native_runner.py",
				self.core, self.game], env=env)
		log.debug("Subprocess started")
		os.close(his_rfd); os.close(his_wfd)
	
	def setup_fds(self, read_fd, write_fd):
		def recieved_size(stream, res):
			try:
				bts = stream.read_bytes_finish(res)
				size = decode_size(bts.get_data())
			except Exception:
				# Subprocess crashed or pipe got destroyed by other mean
				if self.proc:
					self.destroy()
					self.app.on_core_crashed()
				return
			self._read.read_bytes_async(size, 0, self._cancel, recieved_call)
		
		def recieved_call(stream, res):
			bts = stream.read_bytes_finish(res)
			mname, args, kws = decode_call(bts.get_data())
			self.call_locally(mname, args, kws)
			self._read.read_bytes_async(4, 0, self._cancel, recieved_size)
		
		self._read = Gio.UnixInputStream.new(read_fd, True)
		self._write = os.fdopen(write_fd, 'wb', 1)
		self._cancel = Gio.Cancellable()
		self._buffer = b" " * 4
		self._read.read_bytes_async(4, 0, self._cancel, recieved_size)
	
	def __del__(self):
		self._cancel.cancel()
		self.close()
		self.destroy()
	
	def destroy(self):
		log.debug("Killing subprocess")
		if self.proc:
			self.proc.kill()
			self.proc = None
		self.shared_data.close()
		self.window = None
	
	def render_size_changed(self, width, height):
		self.render_size = width, height
		self.app.on_render_size_changed(width, height)
	
	def paused_changed(self, paused):
		self.app.on_playpause_changed(paused=paused)
	
	def window_created(self, xid):
		log.debug("Child window %x", xid)
		self.window = GdkX11.X11Window.foreign_new_for_display(
			self.parent.get_window().get_display(), xid)
		self.app.on_core_ready()
	
	def saving_supported(self):
		self.app.on_saving_supported()
	
	def add_variable(self, key, description, options):
		self.retro_config[key] = (description, options)
	
	def set_size_allocation(self, width, height):
		if self.window:
			self.width, self.height = width, height
			self.window.move_resize(0, 0, width, height)
	
	def set_screen_size(self, width, height):
		self.screen_size = width, height
		factor = self.parent.get_scale_factor()
		self.shared_data.set_scale_factor(factor)
		self.call('set_screen_size', width, height)
	
	def save_state(self, filename):
		self.call('save_state', filename)
	
	def on_state_saved(self, filename):
		self.app.on_state_saved(filename)
	
	def load_state(self, filename):
		self.call('load_state', filename)
	
	def ping(self, *a):
		self.call('ping')
	
	def config_changed(self, *a):
		self.call('config_changed')
	
	def save_screenshot(self, filename):
		self.call('save_screenshot', filename)
	
	def save_both(self, prefix, ext_state, ext_screenshot):
		self.call('save_both', prefix, ext_state, ext_screenshot)
	
	def set_button(self, button, state):
		if state:
			self.shared_data.input_state.buttons |= 1 << button
		else:
			self.shared_data.input_state.buttons &= ~(1 << button)
	
	def set_mouse(self, x, y):
		self.shared_data.input_state.mouse[0] = x
		self.shared_data.input_state.mouse[1] = y
	
	def set_mouse_button(self, button, state):
		if state:
			self.shared_data.input_state.mouse_buttons |= 1 << button
		else:
			self.shared_data.input_state.mouse_buttons &= ~(1 << button)
	
	def set_analog(self, index, x, y):
		self.shared_data.input_state.analogs[index + 0] = x
		self.shared_data.input_state.analogs[index + 1] = y
	
	def set_paused(self, paused):
		self.call('set_paused', paused)
	
	def set_vsync(self, enabled):
		self.call('set_vsync', enabled)
	
	def load_core(self, *a):
		pass
	
	def load_game(self, *a):
		pass
	
	def get_pad_at(self, x, y):
		""" Returns (index, pad_position_x, pad_position_y) or (-1, 0, 0) """
		index = 0
		for (px, py, w, h) in self.pads:
			if x >= px and x < px + w:
				if y >= py and y < py + h:
					return index, px, py
			index += 1
		return -1, 0, 0
	
	def set_pad_position(self, index, x, y, w, h):
		self.shared_data.set_image_pos(index, x, y, w, h)
		while len(self.pads) <= index:
			self.pads.append((-10, -10, 0, 0))
		self.pads[index] = x, y, w, h
	
	def set_image(self, index, pixbuf):
		assert pixbuf.get_rowstride() == 4 * pixbuf.get_width()
		self.shared_data.set_image(index, pixbuf.get_byte_length(), pixbuf.get_pixels())
