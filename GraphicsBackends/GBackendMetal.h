#pragma once

#include "GBackend/GBackendDevice.h"

#ifdef __APPLE__
    #define METAL_EXPORT __attribute__((visibility("default")))
#else
    #define METAL_EXPORT __declspec(dllexport)
#endif

namespace vz
{
    extern "C" METAL_EXPORT bool Initialize(graphics::ValidationMode validationMode, graphics::GPUPreference preference);
    extern "C" METAL_EXPORT graphics::GraphicsDevice* GetGraphicsDevice();
    extern "C" METAL_EXPORT void Deinitialize();
}
