RetroTouch
=============



[![screenshot1](docs/tn/screenshot-main-screen.png?raw=true)](docs/screenshot-main-screen.png?raw=true)
[![screenshot2](docs/tn/screenshot-nes.png?raw=true)](docs/screenshot-nes.png?raw=true)
[![screenshot3](docs/tn/screenshot-virtual-pad-config.png?raw=true)](docs/screenshot-virtual-pad-config.png?raw=true)

##### Supported systems and emulators
- Nintendo Entertainment System/Famicom via [nestopia](https://github.com/libretro/nestopia)
- Super Nintendo Entertainment System/Super Famicom via [snes9x](https://github.com/libretro/snes9x)
- Gameboy and Gameboy Color via [gambatte](https://github.com/libretro/desmume)
- Gameboy Advance via [mgba](https://github.com/libretro/mgba)
- Nintendo DS via [desmume](https://github.com/libretro/desmume)
- N64 via [mupen64plus](https://github.com/libretro/mupen64plus-libretro)
- PlayStation 1 via [pcsx_rearmed](https://github.com/libretro/pcsx_rearmed)
- Sega Megadrive, Genesis and 32X via [picodrive](https://github.com/libretro/picodrive)

##### Packages
- Ubuntu (deb-based distros): in [OpenSUSE Build Service](http://software.opensuse.org/download.html?project=home%3Akozec&package=retrotouch).
- Fedora, SUSE (rpm-based distros): in [OpenSUSE Build Service](http://software.opensuse.org/download.html?project=home%3Akozec&package=retrotouch).
- AppImage: Attached to [latest release](https://github.com/kozec/retrotouch/releases/latest) (includes all supported cores)

##### To run without package
- download and extract [latest release](https://github.com/kozec/retrotouch/releases/latest) (includes all supported cores)
- navigate to extracted directory and execute `./run.sh`

##### To install without package
- download and extract [latest release](https://github.com/kozec/retrotouch/releases/latest) (includes all supported cores)
- `python2 setup.py build`
- `python2 setup.py install`


##### Dependencies
- **some of supported libretro cores**
- python 2.7, GTK 3.22 or newer and [PyGObject](https://live.gnome.org/PyGObject)
- [python-gi-cairo](https://packages.debian.org/sid/python-gi-cairo) and [gir1.2-rsvg-2.0](https://packages.debian.org/sid/gir1.2-rsvg-2.0) on debian based distros (included in PyGObject elsewhere)
- [setuptools](https://pypi.python.org/pypi/setuptools)
- alsa, opengl, x11
