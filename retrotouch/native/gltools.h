#ifndef __GL_TOOLS_H__
#define __GL_TOOLS_H__
#include <GL/gl.h>


/** Returns 0 and sets 'shader' on success */
int create_shader(int shader_type, const char* source, GLuint* shader);

/** As create_shader, but takes filename instead of source code */
int load_shader(int shader_type, const char* filename, GLuint* shader);

/** 
 * Loads both vertex and fragment shader, links them together and sets entire program 
 * Returns 0 and sets 'program' on success.
 */
int load_shader_program(const char* prefix, GLuint* program);

#endif  // __GL_TOOLS_H__
