//
// Bitonic Sort for Particle System
// Based on AMD's GPUSortLib (MIT License)
// Adapted for VizMotive Engine
//

#include "Globals.hlsli"
#include "../ShaderInterop_EmittedParticle.h"

#define SORT_SIZE 512
#define HALF_SIZE (SORT_SIZE/2)
#define ITERATIONS (HALF_SIZE > 1024 ? HALF_SIZE/1024 : 1)
#define NUM_THREADS (HALF_SIZE/ITERATIONS)

// Resources
ByteAddressBuffer counterBuffer : register(t0);
StructuredBuffer<float> distanceBuffer : register(t1);
RWStructuredBuffer<uint> aliveBuffer : register(u0);

// Shared memory for sorting
groupshared float2 g_LDS[SORT_SIZE];

[numthreads(NUM_THREADS, 1, 1)]
void main(
    uint3 Gid : SV_GroupID,
    uint3 DTid : SV_DispatchThreadID,
    uint3 GTid : SV_GroupThreadID,
    uint GI : SV_GroupIndex)
{
    // Load number of alive particles
    uint NumElements = counterBuffer.Load(PARTICLECOUNTER_OFFSET_ALIVECOUNT_AFTERSIMULATION);

    uint GlobalBaseIndex = (Gid.x * SORT_SIZE) + GTid.x;
    uint LocalBaseIndex = GI;

    uint numElementsInThreadGroup = min(SORT_SIZE, NumElements - (Gid.x * SORT_SIZE));

    // Load shared data (distance, particleIndex pairs)
    uint i;
    [unroll]
    for (i = 0; i < 2 * ITERATIONS; ++i)
    {
        if (GI + i * NUM_THREADS < numElementsInThreadGroup)
        {
            uint particleIndex = aliveBuffer[GlobalBaseIndex + i * NUM_THREADS];
            // Read distance using particleIndex, not alive buffer index!
            float dist = distanceBuffer[particleIndex];
            g_LDS[LocalBaseIndex + i * NUM_THREADS] = float2(dist, (float)particleIndex);
        }
    }
    GroupMemoryBarrierWithGroupSync();

    // Bitonic sort
    for (uint nMergeSize = 2; nMergeSize <= SORT_SIZE; nMergeSize = nMergeSize * 2)
    {
        for (uint nMergeSubSize = nMergeSize >> 1; nMergeSubSize > 0; nMergeSubSize = nMergeSubSize >> 1)
        {
            [unroll]
            for (i = 0; i < ITERATIONS; ++i)
            {
                int tmp_index = GI + NUM_THREADS * i;
                int index_low = tmp_index & (nMergeSubSize - 1);
                int index_high = 2 * (tmp_index - index_low);
                int index = index_high + index_low;

                uint nSwapElem = nMergeSubSize == nMergeSize >> 1 ?
                    index_high + (2 * nMergeSubSize - 1) - index_low :
                    index_high + nMergeSubSize + index_low;

                if (nSwapElem < numElementsInThreadGroup)
                {
                    float2 a = g_LDS[index];
                    float2 b = g_LDS[nSwapElem];

                    // Sort by distance (ascending, since we negated in simulate shader)
                    if (a.x > b.x)
                    {
                        g_LDS[index] = b;
                        g_LDS[nSwapElem] = a;
                    }
                }
                GroupMemoryBarrierWithGroupSync();
            }
        }
    }

    // Store sorted indices back to alive buffer
    [unroll]
    for (i = 0; i < 2 * ITERATIONS; ++i)
    {
        if (GI + i * NUM_THREADS < numElementsInThreadGroup)
        {
            aliveBuffer[GlobalBaseIndex + i * NUM_THREADS] = (uint)g_LDS[LocalBaseIndex + i * NUM_THREADS].y;
        }
    }
}

