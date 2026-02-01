#pragma once
#include "GBackend/GBackendDevice.h"
#include "GBackend/GShaderInterface.h"

#ifdef _WIN32
#define METAL_EXPORT __declspec(dllexport)
#else
#define METAL_EXPORT __attribute__((visibility("default")))
#endif
#include <string>
#include <vector>

// Note: this header file will not be included as an interface

namespace vz
{
	using Entity = uint64_t;

	// ShaderEngineMetal.cpp
	extern "C" METAL_EXPORT bool Initialize(graphics::GraphicsDevice* device);
	extern "C" METAL_EXPORT bool LoadRenderer();
	extern "C" METAL_EXPORT bool ApplyConfiguration();
	extern "C" METAL_EXPORT void Deinitialize();

	// Renderer functions
	extern "C" METAL_EXPORT GScene* NewGScene(Scene* scene);
	extern "C" METAL_EXPORT GRenderPath3D* NewGRenderPath(graphics::SwapChain& swapChain, graphics::Texture& rtRenderFinal);

	extern "C" METAL_EXPORT void AddDeferredMIPGen(const graphics::Texture& texture, bool preserve_coverage);
	extern "C" METAL_EXPORT void AddDeferredBlockCompression(const graphics::Texture& texture_src, const graphics::Texture& texture_bc);
	extern "C" METAL_EXPORT void AddDeferredTextureCopy(const graphics::Texture& texture_src, const graphics::Texture& texture_dst, const bool mipGen);
	extern "C" METAL_EXPORT void AddDeferredBufferUpdate(const graphics::GPUBuffer& buffer, const void* data, const uint64_t size = ~0, const uint64_t offset = 0);
	extern "C" METAL_EXPORT void AddDeferredGeometryGPUBVHUpdate(const Entity entity);

	// ShaderLoader functions
	extern "C" METAL_EXPORT bool LoadShader(
		graphics::ShaderStage stage,
		graphics::Shader& shader,
		const std::string& filename,
		graphics::ShaderModel minshadermodel,
		const std::vector<std::string>& permutation_defines
	);
	extern "C" METAL_EXPORT bool LoadShaders();
}
