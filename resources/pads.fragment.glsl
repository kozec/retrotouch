#version 130
in vec2 uv;
uniform sampler2D texture;
out vec4 outputColor;

void main() {
	outputColor = texture2D(texture, uv).rgba;
}