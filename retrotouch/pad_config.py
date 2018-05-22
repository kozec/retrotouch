#!/usr/bin/env python2
"""
RetroTouch - Virtual Gamepad config dialog
"""
from __future__ import unicode_literals
from gi.repository import Gtk

import os, logging
log = logging.getLogger("PadCfgDlg")

SPINNERS = {
	"spLeftTop": "left_top",
	"spLeftOuter": "left_outer",
	"spLeftBottom": "left_bottom",
	"spRightTop": "right_top",
	"spRightOuter": "right_outer",
	"spRightBottom": "right_bottom",
}


class PadConfigDialog:
	GLADE_FILE = "pad_config.glade"
	
	def __init__(self, app):
		self.app = app
		self.setup_widgets()
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.respath, self.GLADE_FILE))
		self.builder.connect_signals(self)
		self.window = self.builder.get_object("window")
		for id in SPINNERS:
			w = self.builder.get_object(id)
			value = self.app.config["padding"][SPINNERS[id]]
			adj = Gtk.Adjustment(value, 0, 1000, 1, 5)
			w.set_adjustment(adj)
	
	def show(self, *a):
		self.window.set_transient_for(self.app.window)
		self.window.set_visible(True)
	
	def on_outer_change_value(self, *a):
		spLeftInner = self.builder.get_object("spLeftInner")
		spLeftOuter = self.builder.get_object("spLeftOuter")
		spRightInner = self.builder.get_object("spRightInner")
		spRightOuter = self.builder.get_object("spRightOuter")
		
		if spLeftInner.get_value() < spLeftOuter.get_value():
			spLeftInner.set_value(spLeftOuter.get_value())
		if spRightInner.get_value() < spRightOuter.get_value():
			spRightInner.set_value(spRightOuter.get_value())
	
	def on_btApply_clicked(self, *a):
		for id in SPINNERS:
			w = self.builder.get_object(id)
			self.app.config["padding"][SPINNERS[id]] = int(w.get_adjustment().get_value())
		self.app.config.save()
		self.app.apply_pads()
