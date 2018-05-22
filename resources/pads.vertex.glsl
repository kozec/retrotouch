#version 130

in vec3 v_position;
in vec3 v_uv;
out vec2 uv;

uniform vec2 window_size;
uniform vec2 pad_size;
uniform vec2 position;
uniform float scale_factor;

void main() {
	float x, y;
	x = (v_position.x * scale_factor * pad_size.x / window_size.x) - 1.0 + (scale_factor * (pad_size.x + position.x * 2.0) / window_size.x);
	y = (v_position.y * scale_factor * pad_size.y / window_size.y) + 1.0 - (scale_factor * (pad_size.y + position.y * 2.0) / window_size.y);
	gl_Position = vec4(x, y, 0.0, 1.0);
	uv = v_uv.xy;
}
