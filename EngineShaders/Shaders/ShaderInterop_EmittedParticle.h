#ifndef VZ_SHADERINTEROP_EMITTEDPARTICLE_H
#define VZ_SHADERINTEROP_EMITTEDPARTICLE_H
#include "ShaderInterop.h"
#include "ShaderInterop_Renderer.h"

// Single particle structure (GPU representation)
struct Particle
{
	float3 position;
	float mass;
	float3 force;
	uint rotation_rotationVelocity; // packed: uint16 rotation, uint16 rotationVelocity
	float3 velocity;
	float maxLife;
	float2 sizeBeginEnd;
	float life;
	uint color; // packed RGBA color
};

// Atomic counters for particle system state
struct ParticleCounters
{
	uint aliveCount;                    // Number of particles currently alive
	uint deadCount;                     // Number of dead particles available for reuse
	uint realEmitCount;                 // Actual number of particles emitted this frame
	uint aliveCount_afterSimulation;    // Alive count after simulation step
	uint culledCount;                   // Number of culled particles (for frustum culling)
	uint cellAllocator;                 // SPH grid cell allocator (advanced feature)
};

// Byte offsets for counter buffer access
static const uint PARTICLECOUNTER_OFFSET_ALIVECOUNT = 0;
static const uint PARTICLECOUNTER_OFFSET_DEADCOUNT = PARTICLECOUNTER_OFFSET_ALIVECOUNT + 4;
static const uint PARTICLECOUNTER_OFFSET_REALEMITCOUNT = PARTICLECOUNTER_OFFSET_DEADCOUNT + 4;
static const uint PARTICLECOUNTER_OFFSET_ALIVECOUNT_AFTERSIMULATION = PARTICLECOUNTER_OFFSET_REALEMITCOUNT + 4;
static const uint PARTICLECOUNTER_OFFSET_CULLEDCOUNT = PARTICLECOUNTER_OFFSET_ALIVECOUNT_AFTERSIMULATION + 4;
static const uint PARTICLECOUNTER_OFFSET_CELLALLOCATOR = PARTICLECOUNTER_OFFSET_CULLEDCOUNT + 4;

// Emitter option flags (shader-side)
static const uint EMITTER_OPTION_BIT_FRAME_BLENDING_ENABLED = 1 << 0;
// static const uint EMITTER_OPTION_BIT_SPH_ENABLED = 1 << 1;              // Advanced feature - excluded
// static const uint EMITTER_OPTION_BIT_MESH_SHADER_ENABLED = 1 << 2;      // Advanced feature - excluded
static const uint EMITTER_OPTION_BIT_COLLIDERS_DISABLED = 1 << 3;
// static const uint EMITTER_OPTION_BIT_USE_RAIN_BLOCKER = 1 << 4;         // Advanced feature - excluded
// static const uint EMITTER_OPTION_BIT_TAKE_COLOR_FROM_MESH = 1 << 5;     // Advanced feature - excluded

// Constant buffer for particle system parameters
CBUFFER(EmittedParticleCB, CBSLOT_OTHER_EMITTEDPARTICLE)
{
	uint		xEmitterMaxParticleCount;
	uint		xEmitterInstanceIndex;
	uint		xEmitterMeshGeometryOffset;     // For mesh-based emission (optional)
	uint		xEmitterMeshGeometryCount;      // For mesh-based emission (optional)

	float		xParticleSize;
	float		xParticleScaling;
	float		xParticleRotation;
	float		xParticleRandomFactor;

	float		xParticleNormalFactor;
	float		xParticleLifeSpan;
	float		xParticleLifeSpanRandomness;
	float		xParticleMass;

	float		xParticleMotionBlurAmount;
	float		xParticleRandomColorFactor;
	uint		xEmitterOptions;
	float		xEmitterFixedTimestep;          // Fixed timestep for simulation (or -1 for variable)

	uint2		xEmitterFramesXY;               // Sprite sheet dimensions
	uint		xEmitterFrameCount;             // Total frames in sprite sheet
	uint		xEmitterFrameStart;             // Starting frame

	float2		xEmitterTexMul;                 // Texture coordinate multiplier
	float		xEmitterFrameRate;              // Sprite animation frame rate
	uint		xEmitterLayerMask;              // Layer mask for rendering

	float3		xParticleGravity;               // Gravity force
	float		xEmitterRestitution;            // Bounce factor for collision

	float3		xParticleVelocity;              // Initial velocity
	float		xParticleDrag;                  // Drag coefficient

	// SPH fluid simulation parameters (advanced feature - commented out)
	/*
	float		xSPH_h;                         // smoothing radius
	float		xSPH_h_rcp;                     // 1.0f / smoothing radius
	float		xSPH_h2;                        // smoothing radius ^ 2
	float		xSPH_h3;                        // smoothing radius ^ 3

	float		xSPH_poly6_constant;            // precomputed Poly6 kernel constant term
	float		xSPH_spiky_constant;            // precomputed Spiky kernel function constant term
	float		xSPH_visc_constant;             // precomputed viscosity kernel function constant term
	float		xSPH_K;                         // pressure constant

	float		xSPH_e;                         // viscosity constant
	float		xSPH_p0;                        // reference density
	*/

	ShaderTransform xEmitterBaseMeshUnormRemap; // Transform for mesh-based emission
};

// Emit location for burst emission
struct EmitLocation
{
	ShaderTransform transform;
	uint count;
	uint color;
	int padding0;
	int padding1;
};

// Thread group sizes for compute shaders
static const uint THREADCOUNT_EMISSION = 256;
static const uint THREADCOUNT_SIMULATION = 256;

// Indirect argument buffer layout
// These offsets define where dispatch/draw arguments are stored in the indirect buffer
static const uint ARGUMENTBUFFER_OFFSET_DISPATCHEMIT = 0;
static const uint ARGUMENTBUFFER_OFFSET_DISPATCHSIMULATION = ARGUMENTBUFFER_OFFSET_DISPATCHEMIT + (3 * 4);
static const uint ARGUMENTBUFFER_OFFSET_DRAWPARTICLES = ARGUMENTBUFFER_OFFSET_DISPATCHSIMULATION + (3 * 4);

// SPH grid acceleration structure (advanced feature - commented out)
/*
#define SPH_USE_ACCELERATION_GRID
static const uint SPH_PARTITION_BUCKET_COUNT = 128 * 128 * 64;

inline uint SPH_GridHash(int3 cellIndex)
{
	const uint p1 = 73856093;
	const uint p2 = 19349663;
	const uint p3 = 83492791;
	int n = p1 * cellIndex.x ^ p2 * cellIndex.y ^ p3 * cellIndex.z;
	n %= SPH_PARTITION_BUCKET_COUNT;
	return n;
}

struct SPHGridCell
{
	uint count;
	uint offset;
};
*/

#endif // VZ_SHADERINTEROP_EMITTEDPARTICLE_H
