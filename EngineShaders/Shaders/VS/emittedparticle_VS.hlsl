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
	nointerpolation uint particleIndex : PARTICLEIDX;  // DEBUG: particle index
	nointerpolation uint aliveListIndex : ALIVELISTIDX;  // DEBUG: alive list index
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

	// Read particle index from alive list
	uint particleIndex = aliveList[input.instanceID];
	Particle particle = particleBuffer[particleIndex];

	// Check if particle is alive (has valid life)
	float3 particlePos;
	float particleSize;

	float4 particleColor;

	if (particle.life > 0.0f && particle.maxLife > 0.0f)
	{
		// Particle is alive, use real data
		particlePos = particle.position;
		float lifeLerp = 1.0f - particle.life / particle.maxLife;
		output.lifePercent = lifeLerp;
		particleSize = lerp(particle.sizeBeginEnd.x, particle.sizeBeginEnd.y, lifeLerp);
        particleColor = unpack_rgba(particle.color);
    }
	else
	{
		// Particle not initialized or dead - move it far away so it's not visible
		particlePos = float3(0.0f, -10000.0f, 0.0f); // Far below
		particleSize = 0.0f; // Zero size
		output.lifePercent = 0.0f;
		particleColor = float4(0.0f, 0.0f, 0.0f, 0.0f); // Transparent
	}

	// Get billboard corner position
	uint vertexIndex = input.vertexID % 4;
	float3 quadPos = BILLBOARD[vertexIndex];
	float2 uv = UVS[vertexIndex];

	// Apply rotation (unpack from uint16)
	// Rotation is in upper 16 bits, rotationVel in lower 16 bits
	uint packedRotation = particle.rotation_rotationVelocity;
	uint rotationBits = (packedRotation >> 16) & 0xFFFF; // Upper 16 bits
	// Unpack: 0~65535 -> -PI ~ +PI
	float rotation = (float(rotationBits) / 65535.0f) * 2.0f * 3.14159265f - 3.14159265f;

	// 2D rotation matrix
	float cosRot = cos(rotation);
	float sinRot = sin(rotation);
	float2 rotatedXY = float2(
		quadPos.x * cosRot - quadPos.y * sinRot,
		quadPos.x * sinRot + quadPos.y * cosRot
	);
	quadPos.xy = rotatedXY;

	// Scale billboard
	quadPos *= particleSize;

	// Motion blur: stretch quad along velocity direction in view space
	if (xParticleMotionBlurAmount > 0.0f)
	{
		// Transform velocity to view space
		float3 velocityViewSpace = mul((float3x3)GetCamera().view, particle.velocity);

		// Stretch quad vertices along velocity direction
		// dot(quadPos, velocity) projects the vertex position onto the velocity vector
		// This makes vertices along the motion direction stretch more
		quadPos += dot(quadPos, velocityViewSpace) * velocityViewSpace * xParticleMotionBlurAmount;
	}

	// Billboard facing camera
	// Use inverse view matrix columns for world-space camera axes
	float3 cameraRight = float3(GetCamera().inverse_view._11, GetCamera().inverse_view._21, GetCamera().inverse_view._31);
	float3 cameraUp = float3(GetCamera().inverse_view._12, GetCamera().inverse_view._22, GetCamera().inverse_view._32);

	// Transform quad to world space (billboarding)
	float3 worldPos = particlePos;
	worldPos += cameraRight * quadPos.x;
	worldPos += cameraUp * quadPos.y;

	// Transform to clip space
	output.position = mul(GetCamera().view_projection, float4(worldPos, 1.0f));

	// Sprite sheet UV (simple for now, using single frame)
	output.uv = uv;

	// Set color at the end (after all other processing)
	output.color = particleColor;

	// DEBUG: Pass particle index and alive list index to pixel shader
	output.particleIndex = particleIndex;
	output.aliveListIndex = input.instanceID;

	return output;
}
