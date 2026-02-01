// ShaderEngineMetal - Metal shader engine module for VizMotive Engine
// Phase 5A: Hardcoded triangle rendering implementation

#include "ShaderEngineMetal.h"
#include "Components/Components.h"
#include "Utils/Backlog.h"
#include "Common/Version.h"
#include "GBackend/GBackend.h"

// Include GraphicsDevice_Metal for helper function access
#include "GraphicsDevice_Metal.h"

#include <atomic>
#include <mutex>

using namespace vz::graphics;

// Provide definition for the pure virtual function to satisfy linker
// This is needed because GRenderPath3D has an inline implementation that calls this
namespace vz
{
    bool GRenderPath2D::Render2D(const float dt)
    {
        // Base implementation - should be overridden by derived classes
        return true;
    }
}

namespace vz::renderer_metal
{
    static GraphicsDevice* device = nullptr;
    static std::atomic<bool> initialized{ false };
    static std::mutex deferredResourceMutex;
    static Texture dummyTexture;

    // Deferred operations (stubs for now)
    static std::vector<std::pair<Texture, bool>> deferredMIPGens;
    static std::vector<std::pair<Texture, Texture>> deferredBCQueue;
    static std::vector<std::pair<Texture, Texture>> deferredTextureCopy;
    static std::vector<std::pair<GPUBuffer, std::pair<const void*, std::pair<uint64_t, uint64_t>>>> deferredBufferUpdate;
    static std::vector<uint64_t> deferredGeometryGPUBVHGens;

    bool Initialize()
    {
        if (initialized.load())
            return true;

        vz::backlog::post("[Metal] Renderer initializing...");

        // Metal-specific initialization would go here
        // For now, just mark as initialized

        initialized.store(true);
        vz::backlog::post("[Metal] Renderer initialized successfully");
        return true;
    }

    void Deinitialize()
    {
        if (!initialized.load())
            return;

        vz::backlog::post("[Metal] Renderer deinitializing...");

        // Cleanup deferred queues
        {
            std::lock_guard<std::mutex> lock(deferredResourceMutex);
            deferredMIPGens.clear();
            deferredBCQueue.clear();
            deferredTextureCopy.clear();
            deferredBufferUpdate.clear();
            deferredGeometryGPUBVHGens.clear();
        }

        initialized.store(false);
        vz::backlog::post("[Metal] Renderer deinitialized");
    }
}

// Minimal GScene implementation for Metal
namespace vz
{
    class GSceneMetal : public GScene
    {
    public:
        GSceneMetal(Scene* scene) : GScene(scene) {}
        virtual ~GSceneMetal() = default;

        bool Update(const float dt) override { return true; }
        bool Destroy() override { return true; }

        bool SetOptionEnabled(const std::string& optionName, const bool enabled) override { return true; }
        bool SetOptionValueArray(const std::string& optionName, const std::vector<float>& values) override { return true; }

        void Debug_AddLine(const XMFLOAT3 p0, const XMFLOAT3 p1, const XMFLOAT4 color0, const XMFLOAT4 color1, const bool depthTest) const override {}
        void Debug_AddPoint(const XMFLOAT3 p, const XMFLOAT4 color, const bool depthTest) const override {}
        void Debug_AddCircle(const XMFLOAT3 p, const float r, const XMFLOAT4 color, const bool depthTest) const override {}
    };

#ifdef __APPLE__
    // MSL shader source code embedded as string
    static const char* simpleShaderSource = R"(
#include <metal_stdlib>
using namespace metal;

struct VertexOut {
    float4 position [[position]];
    float3 color;
};

vertex VertexOut simple_vertex(uint vid [[vertex_id]]) {
    float2 positions[3] = {
        float2(-0.5, -0.5),
        float2( 0.5, -0.5),
        float2( 0.0,  0.5)
    };
    float3 colors[3] = {
        float3(1.0, 0.0, 0.0),
        float3(0.0, 1.0, 0.0),
        float3(0.0, 0.0, 1.0)
    };

    VertexOut out;
    out.position = float4(positions[vid], 0.0, 1.0);
    out.color = colors[vid];
    return out;
}

fragment float4 simple_fragment(VertexOut in [[stage_in]]) {
    return float4(in.color, 1.0);
}
)";
#endif

    // GRenderPath3D implementation for Metal with triangle rendering
    class GRenderPath3DMetal : public GRenderPath3D
    {
    private:
#ifdef __APPLE__
        // Metal resources for simple triangle rendering
        id<MTLDevice> mtlDevice = nil;
        id<MTLLibrary> shaderLibrary = nil;
        id<MTLRenderPipelineState> simplePSO = nil;
        bool pipelinesInitialized = false;
        bool initializationFailed = false;

        void InitializePipelines()
        {
            if (pipelinesInitialized || initializationFailed)
                return;

            vz::backlog::post("[Metal] Initializing simple triangle pipelines...");

            // Get MTLDevice from GraphicsDevice_Metal
            // We need to access the internal device - use dynamic cast or a helper method
            if (!device)
            {
                vz::backlog::post("[Metal] ERROR: No graphics device available");
                initializationFailed = true;
                return;
            }

            // Try to get the MTLDevice through GraphicsDevice_Metal's helper method
            // The helper method returns void* which we cast back to id<MTLDevice>
            void* devicePtr = nullptr;

            // Use dynamic_cast to check if we have a Metal device
            // First, try to access the MTLDevice through the device name check
            std::string adapterName = device->GetAdapterName();
            vz::backlog::post("[Metal] Device adapter: " + adapterName);

            // Create a new MTLDevice for our rendering (simple approach)
            // In production, we would share the device from GraphicsDevice_Metal
            mtlDevice = MTLCreateSystemDefaultDevice();
            if (!mtlDevice)
            {
                vz::backlog::post("[Metal] ERROR: Failed to create Metal device");
                initializationFailed = true;
                return;
            }

            // Compile shader from source
            NSError* error = nil;
            NSString* sourceString = [NSString stringWithUTF8String:simpleShaderSource];

            MTLCompileOptions* compileOptions = [[MTLCompileOptions alloc] init];
            compileOptions.languageVersion = MTLLanguageVersion2_4;

            shaderLibrary = [mtlDevice newLibraryWithSource:sourceString
                                                    options:compileOptions
                                                      error:&error];
            if (!shaderLibrary)
            {
                NSString* errorMsg = [error localizedDescription];
                vz::backlog::post("[Metal] ERROR: Failed to compile shaders: " +
                                  std::string([errorMsg UTF8String]));
                initializationFailed = true;
                return;
            }

            vz::backlog::post("[Metal] Shader library compiled successfully");

            // Get shader functions
            id<MTLFunction> vertexFunction = [shaderLibrary newFunctionWithName:@"simple_vertex"];
            id<MTLFunction> fragmentFunction = [shaderLibrary newFunctionWithName:@"simple_fragment"];

            if (!vertexFunction || !fragmentFunction)
            {
                vz::backlog::post("[Metal] ERROR: Failed to get shader functions");
                initializationFailed = true;
                return;
            }

            // Create render pipeline descriptor
            MTLRenderPipelineDescriptor* pipelineDesc = [[MTLRenderPipelineDescriptor alloc] init];
            pipelineDesc.label = @"Simple Triangle Pipeline";
            pipelineDesc.vertexFunction = vertexFunction;
            pipelineDesc.fragmentFunction = fragmentFunction;
            pipelineDesc.colorAttachments[0].pixelFormat = MTLPixelFormatBGRA8Unorm;

            // Create pipeline state
            simplePSO = [mtlDevice newRenderPipelineStateWithDescriptor:pipelineDesc
                                                                  error:&error];
            if (!simplePSO)
            {
                NSString* errorMsg = [error localizedDescription];
                vz::backlog::post("[Metal] ERROR: Failed to create pipeline state: " +
                                  std::string([errorMsg UTF8String]));
                initializationFailed = true;
                return;
            }

            pipelinesInitialized = true;
            vz::backlog::post("[Metal] Simple triangle pipeline initialized successfully");
        }
#endif

    public:
        GRenderPath3DMetal(SwapChain& swapChain, Texture& rtRenderFinal)
            : GRenderPath3D(swapChain, rtRenderFinal)
        {
            device = renderer_metal::device;
            vz::backlog::post("[Metal] GRenderPath3DMetal created");
        }

        virtual ~GRenderPath3DMetal()
        {
#ifdef __APPLE__
            simplePSO = nil;
            shaderLibrary = nil;
            mtlDevice = nil;
#endif
            vz::backlog::post("[Metal] GRenderPath3DMetal destroyed");
        }

        bool ResizeCanvas(uint32_t canvasWidth, uint32_t canvasHeight) override
        {
            canvasWidth_ = canvasWidth;
            canvasHeight_ = canvasHeight;
            return true;
        }

        bool Render2D(const float dt) override
        {
            // Stub implementation - 2D rendering not yet implemented
            return true;
        }

        bool Render(const float dt) override
        {
            if (!device)
                return false;

#ifdef __APPLE__
            // Initialize pipelines on first render
            if (!pipelinesInitialized && !initializationFailed)
            {
                InitializePipelines();
            }

            // Start command list and render pass
            CommandList cmd = device->BeginCommandList();
            device->RenderPassBegin(&swapChain_, cmd);

            // Set viewport
            Viewport vp;
            vp.width = (float)swapChain_.desc.width;
            vp.height = (float)swapChain_.desc.height;
            vp.min_depth = 0.0f;
            vp.max_depth = 1.0f;
            device->BindViewports(1, &vp, cmd);

            // If pipelines are ready, draw the triangle
            if (pipelinesInitialized && simplePSO)
            {
                // Get the render encoder from the device
                // We need to access the internal command encoder
                // For now, we'll use a workaround by accessing through the device's internal state

                // The GraphicsDevice_Metal stores CommandList_Metal which has renderEncoder
                // We added GetRenderCommandEncoder helper for this purpose
                void* encoderPtr = nullptr;

                // Try to get encoder through a known interface pattern
                // Since we can't directly cast, we'll rely on the device's Draw method
                // But the device's Draw expects a bound pipeline state...

                // Alternative approach: Use the device's native draw call
                // We need to bind our pipeline state first

                // Get the internal encoder - this requires accessing GraphicsDevice_Metal
                // through its helper method that we added
                auto* metalDevice = dynamic_cast<graphics::GraphicsDevice_Metal*>(device);
                if (metalDevice)
                {
                    encoderPtr = metalDevice->GetRenderCommandEncoder(cmd);
                }

                if (encoderPtr)
                {
                    id<MTLRenderCommandEncoder> encoder = (__bridge id<MTLRenderCommandEncoder>)encoderPtr;

                    // Set our pipeline state and draw
                    [encoder setRenderPipelineState:simplePSO];
                    [encoder drawPrimitives:MTLPrimitiveTypeTriangle
                                vertexStart:0
                                vertexCount:3];
                }
                else
                {
                    // Fallback: just log that we can't access encoder
                    static bool warnedOnce = false;
                    if (!warnedOnce)
                    {
                        vz::backlog::post("[Metal] Warning: Could not access render encoder for triangle drawing");
                        warnedOnce = true;
                    }
                }
            }

            device->RenderPassEnd(cmd);
            device->SubmitCommandLists();

            return true;
#else
            // Non-Apple fallback
            CommandList cmd = device->BeginCommandList();
            device->RenderPassBegin(&swapChain_, cmd);

            Viewport vp;
            vp.width = (float)swapChain_.desc.width;
            vp.height = (float)swapChain_.desc.height;
            vp.min_depth = 0.0f;
            vp.max_depth = 1.0f;
            device->BindViewports(1, &vp, cmd);

            device->RenderPassEnd(cmd);
            device->SubmitCommandLists();

            return true;
#endif
        }

        bool Destroy() override
        {
#ifdef __APPLE__
            simplePSO = nil;
            shaderLibrary = nil;
            mtlDevice = nil;
            pipelinesInitialized = false;
            initializationFailed = false;
#endif
            return true;
        }

        const Texture& GetLastProcessRT() const override
        {
            return renderer_metal::dummyTexture;
        }

        bool SetOptionEnabled(const std::string& optionName, const bool enabled) override { return true; }
        bool SetOptionValueArray(const std::string& optionName, const std::vector<float>& values) override { return true; }
    };
}

// Exported functions
namespace vz
{
    using namespace graphics;

    bool Initialize(GraphicsDevice* device)
    {
        std::string version = vz::GetComponentVersion();
        assert(version == vz::COMPONENT_INTERFACE_VERSION);

        renderer_metal::device = device;
        graphics::GetDevice() = device;

        std::string deviceName = device ? device->GetAdapterName() : "null";
        vz::backlog::post("[Metal] ShaderEngineMetal initialized with device: " + deviceName);

        return true;
    }

    bool LoadRenderer()
    {
        return renderer_metal::Initialize();
    }

    bool ApplyConfiguration()
    {
        // Configuration settings would be applied here
        return true;
    }

    void Deinitialize()
    {
        renderer_metal::Deinitialize();
        renderer_metal::device = nullptr;
    }

    GScene* NewGScene(Scene* scene)
    {
        return new GSceneMetal(scene);
    }

    GRenderPath3D* NewGRenderPath(SwapChain& swapChain, Texture& rtRenderFinal)
    {
        return new GRenderPath3DMetal(swapChain, rtRenderFinal);
    }

    void AddDeferredMIPGen(const Texture& texture, bool preserve_coverage)
    {
        std::lock_guard<std::mutex> lock(renderer_metal::deferredResourceMutex);
        for (auto& it : renderer_metal::deferredMIPGens)
        {
            if (it.first.internal_state.get() == texture.internal_state.get())
                return;
        }
        renderer_metal::deferredMIPGens.push_back(std::make_pair(texture, preserve_coverage));
    }

    void AddDeferredBlockCompression(const Texture& texture_src, const Texture& texture_bc)
    {
        std::lock_guard<std::mutex> lock(renderer_metal::deferredResourceMutex);
        for (auto& it : renderer_metal::deferredBCQueue)
        {
            if (it.first.internal_state.get() == texture_src.internal_state.get() &&
                it.second.internal_state.get() == texture_bc.internal_state.get())
                return;
        }
        renderer_metal::deferredBCQueue.push_back(std::make_pair(texture_src, texture_bc));
    }

    void AddDeferredTextureCopy(const Texture& texture_src, const Texture& texture_dst, const bool mipGen)
    {
        std::lock_guard<std::mutex> lock(renderer_metal::deferredResourceMutex);
        if (!texture_src.IsValid() || !texture_dst.IsValid())
            return;
        for (auto& it : renderer_metal::deferredTextureCopy)
        {
            if (it.first.internal_state.get() == texture_src.internal_state.get() &&
                it.second.internal_state.get() == texture_dst.internal_state.get())
                return;
        }
        renderer_metal::deferredTextureCopy.push_back(std::make_pair(texture_src, texture_dst));
    }

    void AddDeferredBufferUpdate(const GPUBuffer& buffer, const void* data, const uint64_t size, const uint64_t offset)
    {
        std::lock_guard<std::mutex> lock(renderer_metal::deferredResourceMutex);
        if (!buffer.IsValid() || data == nullptr)
            return;
        renderer_metal::deferredBufferUpdate.push_back(
            std::make_pair(buffer, std::make_pair(data, std::make_pair(size, offset))));
    }

    void AddDeferredGeometryGPUBVHUpdate(const Entity entity)
    {
        std::lock_guard<std::mutex> lock(renderer_metal::deferredResourceMutex);
        for (auto& it : renderer_metal::deferredGeometryGPUBVHGens)
        {
            if (it == entity)
                return;
        }
        renderer_metal::deferredGeometryGPUBVHGens.push_back(entity);
    }

    bool LoadShader(
        ShaderStage stage,
        Shader& shader,
        const std::string& filename,
        ShaderModel minshadermodel,
        const std::vector<std::string>& permutation_defines)
    {
        // For now, return true without actually loading shaders
        // Metal shader loading will be implemented in a future phase
        vz::backlog::post("[Metal] LoadShader called for: " + filename + " (stub)");
        return true;
    }

    bool LoadShaders()
    {
        vz::backlog::post("[Metal] LoadShaders called (stub - no shaders loaded)");
        // Return true to indicate success, even though no shaders are loaded yet
        // This allows the engine to initialize
        return true;
    }
}
