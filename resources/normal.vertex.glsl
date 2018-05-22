#version 130

in vec3 v_position;
in vec3 v_uv;
out vec2 uv;

uniform vec2 window_size;
uniform vec2 screen_size;
uniform vec2 frame_size;
uniform vec2 internal_size;
uniform float scale_factor;

void main() {
#if defined(HW_RENDERING)
	gl_Position = vec4(
			scale_factor * v_position.x * screen_size.x / window_size.x,
			scale_factor * (0.0 - v_position.y) * screen_size.y / window_size.y,
			0.0, 1.0);
#else
	gl_Position = vec4(
			scale_factor * v_position.x * screen_size.x / window_size.x,
			scale_factor * v_position.y * screen_size.y / window_size.y,
			0.0, 1.0);
#endif
	uv = vec2(
		v_uv.x * internal_size.x / frame_size.x,
		v_uv.y * internal_size.y / frame_size.y
	);
}
