#version 150

in vec2 uv;
uniform sampler2D texture;
out vec4 outputColor;

void main() {
	vec3 color = texture2D(texture, uv).bgr;
	outputColor = vec4(color, 1);
}