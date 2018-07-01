#!/usr/bin/env python2
"""
RetroTouch - OSP

On Screen Pad(s)
"""
from __future__ import unicode_literals
from gi.repository import Gdk
from retrotouch.svg_widget import SVGWidget

import logging
log = logging.getLogger("OSP")


class OSP(SVGWidget):
	HILIGHT = "#FF0000"
	DPAD_DIRECTIONS = (4, 5, 6, 7)
	TOUCH_MAPPINGS = {
		"A":			8,
		"B":			0,
		"X":			9,
		"Y":			1,
		"LT":			10, # RETRO_DEVICE_ID_JOYPAD_L
		"RT":			11, # RETRO_DEVICE_ID_JOYPAD_R
		"START":		3,
		"SELECT":		2,
		"DPAD_UP":		4,
		"DPAD_DOWN":	5,
		"DPAD_LEFT":	6,
		"DPAD_RIGHT":	7,
		'L2':			12,
		'R2':			13,
		'L3':			14,
		'R3':			15,
		"A2":			8,
		"B2":			0,
		"X2":			9,
		"Y2":			1,
	}
	
	def __init__(self, app, index, image):
		self.image = None
		SVGWidget.__init__(self, image)
		self.app = app
		self.index = index
		self.hilights = {}
		self.image.set_alignment(0, 0)
		self.set_events(Gdk.EventMask.TOUCH_MASK)
		self.connect('touch-event', self.on_event)
		self.connect('size-allocate', self.on_size_allocate)
		self.connect('button-press-event', self.on_event)
		self.connect('button-release-event', self.on_event)
	
	def set_image(self, filename):
		SVGWidget.set_image(self, filename)
		self.hilights = {}
		if self.image:
			self.hilight({})
	
	def on_event(self, widget, event):
		if event.type == Gdk.EventType.TOUCH_BEGIN:
			self.hilights[event.sequence] = TouchData(set(widget.get_areas_at(event.x, event.y)), from_event=event)
			hi = self.hilights[event.sequence]
			if hi.is_dpad:
				self.dpad_update(widget, event)
			elif hi.is_analog:
				self.analog_update(widget, event, hi)
			else:
				for a in hi.areas:
					if a in OSP.TOUCH_MAPPINGS and self.app.wrapper:
						self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS[a], True)
				self.update_hilights(widget)
		elif event.type == Gdk.EventType.TOUCH_UPDATE:
			hi = self.hilights.get(event.sequence)
			if hi is not None:
				if hi.is_dpad:
					self.dpad_update(widget, event)
				elif hi.is_analog:
					self.analog_update(widget, event, hi)
				elif hi.is_change(event):
					c = set(widget.get_areas_at(event.x, event.y))
					if c.symmetric_difference(hi.areas):
						if self.app.wrapper:
							for a in hi.areas - c:
								self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS[a], False)
							for a in c - hi.areas:
								self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS[a], True)
						hi.set_areas(c, from_event=event)
						self.update_hilights(widget)
		elif event.type == Gdk.EventType.TOUCH_END:
			hi = self.hilights.get(event.sequence)
			if hi:
				if hi.is_dpad:
					self.dpad_cancel()
				elif hi.is_analog:
					self.analog_cancel(hi)
				else:
					for a in hi.areas:
						if a in OSP.TOUCH_MAPPINGS and self.app.wrapper:
							self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS[a], False)
				del self.hilights[event.sequence]
				self.update_hilights(widget)
		elif event.type == Gdk.EventType.BUTTON_PRESS:
			self.hilights[-1] = TouchData(set(widget.get_areas_at(event.x, event.y)), from_event=event)
			hi = self.hilights[-1]
			if hi.is_dpad:
				self.dpad_update(widget, event)
			elif hi.is_analog:
				self.analog_update(widget, event, hi)
			else:
				for a in hi.areas:
					if a in OSP.TOUCH_MAPPINGS and self.app.wrapper:
						self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS[a], True)
				self.update_hilights(widget)
		elif event.type == Gdk.EventType.BUTTON_RELEASE:
			hi = self.hilights.get(-1)
			if hi:
				if hi.is_dpad:
					self.dpad_cancel()
				elif hi.is_analog:
					self.analog_cancel(hi)
				else:
					for a in hi.areas:
						if a in OSP.TOUCH_MAPPINGS and self.app.wrapper:
							self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS[a], False)
				del self.hilights[-1]
				self.update_hilights(widget)
	
	def on_size_allocate(self, widget, allocation=None):
		if self.app.wrapper:
			width = widget.image.get_pixbuf().get_width()
			height = widget.image.get_pixbuf().get_height()
			if allocation is None:
				allocation = widget.image.get_allocation()
			x, y = widget.translate_coordinates(widget.get_parent().get_parent(), 0, 0)
			self.app.wrapper.set_pad_position(self.index, x, y, width, height)
	
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
				if self.app.wrapper:
					self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS["DPAD_RIGHT"], True)
					self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS["DPAD_LEFT"], False)
				update = True
			else:
				self.hilights["DPAD1"].set_areas(set(("DPAD_LEFT", )))
				if self.app.wrapper:
					self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS["DPAD_LEFT"], True)
					self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS["DPAD_RIGHT"], False)
				update = True
		elif "DPAD1" in self.hilights:
			del self.hilights["DPAD1"]
			if self.app.wrapper:
				self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS["DPAD_LEFT"], False)
				self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS["DPAD_RIGHT"], False)
			update = True
		
		if x > width * 0.25 and x < width * 0.75:
			if y > height * 0.5:
				self.hilights["DPAD2"].set_areas(set(("DPAD_DOWN", )))
				if self.app.wrapper:
					self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS["DPAD_DOWN"], True)
					self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS["DPAD_UP"], False)
				update = True
			else:
				self.hilights["DPAD2"].set_areas(set(("DPAD_UP", )))
				if self.app.wrapper:
					self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS["DPAD_UP"], True)
					self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS["DPAD_DOWN"], False)
				update = True
		elif "DPAD2" in self.hilights:
			del self.hilights["DPAD2"]
			if self.app.wrapper:
				self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS["DPAD_UP"], False)
				self.app.wrapper.set_button(OSP.TOUCH_MAPPINGS["DPAD_DOWN"], False)
			update = True
		
		if update:
			self.update_hilights(widget)
	
	def dpad_cancel(self):
		if "DPAD1" in self.hilights:
			del self.hilights["DPAD1"]
		if "DPAD2" in self.hilights:
			del self.hilights["DPAD2"]
		for i in OSP.DPAD_DIRECTIONS:
			if self.app.wrapper:
				self.app.wrapper.set_button(i, False)
	
	def analog_update(self, widget, event, hi):
		""" Special case so dpad 'buttons' blinks nicelly """
		area = list(hi.areas)[0]
		x, y, width, height = widget.get_area_position(area)
		x = int((event.x - (x + (width / 2))) / width * 0xFFFF)
		y = int((event.y - (y + (height / 2))) / height * 0xFFFF)
		if self.app.wrapper:
			self.app.wrapper.set_analog(0, x, y)
		if area not in self.hilights:
			self.hilights[area] = TouchData(set())
			self.update_hilights(widget)
	
	def analog_cancel(self, hi):
		area = list(hi.areas)[0]
		if self.app.wrapper:
			self.app.wrapper.set_analog(0, 0, 0)
		if area in self.hilights:
			del self.hilights[area]
	
	def update_hilights(self, widget):
		areas = reduce(
			lambda a,b: a.union(b),
			(set(x.areas) for x in self.hilights.values()),
			set()
		)
		widget.hilight({ a : self.HILIGHT for a in areas })
		if self.app.wrapper:
			self.app.wrapper.set_image(self.index, widget.image.get_pixbuf())


class TouchData:
	
	def __init__(self, areas, from_event=None):
		self.areas = areas
		self.is_dpad = "DPAD" in areas
		self.is_analog = "LPAD" in areas
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
