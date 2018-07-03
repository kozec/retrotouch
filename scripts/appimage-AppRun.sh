#!/bin/bash
export PATH=${APPDIR}:${APPDIR}/usr/bin:$PATH
export LD_LIBRARY_PATH=${APPDIR}/usr/lib/x86_64-linux-gnu
export GI_TYPELIB_PATH=${LD_LIBRARY_PATH}/girepository-1.0
export GDK_PIXBUF_MODULEDIR=${LD_LIBRARY_PATH}/gdk-pixbuf-2.0/2.10.0/loaders
export PYTHONPATH=${APPDIR}/usr/lib/python2.7/site-packages:${APPDIR}/usr/lib/python2.7/dist-packages
export CORE_SEARCH_PATH=${APPDIR}/cores
export SHARED=${APPDIR}/usr/share/retrotouch

export GDK_PIXBUF_MODULE_FILE=${APPDIR}/../$$-gdk-pixbuf-loaders.cache
if [ x"$1" == x"bash" ] ; then
	cd ${APPDIR}
	bash
else
	${LD_LIBRARY_PATH}/gdk-pixbuf-2.0/gdk-pixbuf-query-loaders >"$GDK_PIXBUF_MODULE_FILE"
	python2 ${APPDIR}/usr/bin/retrotouch $@
	rv=$?
	rm "$GDK_PIXBUF_MODULE_FILE" &>/dev/null
	exit $rv
fi
