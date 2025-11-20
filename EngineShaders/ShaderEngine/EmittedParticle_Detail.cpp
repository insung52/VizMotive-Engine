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
		Shader sortCS;
		Shader kickoffUpdateCS;
		Shader finishUpdateCS;

		// Render shaders
		Shader particleVS;
		Shader particlePS;

		// Pipeline State Objects
		PipelineState emitPSO;
		PipelineState simulatePSO;
		PipelineState sortPSO;
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

			// Load sort compute shader
			{
				sortCS = {};
				if (!shader::LoadShader(ShaderStage::CS, sortCS, "emittedparticle_sort_CS.hlsl"))
				{
					backlog::post("Failed to load emittedparticle_sort_CS.hlsl", backlog::LogLevel::Error);
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
				// Note: Using GREATER_EQUAL to reduce z-fighting when particles overlap
				static DepthStencilState depthState;
				depthState.depth_enable = true;
				depthState.depth_write_mask = DepthWriteMask::ZERO;
				depthState.depth_func = ComparisonFunc::GREATER_EQUAL;

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


				bool success = device->CreatePipelineState(&desc, &particleRenderPSO);
				if (!success)
				{
					backlog::post("Failed to create particle render PSO", backlog::LogLevel::Error);
				}
			}

			// Create index buffer for quads (6 indices per quad: 2 triangles)
			// Only create once
			if (!initialized)
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
		}

		void Deinitialize()
		{
			if (!initialized)
				return;

			// Release shaders
			emitCS = {};
			simulateCS = {};
			sortCS = {};
			kickoffUpdateCS = {};
			finishUpdateCS = {};
			particleVS = {};
			particlePS = {};

			// Release PSOs
			emitPSO = {};
			simulatePSO = {};
			sortPSO = {};
			kickoffUpdatePSO = {};
			finishUpdatePSO = {};
			particleRenderPSO = {};

			// Release index buffer
			particleIndexBuffer = {};

			initialized = false;
		}
	}

	void GRenderPath3DDetails::UpdateParticleSystem(
		GEmittedParticleComponent& emitter,
		uint32_t instanceIndex,
		CommandList cmd
	)
	{
		// Initialize particle system shaders (only once)
		particlesystem::Initialize();

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

		// Emit new particles FIRST (before kickoff)
		EmitParticles(emitter, instanceIndex, cmd);

		// Barrier after emit
		{
			GPUBarrier barriers[] = {
				GPUBarrier::Memory(),
			};
			device->Barrier(barriers, arraysize(barriers), cmd);
		}

		// Kickoff update: prepare counters and indirect args AFTER emit
		{
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

		// Simulate particles
		SimulateParticles(emitter, instanceIndex, cmd);

		// Barrier after simulate
		{
			GPUBarrier barriers[] = {
				GPUBarrier::Memory(),
			};
			device->Barrier(barriers, arraysize(barriers), cmd);
		}

		// Sort particles (if enabled)
		SortParticles(emitter, cmd);

		// Barrier after sort (if sorting was performed)
		if (emitter.IsSorted())
		{
			GPUBarrier barriers[] = {
				GPUBarrier::Memory(),
			};
			device->Barrier(barriers, arraysize(barriers), cmd);
		}

		// Finish update: prepare draw arguments
		{
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

		// Note: Counter readback would require async GPU->CPU copy which is complex
		// For now, we rely on indirect draw arguments being prepared correctly
		// If particles don't render, check:
		// 1. emit shader creates particles (aliveCount_afterSimulation > 0)
		// 2. finishUpdate prepares correct draw args
		// 3. DrawIndexedInstancedIndirect uses correct offset

		// Swap buffer indices for next frame
		// This ensures that next frame's Emit writes to the buffer that Simulate didn't write to this frame
		// and next frame's Simulate reads from the buffer that contains updated particles
		emitter.SwapBuffers();

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
			return;
		}

		device->EventBegin("Emit Particles", cmd);

		// Process any pending burst emissions immediately
		emitter.ProcessPendingBurst();

		// Calculate number of particles to emit this frame
		// This is accumulated in UpdateCPU
		float pendingEmit = emitter.GetPendingEmitCount();
		uint32_t emitCount = (uint32_t)pendingEmit;

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

		// Update emit buffer (reuse existing buffer instead of creating new one each frame)
		GPUBuffer& emitBuffer = emitter.GetEmitBuffer();
		{
			// Transition to COPY_DEST before updating
			{
				GPUBarrier barriers[] = {
					GPUBarrier::Buffer(&emitBuffer, ResourceState::SHADER_RESOURCE, ResourceState::COPY_DST)
				};
				device->Barrier(barriers, 1, cmd);
			}

			// Upload emit location data
			device->UpdateBuffer(&emitBuffer, &emitLocation, cmd, sizeof(EmitLocation));

			// Transition to SHADER_RESOURCE for use in compute shader
			{
				GPUBarrier barriers[] = {
					GPUBarrier::Buffer(&emitBuffer, ResourceState::COPY_DST, ResourceState::SHADER_RESOURCE)
				};
				device->Barrier(barriers, 1, cmd);
			}
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
			cb.xParticleRandomPositionOffset = emitter.GetRandomPositionOffset();

			cb.xParticleNormalFactor = emitter.GetNormalFactor();
			cb.xParticleLifeSpan = emitter.GetLife();
			cb.xParticleLifeSpanRandomness = emitter.GetRandomLife();
			cb.xParticleMass = emitter.GetMass();

			cb.xParticleMotionBlurAmount = emitter.GetMotionBlurAmount();
			cb.xParticleRandomColorFactor = emitter.GetRandomColor();
			cb.xParticleRandomVelocity = emitter.GetRandomVelocity();
			cb.xParticleRandomSize = emitter.GetRandomSize();
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

			cb.xOpacityCurvePeakStart = emitter.GetOpacityCurvePeakStart();
			cb.xOpacityCurvePeakEnd = emitter.GetOpacityCurvePeakEnd();
			cb.xParticleRandomRotation = emitter.GetRandomRotation();
			cb.xParticleRandomRotationVelocity = emitter.GetRandomRotationVelocity();

			XMFLOAT4 baseColor = emitter.GetBaseColor();
			cb.xParticleBaseColor = float4(baseColor.x, baseColor.y, baseColor.z, baseColor.w);

			// DEBUG: Print CB values (including opacity curve - always print for debugging)
			static float prevOpacityStart = -1.0f;
			static float prevOpacityEnd = -1.0f;
			if (prevOpacityStart != cb.xOpacityCurvePeakStart || prevOpacityEnd != cb.xOpacityCurvePeakEnd)
			{
				backlog::post("[PARTICLE DEBUG] Opacity Curve: start=" + std::to_string(cb.xOpacityCurvePeakStart) +
							  ", end=" + std::to_string(cb.xOpacityCurvePeakEnd), backlog::LogLevel::Info);
				prevOpacityStart = cb.xOpacityCurvePeakStart;
				prevOpacityEnd = cb.xOpacityCurvePeakEnd;
			}

			static bool debugOnceCB = false;
			if (!debugOnceCB)
			{
				backlog::post("[PARTICLE DEBUG] CB Values:", backlog::LogLevel::Info);
				backlog::post("  Life: " + std::to_string(cb.xParticleLifeSpan), backlog::LogLevel::Info);
				backlog::post("  RandomLife: " + std::to_string(cb.xParticleLifeSpanRandomness), backlog::LogLevel::Info);
				backlog::post("  Mass: " + std::to_string(cb.xParticleMass), backlog::LogLevel::Info);
				backlog::post("  Velocity: (" + std::to_string(velocity.x) + ", " +
							  std::to_string(velocity.y) + ", " +
							  std::to_string(velocity.z) + ")", backlog::LogLevel::Info);
				backlog::post("  Gravity: (" + std::to_string(gravity.x) + ", " +
							  std::to_string(gravity.y) + ", " +
							  std::to_string(gravity.z) + ")", backlog::LogLevel::Info);
				backlog::post("  Drag: " + std::to_string(cb.xParticleDrag), backlog::LogLevel::Info);
				debugOnceCB = true;
			}

			// Bind constant buffer with dynamic data (UPLOAD buffers should use BindDynamicConstantBuffer)
			device->BindDynamicConstantBuffer(cb, CB_GETBINDSLOT(EmittedParticleCB), cmd);
		}

		// Bind resources
		const GPUResource* srvs[] = {
			&emitBuffer, // t0: emit buffer
		};
		device->BindResources(srvs, 0, arraysize(srvs), cmd);

		const GPUResource* uavs[] = {
			&emitter.GetParticleBuffer(),                        // u0: particle buffer
			&emitter.GetAliveList(0),                            // u1: alive list CURRENT (Emit writes here, always index 0)
			&emitter.GetDeadList(),                              // u2: dead list
			&emitter.GetCounterBuffer(),                         // u3: counter buffer
		};
		device->BindUAVs(uavs, 0, arraysize(uavs), cmd);

		// Dispatch compute shader
		device->BindComputeShader(&particlesystem::emitCS, cmd);

		uint32_t threadGroups = (emitCount + THREADCOUNT_EMISSION - 1) / THREADCOUNT_EMISSION;
		device->Dispatch(threadGroups, 1, 1, cmd);

		// Reset emit counter, keeping the fractional part for next frame
		float remainingFraction = pendingEmit - (float)emitCount;
		emitter.ResetPendingEmitCount(remainingFraction);

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
			backlog::post("[PARTICLE DEBUG] SimulateParticles: simulateCS is INVALID!", backlog::LogLevel::Error);
			return;
		}

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
			cb.xParticleRandomPositionOffset = emitter.GetRandomPositionOffset();

			cb.xParticleNormalFactor = emitter.GetNormalFactor();
			cb.xParticleLifeSpan = emitter.GetLife();
			cb.xParticleLifeSpanRandomness = emitter.GetRandomLife();
			cb.xParticleMass = emitter.GetMass();

			cb.xParticleMotionBlurAmount = emitter.GetMotionBlurAmount();
			cb.xParticleRandomColorFactor = emitter.GetRandomColor();
			cb.xParticleRandomVelocity = emitter.GetRandomVelocity();
			cb.xParticleRandomSize = emitter.GetRandomSize();
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

			cb.xOpacityCurvePeakStart = emitter.GetOpacityCurvePeakStart();
			cb.xOpacityCurvePeakEnd = emitter.GetOpacityCurvePeakEnd();
			cb.xParticleRandomRotation = emitter.GetRandomRotation();
			cb.xParticleRandomRotationVelocity = emitter.GetRandomRotationVelocity();

			XMFLOAT4 baseColor = emitter.GetBaseColor();
			cb.xParticleBaseColor = float4(baseColor.x, baseColor.y, baseColor.z, baseColor.w);

			// Bind constant buffer with dynamic data (UPLOAD buffers should use BindDynamicConstantBuffer)
			device->BindDynamicConstantBuffer(cb, CB_GETBINDSLOT(EmittedParticleCB), cmd);
		}

		// Bind UAVs (no SRVs needed - opacity calculated in shader using CB)
		const GPUResource* uavs[] = {
			&emitter.GetParticleBuffer(),                          // u0: particle buffer
			&emitter.GetAliveList(0),                              // u1: alive list CURRENT (read from, always index 0)
			&emitter.GetAliveList(1),                              // u2: alive list NEW (write to, always index 1)
			&emitter.GetDeadList(),                                // u3: dead list
			&emitter.GetCounterBuffer(),                           // u4: counter buffer
			&emitter.GetDistanceBuffer(),                          // u5: distance buffer (for sorting)
		};
		device->BindUAVs(uavs, 0, arraysize(uavs), cmd);

		// Dispatch compute shader using indirect args
		// Note: We prepared the dispatch args in kickoff update shader
		device->BindComputeShader(&particlesystem::simulateCS, cmd);

		// Dispatch indirectly based on alive count
		device->DispatchIndirect(&emitter.GetIndirectBuffers(), ARGUMENTBUFFER_OFFSET_DISPATCHSIMULATION, cmd);

		device->EventEnd(cmd);
	}

	void GRenderPath3DDetails::SortParticles(
		GEmittedParticleComponent& emitter,
		CommandList cmd
	)
	{
		// Skip sorting if not enabled
		if (!emitter.IsSorted())
		{
			return;
		}

		// Skip if sort shader is not valid
		if (!particlesystem::sortCS.IsValid())
		{
			return;
		}

		device->EventBegin("Sort Particles", cmd);

		// Bind resources for sorting
		// t0: counter buffer (to get alive count)
		// t1: distance buffer (read distances)
		const GPUResource* srvs[] = {
			&emitter.GetCounterBuffer(),        // t0: counter buffer
			&emitter.GetDistanceBuffer(),       // t1: distance buffer
		};
		device->BindResources(srvs, 0, arraysize(srvs), cmd);

		// u0: alive buffer (read and write sorted indices)
		const GPUResource* uavs[] = {
			&emitter.GetAliveList(1),           // u0: alive list NEW (read/write - contains particles after simulation)
		};
		device->BindUAVs(uavs, 0, arraysize(uavs), cmd);

		// Bind sort compute shader
		device->BindComputeShader(&particlesystem::sortCS, cmd);

		// Dispatch sort shader
		// Each thread group sorts 512 particles using bitonic sort
		// We need to dispatch enough thread groups to cover all alive particles
		const uint32_t SORT_SIZE = 512;
		uint32_t maxParticles = emitter.GetMaxParticles();
		uint32_t numThreadGroups = (maxParticles + SORT_SIZE - 1) / SORT_SIZE;

		device->Dispatch(numThreadGroups, 1, 1, cmd);

		device->EventEnd(cmd);
	}

	void GRenderPath3DDetails::DrawParticles(
		const GEmittedParticleComponent& emitter,
		CommandList cmd
	)
	{
		if (!particlesystem::particleRenderPSO.IsValid())
		{
			return;
		}

		if (!emitter.HasValidGPUResources())
		{
			return;
		}

		device->EventBegin("Draw Particles", cmd);

		// Bind pipeline state
		device->BindPipelineState(&particlesystem::particleRenderPSO, cmd);

		// Prepare constant buffer with current parameters (needed for opacity curve, base color, and motion blur in VS/PS)
		EmittedParticleCB cb;
		cb.xOpacityCurvePeakStart = emitter.GetOpacityCurvePeakStart();
		cb.xOpacityCurvePeakEnd = emitter.GetOpacityCurvePeakEnd();

		cb.xParticleMotionBlurAmount = emitter.GetMotionBlurAmount();

		// Get base color and emissive from material if available
		cb.xParticleBaseColor = float4(1.0f, 1.0f, 1.0f, 1.0f);  // Default white
		cb.xParticleEmissive = 0.0f;
		Entity materialID = emitter.GetMaterialID();
		if (materialID != INVALID_ENTITY)
		{
			MaterialComponent* material = compfactory::GetMaterialComponent(materialID);
			if (material)
			{
				XMFLOAT4 baseColor = material->GetBaseColor();
				cb.xParticleBaseColor = float4(baseColor.x, baseColor.y, baseColor.z, baseColor.w);
				cb.xParticleEmissive = material->GetEmissiveStrength();
			}
		}

		// Bind constant buffer dynamically
		device->BindDynamicConstantBuffer(cb, CB_GETBINDSLOT(EmittedParticleCB), cmd);

		// Bind resources
		// t0: particle buffer, t1: alive list
		const GPUResource* srvs[] = {
			&emitter.GetParticleBuffer(),                            // t0: particle buffer
			&emitter.GetAliveList(1),                                // t1: alive list NEW (Simulate wrote to this, always index 1)
		};
		device->BindResources(srvs, 0, arraysize(srvs), cmd);

		// Bind index buffer
		device->BindIndexBuffer(&particlesystem::particleIndexBuffer, IndexBufferFormat::UINT16, 0, cmd);

		// Draw using indirect args (prepared in finish update shader)
		device->DrawIndexedInstancedIndirect(&emitter.GetIndirectBuffers(), ARGUMENTBUFFER_OFFSET_DRAWPARTICLES, cmd);

		device->EventEnd(cmd);
	}
}
