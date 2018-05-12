#!/usr/bin/env python2
"""
RetroTouch - Wrapper

Wrapper around native c code
"""
from gi.repository import Gio, GdkX11
from retrotouch.rpc import RPC, decode_call, decode_size, prepare_mmap
import os, logging, subprocess, ctypes
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
		
		# Prepare GTK
		self.parent.realize()
		
		# Prepare mmap
		tmp, self.input_mmap = prepare_mmap()
		self.input_state = ctypes.c_uint.from_buffer(self.input_mmap)
		self.input_state.value = 0
		
		# Prepare RPC
		mine_rfd, his_wfd = os.pipe()
		his_rfd, mine_wfd = os.pipe()
		RPC.__init__(self, mine_rfd, mine_wfd)
		
		# Start retro_runner
		if self.GDB:
			self.proc = subprocess.Popen([ "gdb", "python" ], stdin=subprocess.PIPE)
			print >>self.proc.stdin, " ".join([ "run", "retrotouch/retro_runner.py",
				str(his_rfd), str(his_wfd), str(self.parent.get_window().get_xid()),
				tmp.name, "'%s'" % (self.core,) , "'%s'" % (self.game,) ])
			print >>self.proc.stdin, "bt"
		elif self.VALGRIND:
			self.proc = subprocess.Popen([
				"valgrind",
				"--suppressions=resources/valgrind-python.supp",
				"python", "retrotouch/retro_runner.py",
				str(his_rfd), str(his_wfd), str(self.parent.get_window().get_xid()),
				tmp.name, self.core, self.game]) 
		else:
			self.proc = subprocess.Popen([
				"python", "retrotouch/retro_runner.py",
				str(his_rfd), str(his_wfd), str(self.parent.get_window().get_xid()),
				tmp.name, self.core, self.game]) 
		log.debug("Subprocess started")
		os.close(his_rfd); os.close(his_wfd)
	
	
	def setup_fds(self, read_fd, write_fd):
		def recieved_size(stream, res):
			bts = stream.read_bytes_finish(res)
			size = decode_size(bts.get_data())
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
		self.proc.kill()
		self.input_mmap.close()
	
	
	def render_size_changed(self, width, height):
		self.parent.set_size_request(width, height)
	
	
	def paused_changed(self, paused):
		self.app.on_playpause_changed(paused=paused)
	
	
	def window_created(self, xid):
		self.window = GdkX11.X11Window.foreign_new_for_display(
			self.parent.get_window().get_display(),
			xid)
	
	
	def set_size_allocation(self, width, height):
		if self.window:
			self.window.move_resize(0, 0, width, height)
	
	
	def save_state(self, filename):
		self.call('save_state', filename)
	
	
	def load_state(self, filename):
		self.call('load_state', filename)
	
	
	def save_screenshot(self, filename):
		self.call('save_screenshot', filename)
	
	
	def save_both(self, prefix, ext_state, ext_screenshot):
		self.call('save_both', prefix, ext_state, ext_screenshot)
	
	
	def set_button(self, button, state):
		if state:
			self.input_state.value |= 1 << button
		else:
			self.input_state.value &= ~(1 << button)
	
	
	def set_paused(self, paused):
		self.call('set_paused', paused)
	
	
	def load_core(self, *a):
		pass
	
	
	def load_game(self, *a):
		pass
