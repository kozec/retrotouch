#include <stdlib.h>
#include <stdio.h>
#include <sys/shm.h>
#include <string.h>
#include <libretro.h>
#include <retro.h>

#define LOG(...) rt_log(data, "RMain", __VA_ARGS__)


void rt_log(LibraryData* data, const char* tag, enum retro_log_level level, const char *fmt, ...) {
	char buffer[4096] = {0};
	va_list va;
	va_start(va, fmt);
	vsnprintf(buffer, sizeof(buffer), fmt, va);
	va_end(va);
	
	data->cb_log(tag, (int)level, buffer);
}


void rt_set_error(LibraryData* data, const char* message) {
	strncpy(data->private->error, message, 1023);
	data->private->error[1023] = 0;
	LOG(RETRO_LOG_ERROR, message);
}


const char* rt_check_error(LibraryData* data) {
	if (data->private->error[0] == 0)
		return NULL;
	return data->private->error;
}


int rt_set_paused(LibraryData* data, int paused) {
	if (rt_get_game_loaded(data)) {
		if (paused == !data->private->running) {
			return 0;		// Already in correct state
		} else if (paused) {
			// Core is running but it should be paused
			data->private->running = false;
			LOG(RETRO_LOG_DEBUG, "Core paused");
			return 0;
		} else {
			// Core is paused and it should be resumed
			data->private->running = true;
			LOG(RETRO_LOG_DEBUG, "Core resumed");
			return 0;
		}
	} else {
		LOG(RETRO_LOG_WARN, "Tried to pause/resume game but no game is loaded");
		return 0;
	}
}


int x_init(LibraryData* data) {
	GLint att[] = { GLX_RGBA, GLX_DEPTH_SIZE, 24, GLX_DOUBLEBUFFER, None };
	XSetWindowAttributes wa;
	Colormap cmap;
	
	// Open X connection
	Display* dpy = data->private->x.dpy = XOpenDisplay(NULL);
	if (dpy == NULL) {
		rt_set_error(data, "Failed to open display");
		return 1;
	}
	Window parent = DefaultRootWindow(dpy);
	XVisualInfo* vi = glXChooseVisual(dpy, 0, att);
	if (vi == NULL) {
		rt_set_error(data, "Failed to get appropriate visual");
		return 1;
	}
	cmap = XCreateColormap(dpy, parent, vi->visual, AllocNone);
	wa.colormap = cmap;
	wa.event_mask = ExposureMask | StructureNotifyMask;
	data->private->x.win = XCreateWindow(dpy, parent, 0, 0, 600, 600, 0,
		vi->depth, InputOutput, vi->visual, CWColormap | CWEventMask, &wa);
	XReparentWindow(dpy, data->private->x.win, data->parent, 0, 0);
	XMapWindow(dpy, data->private->x.win);
	XStoreName(dpy, data->private->x.win, "RetroTouch");
	
	data->private->gl.ctx = glXCreateContext(dpy, vi, NULL, GL_TRUE);
	if (data->private->gl.ctx == NULL) {
		rt_set_error(data, "Failed to create gl context");
		return 1;
	}
	return 0;
}


int rt_init(LibraryData* data) {
	if ((data->private = malloc(sizeof(PrivateData))) == NULL)
		return 1; // OOM
	
	memset(data->private, 0, sizeof(PrivateData));
	data->private->frame_width = 640;
	data->private->frame_height = 480;
	
	if (0 != x_init(data)) return 1;
	rt_make_current(data);
	if (0 != rt_init_gl(data)) return 1;
	rt_compile_shaders(data);
	
	LOG(RETRO_LOG_DEBUG, "Native code ready");
	return 0;
}


void rt_step(LibraryData* data) {
	static XEvent xev;
	
	while (XPending(data->private->x.dpy)) {
		XNextEvent(data->private->x.dpy, &xev);
		
		if (xev.type == Expose) {
			XWindowAttributes wa;
			XGetWindowAttributes(data->private->x.dpy, data->private->x.win, &wa);
			rt_set_draw_size(data, wa.width, wa.height);
			rt_render(data);
			glXSwapBuffers(data->private->x.dpy, data->private->x.win);
		} else if (xev.type == ConfigureNotify) {
			rt_set_draw_size(data, xev.xconfigure.width, xev.xconfigure.height);
		}
	}
	
	rt_make_current(data);
	if (data->private->hw_render_state == HW_RENDER_NEEDS_RESET) {
		data->private->hw_render_state = HW_RENDER_READY;
		rt_core_context_reset(data);
		LOG(RETRO_LOG_DEBUG, "HW rendering set up.");
	}
	rt_core_step(data);
	rt_render(data);
	glXSwapBuffers(data->private->x.dpy, data->private->x.win);
}
