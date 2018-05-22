#!/usr/bin/env python2
"""
RetroTouch - Config

Handles loading, storing and querying config file
"""
from __future__ import unicode_literals

from retrotouch.paths import get_config_path

import os, json, logging
log = logging.getLogger("Config")


class Config(object):
	DEFAULTS = {
		"padding": {
			# Space between virtual pad images, game screen and window borders
			"left_top": 10,
			"left_outer": 10,
			"left_bottom": 10,
			"right_top": 10,
			"right_outer": 10,
			"right_bottom": 10,
		},
		"last_saves": [
			# { "game": "full/path/to/game.gb", "state": "/full/path/to/save.sav" }
		]
	}
	
	def __init__(self):
		self.filename = os.path.join(get_config_path(), "config.json")
		self.reload()
	
	def reload(self):
		""" (Re)loads configuration. Works as load(), but handles exceptions """
		try:
			self.load()
		except Exception, e:
			log.warning("Failed to load configuration; Creating new one.")
			log.warning("Reason: %s", (e,))
			self.create()
		if self.check_values():
			self.save()
	
	def _check_dict(self, values, defaults):
		"""
		Recursivelly checks if 'config' contains all keys in 'defaults'.
		Creates keys with default values where missing.
		
		Returns True if anything was changed.
		"""
		rv = False
		for d in defaults:
			if d not in values:
				values[d] = defaults[d]
				rv = True
			if type(values[d]) == dict:
				rv = self._check_dict(values[d], defaults[d]) or rv
		return rv
	
	def check_values(self):
		"""
		Check if all required values are in place and fills missing by default.
		Returns True if anything gets changed.
		"""
		rv = self._check_dict(self.values, self.DEFAULTS)
		return rv
	
	def load(self):
		self.values = json.loads(open(self.filename, "r").read())
	
	def create(self):
		""" Creates new, empty configuration """
		self.values = {}
		self.check_values()
		self.save()
	
	def save(self):
		""" Saves configuration file """
		# Check & create directory
		if not os.path.exists(get_config_path()):
			os.makedirs(get_config_path())
		# Save
		data = { k:self.values[k] for k in self.values }
		jstr = json.dumps(data, indent=4)
		file(self.filename, "w").write(jstr)
		log.debug("Configuration saved")
	
	def __iter__(self):
		for k in self.values:
			yield k
	
	def get(self, key, default=None):
		return self.values.get(key, default)
	
	def set(self, key, value):
		self.values[key] = value
	
	__getitem__ = get
	__setitem__ = set
	
	def __contains__(self, key):
		""" Returns true if there is such value """
		return key in self.values

