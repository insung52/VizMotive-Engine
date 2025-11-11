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
	// Return input color from VS
	return input.color;
}
