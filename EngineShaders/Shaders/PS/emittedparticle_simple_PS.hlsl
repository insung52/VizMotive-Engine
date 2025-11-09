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

Texture1D<float> opacityCurve : register(t0);
Texture2D<float4> particleTexture : register(t1);

float4 main(PSInput input) : SV_TARGET
{
	// Sample particle texture (if bound)
	float4 texColor = float4(1, 1, 1, 1);

	// Simple circular particle (procedural)
	float2 centerDist = (input.uv - 0.5f) * 2.0f;
	float dist = length(centerDist);
	float alpha = 1.0f - smoothstep(0.8f, 1.0f, dist);

	// Sample opacity curve based on life percentage
	float lifeOpacity = opacityCurve.SampleLevel(sampler_linear_clamp, input.lifePercent, 0);

	// Combine color and alpha
	float4 finalColor = input.color;
	finalColor.a *= alpha * lifeOpacity;

	// Discard if too transparent
	if (finalColor.a < 0.01f)
		discard;

	return finalColor;
}
