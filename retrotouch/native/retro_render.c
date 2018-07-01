#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#define GL_GLEXT_PROTOTYPES 1
#include <GL/gl.h>
#include <GL/glx.h>
#include <GL/glext.h>
#define PNG_DEBUG 3
#include <png.h>
#include <retrotouch.h>
#include <gltools.h>

#define LOG(...) rt_log(data, "RRender", __VA_ARGS__)

struct vertex_info {
	GLfloat position[3];
	GLfloat uv[3];
};

static const struct vertex_info vertex_data[] = {
	{ { -1.f,  1.0f, 0.0f }, { 0.f, 0.f, 0.f } },
	{ { -1.f, -1.0f, 0.0f }, { 0.f, 1.f, 0.f } },
	{ {  1.f, -1.0f, 0.0f }, { 1.f, 1.f, 1.f } },
	{ {  1.f,  1.0f, 0.0f }, { 1.f, 0.f, 0.f } },
	{ {  1.f, -1.0f, 0.0f }, { 1.f, 1.f, 0.f } },
	{ { -1.f,  1.0f, 0.0f }, { 0.f, 0.f, 1.f } },
};


int rt_init_gl(LibraryData* data) {
	// Generate and fill buffers
	glGenVertexArrays(1, &(data->private->gl.vao));
	glBindVertexArray(data->private->gl.vao);
	glGenBuffers(1, &data->private->gl.vbo);
	glBindBuffer(GL_ARRAY_BUFFER, data->private->gl.vbo);
	glBufferData(GL_ARRAY_BUFFER, sizeof(vertex_data), vertex_data, GL_STATIC_DRAW);
	
	// Prepare texture
	data->private->gl.bpp = 4;
	data->private->gl.pitch = 0x10;
	data->private->gl.pixel_type = GL_RGB;
	data->private->gl.pixel_format = GL_UNSIGNED_BYTE;
	data->private->gl.background_color[0] = data->private->gl.background_color[1] = \
		data->private->gl.background_color[2] = 0.4;
	// TODO: This should default to 15-bit 0RGB1555, whatever that is
	glGenTextures(1, &(data->private->gl.texture));
	rt_setup_texture(data);
	
	// Grab extensions, disable vsync
	data->private->gl.extensions = glXQueryExtensionsString(data->private->dpy, 0);
	LOG(RETRO_LOG_DEBUG, "Available GL extensions: %s", data->private->gl.extensions);
	data->private->gl.frame_skip = 1;
	
	// Cleanup
	glBindBuffer(GL_ARRAY_BUFFER, 0);
	glBindVertexArray(0);
	LOG(RETRO_LOG_DEBUG, "GL initialized");
	
	return 0;
}


void rt_compile_shaders(LibraryData* data) {
	int i;
	static char defines_log[1024];
	static const char* defines[32];
	// Destroy old shaders
	if (data->private->gl.prog_normal.id != 0) {
		glDeleteProgram(data->private->gl.prog_normal.id);
		data->private->gl.prog_normal.id = 0;
	}
	
	// Prepare #defines
	i = 0;
	defines_log[0] = 0;
	defines[i++] = data->private->gl.colorspace;
	if (data->private->hw_render_state == HW_RENDER_READY)
		defines[i++] = "HW_RENDERING";
	defines[i++] = NULL;
	
	// Log #defines
	for (i=0; defines[i] != NULL;) {
		strcat(defines_log, defines[i]);
		if (defines[++i] != NULL)
			strcat(defines_log, " ");
	}
	LOG(RETRO_LOG_DEBUG, "Compiling shaders [%s]", defines_log);
	
	// Allocate
	char* shader_name = malloc(strlen(data->respath) + 100);
	if (shader_name == NULL) {
		rt_set_error(data, "Out of memory");
		return;
	}
	
	// Load "pads" shader
	if (data->private->gl.prog_pads.id == 0) {
		strcpy(shader_name, data->respath);
		strcat(shader_name, "/pads");
		if (0 != load_shader_program(shader_name, defines, &(data->private->gl.prog_pads.id))) {
			free(shader_name);
			rt_set_error(data, "Failed to compile shaders");
			return;
		}
		// Grab locations for "pads" shader
		data->private->gl.prog_pads.u_texture = glGetUniformLocation(data->private->gl.prog_pads.id, "texture");
		data->private->gl.prog_pads.u_window_size = glGetUniformLocation(data->private->gl.prog_pads.id, "window_size");
		data->private->gl.prog_pads.u_pad_size = glGetUniformLocation(data->private->gl.prog_pads.id, "pad_size");
		data->private->gl.prog_pads.u_position = glGetUniformLocation(data->private->gl.prog_pads.id, "position");
		data->private->gl.prog_pads.u_scale_factor = glGetUniformLocation(data->private->gl.prog_pads.id, "scale_factor");
	}
	
	// Load "main" shader
	strcpy(shader_name, data->respath);
	strcat(shader_name, "/normal");
	if (0 != load_shader_program(shader_name, defines, &(data->private->gl.prog_normal.id))) {
		free(shader_name);
		rt_set_error(data, "Failed to compile shaders");
		return;
	}
	free(shader_name);
	// Grab locations for "main" shader
	data->private->gl.prog_normal.u_texture = glGetUniformLocation(data->private->gl.prog_normal.id, "texture");
	data->private->gl.prog_normal.u_window_size = glGetUniformLocation(data->private->gl.prog_normal.id, "window_size");
	data->private->gl.prog_normal.u_screen_size = glGetUniformLocation(data->private->gl.prog_normal.id, "screen_size");
	data->private->gl.prog_normal.u_internal_size = glGetUniformLocation(data->private->gl.prog_normal.id, "internal_size");
	data->private->gl.prog_normal.u_frame_size = glGetUniformLocation(data->private->gl.prog_normal.id, "frame_size");
	data->private->gl.prog_normal.u_scale_factor = glGetUniformLocation(data->private->gl.prog_normal.id, "scale_factor");
	
	// Grab attributes
	GLuint pos = glGetAttribLocation(data->private->gl.prog_normal.id, "v_position");
	GLuint uv = glGetAttribLocation(data->private->gl.prog_normal.id, "v_uv");
	
	// Enable attributes
	glBindVertexArray(data->private->gl.vao);
	glBindBuffer(GL_ARRAY_BUFFER, data->private->gl.vbo);
	glEnableVertexAttribArray(pos);
	glVertexAttribPointer(pos, 3, GL_FLOAT, GL_FALSE, sizeof(struct vertex_info), 0);
	
	glEnableVertexAttribArray(uv);
	glVertexAttribPointer(uv, 3, GL_FLOAT, GL_FALSE, sizeof(struct vertex_info),
							(void*)(sizeof(GLfloat) * 3));
	glBindBuffer(GL_ARRAY_BUFFER, 0);
	glBindVertexArray(0);
	
	LOG(RETRO_LOG_DEBUG, "Shaders loaded & compiled");
}


void rt_setup_texture(LibraryData* data) {
	glBindTexture(GL_TEXTURE_2D, data->private->gl.texture);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB,
			data->private->internal_width,
			data->private->internal_height,
			0,
			data->private->gl.pixel_format,
			data->private->gl.pixel_type,
			0);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
	glBindTexture(GL_TEXTURE_2D, 0);
}


void rt_setup_depth_buffer(LibraryData* data) {
	if (data->private->gl.depth)
		glDeleteTextures(1, &data->private->gl.depth);
	glGenTextures(1, &(data->private->gl.depth));
	glBindTexture(GL_TEXTURE_2D, data->private->gl.depth);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT24,
			data->private->internal_width,
			data->private->internal_height,
			0,
			GL_DEPTH_COMPONENT,
			GL_UNSIGNED_BYTE,
			0);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
	glBindTexture(GL_TEXTURE_2D, 0);
}


useconds_t rt_get_time() {
	static struct timeval t;
	gettimeofday(&t, NULL);
	return (t.tv_sec * (useconds_t)1000000) + (t.tv_usec);
}


int rt_vsync_enable(LibraryData* data, int i) {
	if (strstr(data->private->gl.extensions, "GLX_MESA_swap_control") != NULL) {
		// Intel
		typedef int (*glXSwapIntervalMESA_t)(int interval);
		glXSwapIntervalMESA_t glXSwapIntervalMESA = (glXSwapIntervalMESA_t)glXGetProcAddress("glXSwapIntervalMESA");
		glXSwapIntervalMESA(i);
	} else if (strstr(data->private->gl.extensions, "GLX_EXT_swap_control") != NULL) {
		// Everything else
		typedef int (*glXSwapIntervalEXT_t)(int interval);
		glXSwapIntervalEXT_t glXSwapIntervalEXT = (glXSwapIntervalEXT_t)glXGetProcAddress("glXSwapIntervalEXT");
		glXSwapIntervalEXT(i);
	} else {
		LOG(RETRO_LOG_ERROR, "Cannot enable/disable VSync - no extension available");
		return 1;
	}
	
	data->private->gl.vsync_enabled = i;
	LOG(RETRO_LOG_DEBUG, "VSync %s", (i == 1) ? "disabled" : "enabled");
	return 0;
}


void rt_retro_frame(LibraryData* data, const char* frame, unsigned width, unsigned height, size_t pitch) {
	if (frame == NULL)
		return;
#if RT_DEBUG_FPS
	data->private->fps.generated ++;
#endif
	if (frame == RETRO_HW_FRAME_BUFFER_VALID) {
		return;
	}
	
	data->private->gl.frame_size[0] = (GLfloat)(pitch / data->private->gl.bpp);
	data->private->gl.pitch = pitch;
	glBindTexture(GL_TEXTURE_2D, data->private->gl.texture);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB,
		pitch / data->private->gl.bpp, height, 0,
		data->private->gl.pixel_format,
		data->private->gl.pixel_type,
		frame);
	glBindTexture(GL_TEXTURE_2D, 0);
	data->private->frame = frame;
}


void rt_render(LibraryData* data) {
	glBindFramebuffer(GL_FRAMEBUFFER, 0);
	glDisable(GL_BLEND);
	glViewport(0, 0, data->private->window_width, data->private->window_height);
	glClearColor(
		data->private->gl.background_color[0],
		data->private->gl.background_color[1],
		data->private->gl.background_color[2],
		0.0);
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
	
	glUseProgram(data->private->gl.prog_normal.id);
	glActiveTexture(GL_TEXTURE0);
	glBindTexture(GL_TEXTURE_2D, data->private->gl.texture);
	glUniform1i(data->private->gl.prog_normal.u_texture, 0);
	glUniform2fv(data->private->gl.prog_normal.u_screen_size, 1, data->private->gl.screen_size);
	glUniform2fv(data->private->gl.prog_normal.u_window_size, 1, data->private->gl.window_size);
	glUniform2fv(data->private->gl.prog_normal.u_internal_size, 1, data->private->gl.internal_size);
	glUniform2fv(data->private->gl.prog_normal.u_frame_size, 1, data->private->gl.frame_size);
	glUniform1f(data->private->gl.prog_normal.u_scale_factor, data->shared_data->scale_factor);
	
	glBindVertexArray(data->private->gl.vao);
	glDrawArrays(GL_TRIANGLES, 0, 6);
	
	glEnable(GL_BLEND);
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
	glUseProgram(data->private->gl.prog_pads.id);
	glUniform1i(data->private->gl.prog_pads.u_texture, 0);
	glUniform2fv(data->private->gl.prog_pads.u_window_size, 1, data->private->gl.window_size);
	glUniform1f(data->private->gl.prog_pads.u_scale_factor, data->shared_data->scale_factor);
	for (size_t i=0; i<RT_MAX_IMAGES; i++) {
		if (data->shared_data->images[i].size) {
			if (data->shared_data->images[i].version != data->private->gl.images[i].version) {
				if (data->private->gl.images[i].version != 0)
					glDeleteTextures(1, &data->private->gl.images[i].tex);
				glGenTextures(1, &(data->private->gl.images[i].tex));
				glBindTexture(GL_TEXTURE_2D, data->private->gl.images[i].tex);
				char* img_data = ((char*)data->shared_data) + data->shared_data->images[i].offset;
				
				glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
					data->shared_data->images[i].width,
					data->shared_data->images[i].height,
					0, GL_RGBA, GL_UNSIGNED_BYTE,
					img_data
				);
				glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
				glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
				data->private->gl.images[i].version = data->shared_data->images[i].version;
			} else {
				glBindTexture(GL_TEXTURE_2D, data->private->gl.images[i].tex);
			}
			glUniform2f(data->private->gl.prog_pads.u_pad_size,
				data->shared_data->images[i].width,
				data->shared_data->images[i].height
			);
			glUniform2f(data->private->gl.prog_pads.u_position,
				data->shared_data->images[i].x,
				data->shared_data->images[i].y
			);
			glDrawArrays(GL_TRIANGLES, 0, 6);
		}
	}
	
	glBindVertexArray(0);
	glUseProgram(0);
	
#if RT_DEBUG_FPS
	useconds_t now = rt_get_time() / 1000;
	if ((data->private->fps.since == 0) || (now > data->private->fps.since + 1000)) {
		if (data->private->fps.since > 0) {
			useconds_t delta = now - data->private->fps.since;
			useconds_t ticks = data->private->fps.ticks * 1000 / delta;
			useconds_t drawn = data->private->fps.drawn * 1000 / delta;
			useconds_t generated = data->private->fps.generated * 1000 / delta;
			LOG(RETRO_LOG_DEBUG, "FPS: %u ticks %u drawn %u generated", ticks, drawn, generated);
		}
		data->private->fps.since = now;
		data->private->fps.drawn = 1;
		data->private->fps.ticks = 0;
		data->private->fps.generated = 0;
	} else {
		data->private->fps.drawn ++;
	}
#endif
}


void rt_make_current(LibraryData* data) {
	glXMakeCurrent(data->private->dpy, data->window, data->private->gl.ctx);
}


static void setup_framebuffer(LibraryData* data) {
	glBindFramebuffer(GL_FRAMEBUFFER, data->private->gl.fbo);
	rt_setup_texture(data);
	glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
			GL_TEXTURE_2D, data->private->gl.texture, 0);
	
	
	// TODO: Do this only if requested
	rt_setup_depth_buffer(data);
	glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
			GL_TEXTURE_2D, data->private->gl.depth, 0);
	
	GLenum state = glCheckFramebufferStatus(GL_FRAMEBUFFER);
	if (state != GL_FRAMEBUFFER_COMPLETE) {
		LOG(RETRO_LOG_ERROR, "glCheckFramebufferStatus returned %p", state);
		rt_set_error(data, "Failed to initialize frame buffer");
		// Going with HW_RENDER_READY anyway, rendering will get _totally_ broken,
		// but at least program will not crash.
	}
	glBindTexture(GL_TEXTURE_2D, 0);
	glBindFramebuffer(GL_FRAMEBUFFER, 0);
}


void rt_set_render_size(LibraryData* data, int width, int height) {
	data->private->internal_width = width;
	data->private->internal_height = height;
	data->private->gl.frame_size[0] = data->private->gl.internal_size[0] =
			data->private->gl.screen_size[0] = (GLfloat)width;
	data->private->gl.frame_size[1] = data->private->gl.internal_size[1] =
			data->private->gl.screen_size[1] = (GLfloat)height;
	
	data->cb_render_size_changed(width, height);
	if (data->private->gl.fbo != 0) {
		// Resolution changed after FBO is initialized, we need
		// to change its resolution as well
		glDeleteFramebuffers(1, &data->private->gl.fbo);
		glGenFramebuffers(1, &data->private->gl.fbo);
		setup_framebuffer(data);
	}
	LOG(RETRO_LOG_DEBUG, "Internal size set to %ix%i", width, height);
}


void rt_set_screen_size(LibraryData* data, int width, int height) {
	// if ((data->private->gl.screen_size[0] != width) || (data->private->gl.screen_size[1] != height)) {
	data->private->gl.screen_size[0] = width;
	data->private->gl.screen_size[1] = height;
	LOG(RETRO_LOG_DEBUG, "Screen size set to %ix%i", width, height);
	// }
}


void rt_set_window_size(LibraryData* data, int width, int height) {
	if ((data->private->gl.window_size[0] != width) || (data->private->gl.window_size[1] != height)) {
		data->private->gl.window_size[0] = data->private->window_width = width;
		data->private->gl.window_size[1] = data->private->window_height = height;
		LOG(RETRO_LOG_DEBUG, "Window size set to %ix%i", width, height);
	}
}


void rt_set_background_color(LibraryData* data, float r, float g, float b) {
	data->private->gl.background_color[0] = r;
	data->private->gl.background_color[1] = g;
	data->private->gl.background_color[2] = b;
}


int rt_hw_render_setup(LibraryData* data) {
	if (data->private->hw_render_state != HW_RENDER_DISABLED)
		return 0;		// Already enabled or setting up
	LOG(RETRO_LOG_DEBUG, "Setting up HW rendering...");
	rt_hw_render_reset(data);
	return 0;
}


void rt_hw_render_reset(LibraryData* data) {
	if (data->private->gl.fbo == 0) {
		glGenFramebuffers(1, &data->private->gl.fbo);
		setup_framebuffer(data);
	}
	
	data->private->hw_render_state = HW_RENDER_NEEDS_RESET;
}


static char* RGB565_to_RGB888(LibraryData* data, const char* source_) {
	unsigned int width = data->private->internal_width;
	unsigned int height = data->private->internal_height;
	const unsigned short* source = (const unsigned short*)source_;

	char* frame = malloc(height * width * 3);
	memset(frame, 0, height * width * 3);
	if (frame == NULL) {
		LOG(RETRO_LOG_ERROR, "Failed convert frame: out of memory");
		return NULL;
	}
	
	size_t x, y;
	for (y=0; y<height; y++) {
		for (x=0; x<width; x++) {
			unsigned short src = source[0 + x + (y * data->private->gl.pitch / data->private->gl.bpp)];
			frame[0 + (x * 3) + (y * width * 3)] = (unsigned char)			// r
				((((unsigned int)(src & 0x1F)) * 255 + 15) / 31);
			frame[1 + (x * 3) + (y * width * 3)] = (unsigned char)			// g
				((((unsigned int)((src >> 5) & 0x3F)) * 255 + 31) / 63);
			frame[2 + (x * 3) + (y * width * 3)] = (unsigned char)
				((((unsigned int)((src >> 11) & 0x1F)) * 255 + 15) / 31);	// b
		}
	}
	return frame;
}


int rt_save_screenshot(LibraryData* data, const char* filename) {
	size_t src_step = 0, src_row_size = 0;
	size_t dst_row_size = 0;
	const char* colorspace = data->private->gl.colorspace;
	char* frame_source = NULL;
	char* tmp = NULL;
	png_structp png_ptr;
	png_infop info_ptr;
	png_bytep* rows = NULL;
	png_bytep frame = NULL;
	FILE* f;
	
	if (data->private->hw_render_state == HW_RENDER_READY) {
		if ((colorspace == NULL) || (strcmp(colorspace, "COLORSPACE_RGB8888") != 0)) {
			LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Unknown colorspace");
			return 1;
		}
		frame_source = malloc(3 * data->private->internal_width * data->private->internal_height);
		if (frame_source == NULL) {
			LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to allocate memory");
			return 2;
		}
		glBindFramebuffer(GL_FRAMEBUFFER, data->private->gl.fbo);
		rt_make_current(data);
		glReadPixels(0, 0, data->private->internal_width,
			data->private->internal_height, GL_RGB, GL_UNSIGNED_BYTE, frame_source);
		if (glGetError() != GL_NO_ERROR) {
			LOG(RETRO_LOG_ERROR, "Failed to save screenshot: glReadPixels failed");
			glBindFramebuffer(GL_FRAMEBUFFER, 0);
			return 8;
		}
		glBindFramebuffer(GL_FRAMEBUFFER, 0);
		
		rows = (png_bytep*) malloc(sizeof(png_bytep) * data->private->internal_height);
		if (rows == NULL) {
			free(frame); free(rows);
			LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to allocate memory");
			return 2;
		}
		
		f = fopen(filename, "wb");
		src_row_size = 3 * data->private->internal_width;
		png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
		info_ptr = (png_ptr==NULL) ? NULL : png_create_info_struct(png_ptr);
		if ((f == NULL) || (png_ptr == NULL) || (info_ptr == NULL)) {
			free(rows);
			LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to open PNG file");
			return 3;
		}
		for (size_t y=0; y<data->private->internal_height; y++) {
			png_bytep src_row = (png_bytep)(frame_source + (y * src_row_size));
			rows[data->private->internal_height - y] = src_row;
		}
	} else if (data->private->frame == NULL) {
		LOG(RETRO_LOG_ERROR, "Failed to save screenshot: No frame generated");
		return 1;
	} else {
		char* (*frame_conversion_fn)(LibraryData* data, const char* source) = NULL;
		
		if ((colorspace != NULL) && (strcmp(colorspace, "COLORSPACE_RGB8888") == 0)) {
			src_step = 4;
			src_row_size = 4 * data->private->internal_width;
			dst_row_size = 3 * data->private->internal_width;
		} else if ((colorspace != NULL) && (strcmp(colorspace, "COLORSPACE_RGB565") == 0)) {
			src_step = 3;
			src_row_size = 3 * data->private->internal_width;
			dst_row_size = 3 * data->private->internal_width;
			frame_conversion_fn = RGB565_to_RGB888;
		} else {
			LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Unknown colorspace");
			return 1;
		}
	
		rows = (png_bytep*) malloc(sizeof(png_bytep) * data->private->internal_height);
		frame = malloc(dst_row_size * data->private->internal_height);
		
		if ((frame == NULL) || (rows == NULL)) {
			free(frame); free(rows);
			LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to allocate memory");
			return 2;
		}
		
		if (frame_conversion_fn != NULL) {
			frame_source = frame_conversion_fn(data, data->private->frame);
			if (frame_source == NULL) {
				free(frame); free(rows);
				LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to convert frame");
				return 4;
			}
		}
		
		f = fopen(filename, "wb");
		
		png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
		info_ptr = (png_ptr==NULL) ? NULL : png_create_info_struct(png_ptr);
		if ((f == NULL) || (png_ptr == NULL) || (info_ptr == NULL)) {
			free(frame); free(rows); free(frame_source);
			LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to open PNG file");
			return 3;
		}
		
		for (size_t y=0; y<data->private->internal_height; y++) {
			const png_bytep src_row = (frame_source == NULL) \
				? ((const png_bytep)(data->private->frame + (y * src_row_size)))
				: ((const png_bytep)(frame_source + (y * src_row_size)));
			png_bytep dst_row = frame + (y * dst_row_size);
			rows[y] = dst_row;
			for (size_t x=0; x<data->private->internal_width; x++) {
				*(dst_row + (x * 3) + 0) = *(src_row + (x * src_step) + 2);
				*(dst_row + (x * 3) + 1) = *(src_row + (x * src_step) + 1);
				*(dst_row + (x * 3) + 2) = *(src_row + (x * src_step) + 0);
			}
		}
	}
	
	if (setjmp(png_jmpbuf(png_ptr))) {
		free(frame); free(rows); free(frame_source);
		LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to initialize PNG file");
		return 4;
	}
	
	png_init_io(png_ptr, f);
	if (setjmp(png_jmpbuf(png_ptr))) {
		free(frame); free(rows); free(frame_source);
		LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to write PNG header");
		return 5;
	}
	
	png_set_IHDR(png_ptr, info_ptr,
		data->private->internal_width, data->private->internal_height,
		8, PNG_COLOR_TYPE_RGB,
		PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_BASE, PNG_FILTER_TYPE_BASE);
	
	png_write_info(png_ptr, info_ptr);
	if (setjmp(png_jmpbuf(png_ptr))) {
		free(frame); free(rows); free(frame_source);
		LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to write image");
		return 6;
	}
	
	png_write_image(png_ptr, rows);
	
	if (setjmp(png_jmpbuf(png_ptr))) {
		free(frame); free(rows); free(frame_source);
		LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to finish image");
		return 7;
	}
	png_write_end(png_ptr, NULL);
	
	fclose(f);
	
	free(frame); free(rows); free(frame_source);
	LOG(RETRO_LOG_INFO, "Screenshot saved to '%s'", filename);
	return 0;
}
