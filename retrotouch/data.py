"""
RetroTouch - data

Constants & stuff
"""

from __future__ import unicode_literals
from gi.repository import Gdk
from collections import OrderedDict
from retrotouch.tools import _


SUPPORTED_CORES = OrderedDict((
	('NES',			('nestopia',)),
	('SNES',		('snes9x',)),
	('GB',			('gambatte', 'mgba')),
	('GBA',			('mgba',)),
	('NDS',			('desmume',)),
	('N64',			("mupen64plus", "parallel_n64")),
	('PS1',			('pcsx_rearmed',)),
	('Megadrive',	('picodrive', 'blastem',)),
	('Sega32x',		('picodrive',)),
))

EXPERIMENTAL_CORES = OrderedDict((
	# Experimental core is one that works, but is known to have issues.
	# It's not listed in welcome screen, but can be used if user requests loading game for it
	('PSP',			('ppsspp',)),			# Crashes randomly
))

ALL_CORES = OrderedDict(SUPPORTED_CORES.items() + EXPERIMENTAL_CORES.items())

CORE_CONFIG_OVERRIDE = {
	# Overrides some core-specific settings
	"desmume_pointer_type": "touch",
	"desmume_pointer_mouse": "enabled",
}

CORE_CONFIG_DEFAULTS = {
	# Overrides defaults for core-specific settings
	"desmume_num_cores": "2",
	"ppsspp_separate_io_thread": "enabled",
	"picodrive_input1": "6 button pad",
}

CSS = """
	#no-background { background-color: rgba(1, 1, 1, 0); }
	#dark-background { background-color: rgba(0, 0, 0, 0.2); }
	
	#BSOD {
		font-family: monospace;
		font-size: 12pt;
		color: #FFFFFF;
		background-color: #0000AA;
	}
	#BSOD #title {
		background-color: #AAAAAA;
		color: #0000AA;
	}
"""


UNKNOWN_FORMAT_ERROR = (
	_("Unknown file format"),
	_("Error: Invalid or unknown ROM file"),
	_("Error: Format not supported by any known core."),
	_("Error -41 while loading file of unknown format."),
	_("Cannot play with what's not a game."),
	_("Cannot display image file."),
	_("Video playback not implemented. Check file format."),
	_("ERR_NOT_A_GAME"),
	_("HCF instruction found in ROM with not known format."),
	_("0F 04 instruction found in ROM with unknown format."),
	_("Fatal exception while converting unknown format"),
	_("What am I supposed to do with that?"),
	_("Error: Does not compute"),
	_("Error: Patent-protected file format (are you dropping MP3 file?)"),
	_("Invalid file possibly pirated; Reporting to NASA."),
	_("Failed to allocate 78 TB to analyze unknown file."),
	_("Failed to allocate (78!)B to analyze unknown file."),
	_("No core to dump with this file format."),
	_("C:\\Windows\\System\\d3code.sys needed to load this file format."),
	_("Failed to analyze binary file."),
	_("CPU on fire or invalid ROM format"),
	_("ROM on fire or invalid ROM format"),
	_("Killer poking detected in invalid file"),
	_("Press F13 to continue loading invalid file")
)


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
	Gdk.KEY_q:			10, # RETRO_DEVICE_ID_JOYPAD_L
	Gdk.KEY_w:			11, # RETRO_DEVICE_ID_JOYPAD_R
}