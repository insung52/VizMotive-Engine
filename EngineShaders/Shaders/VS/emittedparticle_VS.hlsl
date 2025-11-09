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

StructuredBuffer<Particle> particleBuffer : register(t0);
StructuredBuffer<uint> aliveList : register(t1);

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

	// Get particle index from alive list
	uint particleIndex = aliveList[input.instanceID];

	// Load particle data
	Particle particle = particleBuffer[particleIndex];

	// Calculate life percentage
	float lifeLerp = 1.0f - particle.life / particle.maxLife;
	output.lifePercent = lifeLerp;

	// Interpolate size over lifetime
	float particleSize = lerp(particle.sizeBeginEnd.x, particle.sizeBeginEnd.y, lifeLerp);

	// Get billboard corner position
	uint vertexIndex = input.vertexID % 4;
	float3 quadPos = BILLBOARD[vertexIndex];
	float2 uv = UVS[vertexIndex];

	// Unpack rotation
	uint packed = particle.rotation_rotationVelocity;
	float rotation = (float((packed >> 16) & 0xFFFF) / 65535.0f) * 2.0f * 3.14159265f - 3.14159265f;

	// Rotate billboard
	float2x2 rot = float2x2(
		cos(rotation), -sin(rotation),
		sin(rotation), cos(rotation)
	);
	quadPos.xy = mul(quadPos.xy, rot);

	// Scale billboard
	quadPos *= particleSize;

	// Billboard facing camera
	// Get view matrix from camera
	float3 cameraRight = float3(GetCamera().view._11, GetCamera().view._21, GetCamera().view._31);
	float3 cameraUp = float3(GetCamera().view._12, GetCamera().view._22, GetCamera().view._32);
	float3 cameraForward = float3(GetCamera().view._13, GetCamera().view._23, GetCamera().view._33);

	// Transform quad to world space (billboarding)
	float3 worldPos = particle.position;
	worldPos += cameraRight * quadPos.x;
	worldPos += cameraUp * quadPos.y;

	// Transform to clip space
	output.position = mul(GetCamera().view_projection, float4(worldPos, 1.0f));

	// Sprite sheet UV (simple for now, using single frame)
	output.uv = uv;

	// Unpack particle color
	output.color = unpack_rgba(particle.color);

	return output;
}
