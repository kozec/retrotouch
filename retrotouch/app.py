#!/usr/bin/env python2
"""
RetroTouch - App

Main application window
"""
from __future__ import unicode_literals
from gi.repository import Retro, Gtk, Gdk, Gio, GLib, GObject
from retrotouch.svg_widget import SVGWidget
from retrotouch.tools import _, set_logging_level

import os, logging
log = logging.getLogger("App")

class App(Gtk.Application):
	"""
	Main application / window.
	"""
	
	DEFAULT_MAPPINGS = {
		Gdk.KEY_Return:		1 << Retro.GamepadButtonType.START,
		Gdk.KEY_Shift_R:	1 << Retro.GamepadButtonType.SELECT,
		Gdk.KEY_Up:			1 << Retro.GamepadButtonType.DIRECTION_UP,
		Gdk.KEY_Down:		1 << Retro.GamepadButtonType.DIRECTION_DOWN,
		Gdk.KEY_Left:		1 << Retro.GamepadButtonType.DIRECTION_LEFT,
		Gdk.KEY_Right:		1 << Retro.GamepadButtonType.DIRECTION_RIGHT,
		Gdk.KEY_z:			1 << Retro.JoypadId.B,
		Gdk.KEY_y:			1 << Retro.JoypadId.B,
		Gdk.KEY_x:			1 << Retro.JoypadId.A,
	}
	
	
	def __init__(self, gladepath="/usr/share/retrotouch",
						imagepath="/usr/share/retrotouch/images"):
		Gtk.Application.__init__(self,
				application_id="me.kozec.retrotouch",
				flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE | Gio.ApplicationFlags.NON_UNIQUE )
		Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)
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
		
		rvLeft = self.builder.get_object("rvLeft")
		rvRight = self.builder.get_object("rvRight")
		self.left = SVGWidget(os.path.join(self.imagepath, "pads/nes/left.svg"))
		self.right = SVGWidget(os.path.join(self.imagepath, "pads/nes/right.svg"))
		rvLeft.add(self.left)
		rvRight.add(self.right)
		
		self.display = Retro.CairoDisplay()
		self.display.set_size_request(320, 200)
		box = self.builder.get_object("ebMain")
		box.add(self.display)
		self.window.show_all()
		
		self.controller_interface = Retro.InputDeviceManager()
		self.input = RTInput().initialize()
		self.controller_interface.set_controller_device (0, self.input)
		# self.gamepad = Retro.VirtualGamepad.new(box)
		# self.controller_interface.set_keyboard(Retro.Keyboard.new(box))
		
		GLib.timeout_add(100, self.load_game, "Super Mario Bros (E).nes")
	
	
	def load_game(self, path):
		core = "/usr/lib/libretro/nestopia_libretro.so"
		self.game = Retro.GameInfo()
		self.game.init_with_data(path)
		self.core = Retro.Core.new(core)
		self.core.connect("init", self.on_core_initialized)
		self.core.connect("message", self.on_core_message)
		self.core.set_input_interface(self.controller_interface)
		self.core.do_init(self.core)
		self.display.set_core(self.core)
		self.core.load_game(self.game)
		self.paused = False
		GLib.timeout_add(1000.0 / self.core.get_frames_per_second(), self._run)
	
	
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
	
	
	def do_command_line(self, cl):
		Gtk.Application.do_command_line(self, cl)
		self.activate()
		return 0
	
	
	def do_activate(self, *a):
		self.builder.get_object("window").show()
	
	
	def on_window_key_press_event(self, window, event):
		if event.keyval in App.DEFAULT_MAPPINGS:
			self.input.state |= App.DEFAULT_MAPPINGS[event.keyval]
	
	
	def on_window_key_release_event(self, window, event):
		if event.keyval in App.DEFAULT_MAPPINGS:
			self.input.state &= ~App.DEFAULT_MAPPINGS[event.keyval]
	
	
	def do_startup(self, *a):
		Gtk.Application.do_startup(self, *a)
		self.setup_widgets()


class RTInput(GObject.GObject, Retro.InputDevice):
	
	def initialize(self):
		# Because InputDevice classhes with GObject in __init__ 
		self.state = 0
		return self
	
	
	def do_get_device_capabilities(self):
		caps = 0
		caps |= (1 << Retro.DeviceType.JOYPAD)
		# caps |= (1 << Retro.DeviceType.ANALOG)
		return caps
	
	
	def do_get_device_type(self):
		return Retro.DeviceType.JOYPAD
	
	
	def do_get_input_state(self, device, index, id):
		# print "input", device, index, id
		if device == Retro.DeviceType.JOYPAD:
			return self.state & (1 << id)
		else:
			print device
	
	
	def do_poll(self):
		return True
