#!/bin/bash
APP="retrotouch"
EXEC="retrotouch"
[ x"$BUILD_APPDIR" == "x" ] && BUILD_APPDIR=$(pwd)/appimage

CORES=(nestopia snes9x mgba desmume mupen64plus picodrive pcsx_rearmed)
CORE_DOWNLOAD_URL="http://buildbot.libretro.com/nightly/linux/x86_64/latest"

function download_dep() {
	NAME=$1
	URL=$2
	if [ -e ../../${NAME}.obstargz ] ; then
		# Special case for OBS
		cp ../../${NAME}.obstargz /tmp/appimagebuild-cache/${NAME}.deb
	elif [ -e ${NAME}.deb ] ; then
		cp ${NAME}.deb /tmp/appimagebuild-cache/${NAME}.deb
	else
		wget --no-verbose -c "${URL}" -O /tmp/appimagebuild-cache/${NAME}.deb
	fi
}

function unpack_dep() {
	NAME="$1"
	pushd ${BUILD_APPDIR}
	ar x "/tmp/appimagebuild-cache/${NAME}.deb" "data.tar.gz" "data.tar.xz" &>/dev/null
	tar --extract --exclude="usr/include**" --exclude="usr/lib/pkgconfig**" \
			--exclude="usr/lib/python3.6**" -f data.tar.*
	rm data.tar.*
	popd
}

function download_core() {
	FILENAME="$1_libretro.so.zip"
	URL="${CORE_DOWNLOAD_URL}/${FILENAME}"
	wget --no-verbose -c "${URL}" -O "/tmp/appimagebuild-cache/${FILENAME}"
}

function unpack_core() {
	FILENAME="$1_libretro.so.zip"
	pushd "${BUILD_APPDIR}/usr/lib/x86_64-linux-gnu/libretro"
	unzip -o "/tmp/appimagebuild-cache/$FILENAME"
	popd
}

set -exu		# display commands, no empty vars, terminate on 1st failure
mkdir -p /tmp/appimagebuild-cache/

# Download deps
download_dep "gtk-3.22.30" "http://cz.archive.ubuntu.com/ubuntu/pool/main/g/gtk+3.0/libgtk-3-0_3.22.30-1ubuntu1_amd64.deb"
download_dep "atk-2.28.0" "http://cz.archive.ubuntu.com/ubuntu/pool/main/a/atk1.0/libatk1.0-0_2.28.1-1_amd64.deb"
download_dep "libatk-bridge-2.26.2" "http://cz.archive.ubuntu.com/ubuntu/pool/main/a/at-spi2-atk/libatk-bridge2.0-0_2.26.2-1_amd64.deb"
download_dep "glib-2.56.1" "http://cz.archive.ubuntu.com/ubuntu/pool/main/g/glib2.0/libglib2.0-0_2.56.1-2ubuntu1_amd64.deb"
download_dep "python-gi-3.26.1" "http://cz.archive.ubuntu.com/ubuntu/pool/main/p/pygobject/python-gi_3.26.1-2_amd64.deb"
download_dep "python-gi-cairo-3.26.1" "http://cz.archive.ubuntu.com/ubuntu/pool/universe/p/pygobject/python-gi-cairo_3.26.1-2_amd64.deb"
download_dep "gir1.2-pango-1.40.14" "http://cz.archive.ubuntu.com/ubuntu/pool/main/p/pango1.0/gir1.2-pango-1.0_1.40.14-1_amd64.deb"
download_dep "gir1.2-glib-1.56.1" "http://cz.archive.ubuntu.com/ubuntu/pool/main/g/gobject-introspection/gir1.2-glib-2.0_1.56.1-1_amd64.deb"
download_dep "gir1.2-gtk-3.22.30" "http://cz.archive.ubuntu.com/ubuntu/pool/main/g/gtk+3.0/gir1.2-gtk-3.0_3.22.30-1ubuntu1_amd64.deb"
download_dep "gir1.2-atk-3.28.1" "http://cz.archive.ubuntu.com/ubuntu/pool/main/a/atk1.0/gir1.2-atk-1.0_2.28.1-1_amd64.deb"
download_dep "gir1.2-rsvg-2.40.20" "http://cz.archive.ubuntu.com/ubuntu/pool/main/libr/librsvg/gir1.2-rsvg-2.0_2.40.20-2_amd64.deb"
download_dep "gir1.2-gdkpixbuf-2.36.11" "http://cz.archive.ubuntu.com/ubuntu/pool/main/g/gdk-pixbuf/gir1.2-gdkpixbuf-2.0_2.36.11-2_amd64.deb"
download_dep "libgdk-pixbuf2.0-2.36.11" "http://cz.archive.ubuntu.com/ubuntu/pool/main/g/gdk-pixbuf/libgdk-pixbuf2.0-0_2.36.11-2_amd64.deb"
download_dep "libpango-1.40.14" "http://cz.archive.ubuntu.com/ubuntu/pool/main/p/pango1.0/libpango-1.0-0_1.40.14-1_amd64.deb"
download_dep "libfreetype-2.8.1" "http://cz.archive.ubuntu.com/ubuntu/pool/main/f/freetype/libfreetype6_2.8.1-2ubuntu2_amd64.deb"
download_dep "libfontconfig-2.12.6" "http://cz.archive.ubuntu.com/ubuntu/pool/main/f/fontconfig/libfontconfig1_2.12.6-0ubuntu2_amd64.deb"
download_dep "libpng-1.6.34" "http://cz.archive.ubuntu.com/ubuntu/pool/main/libp/libpng1.6/libpng16-16_1.6.34-1_amd64.deb"
download_dep "libpangoft-1.40.14" "http://cz.archive.ubuntu.com/ubuntu/pool/main/p/pango1.0/libpangoft2-1.0-0_1.40.14-1_amd64.deb"
download_dep "libharfbuzz-1.7.2" "http://cz.archive.ubuntu.com/ubuntu/pool/main/h/harfbuzz/libharfbuzz0b_1.7.2-1ubuntu1_amd64.deb"
download_dep "libpangocairo-1.40.14" "http://cz.archive.ubuntu.com/ubuntu/pool/main/p/pango1.0/libpangocairo-1.0-0_1.40.14-1_amd64.deb"
download_dep "libxml-2.9.4" "http://cz.archive.ubuntu.com/ubuntu/pool/main/libx/libxml2/libxml2_2.9.4+dfsg1-6.1ubuntu1_amd64.deb"
download_dep "librsvg-2.40.20" "http://cz.archive.ubuntu.com/ubuntu/pool/main/libr/librsvg/librsvg2-2_2.40.20-2_amd64.deb"
download_dep "librsvg-common-2.40.20" "http://cz.archive.ubuntu.com/ubuntu/pool/main/libr/librsvg/librsvg2-common_2.40.20-2_amd64.deb"
download_dep "libcairo-2.1.15" "http://cz.archive.ubuntu.com/ubuntu/pool/main/c/cairo/libcairo2_1.15.10-2_amd64.deb"
download_dep "libcroco-3.0.6" "http://cz.archive.ubuntu.com/ubuntu/pool/main/libc/libcroco/libcroco3_0.6.12-2_amd64.deb"
download_dep "libpcre-8.39" "http://cz.archive.ubuntu.com/ubuntu/pool/main/p/pcre3/libpcre3_8.39-9_amd64.deb"
download_dep "libselinux-2.7" "http://cz.archive.ubuntu.com/ubuntu/pool/main/libs/libselinux/libselinux1_2.7-2build2_amd64.deb"
download_dep "zlib-1.2.11" "http://cz.archive.ubuntu.com/ubuntu/pool/main/z/zlib/zlib1g_1.2.11.dfsg-0ubuntu2_amd64.deb"
download_dep "icu-60.2" "http://cz.archive.ubuntu.com/ubuntu/pool/main/i/icu/libicu60_60.2-3ubuntu3_amd64.deb"

for core in "${CORES[@]}" ; do
	download_core "$core"
done

# Prepare & build
mkdir -p ${BUILD_APPDIR}/usr/lib/python2.7/site-packages/
unpack_dep "gtk-3.22.30"
unpack_dep "atk-2.28.0"
unpack_dep "libatk-bridge-2.26.2"
unpack_dep "glib-2.56.1"
unpack_dep "python-gi-3.26.1"
unpack_dep "python-gi-cairo-3.26.1"
unpack_dep "gir1.2-pango-1.40.14"
unpack_dep "gir1.2-glib-1.56.1"
unpack_dep "gir1.2-gtk-3.22.30"
unpack_dep "gir1.2-atk-3.28.1"
unpack_dep "gir1.2-rsvg-2.40.20"
unpack_dep "gir1.2-gdkpixbuf-2.36.11"
unpack_dep "libgdk-pixbuf2.0-2.36.11"
unpack_dep "libpango-1.40.14"
unpack_dep "libfreetype-2.8.1"
unpack_dep "libfontconfig-2.12.6"
unpack_dep "libpng-1.6.34"
unpack_dep "libpangoft-1.40.14"
unpack_dep "libharfbuzz-1.7.2"
unpack_dep "libpangocairo-1.40.14"
unpack_dep "libxml-2.9.4"
unpack_dep "librsvg-2.40.20"
unpack_dep "librsvg-common-2.40.20"
unpack_dep "libcairo-2.1.15"
unpack_dep "libcroco-3.0.6"
unpack_dep "libpcre-8.39"
unpack_dep "libselinux-2.7"
unpack_dep "zlib-1.2.11"
unpack_dep "icu-60.2"

# Unpack cores
mkdir -p "${BUILD_APPDIR}/usr/lib/x86_64-linux-gnu/libretro"
[ -h "${BUILD_APPDIR}/cores" ] || ln -s "usr/lib/x86_64-linux-gnu/libretro" "${BUILD_APPDIR}/cores"
for core in "${CORES[@]}" ; do
	unpack_core "$core"
done

# Cleanup
mv "${BUILD_APPDIR}/lib/x86_64-linux-gnu/"* "${BUILD_APPDIR}/usr/lib/x86_64-linux-gnu"
rmdir "${BUILD_APPDIR}/lib/x86_64-linux-gnu"
rmdir "${BUILD_APPDIR}/lib"
ln -s "usr/lib" "${BUILD_APPDIR}/lib"

rm -R ${BUILD_APPDIR}/usr/include || true
for x in aclocal gtk-doc gdb gettext libalpm doc man vala locale bash-completion ; do
	rm -Rf ${BUILD_APPDIR}/usr/share/$x || true
done
for x in win32-1.0 xfixes-4.0 GL-1 GModule PangoFT2-1.0 PangoXft-1.0 PangoCairo-1.0 ; do
	rm -f ${BUILD_APPDIR}/usr/lib/girepository-1.0/$x.typelib || true
done
for x in icns jasper ; do
	rm -f ${BUILD_APPDIR}/usr/lib/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-$x.so || true
done
rm -f ${BUILD_APPDIR}/usr/bin/*
rm -Rf ${BUILD_APPDIR}/usr/lib/gtk-3.0/3.0.0
rm -Rf ${BUILD_APPDIR}/usr/share/applications/*
rm -Rf ${BUILD_APPDIR}/usr/share/glib-2.0
rm -Rf ${BUILD_APPDIR}/usr/share/icons
rm -Rf ${BUILD_APPDIR}/usr/share/icu
rm -Rf ${BUILD_APPDIR}/usr/share/licenses
rm -Rf ${BUILD_APPDIR}/usr/share/themes
rm -Rf ${BUILD_APPDIR}/usr/share/thumbnailers
rm -Rf ${BUILD_APPDIR}/etc
rm -f ${BUILD_APPDIR}/{REMOVE,INSTALL,props.plist,files.plist}

# Fix weird gi stuff
patch -N ${BUILD_APPDIR}/usr/lib/python2.7/dist-packages/gi/module.py << EOF
--- usr/lib/python2.7/dist-packages/gi/module.py.orig	2018-07-02 22:12:57.567232675 +0200
+++ usr/lib/python2.7/dist-packages/gi/module.py	2018-07-02 22:12:59.350565998 +0200
@@ -167,7 +167,10 @@
                     'ABCDEFGJHIJKLMNOPQRSTUVWXYZ')
                 for value_info in info.get_values():
                     value_name = value_info.get_name_unescaped().translate(ascii_upper_trans)
-                    setattr(wrapper, value_name, wrapper(value_info.get_value()))
+                    try:
+                        setattr(wrapper, value_name, wrapper(value_info.get_value()))
+                    except ValueError:
+                        pass
                 for method_info in info.get_methods():
                     setattr(wrapper, method_info.__name__, method_info)
EOF

python2 setup.py build
python2 setup.py install --prefix ${BUILD_APPDIR}/usr

# Move & patch desktop file
mv ${BUILD_APPDIR}/usr/share/applications/${APP}.desktop ${BUILD_APPDIR}/
sed -i "s/Icon=.*/Icon=${APP}/g" ${BUILD_APPDIR}/${APP}.desktop

# Copy icon
cp -H resources/${APP}.png ${BUILD_APPDIR}/${APP}.png
mkdir -p "${BUILD_APPDIR}/usr/share/${APP}/icons/"
[ -e "${BUILD_APPDIR}/usr/share/${APP}/icons/${APP}.png" ] || ln -s "../../../../${APP}.png" "${BUILD_APPDIR}/usr/share/${APP}/icons/${APP}.png"

# Copy appdata.xml
mkdir -p ${BUILD_APPDIR}/usr/share/metainfo/
cp scripts/${APP}.appdata.xml ${BUILD_APPDIR}/usr/share/metainfo/${APP}.appdata.xml

# Copy AppRun script
cp scripts/appimage-AppRun.sh ${BUILD_APPDIR}/AppRun
chmod +x ${BUILD_APPDIR}/AppRun

echo "Run appimagetool -n ${BUILD_APPDIR} to finish prepared appimage"
