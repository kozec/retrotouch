#version 150

in vec3 position;
in vec3 color;

uniform mat4 mvp;
out vec2 uv;

void main() {
	gl_Position = vec4(position, 1.0);
	uv = color.xy;
}
