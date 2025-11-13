#include "Globals.hlsli"
#include "../ShaderInterop_EmittedParticle.h"

// Simulate shader for particle system
// Updates particle physics and removes dead particles

// Resources (opacity curve removed - calculated in PS using CB)
RWStructuredBuffer<Particle> particleBuffer : register(u0);
RWStructuredBuffer<uint> aliveBuffer_CURRENT : register(u1);
RWStructuredBuffer<uint> aliveBuffer_NEW : register(u2);
RWStructuredBuffer<uint> deadBuffer : register(u3);
RWByteAddressBuffer counterBuffer : register(u4);

// Depth collision resources (optional - Phase 6)
// Texture2D<float> texture_depth : register(t1);

[numthreads(THREADCOUNT_SIMULATION, 1, 1)]
void main(uint3 DTid : SV_DispatchThreadID, uint Gid : SV_GroupIndex)
{
	// Load alive count
	uint aliveCount = counterBuffer.Load(PARTICLECOUNTER_OFFSET_ALIVECOUNT);
	if (DTid.x >= aliveCount)
		return;

	// Load particle
	uint particleIndex = aliveBuffer_CURRENT[DTid.x];
	Particle particle = particleBuffer[particleIndex];

	// Get timestep (fixed or variable)
	float dt = xEmitterFixedTimestep;
	if (dt < 0.0f)
	{
		// Use frame delta time if fixed timestep is not set
		dt = GetFrame().delta_time;
		// Fallback to 60 FPS if delta_time is invalid (0 or very large)
		if (dt <= 0.0f || dt > 0.1f)
		{
			//dt = 1.0f / 60.0f;
		}
	}

	// Update life
	particle.life -= dt;

	// Calculate life lerp for size and opacity
	const float lifeLerp = 1.0f - particle.life / particle.maxLife;
	const float particleSize = lerp(particle.sizeBeginEnd.x, particle.sizeBeginEnd.y, lifeLerp);

	// Calculate color based on life
	float4 particleColor = unpack_rgba(particle.color);
	particle.color = pack_rgba(particleColor);

	// Opacity is now calculated in PS using CB parameters
	// No need to sample opacity curve here

	// Check if particle is still alive
	if (particle.life > 0.0f)
	{
		// === Physics Integration ===

		// Add gravity to force
		particle.force += xParticleGravity;

		// Integrate velocity: v += (F/m) * dt
		particle.velocity += (particle.force / particle.mass) * dt;

		// Integrate position: p += v * dt
		particle.position += particle.velocity * dt;

		// Reset force for next frame
		particle.force = float3(0, 0, 0);

		// Apply drag
		particle.velocity *= xParticleDrag;

		// === Rotation Update ===
		// Unpack rotation and rotation velocity (simple unpack for now)
		uint packed = particle.rotation_rotationVelocity;
		float rotation = (float((packed >> 16) & 0xFFFF) / 65535.0f) * 2.0f * 3.14159265f - 3.14159265f;
		float rotationVel = (float(packed & 0xFFFF) / 65535.0f) * 2.0f * 3.14159265f - 3.14159265f;

		// Update rotation
		rotation += rotationVel * dt;

		// Re-pack rotation
		uint rotation_new = uint((rotation + 3.14159265f) / (2.0f * 3.14159265f) * 65535.0f);
		uint rotationVel_new = uint((rotationVel + 3.14159265f) / (2.0f * 3.14159265f) * 65535.0f);
		particle.rotation_rotationVelocity = (rotation_new << 16) | rotationVel_new;

		// === Collider Processing (Optional - Phase 6) ===
		// TODO: Add force field and collider support
		// for (uint i = 0; i < forces().item_count(); ++i) { ... }

		// === Depth Collision (Optional - Phase 6) ===
		// TODO: Add depth buffer collision detection
		// if (xEmitterOptions & EMITTER_OPTION_BIT_DEPTH_COLLISION) { ... }

		// Add to new alive list (push)
		uint newAliveIndex;
		counterBuffer.InterlockedAdd(PARTICLECOUNTER_OFFSET_ALIVECOUNT_AFTERSIMULATION, 1, newAliveIndex);
		aliveBuffer_NEW[newAliveIndex] = particleIndex;
	}
	else
	{
		// === Particle Death ===
		// Add to dead list (push)
		uint deadIndex;
		counterBuffer.InterlockedAdd(PARTICLECOUNTER_OFFSET_DEADCOUNT, 1, deadIndex);
		deadBuffer[deadIndex] = particleIndex;
	}

	// Write back simulated particle (ALWAYS, whether alive or dead, so color/life updates are visible)
	particleBuffer[particleIndex] = particle;
}
