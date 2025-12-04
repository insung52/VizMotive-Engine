#include "Globals.hlsli"
#include "../ShaderInterop_EmittedParticle.h"

// Emit shader for particle system
// Creates new particles from dead list and initializes them
// Supports both point emission and mesh surface emission

// Resources
StructuredBuffer<EmitLocation> emitBuffer : register(t0);

RWStructuredBuffer<Particle> particleBuffer : register(u0);
RWStructuredBuffer<uint> aliveBuffer_CURRENT : register(u1);
RWStructuredBuffer<uint> aliveBuffer_NEW : register(u2);
RWStructuredBuffer<uint> deadBuffer : register(u3);
RWByteAddressBuffer counterBuffer : register(u4);

// Simple random number generator
float rand(uint seed, uint offset)
{
	uint h = seed + offset;
	h = (h ^ 61u) ^ (h >> 16u);
	h *= 9u;
	h = h ^ (h >> 4u);
	h *= 0x27d4eb2du;
	h = h ^ (h >> 15u);
	return float(h) * (1.0f / 4294967296.0f);
}

float3 rand3(uint seed, uint offset)
{
	return float3(
		rand(seed, offset * 3 + 0),
		rand(seed, offset * 3 + 1),
		rand(seed, offset * 3 + 2)
	);
}

[numthreads(THREADCOUNT_EMISSION, 1, 1)]
void main(uint3 DTid : SV_DispatchThreadID, uint3 GTid : SV_GroupThreadID)
{
	// Load emit location from buffer
	EmitLocation location = emitBuffer[0];

	// Check if this thread should emit
	if (DTid.x >= location.count)
		return;

	// Initialize random seed
	uint seed = xEmitterInstanceIndex + DTid.x + GetFrame().frame_count * 1000;

	// Get world matrix from transform
	float4x4 worldMatrix = location.transform.GetMatrix();

	// Initialize emission properties
	float3 emitPos = float3(0, 0, 0);
	float3 nor = float3(0, 0, 0); // IMPORTANT: Initialize to 0 (not (0,1,0)) - fixes velocity issue!
	float3 velocity = xParticleVelocity;
	float4 baseColor = xParticleBaseColor * unpack_rgba(location.color);

	// Check if we should emit from mesh surface
	if (xEmitterMeshGeometryCount > 0)
	{
		// === MESH SURFACE EMISSION (VizMotive version) ===

		// Random subset of emitter mesh
		uint geometryIndex = xEmitterMeshGeometryOffset + uint(rand(seed, 50) * float(xEmitterMeshGeometryCount));
		ShaderGeometry geometry = load_geometry(geometryIndex);

		// For VizMotive, we need to use meshlets to get triangle count
		// Simplified: just use random position on sphere and estimate normal
		// TODO: Proper implementation using index buffer and vertex buffers

		// Generate random point on unit sphere
		float theta = rand(seed, 51) * 2.0f * 3.14159265f;
		float phi = acos(2.0f * rand(seed, 52) - 1.0f);

		float sinPhi = sin(phi);
		emitPos = float3(
			sinPhi * cos(theta),
			sinPhi * sin(theta),
			cos(phi)
		);

		// Normal is same as position for sphere
		nor = normalize(emitPos);

		// Apply mesh transform
		emitPos = mul(xEmitterBaseMeshUnormRemap.GetMatrix(), float4(emitPos, 1)).xyz;
		nor = normalize(mul((float3x3)xEmitterBaseMeshUnormRemap.GetMatrix(), nor));
		nor = normalize(mul((float3x3)worldMatrix, nor));
	}
	else
	{
		// === POINT EMISSION ===

		// Simple point emission at emitter center
		emitPos = float3(0, 0, 0);
		nor = float3(0, 0, 0); // No normal influence for point emission

		// Add randomness to emission position
		emitPos += (rand3(seed, 100) - 0.5f) * xParticleRandomPositionOffset;
	}

	// Transform emission position to world space
	float3 worldPos = mul(worldMatrix, float4(emitPos, 1)).xyz;

	// Calculate velocity with randomness
	// normalFactor only affects particles if nor != 0 (i.e., from mesh surface)
	velocity += (nor + (rand3(seed, 200) - 0.5f) * xParticleRandomVelocity) * xParticleNormalFactor;

	// Calculate particle size with randomness
	float particleStartingSize = xParticleSize + xParticleSize * (rand(seed, 300) - 0.5f) * xParticleRandomSize;

	// Calculate life with randomness
	float maxLife = xParticleLifeSpan + xParticleLifeSpan * (rand(seed, 400) - 0.5f) * xParticleLifeSpanRandomness;

	// Calculate rotation with randomness
	float rotation = (rand(seed, 500) - 0.5f) * xParticleRandomRotation;
	float rotationVelocity = xParticleRotation * (rand(seed, 600) - 0.5f) * xParticleRandomRotationVelocity;

	// Pack rotation
	uint rotation_packed = uint((rotation + 3.14159265f) / (2.0f * 3.14159265f) * 65535.0f);
	uint rotationVel_packed = uint((rotationVelocity + 3.14159265f) / (2.0f * 3.14159265f) * 65535.0f);
	uint rotation_rotationVelocity = (rotation_packed << 16) | rotationVel_packed;

	// Apply random color factor
	baseColor.r *= lerp(1.0f, rand(seed, 700), xParticleRandomColorFactor);
	baseColor.g *= lerp(1.0f, rand(seed, 701), xParticleRandomColorFactor);
	baseColor.b *= lerp(1.0f, rand(seed, 702), xParticleRandomColorFactor);

	// Create new particle
	Particle particle;
	particle.position = worldPos;
	particle.mass = xParticleMass;
	particle.force = float3(0, 0, 0);
	particle.rotation_rotationVelocity = rotation_rotationVelocity;
	particle.velocity = velocity;
	particle.maxLife = maxLife;
	particle.sizeBeginEnd = float2(particleStartingSize, particleStartingSize * xParticleScaling);
	particle.life = maxLife;
	particle.color = pack_rgba(baseColor);

	// Get a particle index from the dead list (pop operation)
	// We pop from the END of the dead list (deadCount - 1)
	int deadCount;
	counterBuffer.InterlockedAdd(PARTICLECOUNTER_OFFSET_DEADCOUNT, -1, deadCount);

	// Check if we have dead particles available
	if (deadCount < 1)
		return; // No dead particles available, cannot emit

	// Get the index of the dead particle (pop from end)
	uint newParticleIndex = deadBuffer[deadCount - 1];

	// Write the new particle to the particle buffer
	particleBuffer[newParticleIndex] = particle;

	// Add the particle index to the alive list (push operation)
	uint aliveCount;
	counterBuffer.InterlockedAdd(PARTICLECOUNTER_OFFSET_ALIVECOUNT_AFTERSIMULATION, 1, aliveCount);
	aliveBuffer_CURRENT[aliveCount] = newParticleIndex;
}
