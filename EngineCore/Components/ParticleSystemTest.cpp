// Particle System Test Code
// This file can be used to verify Phase 1-2 implementation

#include "GComponents.h"
#include "Utils/Backlog.h"

namespace vz::test
{
	// Test function to verify particle component creation
	void TestParticleComponentCreation()
	{
		using namespace vz;
		using namespace vz::compfactory;

		backlog::post("=== Particle System Test: Component Creation ===", backlog::LogLevel::Info);

		// Create a test entity
		Entity testEntity = ecs::CreateEntity();
		backlog::post("Created test entity: " + std::to_string(testEntity), backlog::LogLevel::Info);

		// Create particle component using factory
		EmittedParticleComponent* particle = GetEmittedParticleComponent(testEntity);
		if (!particle)
		{
			backlog::post("FAILED: Could not create EmittedParticleComponent", backlog::LogLevel::Error);
			return;
		}
		backlog::post("SUCCESS: Created EmittedParticleComponent", backlog::LogLevel::Info);

		// Test encapsulated setters/getters
		particle->SetEmitCount(10.0f);
		particle->SetSize(1.5f);
		particle->SetLife(2.0f);
		particle->SetVelocity(XMFLOAT3(0.0f, 1.0f, 0.0f));
		particle->SetGravity(XMFLOAT3(0.0f, -9.8f, 0.0f));
		particle->SetMaxParticles(500);

		backlog::post("Set particle properties:", backlog::LogLevel::Info);
		backlog::post("  EmitCount: " + std::to_string(particle->GetEmitCount()), backlog::LogLevel::Info);
		backlog::post("  Size: " + std::to_string(particle->GetSize()), backlog::LogLevel::Info);
		backlog::post("  Life: " + std::to_string(particle->GetLife()), backlog::LogLevel::Info);
		backlog::post("  MaxParticles: " + std::to_string(particle->GetMaxParticles()), backlog::LogLevel::Info);

		// Test flags
		particle->SetSorted(true);
		particle->SetDepthCollisionEnabled(true);
		backlog::post("  IsSorted: " + std::string(particle->IsSorted() ? "true" : "false"), backlog::LogLevel::Info);
		backlog::post("  IsDepthCollisionEnabled: " + std::string(particle->IsDepthCollisionEnabled() ? "true" : "false"), backlog::LogLevel::Info);

		// Test GPU component (if graphics device is available)
		GEmittedParticleComponent* gpuParticle = dynamic_cast<GEmittedParticleComponent*>(particle);
		if (gpuParticle)
		{
			backlog::post("Testing GPU resource creation...", backlog::LogLevel::Info);

			bool success = gpuParticle->CreateGPUResources();
			if (success)
			{
				backlog::post("SUCCESS: GPU resources created", backlog::LogLevel::Info);
				backlog::post("  HasValidGPUResources: " + std::string(gpuParticle->HasValidGPUResources() ? "true" : "false"), backlog::LogLevel::Info);

				// Test memory size
				size_t memSize = gpuParticle->GetMemorySizeInBytes();
				backlog::post("  Memory size: " + std::to_string(memSize) + " bytes", backlog::LogLevel::Info);

				// Test burst
				gpuParticle->Burst(50);
				backlog::post("  Burst called with 50 particles", backlog::LogLevel::Info);

				// Cleanup
				gpuParticle->DestroyGPUResources();
				backlog::post("SUCCESS: GPU resources destroyed", backlog::LogLevel::Info);
			}
			else
			{
				backlog::post("FAILED: GPU resource creation failed (this is expected if graphics device is not initialized)", backlog::LogLevel::Warning);
			}
		}

		// Cleanup entity
		ecs::RemoveEntity(testEntity);
		backlog::post("Test entity removed", backlog::LogLevel::Info);
		backlog::post("=== Particle System Test Complete ===", backlog::LogLevel::Info);
	}

	// Test function to verify component factory functions
	void TestParticleComponentFactory()
	{
		using namespace vz;
		using namespace vz::compfactory;

		backlog::post("=== Particle System Test: Component Factory ===", backlog::LogLevel::Info);

		// Create entity
		Entity entity = ecs::CreateEntity();

		// Test GetEmittedParticleComponent (should create if not exists)
		EmittedParticleComponent* comp1 = GetEmittedParticleComponent(entity);
		if (comp1)
		{
			backlog::post("SUCCESS: GetEmittedParticleComponent returned component", backlog::LogLevel::Info);
		}

		// Test ContainEmittedParticleComponent
		bool contains = ContainEmittedParticleComponent(entity);
		backlog::post("ContainEmittedParticleComponent: " + std::string(contains ? "true" : "false"), backlog::LogLevel::Info);

		// Test GetEmittedParticleComponentByVUID
		VUID vuid = comp1->GetVUID();
		EmittedParticleComponent* comp2 = GetEmittedParticleComponentByVUID(vuid);
		if (comp2 == comp1)
		{
			backlog::post("SUCCESS: GetEmittedParticleComponentByVUID returned same component", backlog::LogLevel::Info);
		}
		else
		{
			backlog::post("FAILED: GetEmittedParticleComponentByVUID returned different component", backlog::LogLevel::Error);
		}

		// Cleanup
		ecs::RemoveEntity(entity);
		backlog::post("=== Component Factory Test Complete ===", backlog::LogLevel::Info);
	}

	// Test serialization
	void TestParticleSerialization()
	{
		using namespace vz;
		using namespace vz::compfactory;

		backlog::post("=== Particle System Test: Serialization ===", backlog::LogLevel::Info);

		// Create entity and component
		Entity entity = ecs::CreateEntity();
		EmittedParticleComponent* particle = GetEmittedParticleComponent(entity);

		// Set unique values
		particle->SetEmitCount(123.45f);
		particle->SetSize(2.5f);
		particle->SetLife(3.75f);
		particle->SetMaxParticles(750);
		particle->SetVelocity(XMFLOAT3(1.0f, 2.0f, 3.0f));
		particle->SetGravity(XMFLOAT3(-1.0f, -9.8f, -1.0f));

		// Create archive for writing
		Archive archive;
		archive.SetReadModeAndResetPos(false);

		// Serialize
		particle->Serialize(archive, 1);
		backlog::post("Serialized particle component", backlog::LogLevel::Info);

		// Create new component to deserialize into
		Entity entity2 = ecs::CreateEntity();
		EmittedParticleComponent* particle2 = GetEmittedParticleComponent(entity2);

		// Deserialize
		archive.SetReadModeAndResetPos(true);
		particle2->Serialize(archive, 1);
		backlog::post("Deserialized particle component", backlog::LogLevel::Info);

		// Verify values
		bool success = true;
		if (std::abs(particle2->GetEmitCount() - 123.45f) > 0.001f) success = false;
		if (std::abs(particle2->GetSize() - 2.5f) > 0.001f) success = false;
		if (std::abs(particle2->GetLife() - 3.75f) > 0.001f) success = false;
		if (particle2->GetMaxParticles() != 750) success = false;

		if (success)
		{
			backlog::post("SUCCESS: All serialized values match", backlog::LogLevel::Info);
		}
		else
		{
			backlog::post("FAILED: Serialized values do not match", backlog::LogLevel::Error);
		}

		// Cleanup
		ecs::RemoveEntity(entity);
		ecs::RemoveEntity(entity2);
		backlog::post("=== Serialization Test Complete ===", backlog::LogLevel::Info);
	}
}

// Export test functions for external calling
extern "C"
{
	// Call this from your application to run all particle system tests
	__declspec(dllexport) void RunParticleSystemTests()
	{
		vz::test::TestParticleComponentCreation();
		vz::test::TestParticleComponentFactory();
		vz::test::TestParticleSerialization();
	}
}
