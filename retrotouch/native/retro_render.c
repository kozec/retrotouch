#include <stdlib.h>
#include <stdio.h>
#include <string.h>
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
	PrivateData* private = data->private;
	GLuint buffer;
	// Load shader
	char* shader_name = malloc(strlen(data->respath) + 100);
	if (shader_name == NULL) {
		rt_set_error(data, "Out of memory");
		return;
	}
	strcpy(shader_name, data->respath);
	strcat(shader_name, "/normal");
	if (0 != load_shader_program(shader_name, &(private->program))) {
		free(shader_name);
		rt_set_error(data, "Failed to compile shaders");
		return;
	}
	free(shader_name);
	
	// Grab locations
	GLuint pos = glGetAttribLocation(private->program, "position");
	GLuint col = glGetAttribLocation(private->program, "color");
	
	// Generate and fill buffers
	glGenVertexArrays(1, &(private->vao));
	glBindVertexArray(private->vao);
	glGenBuffers(1, &buffer);
	glBindBuffer(GL_ARRAY_BUFFER, buffer);
	glBufferData(GL_ARRAY_BUFFER, sizeof(vertex_data), vertex_data, GL_STATIC_DRAW);
	
	// Enable attributes
	glEnableVertexAttribArray(pos);
	glVertexAttribPointer(pos, 3, GL_FLOAT, GL_FALSE, sizeof(struct vertex_info), 0);
	
	glEnableVertexAttribArray(col);
	glVertexAttribPointer(col, 3, GL_FLOAT, GL_FALSE, sizeof(struct vertex_info),
							(void*)(sizeof(GLfloat) * 3));
	
	// Grab locations
	private->u_texture = glGetUniformLocation(private->program, "texture");
	private->u_input_size = glGetUniformLocation(private->program, "input_size");
	private->u_output_size = glGetUniformLocation(private->program, "output_size");
	
	// Prepare FBO
	glGenFramebuffers(1, &(private->fbo));
	glBindFramebuffer(GL_FRAMEBUFFER, private->fbo);
	
	// Prepare texture
	glEnable(GL_TEXTURE_2D);
	glGenTextures(1, &(private->texture));
	glBindTexture(GL_TEXTURE_2D, private->texture);
	glTexImage2D(GL_TEXTURE_2D, 0,GL_RGB, 1024, 768, 0,GL_RGB, GL_UNSIGNED_BYTE, 0);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
	glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, private->texture, 0);
	if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) {
		printf("Failed to initialize FBO\n");
		exit(1);
	}
	
	// Cleanup
	glBindBuffer(GL_ARRAY_BUFFER, 0);
	glBindTexture(GL_TEXTURE_2D, 0);
	glBindFramebuffer(GL_FRAMEBUFFER, 0);
	glBindVertexArray(0);
	glDeleteBuffers(1, &buffer);
}


void rt_retro_frame(LibraryData* data, const char* frame, unsigned width, unsigned height, size_t pitch) {
	if (frame == NULL)
		return;
	if (frame == RETRO_HW_FRAME_BUFFER_VALID) {
		glFlush();
		gtk_gl_area_queue_render(GTK_GL_AREA(data->private->da));
		return;
	}
	data->private->frame_width = width;
	data->private->frame_height = height;
	data->private->frame = frame;
	
	glBindTexture(GL_TEXTURE_2D, data->private->texture);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB,
		width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, frame);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
	
	gtk_gl_area_queue_render(GTK_GL_AREA(data->private->da));
}


void rt_render(LibraryData* data) {
	glClearColor(0.0, 0.0, 0.5, 1.0);
	glClear(GL_COLOR_BUFFER_BIT);
	
	glUseProgram(data->private->program);
	glActiveTexture(GL_TEXTURE0);
	glBindTexture(GL_TEXTURE_2D, data->private->texture);
	glUniform1i(data->private->u_texture, 0);
	// data.u_input_size = glGetUniformLocation(data.program, "input_size");
	// data.u_output_size = glGetUniformLocation(data.program, "output_size");
	
	glBindVertexArray(data->private->vao);
	glDrawArrays(GL_TRIANGLES, 0, 6);
	glBindVertexArray(0);
	glUseProgram(0);
	
	glFlush();
}


int rt_hw_render_setup(LibraryData* data) {
	if (data->private->hw_render_state != HW_RENDER_DISABLED)
		return 0;		// Already enabled or setting up
	LOG(RETRO_LOG_DEBUG, "Setting up HW rendering...");
	data->private->hw_render_state = HW_RENDER_NEEDS_RESET;
	gtk_gl_area_queue_render(GTK_GL_AREA(data->private->da));
	return 0;
}