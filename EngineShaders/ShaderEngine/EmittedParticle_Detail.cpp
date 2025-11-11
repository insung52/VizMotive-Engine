#include "RenderPath3D_Detail.h"
#include "../Shaders/ShaderInterop_EmittedParticle.h"

namespace vz::renderer
{
	// Particle system compute shaders and PSOs
	namespace particlesystem
	{
		// Compute shaders
		Shader emitCS;
		Shader simulateCS;
		Shader kickoffUpdateCS;
		Shader finishUpdateCS;

		// Render shaders
		Shader particleVS;
		Shader particlePS;

		// Pipeline State Objects
		PipelineState emitPSO;
		PipelineState simulatePSO;
		PipelineState kickoffUpdatePSO;
		PipelineState finishUpdatePSO;
		PipelineState particleRenderPSO;

		// Index buffer for quad (6 indices: 2 triangles)
		GPUBuffer particleIndexBuffer;

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

			// Load simulate compute shader
			{
				simulateCS = {};
				if (!shader::LoadShader(ShaderStage::CS, simulateCS, "emittedparticle_simulate_CS.hlsl"))
				{
					backlog::post("Failed to load emittedparticle_simulate_CS.hlsl", backlog::LogLevel::Error);
				}
			}

			// Load kickoff update compute shader
			{
				kickoffUpdateCS = {};
				if (!shader::LoadShader(ShaderStage::CS, kickoffUpdateCS, "emittedparticle_kickoffUpdate_CS.hlsl"))
				{
					backlog::post("Failed to load emittedparticle_kickoffUpdate_CS.hlsl", backlog::LogLevel::Error);
				}
			}

			// Load finish update compute shader
			{
				finishUpdateCS = {};
				if (!shader::LoadShader(ShaderStage::CS, finishUpdateCS, "emittedparticle_finishUpdate_CS.hlsl"))
				{
					backlog::post("Failed to load emittedparticle_finishUpdate_CS.hlsl", backlog::LogLevel::Error);
				}
			}

			// Note: In VizMotive, compute shaders don't need PSOs
			// They are bound directly with BindComputeShader()
			// These PSO variables are kept for consistency but not used

			// Load particle vertex shader
			{
				particleVS = {};
				if (!shader::LoadShader(ShaderStage::VS, particleVS, "emittedparticle_VS.hlsl"))
				{
					backlog::post("Failed to load emittedparticle_VS.hlsl", backlog::LogLevel::Error);
				}
			}

			// Load particle pixel shader
			{
				particlePS = {};
				if (!shader::LoadShader(ShaderStage::PS, particlePS, "emittedparticle_simple_PS.hlsl"))
				{
					backlog::post("Failed to load emittedparticle_simple_PS.hlsl", backlog::LogLevel::Error);
				}
			}

			// Create particle render PSO
			{
				// Create blend state for alpha blending
				static BlendState blendState;
				blendState.render_target[0].blend_enable = true;
				blendState.render_target[0].src_blend = Blend::SRC_ALPHA;
				blendState.render_target[0].dest_blend = Blend::INV_SRC_ALPHA;
				blendState.render_target[0].blend_op = BlendOp::ADD;
				blendState.render_target[0].src_blend_alpha = Blend::ONE;
				blendState.render_target[0].dest_blend_alpha = Blend::INV_SRC_ALPHA;
				blendState.render_target[0].blend_op_alpha = BlendOp::ADD;
				blendState.render_target[0].render_target_write_mask = ColorWrite::ENABLE_ALL;
				blendState.alpha_to_coverage_enable = false;
				blendState.independent_blend_enable = false;

				// Create depth state (read-only depth, no writes)
				static DepthStencilState depthState;
				depthState.depth_enable = true;
				depthState.depth_write_mask = DepthWriteMask::ZERO;
				depthState.depth_func = ComparisonFunc::GREATER;

				// Create rasterizer state (no culling for billboards)
				static RasterizerState rasterizerState;
				rasterizerState.fill_mode = FillMode::SOLID;
				rasterizerState.cull_mode = CullMode::NONE;
				rasterizerState.front_counter_clockwise = false;
				rasterizerState.depth_bias = 0;
				rasterizerState.depth_bias_clamp = 0;
				rasterizerState.slope_scaled_depth_bias = 0;
				rasterizerState.depth_clip_enable = true;
				rasterizerState.multisample_enable = false;
				rasterizerState.antialiased_line_enable = false;

				// Create pipeline state
				PipelineStateDesc desc = {};
				desc.vs = &particleVS;
				desc.ps = &particlePS;
				desc.bs = &blendState;
				desc.dss = &depthState;
				desc.rs = &rasterizerState;
				desc.pt = PrimitiveTopology::TRIANGLELIST;

				backlog::post("[PARTICLE INIT] Creating particle render PSO...", backlog::LogLevel::Info);
				backlog::post("[PARTICLE INIT] VS valid: " + std::to_string(particleVS.IsValid()) + ", PS valid: " + std::to_string(particlePS.IsValid()), backlog::LogLevel::Info);

				bool success = device->CreatePipelineState(&desc, &particleRenderPSO);
				if (!success)
				{
					backlog::post("Failed to create particle render PSO", backlog::LogLevel::Error);
				}
				else
				{
					backlog::post("[PARTICLE INIT] Particle render PSO created successfully, IsValid: " + std::to_string(particleRenderPSO.IsValid()), backlog::LogLevel::Info);
				}
			}

			// Create index buffer for quads (6 indices per quad: 2 triangles)
			{
				uint16_t indices[6] = { 0, 1, 2, 2, 1, 3 };
				GPUBufferDesc desc = {};
				desc.size = sizeof(indices);
				desc.bind_flags = BindFlag::INDEX_BUFFER;
				desc.format = Format::R16_UINT;

				bool success = device->CreateBuffer(&desc, indices, &particleIndexBuffer);
				if (!success)
				{
					backlog::post("Failed to create particle index buffer", backlog::LogLevel::Error);
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
		backlog::post("[PARTICLE UPDATE] === UpdateParticleSystem START === instance: " + std::to_string(instanceIndex), backlog::LogLevel::Info);

		// Initialize shaders if not already done
		if (!particlesystem::initialized)
		{
			backlog::post("[PARTICLE UPDATE] Initializing particle system shaders", backlog::LogLevel::Info);
			particlesystem::Initialize();
		}

		// Check if GPU resources are valid
		if (!emitter.HasValidGPUResources())
		{
			backlog::post("[PARTICLE UPDATE] GPU resources not valid, creating...", backlog::LogLevel::Info);
			// Try to create resources
			if (!emitter.CreateGPUResources())
			{
				backlog::post("[PARTICLE UPDATE] Failed to create GPU resources!", backlog::LogLevel::Error);
				return; // Failed to create resources
			}
		}

		device->EventBegin("ParticleSystem Update", cmd);
		auto prof_range = profiler::BeginRangeGPU("ParticleSystem", &cmd);

		// Kickoff update: prepare counters and indirect args
		{
			backlog::post("[PARTICLE UPDATE] Kickoff update shader", backlog::LogLevel::Info);
			device->EventBegin("Kickoff Update", cmd);

			const GPUResource* uavs[] = {
				&emitter.GetCounterBuffer(),
				&emitter.GetIndirectBuffers(),
			};
			device->BindUAVs(uavs, 0, arraysize(uavs), cmd);

			device->BindComputeShader(&particlesystem::kickoffUpdateCS, cmd);
			device->Dispatch(1, 1, 1, cmd);

			// Barrier to ensure kickoff is complete
			GPUBarrier barriers[] = {
				GPUBarrier::Memory(),
			};
			device->Barrier(barriers, arraysize(barriers), cmd);

			device->EventEnd(cmd);
		}

		// Emit new particles
		EmitParticles(emitter, instanceIndex, cmd);

		// Barrier between emit and simulate
		{
			GPUBarrier barriers[] = {
				GPUBarrier::Memory(),
			};
			device->Barrier(barriers, arraysize(barriers), cmd);
		}

		// Simulate particles
		SimulateParticles(emitter, instanceIndex, cmd);

		// Barrier after simulate
		{
			GPUBarrier barriers[] = {
				GPUBarrier::Memory(),
			};
			device->Barrier(barriers, arraysize(barriers), cmd);
		}

		// Finish update: prepare draw arguments
		{
			backlog::post("[PARTICLE UPDATE] Finish update shader", backlog::LogLevel::Info);
			device->EventBegin("Finish Update", cmd);

			const GPUResource* srvs[] = {
				&emitter.GetCounterBuffer(),
			};
			device->BindResources(srvs, 0, arraysize(srvs), cmd);

			const GPUResource* uavs[] = {
				&emitter.GetIndirectBuffers(),
			};
			device->BindUAVs(uavs, 0, arraysize(uavs), cmd);

			device->BindComputeShader(&particlesystem::finishUpdateCS, cmd);
			device->Dispatch(1, 1, 1, cmd);

			device->EventEnd(cmd);
		}

		// TODO: Sort particles (Phase 7)

		// Note: Counter readback would require async GPU->CPU copy which is complex
		// For now, we rely on indirect draw arguments being prepared correctly
		// If particles don't render, check:
		// 1. emit shader creates particles (aliveCount_afterSimulation > 0)
		// 2. finishUpdate prepares correct draw args
		// 3. DrawIndexedInstancedIndirect uses correct offset

		backlog::post("[PARTICLE UPDATE] === UpdateParticleSystem END ===", backlog::LogLevel::Info);
		device->EventEnd(cmd);
		profiler::EndRange(prof_range);
	}

	void GRenderPath3DDetails::EmitParticles(
		GEmittedParticleComponent& emitter,
		uint32_t instanceIndex,
		CommandList cmd
	)
	{
		// Note: In VizMotive, compute shaders are bound directly without PSO
		if (!particlesystem::emitCS.IsValid())
		{
			backlog::post("[PARTICLE EMIT] emitCS shader is not valid", backlog::LogLevel::Warn);
			return;
		}

		device->EventBegin("Emit Particles", cmd);

		// Process any pending burst emissions immediately
		backlog::post("[PARTICLE EMIT] Before ProcessPendingBurst, emit: " + std::to_string(emitter.GetPendingEmitCount()), backlog::LogLevel::Info);
		emitter.ProcessPendingBurst();
		backlog::post("[PARTICLE EMIT] After ProcessPendingBurst, emit: " + std::to_string(emitter.GetPendingEmitCount()), backlog::LogLevel::Info);

		// Calculate number of particles to emit this frame
		// This is accumulated in UpdateCPU
		float pendingEmit = emitter.GetPendingEmitCount();
		uint32_t emitCount = (uint32_t)pendingEmit;

		backlog::post("[PARTICLE EMIT] pendingEmit: " + std::to_string(pendingEmit) + ", emitCount: " + std::to_string(emitCount), backlog::LogLevel::Info);

		if (emitCount == 0)
		{
			backlog::post("[PARTICLE EMIT] emitCount is 0, skipping emission", backlog::LogLevel::Info);
			device->EventEnd(cmd);
			return;
		}

		// Clamp to max particles
		uint32_t originalEmitCount = emitCount;
		emitCount = std::min(emitCount, emitter.GetMaxParticles());

		if (originalEmitCount != emitCount)
		{
			backlog::post("[PARTICLE EMIT] Clamped emitCount from " + std::to_string(originalEmitCount) + " to " + std::to_string(emitCount), backlog::LogLevel::Info);
		}

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
			desc.usage = Usage::UPLOAD;

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

		uint32_t threadGroups = (emitCount + THREADCOUNT_EMISSION - 1) / THREADCOUNT_EMISSION;
		backlog::post("[PARTICLE EMIT] Dispatching emit shader: emitCount=" + std::to_string(emitCount) +
					  ", threadGroups=" + std::to_string(threadGroups) +
					  ", maxParticles=" + std::to_string(emitter.GetMaxParticles()), backlog::LogLevel::Info);
		device->Dispatch(threadGroups, 1, 1, cmd);

		// Reset emit counter, keeping the fractional part for next frame
		float remainingFraction = pendingEmit - (float)emitCount;
		emitter.ResetPendingEmitCount(remainingFraction);
		backlog::post("[PARTICLE EMIT] Reset emit count, remaining fraction: " + std::to_string(remainingFraction), backlog::LogLevel::Info);

		device->EventEnd(cmd);
	}

	void GRenderPath3DDetails::SimulateParticles(
		GEmittedParticleComponent& emitter,
		uint32_t instanceIndex,
		CommandList cmd
	)
	{
		// Note: In VizMotive, compute shaders are bound directly without PSO
		if (!particlesystem::simulateCS.IsValid())
		{
			backlog::post("[PARTICLE SIMULATE] simulateCS shader is not valid", backlog::LogLevel::Warn);
			return;
		}

		backlog::post("[PARTICLE SIMULATE] Starting simulation for instance " + std::to_string(instanceIndex), backlog::LogLevel::Info);
		device->EventBegin("Simulate Particles", cmd);

		// Update constant buffer (same as emit, but may need different values)
		{
			EmittedParticleCB cb = {};
			cb.xEmitterMaxParticleCount = emitter.GetMaxParticles();
			cb.xEmitterInstanceIndex = instanceIndex;
			cb.xEmitterMeshGeometryOffset = 0;
			cb.xEmitterMeshGeometryCount = 0;

			cb.xParticleSize = emitter.GetSize();
			cb.xParticleScaling = emitter.GetScaleX();
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
			&emitter.GetOpacityCurveTexture(), // t0: opacity curve texture
		};
		device->BindResources(srvs, 0, arraysize(srvs), cmd);

		const GPUResource* uavs[] = {
			&emitter.GetParticleBuffer(),           // u0: particle buffer
			&emitter.GetAliveList(0),               // u1: alive list CURRENT
			&emitter.GetAliveList(1),               // u2: alive list NEW
			&emitter.GetDeadList(),                 // u3: dead list
			&emitter.GetCounterBuffer(),            // u4: counter buffer
		};
		device->BindUAVs(uavs, 0, arraysize(uavs), cmd);

		// Dispatch compute shader using indirect args
		// Note: We prepared the dispatch args in kickoff update shader
		device->BindComputeShader(&particlesystem::simulateCS, cmd);

		// Dispatch indirectly based on alive count
		backlog::post("[PARTICLE SIMULATE] Dispatching simulate shader (indirect)", backlog::LogLevel::Info);
		device->DispatchIndirect(&emitter.GetIndirectBuffers(), ARGUMENTBUFFER_OFFSET_DISPATCHSIMULATION, cmd);

		device->EventEnd(cmd);
	}

	void GRenderPath3DDetails::DrawParticles(
		const GEmittedParticleComponent& emitter,
		CommandList cmd
	)
	{
		if (!particlesystem::particleRenderPSO.IsValid())
		{
			backlog::post("[PARTICLE DRAW] particleRenderPSO is not valid", backlog::LogLevel::Warn);
			return;
		}

		if (!emitter.HasValidGPUResources())
		{
			backlog::post("[PARTICLE DRAW] GPU resources are not valid", backlog::LogLevel::Warn);
			return;
		}

		backlog::post("[PARTICLE DRAW] Drawing particles (indirect)", backlog::LogLevel::Info);
		device->EventBegin("Draw Particles", cmd);

		// Bind resources
		// t0: opacity curve, t1: particle buffer, t2: alive list
		const GPUResource* srvs[] = {
			&emitter.GetOpacityCurveTexture(),      // t0: opacity curve
			&emitter.GetParticleBuffer(),            // t1: particle buffer
			&emitter.GetAliveList(1),                // t2: alive list (NEW - after simulation)
		};
		device->BindResources(srvs, 0, arraysize(srvs), cmd);

		// Bind index buffer
		device->BindIndexBuffer(&particlesystem::particleIndexBuffer, IndexBufferFormat::UINT16, 0, cmd);

		// Bind pipeline state
		device->BindPipelineState(&particlesystem::particleRenderPSO, cmd);

		backlog::post("[PARTICLE DRAW] Bound resources and PSO, issuing draw indirect", backlog::LogLevel::Info);

		// TEMP DEBUG: Draw maxParticles to see all potentially alive particles
		uint32_t maxParticles = emitter.GetMaxParticles();
		device->DrawIndexedInstanced(6, maxParticles, 0, 0, 0, cmd);
		backlog::post("[PARTICLE DRAW DEBUG] Drew " + std::to_string(maxParticles) + " particles directly (bypassing indirect)", backlog::LogLevel::Warn);

		// Draw using indirect args (prepared in finish update shader)
		//device->DrawIndexedInstancedIndirect(&emitter.GetIndirectBuffers(), ARGUMENTBUFFER_OFFSET_DRAWPARTICLES, cmd);

		device->EventEnd(cmd);
	}
}
