#include "GBackendMetal.h"

// TODO: Include Metal headers when building on macOS
// #import <Metal/Metal.h>
// #import <MetalKit/MetalKit.h>

namespace vz
{
    // TODO: Implement GraphicsDevice_Metal class
    // static std::unique_ptr<graphics::GraphicsDevice_Metal> graphicsDevice;

    bool Initialize(graphics::ValidationMode validationMode, graphics::GPUPreference preference)
    {
        // TODO: Create Metal device
        // graphicsDevice = std::make_unique<graphics::GraphicsDevice_Metal>();
        // return graphicsDevice->Initialize(validationMode, preference);

        return false; // Not implemented yet
    }

    graphics::GraphicsDevice* GetGraphicsDevice()
    {
        // TODO: Return Metal device
        // return graphicsDevice.get();

        return nullptr; // Not implemented yet
    }

    void Deinitialize()
    {
        // TODO: Cleanup Metal device
        // graphicsDevice.reset();
    }
}
