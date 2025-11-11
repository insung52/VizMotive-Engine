#include "Globals.hlsli"
#include "../ShaderInterop_EmittedParticle.h"

// Particle vertex shader
// Generates billboard quads from particle data

struct VSInput
{
	uint vertexID : SV_VertexID;
	uint instanceID : SV_InstanceID;
};

struct PSInput
{
	float4 position : SV_POSITION;
	float2 uv : TEXCOORD0;
	float4 color : COLOR;
	float lifePercent : LIFEPERC;
};

StructuredBuffer<Particle> particleBuffer : register(t1);
StructuredBuffer<uint> aliveList : register(t2);

// Billboard vertices (local space)
static const float3 BILLBOARD[4] = {
	float3(-1, -1, 0),  // bottom-left
	float3( 1, -1, 0),  // bottom-right
	float3(-1,  1, 0),  // top-left
	float3( 1,  1, 0),  // top-right
};

static const float2 UVS[4] = {
	float2(0, 1),  // bottom-left
	float2(1, 1),  // bottom-right
	float2(0, 0),  // top-left
	float2(1, 0),  // top-right
};

PSInput main(VSInput input)
{
	PSInput output;

	// Read particle data from buffer (using instanceID directly, not aliveList yet)
	uint particleIndex = input.instanceID;
	Particle particle = particleBuffer[particleIndex];

	// Check if particle is alive (has valid life)
	float3 particlePos;
	float particleSize;

	if (particle.life > 0.0f && particle.maxLife > 0.0f)
	{
		// Particle is alive, use real data
		particlePos = particle.position;
		float lifeLerp = 1.0f - particle.life / particle.maxLife;
		output.lifePercent = lifeLerp;
		particleSize = lerp(particle.sizeBeginEnd.x, particle.sizeBeginEnd.y, lifeLerp);
		//output.color = unpack_rgba(particle.color); // TEMP: commented out for testing
	}
	else
	{
		// Particle not initialized or dead - move it far away so it's not visible
		particlePos = float3(0.0f, -10000.0f, 0.0f); // Far below
		particleSize = 0.0f; // Zero size
		output.lifePercent = 0.0f;
		output.color = float4(0.0f, 0.0f, 0.0f, 0.0f); // Transparent
	}

	// Get billboard corner position
	uint vertexIndex = input.vertexID % 4;
	float3 quadPos = BILLBOARD[vertexIndex];
	float2 uv = UVS[vertexIndex];

	// No rotation for debug
	// quadPos.xy already set

	// Scale billboard
	quadPos *= particleSize;

	// Billboard facing camera - DEBUG: visualize camera axes
	// Use inverse view matrix columns for world-space camera axes
	float3 cameraRight = float3(GetCamera().inv_view._11, GetCamera().inv_view._21, GetCamera().inv_view._31);
	float3 cameraUp = float3(GetCamera().inv_view._12, GetCamera().inv_view._22, GetCamera().inv_view._32);

	// DEBUG: Output camera right vector as color to see if it changes
	output.color = float4(1.0f,0.0f,0.0f, 1.0f);

	// Transform quad to world space (billboarding)
	float3 worldPos = particlePos;
	worldPos += cameraRight * quadPos.x;
	worldPos += cameraUp * quadPos.y;

	// Transform to clip space
	output.position = mul(GetCamera().view_projection, float4(worldPos, 1.0f));

	// Sprite sheet UV (simple for now, using single frame)
	output.uv = uv;

	// Color already set above

	return output;
}
