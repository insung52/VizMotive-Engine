#include "Globals.hlsli"
#include "../ShaderInterop_EmittedParticle.h"

// Simple particle pixel shader
// Basic alpha-blended rendering

struct PSInput
{
	float4 position : SV_POSITION;
	float2 uv : TEXCOORD0;
	float4 color : COLOR;
	float lifePercent : LIFEPERC;
};

// Texture will be added later when texture support is implemented
// Texture2D<float4> particleTexture : register(t0);

float4 main(PSInput input) : SV_TARGET
{
	// Sample texture (simple white for now - texture binding not implemented yet)
	float4 texColor = float4(1, 1, 1, 1);

	// Calculate opacity based on life percent and curve parameters
	float t = input.lifePercent;
	float opacityFactor = 0.0f;

	if (t < xOpacityCurvePeakStart)
	{
		// Fade in
		opacityFactor = t / xOpacityCurvePeakStart;
	}
	else if (t < xOpacityCurvePeakEnd)
	{
		// Peak (full opacity)
		opacityFactor = 1.0f;
	}
	else
	{
		// Fade out
		opacityFactor = 1.0f - (t - xOpacityCurvePeakEnd) / (1.0f - xOpacityCurvePeakEnd);
	}

	// Combine texture, vertex color, and opacity curve
	float4 finalColor = texColor * input.color;
	finalColor.a *= opacityFactor;
    //float blue = xOpacityCurvePeakStart == 0.0f ? 1.0f : 0.0f;
    //return float4(xOpacityCurvePeakEnd, 0.0f, blue, 1.0f);
	return finalColor;
}
