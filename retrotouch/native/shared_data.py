#!/usr/bin/env python2
"""
RetroTouch - shared_data structure

Portion of memory shared by both processes.
"""
import ctypes, tempfile, mmap

RT_MAX_PORTS		= 1
RT_MAX_ANALOGS		= 2
RT_MAX_IMAGES		= 4


class InputState(ctypes.Structure):
	_fields_ = [
		("buttons", ctypes.c_uint),
		("analogs", ctypes.c_int16 * (2 * RT_MAX_ANALOGS)),
		("mouse", ctypes.c_int16 * 2),
		("mouse_buttons", ctypes.c_uint),
	]


class _ImageData(ctypes.Structure):
	_fields_ = [
		("version", ctypes.c_uint),
		("x", ctypes.c_int),
		("y", ctypes.c_int),
		("width", ctypes.c_uint),
		("height", ctypes.c_uint),
		("offset", ctypes.c_size_t),
		("size", ctypes.c_size_t),
	]


class _SharedData(ctypes.Structure):
	_fields_ = [
		("size", ctypes.c_size_t),
		("scale_factor", ctypes.c_float),
		("input_state", InputState),
		("image_data", _ImageData * 4)
	]


class SharedData:
	
	def __init__(self, filename=None, readwrite=True):
		size = 5 * 102400 # ctypes.sizeof(_SharedData)
		
		# Prepare file
		if filename is None:
			tmp = tempfile.NamedTemporaryFile("w+b", prefix="retrotouch-", delete=False)
			self.filename = tmp.name
			f = tmp.file
		else:
			tmp = None
			f = file(filename, "w+b")
			self.filename = filename
		f.seek(size + 1)
		f.write(b'\x00')
		f.seek(0)
		
		# Prepare mmap
		proto = mmap.PROT_WRITE | mmap.PROT_READ if readwrite else mmap.PROT_WRITE
		self.mmap = mmap.mmap(f.fileno(), size, mmap.MAP_SHARED, proto)
		
		# Finish
		self._data = _SharedData.from_buffer(self.mmap)
		self._data.size = size
		self.input_state = self._data.input_state
	
	def _resize(self, new_size):
		""" Changes size of allocated mmap """
		new_size = max(new_size, 5 * 102400) # ctypes.sizeof(_SharedData))
		self.mmap.resize(new_size)
		self._data = _SharedData.from_buffer(self.mmap)
		self._data.size = new_size
		self.input_state = self._data.input_state
		self.mmap.flush()
	
	def clear_images(self):
		for x in instance.image_data:
			x.offset = x.size = 0
		self._resize(0)
	
	def set_image_pos(self, index, x, y, width, height):
		assert index < RT_MAX_IMAGES
		self._data.image_data[index].x = x
		self._data.image_data[index].y = y
		self._data.image_data[index].width = width
		self._data.image_data[index].height = height
	
	def set_image(self, index, size, bytes):
		assert index < RT_MAX_IMAGES
		if self._data.image_data[index].size < size:
			# Image size increased, it has to be moved to end of buffer
			try:
				offset = max([ x.offset + x.size for x in self._data.image_data if x.size > 0 ])
			except ValueError:
				# arg is an empty sequence
				offset = ctypes.sizeof(_SharedData) + 16
			self._resize(offset + size)
			self._data.image_data[index].offset = offset
		else:
			offset = self._data.image_data[index].offset
		self._data.image_data[index].size = size
		self._data.image_data[index].version += 1
		self.mmap[offset:offset+size] = bytes
		self.mmap.flush()
	
	def set_scale_factor(self, factor):
		self._data.scale_factor = factor
	
	def close(self):
		self.mmap.close()
		try:
			os.unlink(self.filename)
		except: pass
	
	def get_filename(self):
		return self.filename
	
	@staticmethod
	def get_c_type():
		return ctypes.POINTER(_SharedData)
	
	def get_ptr(self):
		return ctypes.POINTER(_SharedData)(self._data)
