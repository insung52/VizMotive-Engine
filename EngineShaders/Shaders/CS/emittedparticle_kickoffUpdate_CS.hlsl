#include "Globals.hlsli"
#include "../ShaderInterop_EmittedParticle.h"

// Kickoff update shader
// Prepares counters and indirect arguments for simulation

RWByteAddressBuffer counterBuffer : register(u0);
RWByteAddressBuffer indirectBuffers : register(u1);

[numthreads(1, 1, 1)]
void main(uint3 DTid : SV_DispatchThreadID)
{
	// Load alive count from after simulation (or emission)
	uint aliveCount = counterBuffer.Load(PARTICLECOUNTER_OFFSET_ALIVECOUNT_AFTERSIMULATION);
	int deadCount = counterBuffer.Load(PARTICLECOUNTER_OFFSET_DEADCOUNT);

	// Prepare dispatch arguments for simulation
	// Each thread group processes THREADCOUNT_SIMULATION particles
	uint dispatchX = (aliveCount + THREADCOUNT_SIMULATION - 1) / THREADCOUNT_SIMULATION;
	uint offset = ARGUMENTBUFFER_OFFSET_DISPATCHSIMULATION;
	indirectBuffers.Store(offset + 0, dispatchX);
	indirectBuffers.Store(offset + 4, 1);
	indirectBuffers.Store(offset + 8, 1);

	// Copy alive count after simulation to current alive count
	counterBuffer.Store(PARTICLECOUNTER_OFFSET_ALIVECOUNT, aliveCount);

	// Reset alive count after simulation for next frame
	counterBuffer.Store(PARTICLECOUNTER_OFFSET_ALIVECOUNT_AFTERSIMULATION, 0);

	// Clamp dead count to be non-negative
	counterBuffer.Store(PARTICLECOUNTER_OFFSET_DEADCOUNT, max(0, deadCount));

	// Reset culled count for frustum culling (will be used in rendering phase)
	counterBuffer.Store(PARTICLECOUNTER_OFFSET_CULLEDCOUNT, 0);

	// Reset cell allocator (SPH - not used yet)
	counterBuffer.Store(PARTICLECOUNTER_OFFSET_CELLALLOCATOR, 0);
}
