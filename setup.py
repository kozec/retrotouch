#!/usr/bin/env python2
from distutils.core import setup, Extension
import os, glob

data_files = [
	('share/retrotouch/', glob.glob("resources/*.svg")),
	('share/retrotouch/', glob.glob("resources/*.glade")),
	('share/retrotouch/', glob.glob("resources/*.glsl")),
	('share/retrotouch/core_icons', glob.glob("resources/core_icons/*")),
	('share/pixmaps', [ "resources/retrotouch.svg" ]),
	('share/applications', ['scripts/retrotouch.desktop' ]),
]

for root in glob.glob('resources/pads/*'):
	if os.path.islink(root):
		for filename in glob.glob(root + "/*"):
			data_files += [(
				os.path.join('share/retrotouch/', root[len('resources/'):]),
				[ filename ]
			)]

for root, dirnames, filenames in os.walk('resources/pads'):
	for filename in filenames:
		if filename.endswith(".svg"):
			data_files += [(
				os.path.join('share/retrotouch/', root[len('resources/'):]),
				[ os.path.join(root, filename) ]
			)]

packages = [ 'retrotouch', 'retrotouch.native' ]

if __name__ == "__main__":
	setup(name = 'retrotouch',
			version = "0.1",
			description = 'Libretro frontend for touchscreen',
			author = 'kozec',
			packages = packages,
			data_files = data_files,
			scripts = [
				'scripts/retrotouch',
			],
			license = 'GPL2',
			platforms = ['Linux'],
			ext_modules = [
				Extension('libnative_runner',
					sources = [
						'retrotouch/native/retro_main.c',
						'retrotouch/native/retro_audio.c',
						'retrotouch/native/retro_render.c',
						'retrotouch/native/retro_internal.c',
						'retrotouch/native/gltools.c',
					],
					extra_compile_args = [ '-g', '-O0', '-std=gnu99' ],
					libraries = [ 'GL', 'asound', 'png', 'X11' ],
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
