#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#define GL_GLEXT_PROTOTYPES 1
#include <GL/gl.h>
#include <GL/glx.h>
#include <GL/glext.h>
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


uint64_t get_time() {
	static struct timeval t;
	gettimeofday(&t, NULL);
	return (t.tv_sec * (uint64_t)1000) + (t.tv_usec / 1000);
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
	uint64_t now = get_time();
	if ((data->private->fps.since == 0) || (now > data->private->fps.since + 1000)) {
		if (data->private->fps.since > 0) {
			uint64_t delta = now - data->private->fps.since;
			uint64_t ticks = data->private->fps.ticks * 1000 / delta;
			uint64_t drawn = data->private->fps.drawn * 1000 / delta;
			uint64_t generated = data->private->fps.generated * 1000 / delta;
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
