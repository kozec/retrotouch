#ifndef _TM_RETRO_H__
#define _TM_RETRO_H__
#define XLIB_ILLEGAL_ACCESS
#include <X11/Xlib.h>
#include <GL/gl.h>
#include <GL/glx.h>
#include <alsa/asoundlib.h>
#include <libretro.h>
#include <unistd.h>

#define RT_MAX_PORTS		4
#define RT_DEBUG_FPS			1
#define RT_AUDIO_ENABLED	0
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
	unsigned int frame_width;
	unsigned int frame_height;
	unsigned int draw_width;
	unsigned int draw_height;
	enum HwRenderState hw_render_state;
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
		GLuint program;
		GLuint texture;
		GLuint fbo;
		GLuint u_texture;
		GLuint u_input_size;
		GLuint u_output_size;
		GLuint vao;
		GLuint vbo;
		
		GLXContext ctx;
		GLfloat input_size[2];
		GLfloat output_size[2];
		useconds_t target_frame_time;
		unsigned int frame_skip;
		bool vsync_enabled;
		const char* extensions;
		const char* colorspace;
		bool flipped;
	} gl;
	
} PrivateData;


typedef struct {
	const char* respath;
	int parent;
	int window;
	void (*cb_log) (const char* tag, int level, const char* message);
	void (*cb_render_size_changed) (int width, int height);
	uint* input_state;
	PrivateData* private;
	struct CoreData* core;
} LibraryData;


void rt_log(LibraryData* data, const char* tag, enum retro_log_level level, const char *fmt, ...);
void rt_set_error(LibraryData* data, const char* message);
// Returns time in µs
useconds_t rt_get_time();

int rt_init_gl(LibraryData* data);
void rt_render(LibraryData* data);
void rt_make_current(LibraryData* data);
void rt_compile_shaders(LibraryData* data);

// Returns 0 on success. Can be called multiple times to reconfigure frequency
int rt_audio_init(LibraryData* data, int frequency);
void rt_audio_sample(LibraryData* data, int16_t left, int16_t right);
size_t rt_audio_sample_batch(LibraryData* data, const int16_t* audiodata, size_t frames);

// Callback called when core decides on desired screen size
void rt_set_render_size(LibraryData* data, int width, int height);
// Callback called actual window to which image is drawn is resized
void rt_set_draw_size(LibraryData* data, int width, int height);

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