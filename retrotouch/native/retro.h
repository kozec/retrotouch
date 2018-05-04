#ifndef _TM_RETRO_H__
#define _TM_RETRO_H__
#define XLIB_ILLEGAL_ACCESS
#include <GL/gl.h>
#include <gtk/gtk.h>
#include <gtk/gtkwidget.h>
#include <libretro.h>

#define RT_MAX_PORTS	4
struct CoreData;

enum HwRenderState {
	HW_RENDER_DISABLED,
	HW_RENDER_NEEDS_RESET,
	HW_RENDER_READY
};

typedef struct {
	GtkWidget* da;
	
	char error[1024];
	const char* frame;
	unsigned int frame_width;
	unsigned int frame_height;
	unsigned int da_width;
	unsigned int da_height;
	uint32_t controller_state[RT_MAX_PORTS];
	enum HwRenderState hw_render_state;
	guint tick_id;
	
	GLuint program;
	GLfloat input_size[2];
	GLfloat output_size[2];
	const char* colorspace;
	bool flipped;
	GLuint texture;
	GLuint fbo;
	GLuint u_texture;
	GLuint u_input_size;
	GLuint u_output_size;
	GLuint vao;
	GLuint vbo;
	GLuint last_frame;
} PrivateData;


typedef struct {
	GtkWidget* parent;
	const char* respath;
	void (*log_fn) (const char* tag, int level, const char* message);
	struct CoreData* core;
	PrivateData* private;
} LibraryData;


void rt_log(LibraryData* data, const char* tag, enum retro_log_level level, const char *fmt, ...);
void rt_set_error(LibraryData* data, const char* message);

void rt_init_gl(LibraryData* data);
void rt_render(LibraryData* data);

void rt_compile_shaders(LibraryData* data);

// Callback called when core decides on desired screen size
void rt_set_render_size(LibraryData* data, int width, int height);
// Callback called when core has video frame ready
void rt_retro_frame(LibraryData* data, const char* frame, unsigned width, unsigned height, size_t pitch);
// Callback called when core requests HW rendering. Returns 0 for success
int rt_hw_render_setup(LibraryData* data);
// Called from event after rt_hw_render_setup is called and gl contect
// can be acquired, or when render resolution is changed
void rt_hw_render_reset(LibraryData* data);
// Computes and sets size_request based on frame_width and height.
// That is, at least 100px width and height while keeping aspect ratio
void rt_compute_size_request(LibraryData* data);

// Signalizes to core that GL context has been reset (used with HW rendering)
void rt_core_context_reset(LibraryData* data);
// Returns 0 on success, non-zero error code on failure
int rt_core_load(LibraryData* data, const char* filename);
// Returns 0 on success, non-zero error code on failure
int rt_game_load(LibraryData* data, const char* filename);
void rt_core_unload();
// Returns 1 if game is loaded
int rt_get_game_loaded(LibraryData* data);
// Starts, pauses or resumes game. 1 for paused. Returns 0 on success.
int rt_set_paused(LibraryData* data, int paused);
// Steps game one time (call this 60 times per second to get 60 FPS)
void rt_core_step(LibraryData* data);

#endif // _TM_RETRO_H