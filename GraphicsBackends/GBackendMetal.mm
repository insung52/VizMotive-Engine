#include "GBackendMetal.h"
#include "GraphicsDevice_Metal.h"

#import <Foundation/Foundation.h>
#import <Metal/Metal.h>

namespace vz
{
    static std::unique_ptr<graphics::GraphicsDevice_Metal> graphicsDevice;

    bool Initialize(graphics::ValidationMode validationMode, graphics::GPUPreference preference)
    {
        if (graphicsDevice != nullptr)
        {
            return false; // Already initialized
        }

        graphicsDevice = std::make_unique<graphics::GraphicsDevice_Metal>();
        return graphicsDevice->Initialize(validationMode, preference);
    }

    graphics::GraphicsDevice* GetGraphicsDevice()
    {
        return graphicsDevice.get();
    }

    void Deinitialize()
    {
        graphicsDevice.reset();
    }
}
