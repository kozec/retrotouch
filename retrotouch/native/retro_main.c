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
	
	data->log_fn(tag, (int)level, buffer);
}


void rt_set_error(LibraryData* data, const char* message) {
	strncpy(data->private->error, message, 1023);
	data->private->error[1023] = 0;
	LOG(RETRO_LOG_ERROR, message);
}


static gboolean on_render(GtkGLArea* da, GdkGLContext* context, LibraryData* data) {
	if (data->private->hw_render_state == HW_RENDER_NEEDS_RESET) {
		rt_hw_render_reset(data);
	} else {
		rt_render(data);
	}
	return TRUE;
}


static gboolean on_resize(GtkGLArea* da, gint width, gint height, LibraryData* data) {
	data->private->da_width = width;
	data->private->da_height = height;
	if ((data->private->vao == 0) && (data->private->error[0] == 0))
		rt_init_gl(data);
	if ((data->private->program == 0) && (data->private->error[0] == 0))
		rt_compile_shaders(data);
	return TRUE;
}


static gboolean tick_callback(GtkGLArea* da, GdkFrameClock* frame_clock, LibraryData* data) {
	if (data->private->hw_render_state == HW_RENDER_NEEDS_RESET) {
		return TRUE;
	} else if (data->private->hw_render_state == HW_RENDER_READY) {
		GdkGLContext* glctx = gtk_gl_area_get_context(GTK_GL_AREA(data->private->da));
		gdk_gl_context_make_current(glctx);
	}
	gint64 frame = gdk_frame_clock_get_frame_counter(frame_clock);
	// Following should keep retro core running roughly at 60FPS,
	// skipping frames when GTK falls behind.
	if (frame < data->private->last_frame) {
		// Overflow
		rt_core_step(data);
		data->private->last_frame = frame;
	} else {
		while (data->private->last_frame < frame) {
			rt_core_step(data);
			data->private->last_frame ++;
		}
	}
	return TRUE;
}


const char* rt_check_error(LibraryData* data) {
	if (data->private->error[0] == 0)
		return NULL;
	return data->private->error;
}


void rt_compute_size_request(LibraryData* data) {
	double aspect = (double)data->private->frame_height / (double)data->private->frame_width;
	guint width = MIN(data->private->frame_width, 100);
	// TODO: Maybe test if computing with height would not be better
	guint height = (guint)((double)width * aspect);
	gtk_widget_set_size_request(data->private->da, width, height);
}


int rt_set_paused(LibraryData* data, int paused) {
	if (rt_get_game_loaded(data)) {
		int paused_now = (data->private->tick_id == 0) ? 1 : 0;
		if (paused == paused_now) {
			return 0;		// Already in correct state
		} else if (paused) {
			// Core is running but it should be paused
			gtk_widget_remove_tick_callback(data->private->da, data->private->tick_id);
			data->private->tick_id = 0;
			LOG(RETRO_LOG_DEBUG, "Core paused");
			return 0;
		} else {
			// Core is paused and it should be resumed
			data->private->tick_id = gtk_widget_add_tick_callback(data->private->da,
					(GtkTickCallback)tick_callback, data, NULL);
			if (data->private->tick_id < 1)
				return 1; // failed
			LOG(RETRO_LOG_DEBUG, "Core resumed");
			return 0;
		}
	} else {
		LOG(RETRO_LOG_WARN, "Tried to pause/resume game but no game is loaded");
		return 0;
	}
}


int rt_create(LibraryData* data) {
	GtkWidget* da;
	if (GTK_CONTAINER(data->parent) == NULL)
		return 2; // Invalid parent
	if ((data->private = malloc(sizeof(PrivateData))) == NULL)
		return 1; // OOM
	
	if ((data->private->da = da = gtk_gl_area_new()) == NULL) {
		free(data->private);
		return 3; // Failed to create widget
	}
	
	gtk_gl_area_set_use_es(GTK_GL_AREA(da), FALSE);
	gtk_gl_area_set_auto_render(GTK_GL_AREA(da), TRUE);
	gtk_gl_area_set_has_depth_buffer(GTK_GL_AREA(da), FALSE);
	gtk_gl_area_set_has_stencil_buffer(GTK_GL_AREA(da), FALSE);
	gtk_container_add(GTK_CONTAINER(data->parent), da);
	g_signal_connect(da, "render", (GCallback)on_render, data);
	g_signal_connect(da, "resize", (GCallback)on_resize, data);
	data->private->error[0] = 0;
	data->private->hw_render_state = HW_RENDER_DISABLED;
	data->private->program = 0;
	data->private->frame_width = 640;
	data->private->frame_height = 480;
	data->private->vao = 0;
	data->private->fbo = 0;
	data->private->frame = NULL;
	data->private->tick_id = 0;
	data->private->last_frame = 0;
	rt_compute_size_request(data);
	LOG(RETRO_LOG_DEBUG, "Native code ready");
	return 0;
}
