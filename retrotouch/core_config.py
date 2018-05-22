#!/usr/bin/env python2
"""
RetroTouch - Core config dialog
"""
from __future__ import unicode_literals
from retrotouch.data import CORE_CONFIG_OVERRIDE, CORE_CONFIG_DEFAULTS
from retrotouch.tools import load_core_config, save_core_config
from gi.repository import Gtk

import os, logging
log = logging.getLogger("CoreCfgDlg")


class CoreConfigDialog:
	GLADE_FILE = "core_config.glade"
	
	def __init__(self, app):
		self.app = app
		self.setup_widgets()
	
	def setup_widgets(self):
		# Important stuff
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.respath, self.GLADE_FILE))
		self.builder.connect_signals(self)
		self.window = self.builder.get_object("window")
		self.options = {}
		
		# Config rows
		grValues = self.builder.get_object("grValues")
		x = 2
		for key, (description, options) in self.app.wrapper.retro_config.items():
			setting = Setting(description, options)
			self.options[key] = setting
			grValues.attach(setting.lbl, 0, x, 1, 1)
			grValues.attach(setting.combo, 1, x, 1, 1)
			x = x + 1
		
		# Config values
		config = load_core_config(self.app.wrapper.core)
		for key in self.options:
			if key in CORE_CONFIG_OVERRIDE:
				self.options[key].set_value(CORE_CONFIG_OVERRIDE[key])
				self.options[key].disable()
			elif key in config:
				# If value in config is not available, this leaves combobox "empty"
				self.options[key].set_value(config[key])
			elif key in CORE_CONFIG_DEFAULTS:
				self.options[key].set_value(CORE_CONFIG_DEFAULTS[key])
			else:
				self.options[key].set_default()
		
		# Done
		grValues.show_all()
	
	
	def show(self, *a):
		self.window.set_transient_for(self.app.window)
		self.window.set_visible(True)
	
	
	def on_btApply_clicked(self, *a):
		config = {
			key: option.get_value()
			for (key, option) in self.options.items()
		}
		save_core_config(self.app.wrapper.core, config)
		self.app.wrapper.config_changed()


class Setting:
	
	def __init__(self, description, options):
		self.options = options
		self.combo = Gtk.ComboBoxText()
		self.lbl = Gtk.Label(description)
		self.combo.set_property("expand", True)
		self.lbl.set_xalign(0)
		for option in options:
			self.combo.append_text(option)
	
	def disable(self):
		""" Used for settings too important to be changed """
		for x in (self.lbl, self.combo):
			x.set_sensitive(False)
	
	def set_value(self, value):
		""" Returns True if value was found """
		for x in self.combo.get_model():
			if value == x[0]:
				self.combo.set_active_iter(x.iter)
				return True
		return False
	
	def set_default(self):
		""" Sets 1st possible value. Returns False if there is none """
		try:
			self.combo.set_active(0)
			return True
		except:
			return False
	
	def get_value(self):
		return self.combo.get_active_text()
