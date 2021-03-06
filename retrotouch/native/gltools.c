#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#define GL_GLEXT_PROTOTYPES 1
#include <GL/gl.h>
#include <GL/glx.h>
#include <GL/glext.h>
#include "gltools.h"

int create_shader(int shader_type, const char* source, GLuint* shader) {
	int status = GL_TRUE;
	*shader = glCreateShader(shader_type);
	glShaderSource(*shader, 1, &source, NULL);
	glCompileShader(*shader);

	glGetShaderiv(*shader, GL_COMPILE_STATUS, &status);
	if (status == GL_FALSE) {
		int len;
		glGetShaderiv(*shader, GL_INFO_LOG_LENGTH, &len);
		
		char* buffer = malloc(len + 1);
		char* shader_type_c = (shader_type == GL_VERTEX_SHADER) ? "Vertex" : "Fragment";
		
		if (buffer != NULL) {
			glGetShaderInfoLog(*shader, len, NULL, buffer);
			fprintf(stderr, "%s shader compilation failed: %s\n", shader_type_c, buffer);
			free(buffer);
		} else {
			fprintf(stderr, "%s shader compilation failed; Getting shader log failed: OOM\n", shader_type_c);
		}
		fprintf(stderr, "Shader source:\n%s\n", source);
		glDeleteShader(*shader);
		return 1;
	}
	return 0;
}


int load_shader(int shader_type, const char* const defines[], const char* filename, GLuint* shader) {
	FILE* f = fopen(filename, "r");
	if (f == NULL) {
		fprintf(stderr, "Failed to open shader file: %s\n", filename);
		return 4;
	}
	
	fseek(f, 0L, SEEK_END);
	size_t filesize = ftell(f);
	size_t total_size = filesize + 10;
	for (int i=0; defines[i] != NULL; i++)
		total_size += strlen(defines[i]) + 12;
	rewind(f);
	
	char* source = malloc(filesize + 1);
	char* preprocessed = malloc(total_size + 1);
	if ((source == NULL) || (preprocessed == NULL)) {
		free(source); free(preprocessed);
		fclose(f);
		fprintf(stderr, "OOM while loading shader file: %s\n", filename);
		return 3;
	}
	
	if (fread(source, filesize, 1, f) < 1) {
		fclose(f);
		free(source); free(preprocessed);
		fprintf(stderr, "Failed to load shader file: %s\n", filename);
		return 4;
	}
	
	fclose(f);
	source[filesize] = 0;
	char* first_newline = strstr(source, "\n");
	*first_newline = 0;
	
	strcpy(preprocessed, source);				// #version
	strcat(preprocessed, "\n");					// newline
	for (int i=0; defines[i] != NULL; i++) {	// #defines
		strcat(preprocessed, "#define ");
		strcat(preprocessed, defines[i]);
		strcat(preprocessed, "\n");
	}
	strcat(preprocessed, "#line 1\n");
	strcat(preprocessed, first_newline + 1);
	free(source);
	
	int rv = create_shader(shader_type, preprocessed, shader);
	free(preprocessed);
	return rv;
}


int load_shader_program(const char* prefix, const char* const defines[], GLuint* program) {
	int err, status = GL_TRUE;
	GLuint vshader, fshader;
	char* filenamebuff = malloc(strlen(prefix) + 16);
	if (filenamebuff == NULL) {
		fprintf(stderr, "OOM while preparing to link shader program: %s\n", prefix);
		return 2;
	}
	
	strcpy(filenamebuff, prefix);
	strcat(filenamebuff, ".vertex.glsl");
	err = load_shader(GL_VERTEX_SHADER, defines, filenamebuff, &vshader);
	if (err != 0) {
		free(filenamebuff);
		return err;
	}
	
	strcpy(filenamebuff, prefix);
	strcat(filenamebuff, ".fragment.glsl");
	err = load_shader(GL_FRAGMENT_SHADER, defines, filenamebuff, &fshader);
	if (err != 0) {
		glDeleteShader(vshader);
		free(filenamebuff);
		return err;
	}
	
	free(filenamebuff);
	*program = glCreateProgram();
	glAttachShader(*program, vshader);
	glAttachShader(*program, fshader);
	glLinkProgram(*program);
	
	glGetProgramiv(*program, GL_LINK_STATUS, &status);
	if (status == GL_FALSE) {
		int len;
		glGetProgramiv(*program, GL_INFO_LOG_LENGTH, &len);
		char* buffer = malloc(len + 1);
		if (buffer != NULL) {
			glGetProgramInfoLog(*program, len, NULL, buffer);
			fprintf(stderr, "Shader program linking failed: %s\n", buffer);
			free(buffer);
		} else {
			fprintf(stderr, "Shader program linking failed; Getting log failed: OOM\n");
		}
		glDeleteShader(fshader);
		glDeleteShader(vshader);
		glDeleteProgram(*program);
		return 1;
	}
	
	// glDetachShader(program, vertex);
	// glDetachShader(program, fragment);
	return 0;
}