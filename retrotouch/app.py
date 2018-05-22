#!/usr/bin/env python2
"""
RetroTouch - App

Main application window
"""
from __future__ import unicode_literals
from gi.repository import Gtk, Gdk, Gio, GLib, GdkPixbuf
from retrotouch.load_dialog import LoadDialog
from retrotouch.load_dialog import get_savegame_icon, tint_savegame_at
from retrotouch.native.wrapper import Wrapper
from retrotouch.config import Config
from retrotouch.data import DEFAULT_MAPPINGS, SUPPORTED_CORES, ALL_CORES
from retrotouch.data import CSS, UNKNOWN_FORMAT_ERROR
from retrotouch.paths import get_data_path
from retrotouch.osp import OSP
from retrotouch.tools import _

import os, logging, random, datetime
log = logging.getLogger("App")


class App(Gtk.Application):
	"""
	Main application / window.
	"""
	
	GLADE_FILE = "app.glade"
	CORE_ICON_SIZE = 24
	WIDGETS_ACTIVE_WHILE_LOADED = ( "btShowLoadScreen", "btCloseGame",
			"btQuickSave", "btPlayPause", "btCoreConfig" )
	HEADER_BUTTONS_START = ( "btPlayPause", "btQuickSave" )
	HEADER_BUTTONS_END = ( "btFullscreen", "btSettings" )
	
	def __init__(self, respath="/usr/share/retrotouch"):
		Gtk.Application.__init__(self,
				application_id="me.kozec.retrotouch",
				flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE | Gio.ApplicationFlags.NON_UNIQUE )
		Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)
		self.config = Config()
		self.dialogs = {}
		self.core_filenames = {}
		self.core_icons = {}
		self.pads = []
		self.respath = respath
		self.savegame_path = None
		self.fullscreen = False
		self._hfst_timer = None
		self._motion_h_id = None
		self.paused = False
		self.core = None
		self.save_to_load = None
		self.rom_to_load = None
	
	def setup_widgets(self):
		# Important stuff
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.respath, self.GLADE_FILE))
		self.builder.connect_signals(self)
		self.window = self.builder.get_object("window")
		self.add_window(self.window)
		self.window.set_title(_("RetroTouch"))
		self.window.set_wmclass("RetroTouch", "RetroTouch")
		
		provider = Gtk.CssProvider()
		provider.load_from_data(CSS.encode("utf-8"))
		Gtk.StyleContext.add_provider_for_screen(
			Gdk.Screen.get_default(), provider,
			Gtk.STYLE_PROVIDER_PRIORITY_USER - 1
		)
		
		# Drag&drop target
		self.window.drag_dest_set(Gtk.DestDefaults.ALL, [
			Gtk.TargetEntry.new("text/uri-list", Gtk.TargetFlags.OTHER_APP, 0),
			], Gdk.DragAction.COPY
		)
		
		self.pads = [
			OSP(self, 0, os.path.join(self.respath, "pads/default/up-left.svg")),
			OSP(self, 1, os.path.join(self.respath, "pads/default/up-right.svg")),
			OSP(self, 2, os.path.join(self.respath, "pads/default/down-left.svg")),
			OSP(self, 3, os.path.join(self.respath, "pads/default/down-right.svg")),
		]
		self.builder.get_object("asUpLeft").add(self.pads[0])
		self.builder.get_object("asUpRight").add(self.pads[1])
		self.builder.get_object("asDownLeft").add(self.pads[2])
		self.builder.get_object("asDownRight").add(self.pads[3])
		
		self.wrapper = None
		self.apply_pads()
		self.window.show_all()
	
	def setup_cores(self):
		"""
		Populates list of supported formats and starts task that checks
		for their availability
		"""
		lstSupported = self.builder.get_object("lstSupported")
		keys = list(SUPPORTED_CORES.keys())
		for key in keys:
			p = GdkPixbuf.Pixbuf.new_from_file_at_size(
					os.path.join(
						self.respath,
						"core_icons",
						key.lower() + ".svg"),
					self.CORE_ICON_SIZE, self.CORE_ICON_SIZE)
			self.core_icons[key] = p
			lstSupported.append((p, False, key, _('<i>Checking...</i>')))
		
		def check_next(keys):
			if len(keys):
				key, keys = keys[0], keys[1:]
				# TODO: more search options
				for core in ALL_CORES[key]:
					filename = "%s_libretro.so" % (core, )
					# TODO: Somehow get abs.path to ./cores
					for path in ("/usr/lib/libretro", "./cores"):
						path = os.path.join(path, filename)
						lst = list(SUPPORTED_CORES.keys())
						try:
							index = lst.index(key)
							if os.path.exists(path):
								self.core_filenames[key] = path
								lstSupported[index][3] = _("(%s)") % (core, )
								lstSupported[index][1] = True
								break
							else:
								lstSupported[index][3] = _("<i>libretro-%s not installed</i>") % (core, )
								lstSupported[index][1] = False
						except ValueError:
							# 'experimental' core
							if os.path.exists(path):
								self.core_filenames[key] = path
				
				GLib.idle_add(check_next, keys)
			elif self.rom_to_load:
				rom, self.rom_to_load = self.rom_to_load, None
				self.select_core(rom)
			
			return False
		
		GLib.idle_add(check_next, list(ALL_CORES.keys()))
	
	def select_core(self, rom_file):
		"""
		Uses async stuff to load file header and loads apropriate core.
		Or, with formats where headers are not used, just uses extensions.
		"""
		game_filename = rom_file.get_path()
		
		def analyze_file(stream, task):
			a = stream.read_bytes_finish(task).get_data()
			if a[0:4] == b"\x4e\x45\x53\x1A":
				log.debug("Loading NES game")
				self.load_game("NES", game_filename)
			elif a[0x100:0x102] == b"\x00\xc3":
				log.debug("Loading Gameboy game")
				GLib.timeout_add(100, self.load_game, "GB", game_filename)
			elif (a[1:0xb] == b"\x03\x00\x00\x00\x00\x00\x00\xaa\xbb\x06"
					or a[0x100:0x10f] == b"SEGA MEGA DRIVE"
					or a[0:0xe] == b"SEGADISCSYSTEM"):
				log.debug("Loading Sega Megadrive game")
				GLib.timeout_add(100, self.load_game, "Megadrive", game_filename)
			elif a[0x100:0x108] == b"SEGA 32X":
				# TODO: 32x
				log.debug("Loading Sega Megadrive game")
				GLib.timeout_add(100, self.load_game, "Sega32x", game_filename)
			elif a[0xC0:0xc9] == b"\x24\xff\xae\x51\x69\x9a\xa2\x21\x3d":
				# This matches logo in ROM header.
				# Matching by extension is better in NDS case, as logo
				# may be changed
				log.debug("Loading NDS game")
				self.load_game("NDS", game_filename)
			else:
				log.debug("Unknown file type")
				self.set_intro_status(random.choice(UNKNOWN_FORMAT_ERROR), True)
		
		def analyze_iso(stream, task):
			a = stream.read_bytes_finish(task).get_data()
			print (a[0x8008:0x8010],)
			if a[0:0xe] == b"SEGADISCSYSTEM":
				log.debug("Loading Sega Megadrive game")
				GLib.timeout_add(100, self.load_game, "Megadrive", game_filename)
			elif a[0:0x13] == b"\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x02\x00\x02\x00\x00\x08":
				# TODO: I'm not sure if this is right, but matches everything so far
				log.debug("Loading PS1 game")
				GLib.timeout_add(100, self.load_game, "PS1", game_filename)
			elif a[0x8008:0x8010] == b"PSP GAME":
				log.debug("Loading PSP game")
				GLib.timeout_add(100, self.load_game, "PSP", game_filename)
			else:
				log.debug("Unknown file type")
				self.set_intro_status(random.choice(UNKNOWN_FORMAT_ERROR), True)

		def read_header(file, task, size, cb):
			inputstream = file.read_finish(task)
			inputstream.read_bytes_async(size, 0, None, cb)
		
		if game_filename.lower().split(".")[-1] in ("smc", "snes"):
			log.debug("Loading SNES game")
			GLib.timeout_add(100, self.load_game, "SNES", game_filename)
		elif game_filename.lower().split(".")[-1] in ("iso", "img", "bin"):
			# May be PSP, PS1 or even Sega Megadrive game
			rom_file.read_async(0, None, read_header, 0x8040, analyze_iso)
		elif game_filename.lower().split(".")[-1] in ("cso",):
			log.debug("Loading PSP game")
			GLib.timeout_add(100, self.load_game, "PSP", game_filename)
		elif game_filename.lower().split(".")[-1] in ("gb", "sgb", "gbc", "cgb"):
			log.debug("Loading Gameboy game")
			GLib.timeout_add(100, self.load_game, "GB", game_filename)
		elif game_filename.lower().split(".")[-1] in ("nds",):
			log.debug("Loading NDS game")
			GLib.timeout_add(100, self.load_game, "NDS", game_filename)
		else:
			rom_file.read_async(0, None, read_header, 1024, analyze_file)
	
	def load_recent_games(self):
		lblContinue = self.builder.get_object("lblContinue")
		lstLoadGame = self.builder.get_object("lstLoadGame")
		rvLoadGame = self.builder.get_object("rvLoadGame")
		ivLoadGame = self.builder.get_object("ivLoadGame")
		lstLoadGame.clear()
		first = True
		for item in self.config['last_saves']:
			filepath = item["state"]
			gamepath = item["game"]
			pb = get_savegame_icon(filepath, at_size=64, max_height=48, tint=True)
			lstLoadGame.append(( pb, "xxx", filepath, gamepath) )
			if first:
				first = False
				lblContinue.set_visible(True)
				rvLoadGame.set_visible(True)
				ivLoadGame.set_visible(True)
		if first:
			rvFormats = self.builder.get_object("rvFormats")
			rvFormats.set_reveal_child(True)
	
	def load_game(self, rom_type, game_path):
		if self.wrapper:
			self.wrapper.destroy()
		try:
			core_filename = self.core_filenames[rom_type]
			self.set_icon(rom_type)
		except KeyError:
			core = ALL_CORES[rom_type][0]
			self.set_icon(None)
			self.set_intro_status(
				_("Please, install %s core to run %s game") % (core, rom_type),
				True)
			return
		ebMain = self.builder.get_object("ebMain")
		btQuickSave = self.builder.get_object("btQuickSave")
		name = os.path.splitext(os.path.split(game_path)[-1])[0]
		self.savegame_path = os.path.join(get_data_path(), "savegames", name)
		try:
			os.makedirs(self.savegame_path)
		except: pass
		btQuickSave.set_visible(False)
		self.wrapper = Wrapper(self, ebMain, core_filename, game_path)
		self.wrapper.set_vsync(False)
		self.select_pads(rom_type, name)
		for pad in self.pads:
			pad.on_size_allocate(pad)
	
	def apply_pads(self):
		asUpLeft = self.builder.get_object("asUpLeft")
		asUpRight = self.builder.get_object("asUpRight")
		asDownLeft = self.builder.get_object("asDownLeft")
		asDownRight = self.builder.get_object("asDownRight")
		
		asUpLeft.set_margin_left(self.config["padding"]["left_outer"])
		asDownLeft.set_margin_left(self.config["padding"]["left_outer"])
		asUpLeft.set_margin_right(10)
		asDownLeft.set_margin_right(10)

		asUpRight.set_margin_left(10)
		asDownRight.set_margin_left(10)
		asUpRight.set_margin_right(self.config["padding"]["right_outer"])
		asDownRight.set_margin_right(self.config["padding"]["right_outer"])

		asUpLeft.set_margin_top(self.config["padding"]["left_top"])
		asUpRight.set_margin_top(self.config["padding"]["right_top"])
		asDownLeft.set_margin_bottom(self.config["padding"]["left_bottom"])
		asDownRight.set_margin_bottom(self.config["padding"]["right_bottom"])
		
		grNotGame = self.builder.get_object("grNotGame")
		grNotGame.size_allocate(grNotGame.get_allocation())
	
	def set_icon(self, rom_type):
		if rom_type in self.core_icons:
			self.window.set_icon(self.core_icons[rom_type])
	
	def select_pads(self, type, name):
		self.pads[0].set_image(os.path.join(self.respath, "pads/%s/up-left.svg" % (type,)))
		self.pads[1].set_image(os.path.join(self.respath, "pads/%s/up-right.svg" % (type,)))
		self.pads[2].set_image(os.path.join(self.respath, "pads/%s/down-left.svg" % (type,)))
		self.pads[3].set_image(os.path.join(self.respath, "pads/%s/down-right.svg" % (type,)))
	
	def on_core_ready(self):
		stMain = self.builder.get_object("stMain")
		ebMain = self.builder.get_object("ebMain")
		
		stMain.set_visible_child(ebMain)
		self.set_intro_status("", False)
		for w in self.WIDGETS_ACTIVE_WHILE_LOADED:
			self.builder.get_object(w).set_sensitive(True)
		for pad in self.pads:
			pad.on_size_allocate(pad)
			pad.update_hilights(pad)
		if self.save_to_load:
			filename, self.save_to_load = self.save_to_load, None
			self.wrapper.load_state(filename)
	
	def on_core_finished(self):
		stMain = self.builder.get_object("stMain")
		grNotGame = self.builder.get_object("grNotGame")
		stNotGame = self.builder.get_object("stNotGame")
		grIntroScreen = self.builder.get_object("grIntroScreen")
		stMain.set_visible_child(grNotGame)
		stNotGame.set_visible_child(grIntroScreen)
		self.wrapper = None
		self.set_intro_status(_("Game finished"), True)
		self.builder.get_object("btFullscreen").set_active(False)
		for w in self.WIDGETS_ACTIVE_WHILE_LOADED:
			self.builder.get_object(w).set_sensitive(False)
	
	def on_core_crashed(self):
		stMain = self.builder.get_object("stMain")
		stNotGame = self.builder.get_object("stNotGame")
		grNotGame = self.builder.get_object("grNotGame")
		grCrash = self.builder.get_object("grCrash")
		lblCrash = self.builder.get_object("lblCrash")
		btCloseGame = self.builder.get_object("btCloseGame")
		lblCrash.set_visible(True)
		ttype = stMain.get_transition_type()
		stMain.set_transition_type(Gtk.StackTransitionType.NONE)
		stMain.set_visible_child(grNotGame)
		stNotGame.set_visible_child(grCrash)
		stMain.set_transition_type(ttype)
		self.wrapper = None
		self.set_intro_status("", True)
		# self.builder.get_object("btFullscreen").set_active(False)
		for w in self.WIDGETS_ACTIVE_WHILE_LOADED:
			self.builder.get_object(w).set_sensitive(False)
		btCloseGame.set_sensitive(True)
	
	def on_saving_supported(self):
		btQuickSave = self.builder.get_object("btQuickSave")
		btQuickSave.set_visible(True)
	
	def on_render_size_changed(self, width, height):
		ebMain = self.builder.get_object("ebMain")
		rect = ebMain.get_allocation()
		a = float(width) / float(height)
		if rect.height * a <= rect.width:
			self.wrapper.set_screen_size(int(rect.height * a), int(rect.height))
		else:
			self.wrapper.set_screen_size(int(rect.width), int(rect.width / a))
			
		GLib.timeout_add(100, self.wrapper.ping)
	
	def on_close_dont_destroy(self, window, *a):
		window.set_visible(False)
		return True
	
	def on_btSettings_clicked(self, bt, *a):
		ppMenu = self.builder.get_object("ppMenu")
		ppMenu.popup()
	
	def on_btFullscreen_toggled(self, bt, *a):
		vbFullscreen = self.builder.get_object("vbFullscreen")
		hbWindow = self.builder.get_object("hbWindow")
		
		if bt.get_active():
			move_to = vbFullscreen
			args = False, False, 0
			self.window.fullscreen()
			self.show_fullscreen_toolbar()
			self._motion_h_id = self.window.connect("motion-notify-event", self.on_window_motion_notify)
			self.fullscreen = True
		else:
			move_to = hbWindow
			args = ()
			self.window.disconnect(self._motion_h_id)
			self.hide_fullscreen_toolbar()
			self.window.unfullscreen()
			self.fullscreen = False
		
		for w in self.HEADER_BUTTONS_START:
			x = self.builder.get_object(w)
			x.get_parent().remove(x)
			move_to.pack_start(x, *args)
		for w in reversed(self.HEADER_BUTTONS_END):
			x = self.builder.get_object(w)
			x.get_parent().remove(x)
			move_to.pack_end(x, *args)
	
	def on_btCoreConfig_clicked(self, *a):
		from retrotouch.core_config import CoreConfigDialog
		ppMenu = self.builder.get_object("ppMenu")
		CoreConfigDialog(self).show()
		ppMenu.popdown()
	
	def on_btPadConfig_clicked(self, *a):
		from retrotouch.pad_config import PadConfigDialog
		ppMenu = self.builder.get_object("ppMenu")
		PadConfigDialog(self).show()
		ppMenu.popdown()
	
	def on_btShowLoadScreen_clicked(self, *a):
		ppMenu = self.builder.get_object("ppMenu")
		ppMenu.popdown()
		load_dialog = self.dialogs.get(LoadDialog)
		if load_dialog is None:
			load_dialog = self.dialogs[LoadDialog] = LoadDialog(self)
		load_dialog.show()
	
	def on_btCloseGame_clicked(self, *a):
		ppMenu = self.builder.get_object("ppMenu")
		ppMenu.popdown()
		if self.wrapper:
			self.wrapper.destroy()
		self.on_core_finished()
	
	def on_btPlayPause_clicked(self, *a):
		if self.wrapper:
			self.wrapper.set_paused(not self.paused)
	
	def on_btQuickSave_clicked(self, *a):
		if self.wrapper:
			filename = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
			savefile = os.path.join(self.savegame_path, filename)
			
			self.wrapper.save_both(savefile, "sav", "png")
	
	def ivLoadGame_item_activated_cb(self, view, path):
		self.save_to_load = view.get_model()[path][2]
		self.select_core(Gio.File.new_for_path(view.get_model()[path][3]))
	
	def on_ivLoadGame_motion_notify_event(self, iv, event):
		tint_savegame_at(iv, event.x, event.y, at_size=64, max_height=48)
	
	def on_txSavedGame_key_press_event(self, entry, event):
		if event.keyval in (Gdk.KEY_KP_Enter, Gdk.KEY_Return):
			ppSaved = self.builder.get_object("ppSaved")
			ppSaved.popdown()
	
	def on_state_saved(self, filename):
		imgSavedGame = self.builder.get_object("imgSavedGame")
		txSavedGame = self.builder.get_object("txSavedGame")
		pb = get_savegame_icon(filename, at_size=64)
		txSavedGame.set_text(os.path.split(filename)[-1][:-4])
		txSavedGame.set_sensitive(True)
		txSavedGame._last_filename = filename
		imgSavedGame.set_from_pixbuf(pb)
		ppSaved = self.builder.get_object("ppSaved")
		ppSaved.popup()
		txSavedGame.grab_focus()
	
	def on_txSavedGame_changed(self, txSavedGame):
		try:
			old_filename = txSavedGame._last_filename
		except AttributeError:
			return
		if not txSavedGame.get_sensitive():
			return
		new_name = txSavedGame.get_text()
		if len(new_name) < 1: return
		path, old_name = os.path.split(old_filename)
		ext = old_filename.split(".")[-1]
		old_screenshot = old_filename[0:-len(ext)] + "png"
		new_filename = os.path.join(path, "%s.%s" % (new_name, ext))
		while os.path.exists(new_filename):
			new_name += "_"
			new_filename = os.path.join(path, "%s.%s" % (new_name, ext))
		new_screenshot = new_filename[0:-len(ext)] + "png"
		
		try:
			log.debug("Renaming %s -> %s", old_filename, new_filename)
			os.rename(old_filename, new_filename)
			if os.path.exists(old_screenshot):
				os.rename(old_screenshot, new_screenshot)
			txSavedGame._last_filename = new_filename
		except OSError, e:
			log.exception(e)
			txSavedGame.set_sensitive(False)
			del txSavedGame._last_filename
	
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
			grNotGame = self.builder.get_object("grNotGame")
			grNotGame.size_allocate(rect)
			self.wrapper.set_size_allocation(rect.width, rect.height)
			self.on_render_size_changed(*self.wrapper.render_size)
			for pad in self.pads:
				pad.on_size_allocate(pad)
	
	def on_ebMain_touch_event(self, eb, event):
		if self.wrapper:
			index, px, py = self.wrapper.get_pad_at(event.x, event.y)
			if index >= 0:
				event.x, event.y = event.x - px, event.y - py
				self.pads[index].on_event(self.pads[index], event)
	
	def on_ebMain_button_event(self, eb, event):
		if self.wrapper:
			index, px, py = self.wrapper.get_pad_at(event.x, event.y)
			if index >= 0:
				event.x, event.y = event.x - px, event.y - py
				self.pads[index].on_event(self.pads[index], event)
				return
			button = 2			# RETRO_DEVICE_ID_MOUSE_LEFT
			if event.button == 2:
				button = 6		# RETRO_DEVICE_ID_MOUSE_MIDDLE
			elif event.button == 3:
				button = 3		# RETRO_DEVICE_ID_MOUSE_RIGHT
			self._set_mouse(event)
			self.wrapper.set_mouse_button(button, event.type == Gdk.EventType.BUTTON_PRESS)
	
	def _set_mouse(self, event):
		ax = float(self.wrapper.width) / float(self.wrapper.screen_size[0])
		ay = float(self.wrapper.height) / float(self.wrapper.screen_size[1])
		x = int(max(-0x7FFF, min(0x7FFF, ax * ((float(event.x) / self.wrapper.width * 2.0) - 1.0) * 0x7FFF)))
		y = int(max(-0x7FFF, min(0x7FFF, ay * ((float(event.y) / self.wrapper.height * 2.0) - 1.0) * 0x7FFF)))
		self.wrapper.set_mouse(x, y)
	
	def on_ebMain_motion_notify_event(self, eb, event):
		if self.wrapper:
			self._set_mouse(event)
	
	def on_window_key_press_event(self, window, event):
		if event.keyval in DEFAULT_MAPPINGS:
			self.wrapper.set_button(DEFAULT_MAPPINGS[event.keyval], True)
	
	def on_window_key_release_event(self, window, event):
		if event.keyval in DEFAULT_MAPPINGS:
			self.wrapper.set_button(DEFAULT_MAPPINGS[event.keyval], False)
	
	def on_drag_data_received(self, widget, context, x, y, data, info, time):
		if self.wrapper: return
		try:
			file = Gio.File.new_for_uri(data.get_uris()[0])
			GLib.idle_add(self.select_core, file)
			self.set_intro_status(_("Just a moment..."), False)
			self.window.grab_focus()
			return True
		except Exception, e:
			log.exception(e)
	
	def set_intro_status(self, text, intro_sensitivity=True):
		stNotGame = self.builder.get_object("stNotGame")
		lblIntroStatus = self.builder.get_object("lblIntroStatus")
		lblIntroStatus.set_label(text)
		stNotGame.set_sensitive(intro_sensitivity)
	
	def on_drag_motion(self, widget, *a):
		if self.wrapper: return
		img = self.builder.get_object("imgFolderIcon")
		name, size = img.get_icon_name()
		if name == "folder":
			img.set_from_icon_name("folder-drag-accept", size)
	
	def on_drag_leave(self, widget, *a):
		img = self.builder.get_object("imgFolderIcon")
		name, size = img.get_icon_name()
		img.set_from_icon_name("folder", size)
	
	def do_command_line(self, cl):
		Gtk.Application.do_command_line(self, cl)
		if len(cl.get_arguments()) > 1:
			filename = " ".join(cl.get_arguments()[1:]) # 'cos fuck Gtk...
			self.rom_to_load = Gio.File.new_for_path(filename)
		self.activate()
		return 0
	
	def get_screen_size():
		ebMain = self.builder.get_object("ebMain")
		rect = ebMain.get_allocation()
		return rect.width, rect.height
	
	def do_activate(self, *a):
		self.builder.get_object("window").show()
	
	def do_startup(self, *a):
		Gtk.Application.do_startup(self, *a)
		self.setup_widgets()
		self.setup_cores()
		self.load_recent_games()
	
	def on_window_motion_notify(self, trash, event):
		if event.y < 25:
			self.show_fullscreen_toolbar()
	
	def show_fullscreen_toolbar(self, *a):
		if self._hfst_timer is None:
			rvFullscreen = self.builder.get_object("rvFullscreen")
			rvFullscreen.set_visible(True)
			rvFullscreen.set_reveal_child(True)
			self._hfst_timer = GLib.timeout_add_seconds(2, self.hide_fullscreen_toolbar)
		else:
			GLib.source_remove(self._hfst_timer)
			self._hfst_timer = GLib.timeout_add_seconds(2, self.hide_fullscreen_toolbar)

	def hide_fullscreen_toolbar(self, *a):
		rvFullscreen = self.builder.get_object("rvFullscreen")
		rvFullscreen.set_reveal_child(False)
		if self._hfst_timer is not None:
			GLib.source_remove(self._hfst_timer)
		self._hfst_timer = None
