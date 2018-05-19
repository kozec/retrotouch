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
#include <retro.h>
#include <gltools.h>

#define LOG(...) rt_log(data, "RRender", __VA_ARGS__)

struct vertex_info {
	GLfloat position[3];
	GLfloat color[3];
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
	glEnable(GL_TEXTURE_2D);
	glGenTextures(1, &(data->private->gl.texture));
	glBindTexture(GL_TEXTURE_2D, data->private->gl.texture);
	glTexImage2D(GL_TEXTURE_2D, 0,GL_RGB, 1024, 768, 0,GL_RGB, GL_UNSIGNED_BYTE, 0);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
	
	// Grab extensions, disable vsync
	data->private->gl.extensions = glXQueryExtensionsString(data->private->dpy, 0);
	LOG(RETRO_LOG_DEBUG, "Available GL extensions: %s", data->private->gl.extensions);
	data->private->gl.frame_skip = 1;
	
	// Cleanup
	glBindBuffer(GL_ARRAY_BUFFER, 0);
	glBindTexture(GL_TEXTURE_2D, 0);
	glBindVertexArray(0);
	LOG(RETRO_LOG_DEBUG, "GL initialized");
	
	return 0;
}


void rt_compile_shaders(LibraryData* data) {
	// Destroy old shaders
	if (data->private->gl.program != 0) {
		glDeleteProgram(data->private->gl.program);
		data->private->gl.program = 0;
	}
	
	// Prepare #defines
	const char const* defines[] = {
		data->private->gl.colorspace,
		NULL,
		NULL
	};
	if (data->private->hw_render_state != HW_RENDER_DISABLED)
		defines[1] = "HW_RENDERING";
	
	// Load shader
	char* shader_name = malloc(strlen(data->respath) + 100);
	if (shader_name == NULL) {
		rt_set_error(data, "Out of memory");
		return;
	}
	strcpy(shader_name, data->respath);
	strcat(shader_name, "/normal");
	if (0 != load_shader_program(shader_name, defines, &(data->private->gl.program))) {
		free(shader_name);
		rt_set_error(data, "Failed to compile shaders");
		return;
	}
	free(shader_name);
	
	// Grab locations
	GLuint pos = glGetAttribLocation(data->private->gl.program, "position");
	GLuint col = glGetAttribLocation(data->private->gl.program, "color");
	
	// Enable attributes
	glBindVertexArray(data->private->gl.vao);
	glBindBuffer(GL_ARRAY_BUFFER, data->private->gl.vbo);
	glEnableVertexAttribArray(pos);
	glVertexAttribPointer(pos, 3, GL_FLOAT, GL_FALSE, sizeof(struct vertex_info), 0);
	
	glEnableVertexAttribArray(col);
	glVertexAttribPointer(col, 3, GL_FLOAT, GL_FALSE, sizeof(struct vertex_info),
							(void*)(sizeof(GLfloat) * 3));
	glBindBuffer(GL_ARRAY_BUFFER, 0);
	glBindVertexArray(0);
	
	// Grab locations
	data->private->gl.u_texture = glGetUniformLocation(data->private->gl.program, "texture");
	data->private->gl.u_input_size = glGetUniformLocation(data->private->gl.program, "input_size");
	data->private->gl.u_output_size = glGetUniformLocation(data->private->gl.program, "output_size");
	
	LOG(RETRO_LOG_DEBUG, "Shaders loaded");
}


useconds_t rt_get_time() {
	static struct timeval t;
	gettimeofday(&t, NULL);
	return (t.tv_sec * (useconds_t)1000000) + (t.tv_usec);
}


int rt_vsync_enable(LibraryData* data, int i) {
	if (strstr(data->private->gl.extensions, "GLX_MESA_swap_control") != NULL) {
		typedef int (*glXSwapIntervalMESA_t)(int interval);
		glXSwapIntervalMESA_t glXSwapIntervalMESA = (glXSwapIntervalMESA_t)glXGetProcAddress("glXSwapIntervalMESA");
		glXSwapIntervalMESA(i);
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
	
	glBindTexture(GL_TEXTURE_2D, data->private->gl.texture);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB,
		width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, frame);
	glBindTexture(GL_TEXTURE_2D, 0);
	data->private->frame = frame;
}


void rt_render(LibraryData* data) {
	glViewport(0, 0, data->private->draw_width, data->private->draw_height);
	glClearColor(0.0, 0.0, 0.5, 1.0);
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
	
	glUseProgram(data->private->gl.program);
	glActiveTexture(GL_TEXTURE0);
	glBindTexture(GL_TEXTURE_2D, data->private->gl.texture);
	glUniform1i(data->private->gl.u_texture, 0);
	
	glBindVertexArray(data->private->gl.vao);
	glDrawArrays(GL_TRIANGLES, 0, 6);
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


void rt_set_render_size(LibraryData* data, int width, int height) {
	data->private->frame_width = width;
	data->private->frame_height = height;
	data->cb_render_size_changed(width, height);
	if (data->private->gl.fbo != 0) {
		// Resolution changed after FBO is initialized, we need
		// to change its resolution as well
		glBindFramebuffer(GL_FRAMEBUFFER, data->private->gl.fbo);
		glEnable(GL_TEXTURE_2D);
		glBindTexture(GL_TEXTURE_2D, data->private->gl.texture);
		glTexImage2D(GL_TEXTURE_2D, 0,GL_RGB, data->private->frame_width,
				data->private->frame_height, 0, GL_RGB, GL_UNSIGNED_BYTE, 0);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
		glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
				data->private->gl.texture, 0);
		glBindFramebuffer(GL_FRAMEBUFFER, 0);
		glBindTexture(GL_TEXTURE_2D, 0);
	}
	LOG(RETRO_LOG_DEBUG, "Screen size set to %ix%i", width, height);
}


void rt_set_draw_size(LibraryData* data, int width, int height) {
	data->private->draw_width = width;
	data->private->draw_height = height;
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
		glBindFramebuffer(GL_FRAMEBUFFER, data->private->gl.fbo);
		glEnable(GL_TEXTURE_2D);
		glBindTexture(GL_TEXTURE_2D, data->private->gl.texture);
		glTexImage2D(GL_TEXTURE_2D, 0,GL_RGB, data->private->frame_width,
				data->private->frame_height, 0, GL_RGB, GL_UNSIGNED_BYTE, 0);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
		glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
				data->private->gl.texture, 0);
		if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) {
			rt_set_error(data, "Failed to initialize frame buffer");
			// Going with HW_RENDER_READY anyway, rendering will get _totally_ broken,
			// but at least program will not crash.
		}
		glBindFramebuffer(GL_FRAMEBUFFER, 0);
		glBindTexture(GL_TEXTURE_2D, 0);
	}
	
	data->private->hw_render_state = HW_RENDER_NEEDS_RESET;
}


int rt_save_screenshot(LibraryData* data, const char* filename) {
	size_t src_step = 0, src_row_size = 0;
	size_t dst_row_size = 0;
	const char* colorspace = data->private->gl.colorspace;
	
	if (data->private->frame == NULL) {
		LOG(RETRO_LOG_ERROR, "Failed to save screenshot: No frame generated");
		return 1;
	}
	if ((colorspace != NULL) && (strcmp(colorspace, "COLORSPACE_RGB") == 0)) {
		src_step = 4;
		src_row_size = 4 * data->private->frame_width;
		dst_row_size = 3 * data->private->frame_width;
		// TODO: Maybe support for multiple colorspaces
	} else {
		LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Unknown colorspace");
		return 1;
	}
	
	png_bytep* rows = (png_bytep*) malloc(sizeof(png_bytep) * data->private->frame_height);
	png_bytep frame = malloc(dst_row_size * data->private->frame_width);
	if ((frame == NULL) || (rows == NULL)) {
		free(frame); free(rows);
		LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to allocate memory");
		return 2;
	}
	
	FILE* f = fopen(filename, "wb");

	png_structp png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
	png_infop info_ptr = (png_ptr==NULL) ? NULL : png_create_info_struct(png_ptr);
	if ((f == NULL) || (png_ptr == NULL) || (info_ptr == NULL)) {
		free(frame); free(rows);
		LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to open PNG file");
		return 3;
	}
	for (size_t y=0; y<data->private->frame_height; y++) {
		png_bytep src_row = (png_bytep)(data->private->frame + (y * src_row_size));
		png_bytep dst_row = frame + (y * dst_row_size);
		rows[y] = dst_row;
		for (size_t x=0; x<data->private->frame_width; x++) {
			*(dst_row + (x * 3) + 0) = *(src_row + (x * src_step) + 2);
			*(dst_row + (x * 3) + 1) = *(src_row + (x * src_step) + 1);
			*(dst_row + (x * 3) + 2) = *(src_row + (x * src_step) + 0);
		}
	}
	
	if (setjmp(png_jmpbuf(png_ptr))) {
		free(frame); free(rows);
		LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to initialize PNG file");
		return 4;
	}
	
	png_init_io(png_ptr, f);
	if (setjmp(png_jmpbuf(png_ptr))) {
		free(frame); free(rows);
		LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to write PNG header");
		return 5;
	}
	
	png_set_IHDR(png_ptr, info_ptr,
		data->private->frame_width, data->private->frame_height,
		8, PNG_COLOR_TYPE_RGB,
		PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_BASE, PNG_FILTER_TYPE_BASE);
	
	png_write_info(png_ptr, info_ptr);
	if (setjmp(png_jmpbuf(png_ptr))) {
		free(frame); free(rows);
		LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to write image");
		return 6;
	}
	
	png_write_image(png_ptr, rows);
	
	if (setjmp(png_jmpbuf(png_ptr))) {
		free(frame); free(rows);
		LOG(RETRO_LOG_ERROR, "Failed to save screenshot: Failed to finish image");
		return 7;
	}
	png_write_end(png_ptr, NULL);
	
	fclose(f);
	
	free(frame); free(rows);
	LOG(RETRO_LOG_INFO, "Screenshot saved to '%s'", filename);
	return 0;
}
