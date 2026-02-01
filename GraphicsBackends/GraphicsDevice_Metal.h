#pragma once

#include "GBackend/GBackendDevice.h"

#ifdef __APPLE__
#import <Metal/Metal.h>
#import <MetalKit/MetalKit.h>
#import <QuartzCore/CAMetalLayer.h>
#import <dispatch/dispatch.h>
#endif

#include <vector>
#include <mutex>
#include <deque>

namespace vz::graphics
{
#ifdef __APPLE__
    namespace metal_internal
    {
        static constexpr uint32_t BUFFERCOUNT = 2;
        static constexpr uint32_t MAX_COMMANDLISTS = 32;

        // Resource wrapper for MTLBuffer/MTLTexture
        struct Resource_Metal
        {
            id<MTLBuffer> buffer = nil;
            id<MTLTexture> texture = nil;
            void* mapped_data = nullptr;
            size_t mapped_size = 0;
        };

        // Texture-specific wrapper with format info
        struct Texture_Metal : public Resource_Metal
        {
            MTLPixelFormat pixelFormat = MTLPixelFormatInvalid;
            uint32_t width = 0;
            uint32_t height = 0;
            uint32_t depth = 0;
            uint32_t mipLevels = 1;
            uint32_t arraySize = 1;
        };

        // Sampler wrapper
        struct Sampler_Metal
        {
            id<MTLSamplerState> sampler = nil;
        };

        // Shader wrapper
        struct Shader_Metal
        {
            id<MTLLibrary> library = nil;
            id<MTLFunction> function = nil;
            ShaderStage stage = ShaderStage::Count;
            std::string entryPoint;
        };

        // Pipeline state wrapper
        struct PipelineState_Metal
        {
            id<MTLRenderPipelineState> renderPipeline = nil;
            id<MTLDepthStencilState> depthStencilState = nil;
            id<MTLComputePipelineState> computePipeline = nil;

            // Rasterizer state (applied at encoder level)
            MTLCullMode cullMode = MTLCullModeNone;
            MTLWinding frontFace = MTLWindingCounterClockwise;
            MTLTriangleFillMode fillMode = MTLTriangleFillModeFill;
            float depthBias = 0;
            float depthBiasClamp = 0;
            float slopeScaledDepthBias = 0;
            bool depthClipEnable = false;

            MTLPrimitiveType primitiveType = MTLPrimitiveTypeTriangle;
        };

        // SwapChain wrapper
        struct SwapChain_Metal
        {
            CAMetalLayer* metalLayer = nil;
            id<CAMetalDrawable> currentDrawable = nil;
            Texture backBuffer;
            SwapChainDesc desc;
            ColorSpace colorSpace = ColorSpace::SRGB;
        };

        // Command list state
        struct CommandList_Metal
        {
            id<MTLCommandBuffer> commandBuffer = nil;
            id<MTLRenderCommandEncoder> renderEncoder = nil;
            id<MTLComputeCommandEncoder> computeEncoder = nil;
            id<MTLBlitCommandEncoder> blitEncoder = nil;

            QUEUE_TYPE queueType = QUEUE_GRAPHICS;
            bool isInsideRenderPass = false;

            // Current render pass info
            RenderPassInfo renderPassInfo = {};

            // Bound state
            const PipelineState_Metal* boundPipeline = nullptr;

            // Index buffer state
            id<MTLBuffer> boundIndexBuffer = nil;
            MTLIndexType indexType = MTLIndexTypeUInt16;
            uint64_t indexBufferOffset = 0;

            // Viewport and scissor
            std::vector<MTLViewport> viewports;
            std::vector<MTLScissorRect> scissorRects;

            // Current drawable for presentation
            id<CAMetalDrawable> currentDrawable = nil;

            void Reset()
            {
                commandBuffer = nil;
                renderEncoder = nil;
                computeEncoder = nil;
                blitEncoder = nil;
                isInsideRenderPass = false;
                renderPassInfo = {};
                boundPipeline = nullptr;
                boundIndexBuffer = nil;
                indexBufferOffset = 0;
                viewports.clear();
                scissorRects.clear();
                currentDrawable = nil;
            }
        };

        // Deferred destruction handler
        struct AllocationHandler_Metal
        {
            std::mutex mutex;
            std::deque<std::pair<uint64_t, id<MTLBuffer>>> destroyedBuffers;
            std::deque<std::pair<uint64_t, id<MTLTexture>>> destroyedTextures;
            std::deque<std::pair<uint64_t, id<MTLSamplerState>>> destroyedSamplers;

            void DeferredDestroy(id<MTLBuffer> buffer, uint64_t frameCount)
            {
                std::lock_guard<std::mutex> lock(mutex);
                destroyedBuffers.push_back({frameCount, buffer});
            }

            void DeferredDestroy(id<MTLTexture> texture, uint64_t frameCount)
            {
                std::lock_guard<std::mutex> lock(mutex);
                destroyedTextures.push_back({frameCount, texture});
            }

            void DeferredDestroy(id<MTLSamplerState> sampler, uint64_t frameCount)
            {
                std::lock_guard<std::mutex> lock(mutex);
                destroyedSamplers.push_back({frameCount, sampler});
            }

            void Update(uint64_t completedFrame)
            {
                std::lock_guard<std::mutex> lock(mutex);
                while (!destroyedBuffers.empty() && destroyedBuffers.front().first <= completedFrame)
                {
                    destroyedBuffers.pop_front();
                }
                while (!destroyedTextures.empty() && destroyedTextures.front().first <= completedFrame)
                {
                    destroyedTextures.pop_front();
                }
                while (!destroyedSamplers.empty() && destroyedSamplers.front().first <= completedFrame)
                {
                    destroyedSamplers.pop_front();
                }
            }
        };

        // Helper to get internal state
        template<typename T>
        inline T* to_internal(const GraphicsDeviceChild* child)
        {
            return static_cast<T*>(child->internal_state.get());
        }
    }
#endif

    class GraphicsDevice_Metal : public GraphicsDevice
    {
    private:
#ifdef __APPLE__
        id<MTLDevice> device = nil;
        id<MTLCommandQueue> commandQueue = nil;

        // Frame synchronization
        dispatch_semaphore_t frameSemaphore = nullptr;
        uint64_t completedFrameCount = 0;

        // Command list pool
        mutable std::mutex cmdListMutex;
        mutable std::vector<metal_internal::CommandList_Metal> commandLists;
        mutable std::vector<CommandList> activeCommandLists;
        mutable uint32_t nextCommandListIndex = 0;

        // Allocation handler
        mutable metal_internal::AllocationHandler_Metal allocationHandler;

        // Frame allocators per command list
        mutable std::vector<GPULinearAllocator> frameAllocators;
#endif

    public:
        GraphicsDevice_Metal() = default;
        virtual ~GraphicsDevice_Metal();

        bool Initialize(ValidationMode validationMode, GPUPreference preference);

        // === Required Pure Virtual Methods ===

        bool CreateSwapChain(const SwapChainDesc* desc, vz::platform::window_type window, SwapChain* swapchain) const override;
        bool CreateBuffer2(const GPUBufferDesc* desc, const std::function<void(void* dest)>& init_callback, GPUBuffer* buffer, const GPUResource* alias = nullptr, uint64_t alias_offset = 0ull) const override;
        void UploadToBufferRegion(GPUBuffer* buffer, uint64_t offset, const void* data, uint64_t size) const;
        bool CreateTexture(const TextureDesc* desc, const SubresourceData* initial_data, Texture* texture, const GPUResource* alias = nullptr, uint64_t alias_offset = 0ull) const override;
        bool CreateShader(ShaderStage stage, const void* shadercode, size_t shadercode_size, Shader* shader) const override;
        bool CreateSampler(const SamplerDesc* desc, Sampler* sampler) const override;
        bool CreateQueryHeap(const GPUQueryHeapDesc* desc, GPUQueryHeap* queryheap) const override;
        bool CreatePipelineState(const PipelineStateDesc* desc, PipelineState* pso, const RenderPassInfo* renderpass_info = nullptr) const override;

        int CreateSubresource(Texture* texture, SubresourceType type, uint32_t firstSlice, uint32_t sliceCount, uint32_t firstMip, uint32_t mipCount, const Format* format_change = nullptr, const ImageAspect* aspect = nullptr, const Swizzle* swizzle = nullptr, float min_lod_clamp = 0) const override;
        int CreateSubresource(GPUBuffer* buffer, SubresourceType type, uint64_t offset, uint64_t size = ~0, const Format* format_change = nullptr, const uint32_t* structuredbuffer_stride_change = nullptr) const override;

        bool OpenSharedResource(const void* device2, const void* srvDescHeap2, const int descriptorIndex, const Texture* textureShared,
            uint64_t& gpuDesciptorHandlerPtr, GPUResource& sharedRes, void** backendResPtr) override;

        void DeleteSubresources(GPUResource* resource) override;

        int GetDescriptorIndex(const GPUResource* resource, SubresourceType type, int subresource = -1) const override;
        int GetDescriptorIndex(const Sampler* sampler) const override;

        CommandList BeginCommandList(QUEUE_TYPE queue = QUEUE_GRAPHICS) override;
        void SubmitCommandLists() override;
        void WaitForGPU() const override;
        void ClearPipelineStateCache() override;
        size_t GetActivePipelineCount() const override;

        ShaderFormat GetShaderFormat() const override;
        Texture GetBackBuffer(const SwapChain* swapchain) const override;
        ColorSpace GetSwapChainColorSpace(const SwapChain* swapchain) const override;
        bool IsSwapChainSupportsHDR(const SwapChain* swapchain) const override;
        uint64_t GetMinOffsetAlignment(const GPUBufferDesc* desc) const override;
        MemoryUsage GetMemoryUsage() const override;
        uint32_t GetMaxViewportCount() const override;

        // Command List functions
        void WaitCommandList(CommandList cmd, CommandList wait_for) override;
        void WaitQueue(CommandList cmd, QUEUE_TYPE wait_for) override;
        void RenderPassBegin(const SwapChain* swapchain, CommandList cmd) override;
        void RenderPassBegin(const RenderPassImage* images, uint32_t image_count, CommandList cmd, RenderPassFlags flags = RenderPassFlags::NONE) override;
        void RenderPassEnd(CommandList cmd) override;
        void BindScissorRects(uint32_t numRects, const Rect* rects, CommandList cmd) override;
        void BindViewports(uint32_t NumViewports, const Viewport* pViewports, CommandList cmd) override;
        void BindResource(const GPUResource* resource, uint32_t slot, CommandList cmd, int subresource = -1) override;
        void BindResources(const GPUResource* const* resources, uint32_t slot, uint32_t count, CommandList cmd) override;
        void BindUAV(const GPUResource* resource, uint32_t slot, CommandList cmd, int subresource = -1) override;
        void BindUAVs(const GPUResource* const* resources, uint32_t slot, uint32_t count, CommandList cmd) override;
        void BindSampler(const Sampler* sampler, uint32_t slot, CommandList cmd) override;
        void BindConstantBuffer(const GPUBuffer* buffer, uint32_t slot, CommandList cmd, uint64_t offset = 0ull) override;
        void BindVertexBuffers(const GPUBuffer* const* vertexBuffers, uint32_t slot, uint32_t count, const uint32_t* strides, const uint64_t* offsets, CommandList cmd) override;
        void BindIndexBuffer(const GPUBuffer* indexBuffer, const IndexBufferFormat format, uint64_t offset, CommandList cmd) override;
        void BindStencilRef(uint32_t value, CommandList cmd) override;
        void BindBlendFactor(float r, float g, float b, float a, CommandList cmd) override;
        void BindPipelineState(const PipelineState* pso, CommandList cmd) override;
        void BindComputeShader(const Shader* cs, CommandList cmd) override;
        void BindDepthBounds(float min_bounds, float max_bounds, CommandList cmd) override;
        void Draw(uint32_t vertexCount, uint32_t startVertexLocation, CommandList cmd) override;
        void DrawIndexed(uint32_t indexCount, uint32_t startIndexLocation, int32_t baseVertexLocation, CommandList cmd) override;
        void DrawInstanced(uint32_t vertexCount, uint32_t instanceCount, uint32_t startVertexLocation, uint32_t startInstanceLocation, CommandList cmd) override;
        void DrawIndexedInstanced(uint32_t indexCount, uint32_t instanceCount, uint32_t startIndexLocation, int32_t baseVertexLocation, uint32_t startInstanceLocation, CommandList cmd) override;
        void DrawInstancedIndirect(const GPUBuffer* args, uint64_t args_offset, CommandList cmd) override;
        void DrawIndexedInstancedIndirect(const GPUBuffer* args, uint64_t args_offset, CommandList cmd) override;
        void DrawInstancedIndirectCount(const GPUBuffer* args, uint64_t args_offset, const GPUBuffer* count, uint64_t count_offset, uint32_t max_count, CommandList cmd) override;
        void DrawIndexedInstancedIndirectCount(const GPUBuffer* args, uint64_t args_offset, const GPUBuffer* count, uint64_t count_offset, uint32_t max_count, CommandList cmd) override;
        void Dispatch(uint32_t threadGroupCountX, uint32_t threadGroupCountY, uint32_t threadGroupCountZ, CommandList cmd) override;
        void DispatchIndirect(const GPUBuffer* args, uint64_t args_offset, CommandList cmd) override;
        void CopyResource(const GPUResource* pDst, const GPUResource* pSrc, CommandList cmd) override;
        void CopyBuffer(const GPUBuffer* pDst, uint64_t dst_offset, const GPUBuffer* pSrc, uint64_t src_offset, uint64_t size, CommandList cmd) override;
        void CopyTexture(const Texture* dst, uint32_t dstX, uint32_t dstY, uint32_t dstZ, uint32_t dstMip, uint32_t dstSlice, const Texture* src, uint32_t srcMip, uint32_t srcSlice, CommandList cmd, const Box* srcbox = nullptr, ImageAspect dst_aspect = ImageAspect::COLOR, ImageAspect src_aspect = ImageAspect::COLOR) override;
        void QueryBegin(const GPUQueryHeap* heap, uint32_t index, CommandList cmd) override;
        void QueryEnd(const GPUQueryHeap* heap, uint32_t index, CommandList cmd) override;
        void QueryResolve(const GPUQueryHeap* heap, uint32_t index, uint32_t count, const GPUBuffer* dest, uint64_t dest_offset, CommandList cmd) override;
        void Barrier(const GPUBarrier* barriers, uint32_t numBarriers, CommandList cmd) override;
        void PushConstants(const void* data, uint32_t size, CommandList cmd, uint32_t offset = 0) override;
        void ClearUAV(const GPUResource* resource, uint32_t value, CommandList cmd) override;

        void EventBegin(const char* name, CommandList cmd) override;
        void EventEnd(CommandList cmd) override;
        void SetMarker(const char* name, CommandList cmd) override;

        RenderPassInfo GetRenderPassInfo(CommandList cmd) override;

        void Map(GPUResource* resource) override;
        void Unmap(GPUResource* resource) override;

        GPULinearAllocator& GetFrameAllocator(CommandList cmd) override;

        // Metal internal access helpers (for ShaderEngineMetal)
        void* GetMTLDevice() const { return (__bridge void*)device; }
        void* GetRenderCommandEncoder(CommandList cmd) const;
        void* GetCommandBuffer(CommandList cmd) const;
    };
}
