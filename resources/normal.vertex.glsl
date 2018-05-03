#version 150

in vec3 position;
in vec3 color;

uniform mat4 mvp;
out vec2 uv;

void main() {
#if defined(HW_RENDERING)
	gl_Position = vec4(position.x, 0.0 - position.y, 0.0, 1.0);
#else
	gl_Position = vec4(position, 1.0);
#endif
	uv = color.xy;
}
