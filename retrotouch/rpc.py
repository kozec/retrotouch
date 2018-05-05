#!/usr/bin/env python2
"""
RetroTouch - RPC

Handles talking between runner and GUI
"""
from __future__ import unicode_literals

import os, tempfile, mmap, struct, pickle, select, logging
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
	
	
	def select(self):
		r, w, x = select.select([self._read], [], [], 0)
		if len(r):
			size = decode_size(self._read.read(4))
			mname, args, kws = decode_call(self._read.read(size))
			self.call_locally(mname, args, kws)
	
	
	def call(self, mname, *args, **kws):
		encoded = encode_call(mname, args, kws)
		self._write.write(encode_size(len(encoded)))
		self._write.write(encoded)
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
	return pickle.dumps((mname, args, kws))

def decode_call(bts):
	mname, args, kws = pickle.loads(bts)
	return mname, args, kws


def prepare_mmap(connect_to=None, readwrite=True):
	if connect_to is None:
		tmp = tempfile.NamedTemporaryFile("w+b", prefix="retrotouch-", delete=False)
		f = tmp.file
	else:
		tmp = None
		f = file(connect_to, "w+b")
	f.write(b'\x00' * mmap.PAGESIZE) == mmap.PAGESIZE
	proto = mmap.PROT_WRITE
	if not readwrite:
		proto |= mmap.PROT_READ
	m = mmap.mmap(f.fileno(), mmap.PAGESIZE, mmap.MAP_SHARED, proto)
	try:
		if connect_to:
			os.unlink(connect_to)
	except:
		pass
	return tmp, m
