#!/usr/bin/env python2
"""
RetroTouch - App

Main application window
"""
from __future__ import unicode_literals
from gi.repository import Gtk, Gdk, Gio, GLib
from retrotouch.svg_widget import SVGWidget
from retrotouch.native.wrapper import Wrapper
from retrotouch.paths import get_data_path
from retrotouch.tools import _

import os, logging, datetime
log = logging.getLogger("App")


class App(Gtk.Application):
	"""
	Main application / window.
	"""
	
	HILIGHT = "#FF0000"
	DEFAULT_MAPPINGS = {
		Gdk.KEY_Return:		2,	# RETRO_DEVICE_ID_JOYPAD_SELECT
		Gdk.KEY_Shift_R:	3,	# RETRO_DEVICE_ID_JOYPAD_START
		Gdk.KEY_Up:			4,	# RETRO_DEVICE_ID_JOYPAD_UP
		Gdk.KEY_Down:		5,	# RETRO_DEVICE_ID_JOYPAD_DOWN
		Gdk.KEY_Left:		6,	# RETRO_DEVICE_ID_JOYPAD_LEFT
		Gdk.KEY_Right:		7,	# RETRO_DEVICE_ID_JOYPAD_RIGHT
		Gdk.KEY_z:			8,	# RETRO_DEVICE_ID_JOYPAD_A
		Gdk.KEY_x:			0,	# RETRO_DEVICE_ID_JOYPAD_B
		Gdk.KEY_a:			9,	# RETRO_DEVICE_ID_JOYPAD_X
		Gdk.KEY_s:			1,	# RETRO_DEVICE_ID_JOYPAD_Y
	}
	
	TOUCH_MAPPINGS = {
		"A":			8,
		"B":			0,
		"START":		3,
		"SELECT":		2,
		"DPAD_UP":		4,
		"DPAD_DOWN":	5,
		"DPAD_LEFT":	6,
		"DPAD_RIGHT":	7,
	}
	
	DPAD_DIRECTIONS = (4, 5, 6, 7)
	
	
	def __init__(self, respath="/usr/share/retrotouch"):
		Gtk.Application.__init__(self,
				application_id="me.kozec.retrotouch",
				flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE | Gio.ApplicationFlags.NON_UNIQUE )
		Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)
		self.hilights = {}
		self.core = None
		self.respath = respath
		self.paused = False
	
	
	def setup_widgets(self):
		# Important stuff
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.respath, "app.glade"))
		self.builder.connect_signals(self)
		self.window = self.builder.get_object("window")
		self.add_window(self.window)
		self.window.set_title(_("RetroTouch"))
		self.window.set_wmclass("RetroTouch", "RetroTouch")
		
		asLeft = self.builder.get_object("asLeft")
		asRight = self.builder.get_object("asRight")
		self.left = SVGWidget(os.path.join(self.respath, "pads/nes/left.svg"))
		self.right = SVGWidget(os.path.join(self.respath, "pads/nes/right.svg"))
		asLeft.add(self.left)
		asRight.add(self.right)
		
		for x in (self.left, self.right):
			x.set_events(Gdk.EventMask.TOUCH_MASK)
			x.connect('touch-event', self.on_touch_event)
		
		self.wrapper = None
		self.window.show_all()
		
		# Glib.idle_add(self.select_core, "./Danganronpa [EN][v1.0][Full].iso")
		GLib.idle_add(self.select_core, "./Super Mario Bros (E).nes")
	
	
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
		if self.wrapper:
			self.wrapper.destroy()
		ebMain = self.builder.get_object("ebMain")
		self.wrapper = Wrapper(self, ebMain, self.find_core_filename(core), game_path)
	
	
	def on_btSettings_toggled(self, bt, *a):
		rvToolbar = self.builder.get_object("rvToolbar")
		def change(*a):
			if bt.get_active():
				rvToolbar.set_reveal_child(True)
			else:
				rvToolbar.set_reveal_child(False)
			return False
		
		def pause_resume(*a):
			self.on_btPlayPause_clicked()
			return False
		
		if self.paused:
			change()
		else:
			pause_resume()
			GLib.idle_add(change)
			GLib.timeout_add(rvToolbar.get_transition_duration() + 50, pause_resume)
	
	
	def on_btPlayPause_clicked(self, *a):
		if self.wrapper:
			self.wrapper.set_paused(not self.paused)
	
	
	def on_btQuickSave_clicked(self, *a):
		if self.wrapper:
			path = get_data_path()
			try:
				os.makedirs(path)
			except: pass
			savefile = os.path.join(path, "%s-%s.sav" % (
				"game",
				datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
			))
			
			self.wrapper.save_state(savefile)
	
	
	def on_window_delete_event(self, *a):
		""" Called when user tries to close window """
		if self.wrapper:
			self.wrapper.destroy()
		return False
	
	
	def on_playpause_changed(self, paused):
		imgPlayPause = self.builder.get_object("imgPlayPause")
		if paused:
			imgPlayPause.set_from_stock("gtk-media-play", Gtk.IconSize.BUTTON)
		else:
			imgPlayPause.set_from_stock("gtk-media-pause", Gtk.IconSize.BUTTON)
		self.paused = paused
	
	
	def on_ebMain_focus_out_event(self, box, whatever):
		# box.grab_focus()
		pass
	
	
	def on_ebMain_size_allocate(self, eb, rect):
		if self.wrapper:
			self.wrapper.set_size_allocation(rect.width, rect.height)
	
	
	def dpad_update(self, widget, event):
		""" Special case so dpad 'buttons' blinks nicelly """
		x, y, width, height = widget.get_area_position("DPAD")
		x = event.x - x
		y = event.y - y
		update = False
		
		if "DPAD1" not in self.hilights:
			self.hilights["DPAD1"] = TouchData(set())
		if "DPAD2" not in self.hilights:
			self.hilights["DPAD2"] = TouchData(set())
		
		if y > height * 0.25 and y < height * 0.75:
			if x > width * 0.5:
				self.hilights["DPAD1"].set_areas(set(("DPAD_RIGHT", )))
				self.wrapper.set_button(App.TOUCH_MAPPINGS["DPAD_RIGHT"], True)
				self.wrapper.set_button(App.TOUCH_MAPPINGS["DPAD_LEFT"], False)
				update = True
			else:
				self.hilights["DPAD1"].set_areas(set(("DPAD_LEFT", )))
				self.wrapper.set_button(App.TOUCH_MAPPINGS["DPAD_LEFT"], True)
				self.wrapper.set_button(App.TOUCH_MAPPINGS["DPAD_RIGHT"], False)
				update = True
		elif "DPAD1" in self.hilights:
			del self.hilights["DPAD1"]
			self.wrapper.set_button(App.TOUCH_MAPPINGS["DPAD_LEFT"], True)
			self.wrapper.set_button(App.TOUCH_MAPPINGS["DPAD_RIGHT"], False)
			update = True
		
		if x > width * 0.25 and x < width * 0.75:
			if y > height * 0.5:
				self.hilights["DPAD2"].set_areas(set(("DPAD_DOWN", )))
				self.wrapper.set_button(App.TOUCH_MAPPINGS["DPAD_DOWN"], True)
				self.wrapper.set_button(App.TOUCH_MAPPINGS["DPAD_UP"], False)
				update = True
			else:
				self.hilights["DPAD2"].set_areas(set(("DPAD_UP", )))
				self.wrapper.set_button(App.TOUCH_MAPPINGS["DPAD_UP"], True)
				self.wrapper.set_button(App.TOUCH_MAPPINGS["DPAD_DOWN"], False)
				update = True
		elif "DPAD2" in self.hilights:
			del self.hilights["DPAD2"]
			self.wrapper.set_button(App.TOUCH_MAPPINGS["DPAD_UP"], True)
			self.wrapper.set_button(App.TOUCH_MAPPINGS["DPAD_DOWN"], False)
			update = True
		
		if update:
			self.update_hilights(widget)
	
	
	def dpad_cancel(self):
		if "DPAD1" in self.hilights:
			del self.hilights["DPAD1"]
		if "DPAD2" in self.hilights:
			del self.hilights["DPAD2"]
		for i in App.DPAD_DIRECTIONS:
			self.wrapper.set_button(i, False)
	
	
	def on_touch_event(self, widget, event):
		if event.type == Gdk.EventType.TOUCH_BEGIN:
			self.hilights[event.sequence] = TouchData(set(widget.get_areas_at(event.x, event.y)), from_event=event)
			hi = self.hilights[event.sequence]
			if hi.is_dpad:
				self.dpad_update(widget, event)
			else:
				for a in hi.areas:
					if a in App.TOUCH_MAPPINGS:
						self.wrapper.set_button(App.TOUCH_MAPPINGS[a], True)
				self.update_hilights(widget)
		elif event.type == Gdk.EventType.TOUCH_UPDATE:
			hi = self.hilights.get(event.sequence)
			if hi is not None:
				if hi.is_dpad:
					self.dpad_update(widget, event)
				elif hi.is_change(event):
					c = set(widget.get_areas_at(event.x, event.y))
					if c.symmetric_difference(hi.areas):
						for a in hi.areas - c:
							self.wrapper.set_button(App.TOUCH_MAPPINGS[a], False)
						for a in c - hi.areas:
							self.wrapper.set_button(App.TOUCH_MAPPINGS[a], True)
						hi.set_areas(c, from_event=event)
						self.update_hilights(widget)
		elif event.type == Gdk.EventType.TOUCH_END:
			hi = self.hilights.get(event.sequence)
			if hi:
				if hi.is_dpad:
					self.dpad_cancel()
				else:
					for a in hi.areas:
						if a in App.TOUCH_MAPPINGS:
							self.wrapper.set_button(App.TOUCH_MAPPINGS[a], False)
				del self.hilights[event.sequence]
				self.update_hilights(widget)
	
	
	def update_hilights(self, widget):
		areas = reduce(
			lambda a,b: a.union(b),
			(set(x.areas) for x in self.hilights.values()),
			set()
		)
		widget.hilight({ a : self.HILIGHT for a in areas })
	
	
	def on_window_key_press_event(self, window, event):
		if event.keyval in App.DEFAULT_MAPPINGS:
			self.wrapper.set_button(App.DEFAULT_MAPPINGS[event.keyval], True)
	
	
	def on_window_key_release_event(self, window, event):
		if event.keyval in App.DEFAULT_MAPPINGS:
			self.wrapper.set_button(App.DEFAULT_MAPPINGS[event.keyval], False)
	
	
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
	


class TouchData:
	
	def __init__(self, areas, from_event=None):
		self.areas = areas
		self.is_dpad = "DPAD" in areas
		if from_event:
			self.from_event = True
			self.x, self.y = int(from_event.x), int(from_event.y)
		else:
			self.from_event = False
	
	
	def set_areas(self, new_list, from_event=None):
		""" Returns True if list was changed """
		old, self.areas = self.areas, new_list
		if from_event:
			self.x, self.y = int(from_event.x), int(from_event.y)
		return old != self.areas
	
	
	def is_change(self, event):
		if not self.from_event:
			return False
		return int(event.x) != self.x or int(event.y) != self.y
