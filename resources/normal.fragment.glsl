#version 130
in vec2 uv;
uniform sampler2D texture;
out vec4 outputColor;

void main() {
#if defined(COLORSPACE_RGB565)
	outputColor = vec4(texture2D(texture, uv).rgb, 1);
#elif defined(HW_RENDERING)
	outputColor = texture2D(texture, uv).rgba;
#else
	outputColor = vec4(texture2D(texture, uv).bgr, 1);
#endif
}