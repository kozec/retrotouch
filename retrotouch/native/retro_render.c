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

// https://www.bassi.io/articles/2015/02/17/using-opengl-with-gtk/

struct vertex_info {
	GLfloat position[3];
	GLfloat color[3];
};

static const struct vertex_info vertex_data[] = {
	{ { -0.95f,  0.95f, 0.0f }, { 0.f, 0.f, 0.f } },
	{ { -0.95f, -0.95f, 0.0f }, { 0.f, 1.f, 0.f } },
	{ {  0.95f, -0.95f, 0.0f }, { 1.f, 1.f, 1.f } },

	{ {  0.95f,  0.95f, 0.0f }, { 1.f, 0.f, 0.f } },
	{ {  0.95f, -0.95f, 0.0f }, { 1.f, 1.f, 0.f } },
	{ { -0.95f,  0.95f, 0.0f }, { 0.f, 0.f, 1.f } },
};


void rt_init_gl(LibraryData* data) {
	// Generate and fill buffers
	glGenVertexArrays(1, &(data->private->vao));
	glBindVertexArray(data->private->vao);
	glGenBuffers(1, &data->private->vbo);
	glBindBuffer(GL_ARRAY_BUFFER, data->private->vbo);
	glBufferData(GL_ARRAY_BUFFER, sizeof(vertex_data), vertex_data, GL_STATIC_DRAW);
	
	// Prepare texture
	glEnable(GL_TEXTURE_2D);
	glGenTextures(1, &(data->private->texture));
	glBindTexture(GL_TEXTURE_2D, data->private->texture);
	glTexImage2D(GL_TEXTURE_2D, 0,GL_RGB, 1024, 768, 0,GL_RGB, GL_UNSIGNED_BYTE, 0);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
	
	// Cleanup
	glBindBuffer(GL_ARRAY_BUFFER, 0);
	glBindTexture(GL_TEXTURE_2D, 0);
	glBindVertexArray(0);
	LOG(RETRO_LOG_DEBUG, "GL initialized");
}


void rt_compile_shaders(LibraryData* data) {
	// Prepare #defines
	const char const* defines[] = {
		data->private->colorspace,
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
	if (0 != load_shader_program(shader_name, defines, &(data->private->program))) {
		free(shader_name);
		rt_set_error(data, "Failed to compile shaders");
		return;
	}
	free(shader_name);
	
	// Grab locations
	GLuint pos = glGetAttribLocation(data->private->program, "position");
	GLuint col = glGetAttribLocation(data->private->program, "color");
	
	// Enable attributes
	glBindVertexArray(data->private->vao);
	glBindBuffer(GL_ARRAY_BUFFER, data->private->vbo);
	glEnableVertexAttribArray(pos);
	glVertexAttribPointer(pos, 3, GL_FLOAT, GL_FALSE, sizeof(struct vertex_info), 0);
	
	glEnableVertexAttribArray(col);
	glVertexAttribPointer(col, 3, GL_FLOAT, GL_FALSE, sizeof(struct vertex_info),
							(void*)(sizeof(GLfloat) * 3));
	glBindBuffer(GL_ARRAY_BUFFER, 0);
	glBindVertexArray(0);
	
	// Grab locations
	data->private->u_texture = glGetUniformLocation(data->private->program, "texture");
	data->private->u_input_size = glGetUniformLocation(data->private->program, "input_size");
	data->private->u_output_size = glGetUniformLocation(data->private->program, "output_size");
	
	LOG(RETRO_LOG_DEBUG, "Shaders loaded");
}


uint64_t get_time() {
	static struct timeval t;
	gettimeofday(&t, NULL);
	return (t.tv_sec * (uint64_t)1000) + (t.tv_usec / 1000);
}


void rt_retro_frame(LibraryData* data, const char* frame, unsigned width, unsigned height, size_t pitch) {
	// gtk_gl_area_queue_render(GTK_GL_AREA(data->private->da));
	// return;
	if (frame == NULL)
		return;
#if DEBUG_FPS
	data->private->fps.generated ++;
#endif
	if (frame == RETRO_HW_FRAME_BUFFER_VALID) {
		// glFlush();
		gtk_gl_area_queue_render(GTK_GL_AREA(data->private->da));
		return;
	}
	// data->private->frame_width = width;
	// data->private->frame_height = height;
	// data->private->frame = frame;
	
	glBindTexture(GL_TEXTURE_2D, data->private->texture);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB,
		width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, frame);
	glBindTexture(GL_TEXTURE_2D, 0);
	// glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
	// glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
	
	gtk_gl_area_queue_render(GTK_GL_AREA(data->private->da));
}


void rt_render(LibraryData* data) {
	glViewport(0, 0, data->private->da_width, data->private->da_height);
	glClearColor(0.0, 0.0, 0.5, 1.0);
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
	
	glUseProgram(data->private->program);
	glActiveTexture(GL_TEXTURE0);
	glBindTexture(GL_TEXTURE_2D, data->private->texture);
	glUniform1i(data->private->u_texture, 0);
	
	glBindVertexArray(data->private->vao);
	glDrawArrays(GL_TRIANGLES, 0, 6);
	glBindVertexArray(0);
	glUseProgram(0);
	
#if DEBUG_FPS
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


void rt_set_render_size(LibraryData* data, int width, int height) {
	data->private->frame_width = width;
	data->private->frame_height = height;
	rt_compute_size_request(data);
	if (data->private->fbo != 0) {
		// Resolution changed after FBO is initialized, we need
		// to change its resolution as well
		glBindFramebuffer(GL_FRAMEBUFFER, data->private->fbo);
		glEnable(GL_TEXTURE_2D);
		glBindTexture(GL_TEXTURE_2D, data->private->texture);
		glTexImage2D(GL_TEXTURE_2D, 0,GL_RGB, data->private->frame_width,
				data->private->frame_height, 0, GL_RGB, GL_UNSIGNED_BYTE, 0);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
		glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
				data->private->texture, 0);
		glBindFramebuffer(GL_FRAMEBUFFER, 0);
		glBindTexture(GL_TEXTURE_2D, 0);
	}
	LOG(RETRO_LOG_DEBUG, "Screen size set to %ix%i", width, height);
}


int rt_hw_render_setup(LibraryData* data) {
	if (data->private->hw_render_state != HW_RENDER_DISABLED)
		return 0;		// Already enabled or setting up
	LOG(RETRO_LOG_DEBUG, "Setting up HW rendering...");
	data->private->hw_render_state = HW_RENDER_NEEDS_RESET;
	gtk_gl_area_queue_render(GTK_GL_AREA(data->private->da));
	return 0;
}


void rt_hw_render_reset(LibraryData* data) {
	if (data->private->fbo == 0) {
		glGenFramebuffers(1, &data->private->fbo);
		glBindFramebuffer(GL_FRAMEBUFFER, data->private->fbo);
		glEnable(GL_TEXTURE_2D);
		glBindTexture(GL_TEXTURE_2D, data->private->texture);
		glTexImage2D(GL_TEXTURE_2D, 0,GL_RGB, data->private->frame_width,
				data->private->frame_height, 0, GL_RGB, GL_UNSIGNED_BYTE, 0);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
		glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
				data->private->texture, 0);
		if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) {
			rt_set_error(data, "Failed to initialize frame buffer");
			// Going with HW_RENDER_READY anyway, rendering will get _totally_ broken,
			// but at least program will not crash.
		}
		glBindFramebuffer(GL_FRAMEBUFFER, 0);
		glBindTexture(GL_TEXTURE_2D, 0);
	}
	
	rt_core_context_reset(data);
	data->private->hw_render_state = HW_RENDER_READY;
	LOG(RETRO_LOG_DEBUG, "HW rendering set up.");
}
