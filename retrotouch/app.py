#!/usr/bin/env python2
"""
RetroTouch - App

Main application window
"""
from __future__ import unicode_literals
from gi.repository import Retro, Gtk, Gdk, Gio, GLib
from retrotouch.svg_widget import SVGWidget
from retrotouch.input import Input
from retrotouch.tools import _

import os, logging
log = logging.getLogger("App")


class App(Gtk.Application):
	"""
	Main application / window.
	"""
	
	HILIGHT = "#FF0000"
	DEFAULT_MAPPINGS = {
		Gdk.KEY_Return:		1 << 1,
		Gdk.KEY_Shift_R:	1 << 2,
		Gdk.KEY_Up:			1 << 3,
		Gdk.KEY_Down:		1 << 4,
		Gdk.KEY_Left:		1 << 5,
		Gdk.KEY_Right:		1 << 6,
		Gdk.KEY_z:			1 << 7,
		Gdk.KEY_y:			1 << 8,
		Gdk.KEY_x:			1 << 9,
	}
	
	TOUCH_MAPPINGS = {
		"A":			1 << 1,
		"B":			1 << 2,
		"START":		1 << 3,
		"SELECT":		1 << 4,
		"DPAD_UP":		1 << 5,
		"DPAD_DOWN":	1 << 6,
		"DPAD_LEFT":	1 << 7,
		"DPAD_RIGHT":	1 << 8,
	}
	
	DPAD_DIRECTIONS = ( 0 )
	#	(1 << Retro.GamepadButtonType.DIRECTION_UP)
	#	| (1 << Retro.GamepadButtonType.DIRECTION_DOWN)
	#	| (1 << Retro.GamepadButtonType.DIRECTION_LEFT)
	#	| (1 << Retro.GamepadButtonType.DIRECTION_RIGHT)
	#
	
	
	def __init__(self, gladepath="/usr/share/retrotouch",
						imagepath="/usr/share/retrotouch/images"):
		Gtk.Application.__init__(self,
				application_id="me.kozec.retrotouch",
				flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE | Gio.ApplicationFlags.NON_UNIQUE )
		Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)
		self.hilights = {}
		self.core = None
		self.gladepath = gladepath
		self.imagepath = imagepath
		self.paused = False
	
	
	def setup_widgets(self):
		# Important stuff
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.gladepath, "app.glade"))
		self.builder.connect_signals(self)
		self.window = self.builder.get_object("window")
		self.add_window(self.window)
		self.window.set_title(_("RetroTouch"))
		self.window.set_wmclass("RetroTouch", "RetroTouch")
		
		asLeft = self.builder.get_object("asLeft")
		asRight = self.builder.get_object("asRight")
		self.left = SVGWidget(os.path.join(self.imagepath, "pads/psp/left.svg"))
		self.right = SVGWidget(os.path.join(self.imagepath, "pads/psp/right.svg"))
		asLeft.add(self.left)
		asRight.add(self.right)
		
		for x in (self.left, self.right):
			x.set_events(Gdk.EventMask.TOUCH_MASK)
			x.connect('touch-event', self.on_touch_event)
		
		self.audio = Retro.PaPlayer()
		
		self.display = Retro.CairoDisplay()
		self.display.set_size_request(320, 200)
		box = self.builder.get_object("ebMain")
		box.add(self.display)
		self.window.show_all()
		
		self.controller_interface = Retro.InputDeviceManager()
		self.input = Input()
		self.controller_interface.set_controller_device (0, self.input)
	
	
	def select_core(self, game_filename):
		"""
		Uses async stuff to load file header and loads apropriate core.
		Or, with formats where headers are not used, just uses extensions.
		"""
		f = Gio.File.new_for_path(game_filename)
		
		def on_read_really_done(stream, task):
			a = stream.read_bytes_finish(task).get_data()
			if a[0:4] == b"\x4e\x45\x53\x1A":
				log.debug("Loading NES game")
				self.load_game("nestopia", game_filename)
			else:
				log.debug("Unknown file type")
		
		def on_read_done(file, task):
			inputstream = file.read_finish(task)
			inputstream.read_bytes_async(1024, 0, None, on_read_really_done)
		
		if game_filename.lower().split(".")[-1] in ("smc", "snes"):
			log.debug("Loading SNES game")
			GLib.timeout_add(100, self.load_game, "snes9x", game_filename)
		elif game_filename.lower().split(".")[-1] in ("iso", "cso"):
			log.debug("Loading PSP game")
			GLib.timeout_add(100, self.load_game, "ppsspp", game_filename)
		elif game_filename.lower().split(".")[-1] in ("gb", ):
			log.debug("Loading GB game")
			GLib.timeout_add(100, self.load_game, "gambatte", game_filename)
		else:
			f.read_async(0, None, on_read_done)
	
	
	def find_core_filename(self, core):
		return "/usr/lib/libretro/%s_libretro.so" % (core, )
	
	
	def load_game(self, core, game_path):
		if self.core is not None:
			for x in self.core.__signals:
				self.core.disconnect(x)
			
		core = self.find_core_filename(core)
		#self.game = Retro.GameInfo()
		#self.game.init_with_data(game_path)
		self.core = Retro.Core.new(core)
		#self.core.__signals = [
		#	self.core.connect("init", self.on_core_initialized),
		#	self.core.connect("message", self.on_core_message)
		#]
		self.core.set_input_interface(self.controller_interface)
		#self.core.do_init(self.core)
		self.display.set_core(self.core)
		self.audio.set_core(self.core)
		#self.core.load_game(self.game)
		self.core.load_game(game_path)
		
		def do_it_later():
			self.paused = False
			GLib.timeout_add(1000.0 / self.core.get_frames_per_second(), self._run)
			return False
		
		GLib.timeout_add(1000, do_it_later)
	
	
	def on_btSettings_toggled(self, bt, *a):
		rvToolbar = self.builder.get_object("rvToolbar")
		btDisplay = self.builder.get_object("btDisplay")
		if bt.get_active():
			rvToolbar.set_reveal_child(True)
		else:
			rvToolbar.set_reveal_child(False)
			btDisplay.set_active(False)
	
	
	def on_btDisplay_toggled(self, bt, *a):
		rvDisplaySettings = self.builder.get_object("rvDisplaySettings")
		rvDisplaySettings.set_reveal_child(bt.get_active())
	
	
	def on_swSharp_activate(self, b, value):
		if value:
			self.display.set_filter(Retro.VideoFilter.SHARP)
		else:
			self.display.set_filter(Retro.VideoFilter.SMOOTH)
	
	
	def on_tvFilter_cursor_changed(self, view):
		model, iter = view.get_selection().get_selected()
		item, = model.get(iter, 0)
		
		if item == "none":
			print Retro.VideoFilter.from_string("scanline")
			self.display.set_filter(Retro.VideoFilter.from_string("scanline"))
		elif item == "smooth":
			self.display.set_filter(Retro.VideoFilter.SMOOTH)
		elif item == "sharp":
			self.display.set_filter(Retro.VideoFilter.SHARP)
	
	
	def _run(self):
		if self.paused:
			btPlayPause = self.builder.get_object("btPlayPause")
			btPlayPause.set_sensitive(True)
			return False
		else:
			self.core.run()
			return True
	
	
	def on_core_initialized(self, *a):
		print "on_core_initialized", a
	
	
	def on_core_message(self, *a):
		print "on_core_message", a
	
	
	def on_window_delete_event(self, *a):
		""" Called when user tries to close window """
		return False
	
	
	def on_btPlayPause_clicked(self, button):
		imgPlayPause = self.builder.get_object("imgPlayPause")
		if self.paused:
			self.paused = False
			GLib.timeout_add(1000.0 / self.core.get_frames_per_second(), self._run)
			imgPlayPause.set_from_stock("gtk-media-pause", Gtk.IconSize.BUTTON)
		else:
			self.paused = True
			button.set_sensitive(False)
			imgPlayPause.set_from_stock("gtk-media-play", Gtk.IconSize.BUTTON)
	
	
	def on_ebMain_focus_out_event(self, box, whatever):
		box.grab_focus()
	
	
	def dpad_update(self, widget, event):
		""" Special case so dpad 'buttons' blings nicelly """
		x, y, width, height = widget.get_area_position("DPAD")
		x = event.x - x
		y = event.y - y
		update = False
		
		if y > height * 0.25 and y < height * 0.75:
			if x > width * 0.5:
				self.hilights["DPAD1"] = "DPAD_RIGHT"
				self.input.state |= App.TOUCH_MAPPINGS["DPAD_RIGHT"]
				self.input.state &= ~App.TOUCH_MAPPINGS["DPAD_LEFT"]
				update = True
			else:
				self.hilights["DPAD1"] = "DPAD_LEFT"
				self.input.state |= App.TOUCH_MAPPINGS["DPAD_LEFT"]
				self.input.state &= ~App.TOUCH_MAPPINGS["DPAD_RIGHT"]
				update = True
		elif "DPAD1" in self.hilights:
			del self.hilights["DPAD1"]
			self.input.state &= ~App.TOUCH_MAPPINGS["DPAD_LEFT"]
			self.input.state &= ~App.TOUCH_MAPPINGS["DPAD_RIGHT"]
			update = True
		
		if x > width * 0.25 and x < width * 0.75:
			if y > height * 0.5:
				self.hilights["DPAD2"] = "DPAD_DOWN"
				self.input.state |= App.TOUCH_MAPPINGS["DPAD_DOWN"]
				self.input.state &= ~App.TOUCH_MAPPINGS["DPAD_UP"]
				update = True
			else:
				self.hilights["DPAD2"] = "DPAD_UP"
				self.input.state |= App.TOUCH_MAPPINGS["DPAD_UP"]
				self.input.state &= ~App.TOUCH_MAPPINGS["DPAD_DOWN"]
				update = True
		elif "DPAD2" in self.hilights:
			del self.hilights["DPAD2"]
			self.input.state &= ~App.TOUCH_MAPPINGS["DPAD_UP"]
			self.input.state &= ~App.TOUCH_MAPPINGS["DPAD_DOWN"]
			update = True
		
		if update:
			widget.hilight({ a : self.HILIGHT for (trash, a) in self.hilights.items() })
	
	
	def dpad_cancel(self):
		if "DPAD1" in self.hilights:
			del self.hilights["DPAD1"]
		if "DPAD2" in self.hilights:
			del self.hilights["DPAD2"]
		self.input.state &= ~App.DPAD_DIRECTIONS
	
	
	def on_touch_event(self, widget, event):
		if event.type == Gdk.EventType.TOUCH_BEGIN:
			a = widget.get_area_at(event.x, event.y)
			if a:
				self.hilights[event.sequence] = a
				if a == "DPAD":
					self.dpad_update(widget, event)
				else:
					widget.hilight({ a : self.HILIGHT for (trash, a) in self.hilights.items() })
				if a in App.TOUCH_MAPPINGS:
					self.input.state |= App.TOUCH_MAPPINGS[a]
		elif event.type == Gdk.EventType.TOUCH_UPDATE:
			if self.hilights.get(event.sequence) == "DPAD":
				self.dpad_update(widget, event)
		elif event.type == Gdk.EventType.TOUCH_END:
			a = self.hilights.get(event.sequence)
			if a:
				if a == "DPAD": self.dpad_cancel()
				del self.hilights[event.sequence]
				if a in App.TOUCH_MAPPINGS:
					self.input.state &= ~App.TOUCH_MAPPINGS[a]
				widget.hilight({ a : self.HILIGHT for (trash, a) in self.hilights.items() })
	
	
	def on_window_key_press_event(self, window, event):
		if event.keyval in App.DEFAULT_MAPPINGS:
			self.input.state |= App.DEFAULT_MAPPINGS[event.keyval]
	
	
	def on_window_key_release_event(self, window, event):
		if event.keyval in App.DEFAULT_MAPPINGS:
			self.input.state &= ~App.DEFAULT_MAPPINGS[event.keyval]
	
	
	def do_command_line(self, cl):
		Gtk.Application.do_command_line(self, cl)
		if len(cl.get_arguments()) > 1:
			filename = " ".join(cl.get_arguments()[1:]) # 'cos fuck Gtk...
			self.select_core(filename)
		self.activate()
		return 0
	
	
	def do_activate(self, *a):
		self.builder.get_object("window").show()
	
	
	def do_startup(self, *a):
		Gtk.Application.do_startup(self, *a)
		self.setup_widgets()