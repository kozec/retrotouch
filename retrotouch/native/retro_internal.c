#include <stdlib.h>
#include <stdio.h>
#include <dlfcn.h>
#include <GL/glx.h>
#include <retro.h>

#define LOG(...) rt_log(current, "RInternal", __VA_ARGS__)

struct CoreData {
	void* handle;
	bool initialized;
	bool game_loaded;
	char* save_state;
	
	void (*retro_init)(void);
	void (*retro_deinit)(void);
	unsigned (*retro_api_version)(void);
	void (*retro_get_system_info)(struct retro_system_info *info);
	void (*retro_get_system_av_info)(struct retro_system_av_info *info);
	void (*retro_set_controller_port_device)(unsigned port, unsigned device);
	void (*retro_reset)(void);
	void (*retro_run)(void);
	size_t (*retro_serialize_size)(void);
	bool (*retro_serialize)(void *data, size_t size);
	bool (*retro_unserialize)(const void *data, size_t size);
	bool (*retro_load_game)(const struct retro_game_info *game);
	void (*retro_unload_game)(void);
	struct retro_hw_render_callback hw_render_callback;
} CoreData;

/** Libretro callbacks can't have user data attached, so this is used for time when libretro code is active */
static LibraryData* current;


#define load_sym(V, S) do {\
	if (!((*(void**)&V) = dlsym(current->core->handle, #S))) \
		LOG(RETRO_LOG_DEBUG, "Failed to load symbol '" #S "'': %s", dlerror()); \
	} while (0)
#define load_retro_sym(S) load_sym(current->core->S, S)


static uintptr_t video_driver_get_current_framebuffer() {
	return current->private->gl.fbo;
}


static retro_proc_address_t video_driver_get_proc_address(const char *sym) {
	return glXGetProcAddress((const GLubyte*)sym);
}


static void core_log(enum retro_log_level level, const char *fmt, ...) {
	char buffer[4096] = {0};
	va_list va;
	va_start(va, fmt);
	int len = vsnprintf(buffer, sizeof(buffer), fmt, va);
	va_end(va);
	buffer[sizeof(buffer) - 1] = 0;
	// Strip \n that some cores tend to add
	while ((len > 1) && (buffer[len - 1] == '\n')) {
		buffer[len - 1] = 0;
		len --;
	}
	
	current->cb_log("Core", (int)level, buffer);
}


static bool video_set_pixel_format(unsigned format) {
	switch (format) {
		case RETRO_PIXEL_FORMAT_XRGB8888:
			current->private->gl.colorspace = "COLORSPACE_RGB";
			LOG(RETRO_LOG_DEBUG, "Pixel format set to XRGB8888");
			if (current->private->gl.program != 0) {
				LOG(RETRO_LOG_WARN, "Pixel format changed after shaders were generated. Regenerating shaders...");
				rt_compile_shaders(current);
			}
			return true;
	}
	LOG(RETRO_LOG_ERROR, "Unknown pixel type %u", format);
	rt_set_error(current, "Unknown pixel format");
	return false;
}


static bool core_environment(unsigned cmd, void* data) {
	bool *bval;

	switch (cmd) {
	case RETRO_ENVIRONMENT_GET_LOG_INTERFACE: {
		struct retro_log_callback *cb = (struct retro_log_callback *)data;
		cb->log = core_log;
		break;
	}
	case RETRO_ENVIRONMENT_GET_CAN_DUPE:
		bval = (bool*)data;
		*bval = true;
		break;
	
	
	case RETRO_ENVIRONMENT_SET_VARIABLES:
		// LOG(RETRO_LOG_DEBUG, "Unhandled RETRO_ENVIRONMENT_SET_VARIABLES");
		return false;
	case RETRO_ENVIRONMENT_GET_VARIABLE:
		// LOG(RETRO_LOG_DEBUG, "Unhandled RETRO_ENVIRONMENT_GET_VARIABLE");
		return false;
	case RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE:
		// LOG(RETRO_LOG_DEBUG, "Unhandled RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE");	
		return false;
	
	case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT: {
		const enum retro_pixel_format *fmt = (enum retro_pixel_format *)data;

		if (*fmt > RETRO_PIXEL_FORMAT_RGB565)
			return false;

		return video_set_pixel_format(*fmt);
	}
	
	case RETRO_ENVIRONMENT_GET_USERNAME:
		*(const char **)data = "RetroTouch";
		return true;
	
	case RETRO_ENVIRONMENT_GET_LANGUAGE:
		*((enum retro_language*)data) = RETRO_LANGUAGE_ENGLISH;
	
	case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
	case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
		*(const char **)data = ".";
		return true;
	
	case RETRO_ENVIRONMENT_SET_HW_RENDER: {
		struct retro_hw_render_callback* cb = (struct retro_hw_render_callback*)data;
		if (cb->context_type != RETRO_HW_CONTEXT_OPENGL) {
			LOG(RETRO_LOG_ERROR, "Requested HW context #%i, but only OpenGL (#1) is supported");
			return false;
		}
		cb->get_current_framebuffer = video_driver_get_current_framebuffer;
		cb->get_proc_address        = NULL; // video_driver_get_proc_address;
		memcpy(&current->core->hw_render_callback, cb, sizeof(struct retro_hw_render_callback));
		return 0 == rt_hw_render_setup(current);
	
	case RETRO_ENVIRONMENT_SET_CONTROLLER_INFO: {
		const struct retro_controller_info* controller_info = (struct retro_controller_info*)data;
		LOG(RETRO_LOG_DEBUG, "Unhandled env RETRO_ENVIRONMENT_SET_CONTROLLER_INFO", cmd);
		return false;
	}
	
	}
	
	default:
		LOG(RETRO_LOG_DEBUG, "Unhandled env #%u", cmd);
		return false;
	}
	
	return true;
}


static void core_video_refresh(const void* frame, unsigned width, unsigned height, size_t pitch) {
	rt_retro_frame(current, frame, width, height, pitch);
}


static void core_input_poll(void) {
	// pass
}

static void core_audio_sample(int16_t left, int16_t right) {
	rt_audio_sample(current, left, right);
}


static size_t core_audio_sample_batch(const int16_t* audiodata, size_t frames) {
	rt_audio_sample_batch(current, audiodata, frames);
}


static int16_t core_input_state(unsigned port, unsigned device, unsigned index, unsigned id) {
	if (port == 0)
		return (*current->input_state & (1<<id)) ? 1 : 0;
	return 0;
}


void rt_core_unload() {
	if (current->core != NULL) {
		if (current->core->initialized)
			current->core->retro_deinit();
		if (current->core->handle)
			dlclose(current->core->handle);
		
		free(current->core);
		current->core = NULL;
	}
}


void rt_core_context_reset(LibraryData* data) {
	current->core->hw_render_callback.context_reset();
}


void rt_core_step(LibraryData* data) {
	current = data;
#if RT_DEBUG_FPS
	data->private->fps.ticks ++;
#endif
	current->core->retro_run();
}


int rt_get_game_loaded(LibraryData* data) {
	return current->core->game_loaded ? 1 : 0;
}


int rt_core_load(LibraryData* data, const char* filename) {
	current = data;
	rt_core_unload();
	current->core = malloc(sizeof(CoreData));
	if (current->core == NULL) {
		LOG(RETRO_LOG_ERROR, "Failed to allocate core data");
		return 3;
	}
	
	memset(current->core, 0, sizeof(CoreData));
	LOG(RETRO_LOG_DEBUG, "Loading core %s", filename);
	
	void (*set_environment)(retro_environment_t) = NULL;
	void (*set_video_refresh)(retro_video_refresh_t) = NULL;
	void (*set_input_poll)(retro_input_poll_t) = NULL;
	void (*set_input_state)(retro_input_state_t) = NULL;
	void (*set_audio_sample)(retro_audio_sample_t) = NULL;
	void (*set_audio_sample_batch)(retro_audio_sample_batch_t) = NULL;
	
	current->core->handle = dlopen(filename, RTLD_LAZY);
	current->core->save_state = NULL;
	
	if (!current->core->handle) {
		LOG(RETRO_LOG_ERROR, "Failed to load core: %s", dlerror());
		return 2;
	}
	
	dlerror();
	
	load_retro_sym(retro_init);
	load_retro_sym(retro_deinit);
	load_retro_sym(retro_api_version);
	load_retro_sym(retro_get_system_info);
	load_retro_sym(retro_get_system_av_info);
	load_retro_sym(retro_set_controller_port_device);
	load_retro_sym(retro_reset);
	load_retro_sym(retro_run);
	load_retro_sym(retro_load_game);
	load_retro_sym(retro_unload_game);
	load_retro_sym(retro_serialize_size);
	load_retro_sym(retro_unserialize);
	load_retro_sym(retro_serialize);
	
	load_sym(set_environment, retro_set_environment);
	load_sym(set_video_refresh, retro_set_video_refresh);
	load_sym(set_input_poll, retro_set_input_poll);
	load_sym(set_input_state, retro_set_input_state);
	load_sym(set_audio_sample, retro_set_audio_sample);
	load_sym(set_audio_sample_batch, retro_set_audio_sample_batch);
	
	set_environment(core_environment);
	set_video_refresh(core_video_refresh);
	set_input_poll(core_input_poll);
	set_input_state(core_input_state);
	set_audio_sample(core_audio_sample);
	set_audio_sample_batch(core_audio_sample_batch);
	
	current->core->retro_init();
	current->core->initialized = true;
	current->core->game_loaded = false;
	
	LOG(RETRO_LOG_DEBUG, "Core loaded");
}


int rt_game_load(LibraryData* data, const char* filename) {
	LOG(RETRO_LOG_DEBUG, "Loading game %s", filename);
	
	struct retro_system_av_info av = {0};
	struct retro_system_info system = {0};
	struct retro_game_info info = { filename, 0 };
	
	current->core->retro_get_system_info(&system);
	if (system.need_fullpath) {
		LOG(RETRO_LOG_DEBUG, "Core needs full path to game file");
		info.path = filename;
	} else {
		FILE *file = fopen(filename, "rb");
		if (!file)
			return 1;

		fseek(file, 0, SEEK_END);
		info.size = ftell(file);
		rewind(file);
		info.data = malloc(info.size);
		if (!info.data || !fread((void*)info.data, info.size, 1, file)) {
			fclose(file);
			return 2;
		}
		fclose(file);
	}
	
	if (!current->core->retro_load_game(&info)) {
		rt_set_error(current, "The core failed to load the game");
		return 3;
	}
		
	current->core->retro_get_system_av_info(&av);
	rt_set_render_size(current, av.geometry.base_width, av.geometry.base_height);
	if (0 != rt_audio_init(current, av.timing.sample_rate))
		return 1;
	current->core->game_loaded = true;
	current->private->gl.target_frame_time = (double)1000000.0 / av.timing.fps;
	LOG(RETRO_LOG_DEBUG, "Target FPS: %.2f, %luµs per frame",
						av.timing.fps, current->private->gl.target_frame_time);
	return 0;
}


int rt_save_state(LibraryData* data, const char* filename) {
	size_t size = data->core->retro_serialize_size();
	if (data->core->save_state == NULL) {
		data->core->save_state = malloc(size);
		if (data->core->save_state == NULL) {
			LOG(RETRO_LOG_ERROR, "Failed to save state: Failed to allocate memory");
			return 2;
		}
	}
	
	if (data->core->retro_serialize(data->core->save_state, size)) {
		FILE* f = fopen(filename, "wb");
		if (f == NULL) {
			LOG(RETRO_LOG_ERROR, "Failed to save state: Failed to open save file");
			return 3;
		}
		if (fwrite(data->core->save_state, size, 1, f) < 1) {
			LOG(RETRO_LOG_ERROR, "Failed to save state: Write failed");
			return 4;
		}
		fclose(f);
	} else {
		LOG(RETRO_LOG_ERROR, "Failed to save state");
		return 1;
	}
	LOG(RETRO_LOG_INFO, "State saved to '%s'", filename);
	return 0;
}


int rt_load_state(LibraryData* data, const char* filename) {
	FILE* f = fopen(filename, "rb");
	if (f == NULL) {
		LOG(RETRO_LOG_ERROR, "Failed to load state: Failed to open file");
		return 3;
	}
	
	fseek(f, 0, SEEK_END);
	size_t size = ftell(f);
	fseek(f, 0, SEEK_SET);
	char* state = malloc(size + 1);
	if (state == NULL) {
		LOG(RETRO_LOG_ERROR, "Failed to load state: Failed to allocate memory");
		return 2;
	}
	
	if (fread(state, size, 1, f) < 1) {
		LOG(RETRO_LOG_ERROR, "Failed to load state: Read failed");
		free(state);
		return 4;
	}
	fclose(f);
	
	if (data->private->frame != NULL) {
		// TODO: Possibly overallocating, this should depend on colorspace
		size_t frame_size = 4 * data->private->frame_width * data->private->frame_height;
		char* new_saved_frame = malloc(frame_size);
		if (new_saved_frame == NULL) {
			LOG(RETRO_LOG_ERROR, "Failed to load state: Failed to allocate memory");
			free(state);
			return 12;
		}
		memcpy(new_saved_frame, data->private->frame, frame_size);
		if (data->private->saved_frame != NULL)
			free(data->private->saved_frame);
		data->private->saved_frame = new_saved_frame;
		data->private->frame = new_saved_frame;
	}
	
	rt_make_current(data);
	if (!data->core->retro_unserialize(state, size)) {
		LOG(RETRO_LOG_ERROR, "Failed to load state");
		free(state);
		return 1;
	}
	
	free(state);
	return 0;
}
