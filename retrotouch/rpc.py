#!/usr/bin/env python2
"""
RetroTouch - RPC

Handles talking between runner and GUI
"""
from __future__ import unicode_literals

import cPickle as pickle
import os, struct, select, logging
log = logging.getLogger("RPC")


class RPC:
	
	def __init__(self, read_fd, write_fd):
		self.setup_fds(read_fd, write_fd)
	
	def setup_fds(self, read_fd, write_fd):
		self._read = os.fdopen(read_fd, 'rb')
		self._write = os.fdopen(write_fd, 'wb')
	
	def close(self):
		self._read.close()
		self._write.close()
	
	def select(self, timeout=0):
		while True:
			r, w, x = select.select([self._read], [], [], timeout)
			if len(r):
				size = decode_size(self._read.read(4))
				mname, args, kws = decode_call(self._read.read(size))
				self.call_locally(mname, args, kws)
			else:
				break
	
	def call(self, mname, *args, **kws):
		encoded = encode_call(mname, args, kws)
		self._write.write(encode_size(len(encoded)) + encoded)
		self._write.flush()
	
	def call_locally(self, mname, args, kws):
		try:
			getattr(self, mname)(*args, **kws)
		except Exception, e:
			log.exception(e)


def encode_size(size):
	return struct.pack("@I", size)


def decode_size(bts):
	return struct.unpack("@I", bts)[0]


def encode_call(mname, args, kws):
	return pickle.dumps((mname, args, kws), -1)


def decode_call(bts):
	mname, args, kws = pickle.loads(bts)
	return mname, args, kws
