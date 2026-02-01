// ShaderEngineMetal - Metal shader engine module for VizMotive Engine
// Phase 5B: Scene-based mesh rendering implementation

#include "ShaderEngineMetal.h"
#include "Components/Components.h"
#include "Components/GComponents.h"
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

    // Mesh shader source for Phase 5B - Scene-based rendering
    static const char* meshShaderSource = R"(
#include <metal_stdlib>
using namespace metal;

// Constant buffer structures (matching CPU-side)
struct CameraConstants {
    float4x4 viewProjection;
    float4x4 view;
    float4x4 projection;
    float3 cameraPosition;
    float padding;
};

struct InstanceConstants {
    float4x4 world;
    float4 color;
};

// Vertex input structure
struct VertexIn {
    float3 position [[attribute(0)]];
    float3 normal   [[attribute(1)]];
    float2 texcoord [[attribute(2)]];
};

// Vertex output / Fragment input
struct MeshVertexOut {
    float4 position [[position]];
    float3 worldPos;
    float3 normal;
    float2 texcoord;
    float4 color;
};

// Basic Mesh Vertex Shader
vertex MeshVertexOut mesh_vertex(
    VertexIn in [[stage_in]],
    constant CameraConstants& camera [[buffer(0)]],
    constant InstanceConstants& instance [[buffer(1)]])
{
    MeshVertexOut out;

    // Transform to world space
    float4 worldPos = instance.world * float4(in.position, 1.0);
    out.worldPos = worldPos.xyz;

    // Transform to clip space
    out.position = camera.viewProjection * worldPos;

    // Transform normal to world space (using upper 3x3 of world matrix)
    float3x3 normalMatrix = float3x3(
        instance.world[0].xyz,
        instance.world[1].xyz,
        instance.world[2].xyz
    );
    out.normal = normalize(normalMatrix * in.normal);

    out.texcoord = in.texcoord;
    out.color = instance.color;

    return out;
}

// Simple position-only vertex shader (for objects without full vertex data)
vertex MeshVertexOut mesh_vertex_simple(
    uint vid [[vertex_id]],
    constant float4* positions [[buffer(0)]],
    constant CameraConstants& camera [[buffer(1)]],
    constant InstanceConstants& instance [[buffer(2)]])
{
    MeshVertexOut out;

    float4 pos = positions[vid];
    float4 worldPos = instance.world * float4(pos.xyz, 1.0);
    out.worldPos = worldPos.xyz;
    out.position = camera.viewProjection * worldPos;
    out.normal = float3(0, 1, 0); // default up normal
    out.texcoord = float2(0, 0);
    out.color = instance.color;

    return out;
}

// Solid color fragment shader
fragment float4 mesh_fragment_solid(MeshVertexOut in [[stage_in]])
{
    return in.color;
}

// Simple lit fragment shader
fragment float4 mesh_fragment_lit(
    MeshVertexOut in [[stage_in]],
    constant CameraConstants& camera [[buffer(0)]])
{
    // Simple directional light from above-right
    float3 lightDir = normalize(float3(0.5, 1.0, 0.3));
    float3 normal = normalize(in.normal);

    // Diffuse lighting
    float NdotL = max(dot(normal, lightDir), 0.0);
    float ambient = 0.3;
    float diffuse = NdotL * 0.7;

    float3 finalColor = in.color.rgb * (ambient + diffuse);

    return float4(finalColor, in.color.a);
}

// Debug: Render normals as color
fragment float4 mesh_fragment_debug_normal(MeshVertexOut in [[stage_in]])
{
    float3 normal = normalize(in.normal);
    // Map normal from [-1,1] to [0,1] for visualization
    float3 color = normal * 0.5 + 0.5;
    return float4(color, 1.0);
}
)";

    // CPU-side constant buffer structures (must match GPU)
    struct alignas(16) CameraConstantsCPU {
        XMFLOAT4X4 viewProjection;
        XMFLOAT4X4 view;
        XMFLOAT4X4 projection;
        XMFLOAT3 cameraPosition;
        float padding;
    };

    struct alignas(16) InstanceConstantsCPU {
        XMFLOAT4X4 world;
        XMFLOAT4 color;
    };
#endif

    // GRenderPath3D implementation for Metal with scene-based mesh rendering
    class GRenderPath3DMetal : public GRenderPath3D
    {
    private:
#ifdef __APPLE__
        // Metal resources
        id<MTLDevice> mtlDevice = nil;
        id<MTLLibrary> simpleShaderLibrary = nil;
        id<MTLLibrary> meshShaderLibrary = nil;
        id<MTLRenderPipelineState> simplePSO = nil;
        id<MTLRenderPipelineState> meshSolidPSO = nil;
        id<MTLRenderPipelineState> meshLitPSO = nil;
        id<MTLBuffer> cameraConstantsBuffer = nil;
        id<MTLBuffer> instanceConstantsBuffer = nil;
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

            simpleShaderLibrary = [mtlDevice newLibraryWithSource:sourceString
                                                    options:compileOptions
                                                      error:&error];
            if (!simpleShaderLibrary)
            {
                NSString* errorMsg = [error localizedDescription];
                vz::backlog::post("[Metal] ERROR: Failed to compile shaders: " +
                                  std::string([errorMsg UTF8String]));
                initializationFailed = true;
                return;
            }

            vz::backlog::post("[Metal] Shader library compiled successfully");

            // Get shader functions
            id<MTLFunction> vertexFunction = [simpleShaderLibrary newFunctionWithName:@"simple_vertex"];
            id<MTLFunction> fragmentFunction = [simpleShaderLibrary newFunctionWithName:@"simple_fragment"];

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

            vz::backlog::post("[Metal] Simple triangle pipeline initialized successfully");

            // =====================================================
            // Phase 5B: Mesh Rendering Pipeline
            // =====================================================
            NSString* meshSourceString = [NSString stringWithUTF8String:meshShaderSource];
            meshShaderLibrary = [mtlDevice newLibraryWithSource:meshSourceString
                                                        options:compileOptions
                                                          error:&error];
            if (!meshShaderLibrary)
            {
                NSString* errorMsg = [error localizedDescription];
                vz::backlog::post("[Metal] ERROR: Failed to compile mesh shaders: " +
                                  std::string([errorMsg UTF8String]));
                initializationFailed = true;
                return;
            }
            vz::backlog::post("[Metal] Mesh shader library compiled successfully");

            // Get mesh shader functions
            id<MTLFunction> meshVertexFunc = [meshShaderLibrary newFunctionWithName:@"mesh_vertex_simple"];
            id<MTLFunction> meshFragmentSolid = [meshShaderLibrary newFunctionWithName:@"mesh_fragment_solid"];
            id<MTLFunction> meshFragmentLit = [meshShaderLibrary newFunctionWithName:@"mesh_fragment_lit"];

            if (!meshVertexFunc || !meshFragmentSolid || !meshFragmentLit)
            {
                vz::backlog::post("[Metal] ERROR: Failed to get mesh shader functions");
                initializationFailed = true;
                return;
            }

            // Create solid mesh pipeline
            MTLRenderPipelineDescriptor* meshSolidDesc = [[MTLRenderPipelineDescriptor alloc] init];
            meshSolidDesc.label = @"Mesh Solid Pipeline";
            meshSolidDesc.vertexFunction = meshVertexFunc;
            meshSolidDesc.fragmentFunction = meshFragmentSolid;
            meshSolidDesc.colorAttachments[0].pixelFormat = MTLPixelFormatBGRA8Unorm;
            meshSolidDesc.depthAttachmentPixelFormat = MTLPixelFormatDepth32Float;

            meshSolidPSO = [mtlDevice newRenderPipelineStateWithDescriptor:meshSolidDesc error:&error];
            if (!meshSolidPSO)
            {
                NSString* errorMsg = [error localizedDescription];
                vz::backlog::post("[Metal] ERROR: Failed to create mesh solid PSO: " +
                                  std::string([errorMsg UTF8String]));
                initializationFailed = true;
                return;
            }

            // Create lit mesh pipeline
            MTLRenderPipelineDescriptor* meshLitDesc = [[MTLRenderPipelineDescriptor alloc] init];
            meshLitDesc.label = @"Mesh Lit Pipeline";
            meshLitDesc.vertexFunction = meshVertexFunc;
            meshLitDesc.fragmentFunction = meshFragmentLit;
            meshLitDesc.colorAttachments[0].pixelFormat = MTLPixelFormatBGRA8Unorm;
            meshLitDesc.depthAttachmentPixelFormat = MTLPixelFormatDepth32Float;

            meshLitPSO = [mtlDevice newRenderPipelineStateWithDescriptor:meshLitDesc error:&error];
            if (!meshLitPSO)
            {
                NSString* errorMsg = [error localizedDescription];
                vz::backlog::post("[Metal] ERROR: Failed to create mesh lit PSO: " +
                                  std::string([errorMsg UTF8String]));
                initializationFailed = true;
                return;
            }

            // Create constant buffers
            cameraConstantsBuffer = [mtlDevice newBufferWithLength:sizeof(CameraConstantsCPU)
                                                           options:MTLResourceStorageModeShared];
            cameraConstantsBuffer.label = @"Camera Constants";

            instanceConstantsBuffer = [mtlDevice newBufferWithLength:sizeof(InstanceConstantsCPU)
                                                             options:MTLResourceStorageModeShared];
            instanceConstantsBuffer.label = @"Instance Constants";

            pipelinesInitialized = true;
            vz::backlog::post("[Metal] Mesh rendering pipelines initialized successfully");
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
            instanceConstantsBuffer = nil;
            cameraConstantsBuffer = nil;
            meshLitPSO = nil;
            meshSolidPSO = nil;
            simplePSO = nil;
            meshShaderLibrary = nil;
            simpleShaderLibrary = nil;
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

            // Get render encoder
            id<MTLRenderCommandEncoder> encoder = nil;
            if (pipelinesInitialized)
            {
                auto* metalDevice = dynamic_cast<graphics::GraphicsDevice_Metal*>(device);
                if (metalDevice)
                {
                    void* encoderPtr = metalDevice->GetRenderCommandEncoder(cmd);
                    if (encoderPtr)
                    {
                        encoder = (__bridge id<MTLRenderCommandEncoder>)encoderPtr;
                    }
                }
            }

            if (encoder && pipelinesInitialized)
            {
                // =====================================================
                // Phase 5B: Scene-based mesh rendering
                // =====================================================
                bool hasSceneContent = false;

                // Update camera constants if camera is available
                if (camera && cameraConstantsBuffer)
                {
                    CameraConstantsCPU* camData = (CameraConstantsCPU*)[cameraConstantsBuffer contents];
                    camData->viewProjection = camera->GetViewProjection();
                    camData->view = camera->GetView();
                    camData->projection = camera->GetProjection();
                    camData->cameraPosition = camera->GetWorldEye();
                    camData->padding = 0.0f;
                }

                // Render scene objects if scene is available
                if (scene && camera && meshLitPSO)
                {
                    const auto& renderables = scene->GetRenderableEntities();

                    for (Entity entity : renderables)
                    {
                        // Get renderable component
                        GRenderableComponent* renderable = static_cast<GRenderableComponent*>(
                            compfactory::GetRenderableComponent(entity));
                        if (!renderable || !renderable->transform || !renderable->geometry)
                            continue;

                        // Only render mesh renderables
                        if (renderable->GetRenderableType() != RenderableComponent::RenderableType::MESH_RENDERABLE)
                            continue;

                        hasSceneContent = true;

                        // Update instance constants
                        if (instanceConstantsBuffer)
                        {
                            InstanceConstantsCPU* instData = (InstanceConstantsCPU*)[instanceConstantsBuffer contents];
                            instData->world = renderable->transform->GetWorldMatrix();

                            // Get color from first material if available
                            if (!renderable->materials.empty() && renderable->materials[0])
                            {
                                XMFLOAT4 baseColor = renderable->materials[0]->GetBaseColor();
                                instData->color = baseColor;
                            }
                            else
                            {
                                instData->color = XMFLOAT4(0.7f, 0.7f, 0.7f, 1.0f); // Default gray
                            }
                        }

                        // Get geometry data
                        GGeometryComponent* geom = renderable->geometry;
                        size_t numParts = geom->GetNumParts();

                        for (size_t partIdx = 0; partIdx < numParts; ++partIdx)
                        {
                            auto* primBuffers = geom->GetGPrimBuffer(partIdx);
                            if (!primBuffers || !primBuffers->generalBuffer.IsValid())
                                continue;

                            // Set pipeline and constant buffers
                            [encoder setRenderPipelineState:meshLitPSO];

                            // Bind vertex buffer (positions)
                            // TODO: Access actual Metal buffer from GPUBuffer
                            // For now, skip actual geometry rendering

                            // Bind camera constants
                            [encoder setVertexBuffer:cameraConstantsBuffer offset:0 atIndex:1];
                            [encoder setFragmentBuffer:cameraConstantsBuffer offset:0 atIndex:0];

                            // Bind instance constants
                            [encoder setVertexBuffer:instanceConstantsBuffer offset:0 atIndex:2];

                            // TODO: Draw actual geometry when we can access the Metal buffers
                            // [encoder drawIndexedPrimitives:...];
                        }
                    }
                }

                // Fallback: Draw simple triangle if no scene content
                if (!hasSceneContent && simplePSO)
                {
                    [encoder setRenderPipelineState:simplePSO];
                    [encoder drawPrimitives:MTLPrimitiveTypeTriangle
                                vertexStart:0
                                vertexCount:3];
                }
            }
            else if (!encoder)
            {
                static bool warnedOnce = false;
                if (!warnedOnce)
                {
                    vz::backlog::post("[Metal] Warning: Could not access render encoder");
                    warnedOnce = true;
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
            instanceConstantsBuffer = nil;
            cameraConstantsBuffer = nil;
            meshLitPSO = nil;
            meshSolidPSO = nil;
            simplePSO = nil;
            meshShaderLibrary = nil;
            simpleShaderLibrary = nil;
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
