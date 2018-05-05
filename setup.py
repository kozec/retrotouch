#!/usr/bin/env python2
from distutils.core import setup, Extension
import glob


packages = [ 'retrotouch', 'retrotouch.native' ]

if __name__ == "__main__":
	setup(name = 'retrotouch',
			version = "0.1",
			description = 'Libretro frontend for touchscreen',
			author = 'kozec',
			packages = packages,
			data_files = [],
			scripts = [
				'scripts/retrotouch',
			],
			license = 'GPL2',
			platforms = ['Linux'],
			ext_modules = [
				Extension('libretrointerface',
					sources = [
						'retrotouch/native/retro_main.c',
						'retrotouch/native/retro_audio.c',
						'retrotouch/native/retro_render.c',
						'retrotouch/native/retro_internal.c',
						'retrotouch/native/gltools.c',
					],
					libraries = [ 'GL', 'GLX', 'asound' ],
					include_dirs = [
						"retrotouch/native",
						"/usr/include/",
						"/usr/include/cairo/",
						"/usr/include/gtk-3.0/",
						"/usr/include/atk-1.0/",
						"/usr/include/glib-2.0/",
						"/usr/include/pango-1.0/",
						"/usr/lib/glib-2.0/include/",
						"/usr/include/gdk-pixbuf-2.0/",
					],
				),
			]
	)
