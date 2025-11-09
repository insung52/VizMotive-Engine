#include "RenderPath3D_Detail.h"
#include "../Shaders/ShaderInterop_EmittedParticle.h"

namespace vz::renderer
{
	// Particle system compute shaders and PSOs
	namespace particlesystem
	{
		// Compute shaders
		Shader emitCS;

		// Pipeline State Objects
		PipelineState emitPSO;

		bool initialized = false;

		void Initialize()
		{
			if (initialized)
				return;

			GraphicsDevice* device = GetDevice();

			// Load emit compute shader
			{
				emitCS = {};
				if (!shader::LoadShader(ShaderStage::CS, emitCS, "emittedparticle_emit_CS.hlsl"))
				{
					backlog::post("Failed to load emittedparticle_emit_CS.hlsl", backlog::LogLevel::Error);
				}
			}

			// Create emit PSO
			{
				PipelineStateDesc desc = {};
				desc.cs = &emitCS;
				bool success = device->CreatePipelineState(&desc, &emitPSO);
				if (!success)
				{
					backlog::post("Failed to create emit PSO", backlog::LogLevel::Error);
				}
			}

			initialized = true;
			backlog::post("Particle system shaders initialized", backlog::LogLevel::Info);
		}
	}

	void GRenderPath3DDetails::UpdateParticleSystem(
		GEmittedParticleComponent& emitter,
		uint32_t instanceIndex,
		CommandList cmd
	)
	{
		// Initialize shaders if not already done
		if (!particlesystem::initialized)
		{
			particlesystem::Initialize();
		}

		// Check if GPU resources are valid
		if (!emitter.HasValidGPUResources())
		{
			// Try to create resources
			if (!emitter.CreateGPUResources())
			{
				return; // Failed to create resources
			}
		}

		device->EventBegin("ParticleSystem Update", cmd);
		auto prof_range = profiler::BeginRangeGPU("ParticleSystem", &cmd);

		// Emit new particles
		EmitParticles(emitter, instanceIndex, cmd);

		// TODO: Simulate particles (Phase 4)
		// TODO: Sort particles (Phase 7)

		device->EventEnd(cmd);
		profiler::EndRange(prof_range);
	}

	void GRenderPath3DDetails::EmitParticles(
		GEmittedParticleComponent& emitter,
		uint32_t instanceIndex,
		CommandList cmd
	)
	{
		if (!particlesystem::emitPSO.IsValid())
			return;

		device->EventBegin("Emit Particles", cmd);

		// Calculate number of particles to emit this frame
		// This is accumulated in UpdateCPU
		uint32_t emitCount = (uint32_t)emitter.GetEmitCount();
		if (emitCount == 0)
		{
			device->EventEnd(cmd);
			return;
		}

		// Clamp to max particles
		emitCount = std::min(emitCount, emitter.GetMaxParticles());

		// Create emit location structure
		EmitLocation emitLocation = {};

		// Set transform
		XMFLOAT4X4 worldMatrix = emitter.worldMatrix;
		emitLocation.transform.Create(worldMatrix);

		// Set emit count and color
		emitLocation.count = emitCount;
		emitLocation.color = 0xFFFFFFFF; // White color (will use material color later)

		// Create emit buffer (upload data)
		GPUBuffer emitBuffer;
		{
			GPUBufferDesc desc = {};
			desc.size = sizeof(EmitLocation);
			desc.bind_flags = BindFlag::SHADER_RESOURCE;
			desc.misc_flags = ResourceMiscFlag::BUFFER_STRUCTURED;
			desc.stride = sizeof(EmitLocation);
			desc.usage = Usage::DYNAMIC;
			desc.cpu_access_flags = CPUAccessFlags::CPU_ACCESS_WRITE;

			bool success = device->CreateBuffer(&desc, nullptr, &emitBuffer);
			if (!success)
			{
				backlog::post("Failed to create emit buffer", backlog::LogLevel::Error);
				device->EventEnd(cmd);
				return;
			}

			// Upload emit location data
			device->UpdateBuffer(&emitBuffer, &emitLocation, cmd, sizeof(EmitLocation));
		}

		// Update constant buffer
		{
			EmittedParticleCB cb = {};
			cb.xEmitterMaxParticleCount = emitter.GetMaxParticles();
			cb.xEmitterInstanceIndex = instanceIndex;
			cb.xEmitterMeshGeometryOffset = 0;
			cb.xEmitterMeshGeometryCount = 0;

			cb.xParticleSize = emitter.GetSize();
			cb.xParticleScaling = emitter.GetScaleX(); // Use ScaleX as overall scaling
			cb.xParticleRotation = emitter.GetRotation();
			cb.xParticleRandomFactor = emitter.GetRandomFactor();

			cb.xParticleNormalFactor = emitter.GetNormalFactor();
			cb.xParticleLifeSpan = emitter.GetLife();
			cb.xParticleLifeSpanRandomness = emitter.GetRandomLife();
			cb.xParticleMass = emitter.GetMass();

			cb.xParticleMotionBlurAmount = emitter.GetMotionBlurAmount();
			cb.xParticleRandomColorFactor = emitter.GetRandomColor();
			cb.xEmitterOptions = 0;
			if (emitter.IsFrameBlendingEnabled())
				cb.xEmitterOptions |= EMITTER_OPTION_BIT_FRAME_BLENDING_ENABLED;
			if (emitter.IsCollidersDisabled())
				cb.xEmitterOptions |= EMITTER_OPTION_BIT_COLLIDERS_DISABLED;
			cb.xEmitterFixedTimestep = emitter.GetFixedTimestep();

			cb.xEmitterFramesXY = uint2(emitter.GetFramesX(), emitter.GetFramesY());
			cb.xEmitterFrameCount = emitter.GetFrameCount();
			cb.xEmitterFrameStart = emitter.GetFrameStart();

			cb.xEmitterTexMul = float2(1.0f / (float)emitter.GetFramesX(), 1.0f / (float)emitter.GetFramesY());
			cb.xEmitterFrameRate = emitter.GetFrameRate();
			cb.xEmitterLayerMask = emitter.layerMask;

			XMFLOAT3 gravity = emitter.GetGravity();
			cb.xParticleGravity = float3(gravity.x, gravity.y, gravity.z);
			cb.xEmitterRestitution = emitter.GetRestitution();

			XMFLOAT3 velocity = emitter.GetVelocity();
			cb.xParticleVelocity = float3(velocity.x, velocity.y, velocity.z);
			cb.xParticleDrag = emitter.GetDrag();

			// Update the constant buffer
			device->UpdateBuffer(&emitter.GetConstantBuffer(), &cb, cmd, sizeof(EmittedParticleCB));
		}

		// Bind constant buffer
		device->BindConstantBuffer(&emitter.GetConstantBuffer(), CB_GETBINDSLOT(EmittedParticleCB), cmd);

		// Bind resources
		const GPUResource* srvs[] = {
			&emitBuffer, // t0: emit buffer
		};
		device->BindResources(srvs, 0, arraysize(srvs), cmd);

		const GPUResource* uavs[] = {
			&emitter.GetParticleBuffer(),           // u0: particle buffer
			&emitter.GetAliveList(1),               // u1: alive list NEW
			&emitter.GetDeadList(),                 // u2: dead list
			&emitter.GetCounterBuffer(),            // u3: counter buffer
		};
		device->BindUAVs(uavs, 0, arraysize(uavs), cmd);

		// Dispatch compute shader
		device->BindComputeShader(&particlesystem::emitCS, cmd);
		device->BindPipelineState(&particlesystem::emitPSO, cmd);

		uint32_t threadGroups = (emitCount + THREADCOUNT_EMISSION - 1) / THREADCOUNT_EMISSION;
		device->Dispatch(threadGroups, 1, 1, cmd);

		// Unbind resources
		device->UnbindUAVs(0, arraysize(uavs), cmd);
		device->UnbindResources(0, arraysize(srvs), cmd);

		device->EventEnd(cmd);
	}
}
