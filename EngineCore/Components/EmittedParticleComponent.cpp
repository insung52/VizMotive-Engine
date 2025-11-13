#include "GComponents.h"
#include "Utils/Backlog.h"
#include "Common/Archive.h"
#include "../../EngineShaders/Shaders/ShaderInterop_EmittedParticle.h"

namespace vz
{
	// EmittedParticleComponent implementation

	void EmittedParticleComponent::Burst(int num)
	{
		// This will be implemented in GEmittedParticleComponent
		// Base implementation does nothing
	}

	void EmittedParticleComponent::Burst(int num, const XMFLOAT3& position)
	{
		// This will be implemented in GEmittedParticleComponent
		// Base implementation does nothing
	}

	void EmittedParticleComponent::Restart()
	{
		// This will be implemented in GEmittedParticleComponent
		// Base implementation does nothing
	}

	size_t EmittedParticleComponent::GetMemorySizeInBytes() const
	{
		size_t size = sizeof(EmittedParticleComponent);
		return size;
	}

	void EmittedParticleComponent::Serialize(vz::Archive& archive, const uint64_t version)
	{
		if (archive.IsReadMode())
		{
			archive >> flags_;
			archive >> (uint32_t&)shaderType_;
			archive >> meshID_;
			archive >> maxParticles_;
			archive >> emitCount_;
			archive >> size_;
			archive >> randomFactor_;
			archive >> normalFactor_;
			archive >> life_;
			archive >> randomLife_;
			archive >> scaleX_;
			archive >> scaleY_;
			archive >> rotation_;
			archive >> motionBlurAmount_;
			archive >> mass_;
			archive >> randomColor_;
			archive >> velocity_;
			archive >> gravity_;
			archive >> drag_;
			archive >> restitution_;
			archive >> fixedTimestep_;
			archive >> opacityCurvePeakStart_;
			archive >> opacityCurvePeakEnd_;
			archive >> framesX_;
			archive >> framesY_;
			archive >> frameCount_;
			archive >> frameStart_;
			archive >> frameRate_;
		}
		else
		{
			archive << flags_;
			archive << (uint32_t)shaderType_;
			archive << meshID_;
			archive << maxParticles_;
			archive << emitCount_;
			archive << size_;
			archive << randomFactor_;
			archive << normalFactor_;
			archive << life_;
			archive << randomLife_;
			archive << scaleX_;
			archive << scaleY_;
			archive << rotation_;
			archive << motionBlurAmount_;
			archive << mass_;
			archive << randomColor_;
			archive << velocity_;
			archive << gravity_;
			archive << drag_;
			archive << restitution_;
			archive << fixedTimestep_;
			archive << opacityCurvePeakStart_;
			archive << opacityCurvePeakEnd_;
			archive << framesX_;
			archive << framesY_;
			archive << frameCount_;
			archive << frameStart_;
			archive << frameRate_;
		}
	}

	// GEmittedParticleComponent implementation

	bool GEmittedParticleComponent::CreateGPUResources()
	{
		if (gpuResourcesCreated_)
		{
			return true; // Already created
		}

		const uint32_t maxCount = GetMaxParticles();
		if (maxCount == 0)
		{
			backlog::post("GEmittedParticleComponent::CreateGPUResources - maxParticles is 0", backlog::LogLevel::Warn);
			return false;
		}

		// Get graphics device
		graphics::GraphicsDevice* device = graphics::GetDevice();
		if (!device)
		{
			backlog::post("GEmittedParticleComponent::CreateGPUResources - Graphics device not available", backlog::LogLevel::Error);
			return false;
		}

		// Create particle buffer
		{
			graphics::GPUBufferDesc desc = {};
			desc.size = maxCount * sizeof(Particle); // Particle struct from ShaderInterop
			desc.bind_flags = graphics::BindFlag::SHADER_RESOURCE | graphics::BindFlag::UNORDERED_ACCESS;
			desc.misc_flags = graphics::ResourceMiscFlag::BUFFER_STRUCTURED;
			desc.stride = sizeof(Particle);
			desc.format = graphics::Format::UNKNOWN;

			// Initialize all particles with life = 0 (dead)
			std::vector<Particle> initParticles(maxCount);
			for (uint32_t i = 0; i < maxCount; ++i)
			{
				initParticles[i] = {}; // Zero-initialize
				initParticles[i].life = 0.0f;
				initParticles[i].maxLife = 0.0f;
			}

			bool success = device->CreateBuffer(&desc, initParticles.data(), &particleBuffer_);
			if (!success)
			{
				backlog::post("GEmittedParticleComponent::CreateGPUResources - Failed to create particle buffer", backlog::LogLevel::Error);
				return false;
			}
			device->SetName(&particleBuffer_, "EmittedParticle_ParticleBuffer");
		}

		// Create alive list buffers (double buffered)
		for (int i = 0; i < 2; ++i)
		{
			graphics::GPUBufferDesc desc = {};
			desc.size = maxCount * sizeof(uint32_t);
			desc.bind_flags = graphics::BindFlag::SHADER_RESOURCE | graphics::BindFlag::UNORDERED_ACCESS;
			desc.misc_flags = graphics::ResourceMiscFlag::BUFFER_RAW;

			bool success = device->CreateBuffer(&desc, nullptr, &aliveList_[i]);
			if (!success)
			{
				backlog::post("GEmittedParticleComponent::CreateGPUResources - Failed to create alive list buffer", backlog::LogLevel::Error);
				DestroyGPUResources();
				return false;
			}
			std::string name = std::string("EmittedParticle_AliveList_") + std::to_string(i);
			device->SetName(&aliveList_[i], name.c_str());
		}

		// Create dead list buffer
		{
			graphics::GPUBufferDesc desc = {};
			desc.size = maxCount * sizeof(uint32_t);
			desc.bind_flags = graphics::BindFlag::SHADER_RESOURCE | graphics::BindFlag::UNORDERED_ACCESS;
			desc.misc_flags = graphics::ResourceMiscFlag::BUFFER_RAW;

			// Initialize with all particle indices (all particles start as dead)
			std::vector<uint32_t> indices(maxCount);
			for (uint32_t i = 0; i < maxCount; ++i)
			{
				indices[i] = i;
			}

			bool success = device->CreateBuffer(&desc, indices.data(), &deadList_);
			if (!success)
			{
				backlog::post("GEmittedParticleComponent::CreateGPUResources - Failed to create dead list buffer", backlog::LogLevel::Error);
				DestroyGPUResources();
				return false;
			}
			device->SetName(&deadList_, "EmittedParticle_DeadList");
		}

		// Create counter buffer
		{
			graphics::GPUBufferDesc desc = {};
			desc.size = sizeof(ParticleCounters); // From ShaderInterop
			desc.bind_flags = graphics::BindFlag::SHADER_RESOURCE | graphics::BindFlag::UNORDERED_ACCESS;
			desc.misc_flags = graphics::ResourceMiscFlag::BUFFER_RAW;

			// Initialize counters
			ParticleCounters counters = {};
			counters.aliveCount = 0;
			counters.deadCount = maxCount;
			counters.realEmitCount = 0;
			counters.aliveCount_afterSimulation = 0;
			counters.culledCount = 0;
			counters.cellAllocator = 0;

			bool success = device->CreateBuffer(&desc, &counters, &counterBuffer_);
			if (!success)
			{
				backlog::post("GEmittedParticleComponent::CreateGPUResources - Failed to create counter buffer", backlog::LogLevel::Error);
				DestroyGPUResources();
				return false;
			}
			device->SetName(&counterBuffer_, "EmittedParticle_CounterBuffer");
		}

		// Create indirect argument buffers
		{
			// Need space for: DispatchEmit(3), DispatchSimulation(3), DrawInstanced(5) = 11 uint32s
			// But align properly for each command
			const uint32_t indirectArgsSize = 256; // Generous size with alignment

			graphics::GPUBufferDesc desc = {};
			desc.size = indirectArgsSize;
			desc.bind_flags = graphics::BindFlag::UNORDERED_ACCESS;
			desc.misc_flags = graphics::ResourceMiscFlag::BUFFER_RAW | graphics::ResourceMiscFlag::INDIRECT_ARGS;

			bool success = device->CreateBuffer(&desc, nullptr, &indirectBuffers_);
			if (!success)
			{
				backlog::post("GEmittedParticleComponent::CreateGPUResources - Failed to create indirect buffers", backlog::LogLevel::Error);
				DestroyGPUResources();
				return false;
			}
			device->SetName(&indirectBuffers_, "EmittedParticle_IndirectBuffers");
		}

		// Create constant buffer
		{
			graphics::GPUBufferDesc desc = {};
			desc.size = sizeof(EmittedParticleCB); // From ShaderInterop
			desc.bind_flags = graphics::BindFlag::CONSTANT_BUFFER;
			desc.usage = graphics::Usage::UPLOAD;

			bool success = device->CreateBuffer(&desc, nullptr, &constantBuffer_);
			if (!success)
			{
				backlog::post("GEmittedParticleComponent::CreateGPUResources - Failed to create constant buffer", backlog::LogLevel::Error);
				DestroyGPUResources();
				return false;
			}
			device->SetName(&constantBuffer_, "EmittedParticle_ConstantBuffer");
		}

		// Create distance buffer for sorting
		{
			graphics::GPUBufferDesc desc = {};
			desc.size = maxCount * sizeof(float);
			desc.bind_flags = graphics::BindFlag::SHADER_RESOURCE | graphics::BindFlag::UNORDERED_ACCESS;
			desc.misc_flags = graphics::ResourceMiscFlag::BUFFER_RAW;

			bool success = device->CreateBuffer(&desc, nullptr, &distanceBuffer_);
			if (!success)
			{
				backlog::post("GEmittedParticleComponent::CreateGPUResources - Failed to create distance buffer", backlog::LogLevel::Error);
				DestroyGPUResources();
				return false;
			}
			device->SetName(&distanceBuffer_, "EmittedParticle_DistanceBuffer");
		}

		// Opacity curve is now calculated in pixel shader using CB parameters
		// No need for opacity curve texture anymore

		gpuResourcesCreated_ = true;
		backlog::post("GEmittedParticleComponent::CreateGPUResources - Successfully created GPU resources for " + std::to_string(maxCount) + " particles", backlog::LogLevel::Info);
		return true;
	}

	GEmittedParticleComponent::~GEmittedParticleComponent()
	{
		// Wait for GPU to finish using resources before destruction
		graphics::GraphicsDevice* device = graphics::GetDevice();
		if (device && gpuResourcesCreated_)
		{
			device->WaitForGPU();
		}
		DestroyGPUResources();
	}

	void GEmittedParticleComponent::DestroyGPUResources()
	{
		particleBuffer_ = {};
		aliveList_[0] = {};
		aliveList_[1] = {};
		deadList_ = {};
		counterBuffer_ = {};
		indirectBuffers_ = {};
		constantBuffer_ = {};
		distanceBuffer_ = {};
		// opacityCurveTexture_ removed - no longer used

		gpuResourcesCreated_ = false;
	}

	void GEmittedParticleComponent::UpdateCPU(const TransformComponent& transform, float dt)
	{
		// Update world matrix
		worldMatrix = transform.GetWorldMatrix();

		// Update center position
		center = XMFLOAT3(worldMatrix._41, worldMatrix._42, worldMatrix._43);

		// Create GPU resources if not yet created
		if (!HasValidGPUResources())
		{
			CreateGPUResources();
		}

		// Accumulate delta time
		dt_ += dt;

		// Handle fixed timestep
		float timestep = GetFixedTimestep();
		if (timestep > 0.0f)
		{
			// Fixed timestep mode
			dt_ = timestep;
		}

		// Accumulate emission
		if (!IsPaused())
		{
			emit_ += GetEmitCount() * dt;
		}

		// Handle burst emission
		if (burst_ > 0)
		{
			emit_ += (float)burst_;
			burst_ = 0;
		}

		// Update activity tracking
		// This will be properly updated after GPU simulation
		// For now, assume active if emitting
		if (emit_ > 0.0f)
		{
			activeFrames_ = 1;
		}
	}

	void GEmittedParticleComponent::Burst(int num)
	{
		burst_ += num;
	}

	void GEmittedParticleComponent::Burst(int num, const XMFLOAT3& position)
	{
		// For now, just accumulate burst count
		// Full burst with position will be implemented in emit shader
		burst_ += num;

		// TODO: Store position for emission in emit shader
	}

	void GEmittedParticleComponent::Restart()
	{
		emit_ = 0.0f;
		burst_ = 0;
		dt_ = 0.0f;
		activeFrames_ = 0;

		// Reset GPU counters if resources exist
		if (gpuResourcesCreated_)
		{
			graphics::GraphicsDevice* device = graphics::GetDevice();
			if (device)
			{
				ParticleCounters counters = {};
				counters.aliveCount = 0;
				counters.deadCount = GetMaxParticles();
				counters.realEmitCount = 0;
				counters.aliveCount_afterSimulation = 0;
				counters.culledCount = 0;
				counters.cellAllocator = 0;

				// Update counter buffer
				// This should ideally be done on GPU timeline, but for restart we can do immediate update
				device->UpdateBuffer(&counterBuffer_, &counters, graphics::CommandList(), sizeof(ParticleCounters));
			}
		}
	}

	bool GEmittedParticleComponent::ResetResources(const std::string& resName)
	{
		// Particle systems don't typically load external resources
		// But we can handle texture resources if needed in the future
		return false;
	}
}
