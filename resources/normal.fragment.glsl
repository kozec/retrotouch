#version 130
in vec2 uv;
uniform sampler2D texture;
out vec4 outputColor;

void main() {
#if defined(HW_RENDERING)
	vec3 color = texture2D(texture, uv).rgb;
#else
	vec3 color = texture2D(texture, uv).bgr;
#endif
	outputColor = vec4(color, 1);
}