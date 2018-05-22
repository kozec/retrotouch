#!/usr/bin/env python2
"""
RetroTouch - LoadDialog

Displays list of saved games
"""
from __future__ import unicode_literals
from gi.repository import Gtk, Gdk, GdkPixbuf

import os, subprocess, logging
log = logging.getLogger("LoadDlg")


class LoadDialog:
	GLADE_FILE = "load_dialog.glade"
	
	def __init__(self, app):
		self.app = app
		self.setup_widgets()
	
	def setup_widgets(self):
		# Important stuff
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.respath, self.GLADE_FILE))
		self.builder.connect_signals(self)
		self.window = self.builder.get_object("window")
	
	def show(self, *a):
		self.load_savegames()
		self.window.set_transient_for(self.app.window)
		self.window.set_visible(True)
	
	def on_btOpenSavegameFolder_clicked(self, *a):
		subprocess.Popen(["xdg-open", self.app.savegame_path])
	
	def load_savegames(self):
		lstLoadGame = self.builder.get_object("lstLoadGame")
		ivLoadGame = self.builder.get_object("ivLoadGame")
		lstLoadGame.clear()
		names = []
		try:
			names = os.listdir(self.app.savegame_path)
		except OSError:
			pass
		for name in reversed(sorted(names)):
			if name.endswith(".sav"):
				filepath = os.path.join(self.app.savegame_path, name)
				pb = get_savegame_icon(filepath, at_size=128, tint=True)
				lstLoadGame.append(( pb, name[:-4], filepath) )
		if len(lstLoadGame) > 0:
			ivLoadGame.select_path(Gtk.TreePath())
	
	def on_close_dont_destroy(self, window, *a):
		window.set_visible(False)
		return True
	
	def on_btLoadGame_clicked(self, *a):
		ivLoadGame = self.builder.get_object("ivLoadGame")
		try:
			filename = ivLoadGame.get_model()[ivLoadGame.get_selected_items()[0]][-1]
		except IndexError:
			return
		clear_icon_cache()
		self.window.set_visible(False)
		self.app.wrapper.load_state(filename)
	
	def on_ivLoadGame_motion_notify_event(self, iv, event):
		tint_savegame_at(iv, event.x, event.y, at_size=128)


def tint_savegame_at(iv, x, y, **opts):
	item = iv.get_item_at_pos(x, y)
	if getattr(iv, "_selected", None):
		path = iv._selected
		iv.get_model()[path][0] = get_savegame_icon(
				iv.get_model()[path][2], tint=True, **opts)
		iv._selected = None
	w = iv.get_window()
	if item:
		path, trash = item
		iv.get_model()[path][0] = get_savegame_icon(
				iv.get_model()[path][2], tint=False, **opts)
		iv._selected = path
		w.set_cursor(Gdk.Cursor.new_from_name(w.get_display(), "pointer"))
	else:
		w.set_cursor(None)


floppy_icon_cache = {}
other_icon_cache = {}
FLOPPY_ICONS = [ "media-floppy", "gtk-floppy", "system-floppy",
				"gnome-dev-floppy", "kfloppy", "media-floppy-symbolic" ]


def get_savegame_icon(filepath, at_size, max_height=-1, tint=False):
	global floppy_icon, other_icon_cache
	filepath = filepath[:-4] + ".png"
	if os.path.exists(filepath):
		try:
			key = (filepath, at_size, max_height)
			if key in other_icon_cache:
				pb = other_icon_cache[key]
			else:
				pb = GdkPixbuf.Pixbuf.new_from_file_at_size(filepath, at_size, -1)
				if max_height > 0:
					w, h = pb.get_width(), pb.get_height()
					if h > max_height:
						pb = pb.new_subpixbuf(0, (h - max_height) * 0.5,
												w, max_height)
			other_icon_cache[key] = pb
			if tint:
				new_pb = GdkPixbuf.Pixbuf.new(pb.get_colorspace(), False,
					pb.get_bits_per_sample(), pb.get_width(), pb.get_height())
				pb.saturate_and_pixelate(new_pb, 0.25, False)
				pb = new_pb
			return pb
		except Exception, e:
			log.exception(e)
	
	if at_size in floppy_icon_cache:
		return floppy_icon_cache[at_size]
	iconinfo = Gtk.IconTheme.get_default().choose_icon(FLOPPY_ICONS,
				at_size, Gtk.IconLookupFlags.FORCE_SIZE)
	icon = iconinfo.load_icon()
	floppy_icon_cache[at_size] = icon
	return icon


def clear_icon_cache():
	global other_icon_cache
	other_icon_cache = {}
