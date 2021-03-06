#ifndef _TM_RETRO_H__
#define _TM_RETRO_H__
#define XLIB_ILLEGAL_ACCESS
#include <X11/Xlib.h>
#include <GL/gl.h>
#include <GL/glx.h>
#include <alsa/asoundlib.h>
#include <libretro.h>
#include <unistd.h>

#define RT_MAX_PORTS		1
#define RT_MAX_ANALOGS		2
#define RT_MAX_IMAGES		4
#define RT_DEBUG_FPS		1
#define RT_AUDIO_ENABLED	1
struct CoreData;

enum HwRenderState {
	HW_RENDER_DISABLED,
	HW_RENDER_NEEDS_RESET,
	HW_RENDER_READY
};

typedef struct {
	char error[1024];
	const char* frame;
	char* saved_frame;
	unsigned int internal_width;
	unsigned int internal_height;
	unsigned int window_width;
	unsigned int window_height;
	enum HwRenderState hw_render_state;
	uint64_t serialization_quirks;
	Display* dpy;
	
	struct {
		uint64_t since;
		uint64_t drawn;
		uint64_t ticks;
		uint64_t generated;
	} fps;
	
	struct {
		int frequency;
		snd_pcm_uframes_t buffer_size;
		snd_pcm_t* device;
	} audio;
	
	struct {
		struct {
			GLuint id;
			GLint u_texture;
			GLint u_window_size;		// Size of target window
			GLint u_screen_size;		// Size of game screen (may not fill entire window)
			GLint u_internal_size;		// Render size set by core
			GLint u_frame_size;			// Size of frame generated by core
										// (may differ from internal size to keep it interesting)
			GLfloat u_scale_factor;
		} prog_normal;
		struct {
			GLuint id;
			GLint u_texture;
			GLint u_window_size;		// Size of target window
			GLint u_pad_size;			// Size of pad image
			GLint u_position;
			GLfloat u_scale_factor;
		} prog_pads;
		
		GLuint texture;
		GLuint depth;
		GLuint fbo;
		GLuint vao;
		GLuint vbo;
		
		struct {
			uint version;
			GLuint tex;
		} images[RT_MAX_IMAGES];
		
		GLXContext ctx;
		GLfloat screen_size[2];
		GLfloat window_size[2];
		GLfloat internal_size[2];
		GLfloat frame_size[2];
		useconds_t target_frame_time;
		unsigned int frame_skip;
		bool vsync_enabled;
		const char* extensions;
		const char* colorspace;
		GLenum pixel_format;
		GLenum pixel_type;
		GLfloat background_color[3];
		size_t bpp;
		size_t pitch;
		bool flipped;
	} gl;
	
} PrivateData;


struct InputState {
	uint buttons;
	int16_t analogs[2 * RT_MAX_ANALOGS];
	int16_t mouse[2];
	uint mouse_buttons;
};


struct SharedData {
	size_t size;
	float scale_factor;
	struct InputState input_state;
	struct {
		uint version;
		int x, y;
		uint width;
		uint height;
		size_t offset;
		size_t size;
	} images[RT_MAX_IMAGES];
};


typedef struct {
	const char* res_path;
	const char* save_path;
	int parent;
	int window;
	void (*cb_log) (const char* tag, int level, const char* message);
	void (*cb_render_size_changed) (int width, int height);
	const char* (*cb_get_variable) (const char* key);
	void (*cb_set_variable) (const char* key, const char* options);
	int variables_changed;
	struct SharedData* shared_data;
	PrivateData* private;
	struct CoreData* core;
} LibraryData;


void rt_log(LibraryData* data, const char* tag, enum retro_log_level level, const char *fmt, ...);
void rt_set_error(LibraryData* data, const char* message);
// Returns time in µs
useconds_t rt_get_time();

int rt_init(LibraryData* data);
int rt_init_gl(LibraryData* data);
void rt_step_paused(LibraryData* data);
void rt_step(LibraryData* data);
void rt_render(LibraryData* data);
void rt_make_current(LibraryData* data);
void rt_compile_shaders(LibraryData* data);
void rt_setup_texture(LibraryData* data);
const char* rt_check_error(LibraryData* data);
/** Returns 1 if saving is supported by core */
int rt_check_saving_supported(LibraryData* data);
// Returns 0 on success. Can be called multiple times to reconfigure frequency
int rt_audio_init(LibraryData* data, int frequency);
void rt_audio_sample(LibraryData* data, int16_t left, int16_t right);
size_t rt_audio_sample_batch(LibraryData* data, const int16_t* audiodata, size_t frames);

// Callback called when core decides on desired internal render size
void rt_set_render_size(LibraryData* data, int width, int height);
// Sets size of image on screen
void rt_set_screen_size(LibraryData* data, int width, int height);
// Sets size of window that drawing is done to
void rt_set_window_size(LibraryData* data, int width, int height);
void rt_set_background_color(LibraryData* data, float r, float g, float b);

// Saves PNG screenshot to given file
int rt_save_screenshot(LibraryData* data, const char* filename);
// Saves game state to given file
int rt_save_state(LibraryData* data, const char* filename);
// Loads game state from given file
int rt_load_state(LibraryData* data, const char* filename);

// Callback called when core has video frame ready
void rt_retro_frame(LibraryData* data, const char* frame, unsigned width, unsigned height, size_t pitch);
// Callback called when core requests HW rendering. Returns 0 for success
int rt_hw_render_setup(LibraryData* data);
// Called from event after rt_hw_render_setup is called and gl contect
// can be acquired, or when render resolution is changed
void rt_hw_render_reset(LibraryData* data);
// Enables or disables VSync; Returns 0 on success;
int rt_vsync_enable(LibraryData* data, int i);

// Signalizes to core that GL context has been reset (used with HW rendering)
void rt_core_context_reset(LibraryData* data);
// Returns 0 on success, non-zero error code on failure
int rt_core_load(LibraryData* data, const char* filename);
// Returns 0 on success, non-zero error code on failure
int rt_game_load(LibraryData* data, const char* filename);
void rt_core_unload();
// Returns 1 if game is loaded
int rt_get_game_loaded(LibraryData* data);
// Steps game one time (call this 60 times per second to get 60 FPS)
void rt_core_step(LibraryData* data);
// Does everything what rt_core_step, with important exception of actually running game. Called while paused.
void rt_core_step_paused(LibraryData* data);

#endif // _TM_RETRO_H