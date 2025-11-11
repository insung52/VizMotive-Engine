#include "Globals.hlsli"
#include "../ShaderInterop_EmittedParticle.h"

// Finish update shader
// Prepares draw arguments for particle rendering

ByteAddressBuffer counterBuffer : register(t0);
RWByteAddressBuffer indirectBuffers : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 DTid : SV_DispatchThreadID)
{
	// Load culled particle count (after frustum culling in simulate)
	// For now, we'll use alive count since we don't have culling yet
	uint particleCount = counterBuffer.Load(PARTICLECOUNTER_OFFSET_ALIVECOUNT_AFTERSIMULATION);

	// Create draw argument buffer for DrawIndexedInstancedIndirect
	// We'll draw 6 indices (2 triangles) per particle instance
	// Format: IndexCountPerInstance, InstanceCount, StartIndexLocation, BaseVertexLocation, StartInstanceLocation
	uint args[5];
	args[0] = 6;              // IndexCountPerInstance (quad = 2 triangles = 6 indices)
	args[1] = particleCount;  // InstanceCount
	args[2] = 0;              // StartIndexLocation
	args[3] = 0;              // BaseVertexLocation
	args[4] = 0;              // StartInstanceLocation

	// Write draw arguments (using individual Store calls since Store5 may not be available)
	uint offset = ARGUMENTBUFFER_OFFSET_DRAWPARTICLES;
	indirectBuffers.Store(offset + 0, args[0]);
	indirectBuffers.Store(offset + 4, args[1]);
	indirectBuffers.Store(offset + 8, args[2]);
	indirectBuffers.Store(offset + 12, args[3]);
	indirectBuffers.Store(offset + 16, args[4]);
}
