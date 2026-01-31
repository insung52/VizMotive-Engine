#include "GraphicsDevice_Metal.h"
#include "SpirvToMsl.h"

#ifdef __APPLE__
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <MetalKit/MetalKit.h>
#import <AppKit/AppKit.h>
#endif

#include <cassert>

namespace vz::graphics
{
#ifdef __APPLE__
    using namespace metal_internal;

    // ============================================
    // Format Conversion Utilities
    // ============================================

    inline MTLPixelFormat _ConvertFormat(Format format)
    {
        switch (format)
        {
        case Format::UNKNOWN:                   return MTLPixelFormatInvalid;
        case Format::R32G32B32A32_FLOAT:        return MTLPixelFormatRGBA32Float;
        case Format::R32G32B32A32_UINT:         return MTLPixelFormatRGBA32Uint;
        case Format::R32G32B32A32_SINT:         return MTLPixelFormatRGBA32Sint;
        case Format::R16G16B16A16_FLOAT:        return MTLPixelFormatRGBA16Float;
        case Format::R16G16B16A16_UNORM:        return MTLPixelFormatRGBA16Unorm;
        case Format::R16G16B16A16_UINT:         return MTLPixelFormatRGBA16Uint;
        case Format::R16G16B16A16_SNORM:        return MTLPixelFormatRGBA16Snorm;
        case Format::R16G16B16A16_SINT:         return MTLPixelFormatRGBA16Sint;
        case Format::R32G32_FLOAT:              return MTLPixelFormatRG32Float;
        case Format::R32G32_UINT:               return MTLPixelFormatRG32Uint;
        case Format::R32G32_SINT:               return MTLPixelFormatRG32Sint;
        case Format::D32_FLOAT_S8X24_UINT:      return MTLPixelFormatDepth32Float_Stencil8;
        case Format::R10G10B10A2_UNORM:         return MTLPixelFormatRGB10A2Unorm;
        case Format::R10G10B10A2_UINT:          return MTLPixelFormatRGB10A2Uint;
        case Format::R11G11B10_FLOAT:           return MTLPixelFormatRG11B10Float;
        case Format::R8G8B8A8_UNORM:            return MTLPixelFormatRGBA8Unorm;
        case Format::R8G8B8A8_UNORM_SRGB:       return MTLPixelFormatRGBA8Unorm_sRGB;
        case Format::R8G8B8A8_UINT:             return MTLPixelFormatRGBA8Uint;
        case Format::R8G8B8A8_SNORM:            return MTLPixelFormatRGBA8Snorm;
        case Format::R8G8B8A8_SINT:             return MTLPixelFormatRGBA8Sint;
        case Format::B8G8R8A8_UNORM:            return MTLPixelFormatBGRA8Unorm;
        case Format::B8G8R8A8_UNORM_SRGB:       return MTLPixelFormatBGRA8Unorm_sRGB;
        case Format::R16G16_FLOAT:              return MTLPixelFormatRG16Float;
        case Format::R16G16_UNORM:              return MTLPixelFormatRG16Unorm;
        case Format::R16G16_UINT:               return MTLPixelFormatRG16Uint;
        case Format::R16G16_SNORM:              return MTLPixelFormatRG16Snorm;
        case Format::R16G16_SINT:               return MTLPixelFormatRG16Sint;
        case Format::D32_FLOAT:                 return MTLPixelFormatDepth32Float;
        case Format::R32_FLOAT:                 return MTLPixelFormatR32Float;
        case Format::R32_UINT:                  return MTLPixelFormatR32Uint;
        case Format::R32_SINT:                  return MTLPixelFormatR32Sint;
        case Format::D24_UNORM_S8_UINT:         return MTLPixelFormatDepth24Unorm_Stencil8;
        case Format::R8G8_UNORM:                return MTLPixelFormatRG8Unorm;
        case Format::R8G8_UINT:                 return MTLPixelFormatRG8Uint;
        case Format::R8G8_SNORM:                return MTLPixelFormatRG8Snorm;
        case Format::R8G8_SINT:                 return MTLPixelFormatRG8Sint;
        case Format::R16_FLOAT:                 return MTLPixelFormatR16Float;
        case Format::D16_UNORM:                 return MTLPixelFormatDepth16Unorm;
        case Format::R16_UNORM:                 return MTLPixelFormatR16Unorm;
        case Format::R16_UINT:                  return MTLPixelFormatR16Uint;
        case Format::R16_SNORM:                 return MTLPixelFormatR16Snorm;
        case Format::R16_SINT:                  return MTLPixelFormatR16Sint;
        case Format::R8_UNORM:                  return MTLPixelFormatR8Unorm;
        case Format::R8_UINT:                   return MTLPixelFormatR8Uint;
        case Format::R8_SNORM:                  return MTLPixelFormatR8Snorm;
        case Format::R8_SINT:                   return MTLPixelFormatR8Sint;
        case Format::BC1_UNORM:                 return MTLPixelFormatBC1_RGBA;
        case Format::BC1_UNORM_SRGB:            return MTLPixelFormatBC1_RGBA_sRGB;
        case Format::BC2_UNORM:                 return MTLPixelFormatBC2_RGBA;
        case Format::BC2_UNORM_SRGB:            return MTLPixelFormatBC2_RGBA_sRGB;
        case Format::BC3_UNORM:                 return MTLPixelFormatBC3_RGBA;
        case Format::BC3_UNORM_SRGB:            return MTLPixelFormatBC3_RGBA_sRGB;
        case Format::BC4_UNORM:                 return MTLPixelFormatBC4_RUnorm;
        case Format::BC4_SNORM:                 return MTLPixelFormatBC4_RSnorm;
        case Format::BC5_UNORM:                 return MTLPixelFormatBC5_RGUnorm;
        case Format::BC5_SNORM:                 return MTLPixelFormatBC5_RGSnorm;
        case Format::BC6H_UF16:                 return MTLPixelFormatBC6H_RGBUfloat;
        case Format::BC6H_SF16:                 return MTLPixelFormatBC6H_RGBFloat;
        case Format::BC7_UNORM:                 return MTLPixelFormatBC7_RGBAUnorm;
        case Format::BC7_UNORM_SRGB:            return MTLPixelFormatBC7_RGBAUnorm_sRGB;
        default:                                return MTLPixelFormatInvalid;
        }
    }

    inline MTLVertexFormat _ConvertFormat_VertexInput(Format format)
    {
        switch (format)
        {
        case Format::R32G32B32A32_FLOAT:        return MTLVertexFormatFloat4;
        case Format::R32G32B32A32_UINT:         return MTLVertexFormatUInt4;
        case Format::R32G32B32A32_SINT:         return MTLVertexFormatInt4;
        case Format::R32G32B32_FLOAT:           return MTLVertexFormatFloat3;
        case Format::R32G32B32_UINT:            return MTLVertexFormatUInt3;
        case Format::R32G32B32_SINT:            return MTLVertexFormatInt3;
        case Format::R16G16B16A16_FLOAT:        return MTLVertexFormatHalf4;
        case Format::R16G16B16A16_UNORM:        return MTLVertexFormatUShort4Normalized;
        case Format::R16G16B16A16_UINT:         return MTLVertexFormatUShort4;
        case Format::R16G16B16A16_SNORM:        return MTLVertexFormatShort4Normalized;
        case Format::R16G16B16A16_SINT:         return MTLVertexFormatShort4;
        case Format::R32G32_FLOAT:              return MTLVertexFormatFloat2;
        case Format::R32G32_UINT:               return MTLVertexFormatUInt2;
        case Format::R32G32_SINT:               return MTLVertexFormatInt2;
        case Format::R10G10B10A2_UNORM:         return MTLVertexFormatUInt1010102Normalized;
        case Format::R8G8B8A8_UNORM:            return MTLVertexFormatUChar4Normalized;
        case Format::R8G8B8A8_UINT:             return MTLVertexFormatUChar4;
        case Format::R8G8B8A8_SNORM:            return MTLVertexFormatChar4Normalized;
        case Format::R8G8B8A8_SINT:             return MTLVertexFormatChar4;
        case Format::R16G16_FLOAT:              return MTLVertexFormatHalf2;
        case Format::R16G16_UNORM:              return MTLVertexFormatUShort2Normalized;
        case Format::R16G16_UINT:               return MTLVertexFormatUShort2;
        case Format::R16G16_SNORM:              return MTLVertexFormatShort2Normalized;
        case Format::R16G16_SINT:               return MTLVertexFormatShort2;
        case Format::R32_FLOAT:                 return MTLVertexFormatFloat;
        case Format::R32_UINT:                  return MTLVertexFormatUInt;
        case Format::R32_SINT:                  return MTLVertexFormatInt;
        case Format::R8G8_UNORM:                return MTLVertexFormatUChar2Normalized;
        case Format::R8G8_UINT:                 return MTLVertexFormatUChar2;
        case Format::R8G8_SNORM:                return MTLVertexFormatChar2Normalized;
        case Format::R8G8_SINT:                 return MTLVertexFormatChar2;
        case Format::R16_FLOAT:                 return MTLVertexFormatHalf;
        case Format::R16_UNORM:                 return MTLVertexFormatUShortNormalized;
        case Format::R16_UINT:                  return MTLVertexFormatUShort;
        case Format::R16_SNORM:                 return MTLVertexFormatShortNormalized;
        case Format::R16_SINT:                  return MTLVertexFormatShort;
        case Format::R8_UNORM:                  return MTLVertexFormatUCharNormalized;
        case Format::R8_UINT:                   return MTLVertexFormatUChar;
        case Format::R8_SNORM:                  return MTLVertexFormatCharNormalized;
        case Format::R8_SINT:                   return MTLVertexFormatChar;
        default:                                return MTLVertexFormatInvalid;
        }
    }

    inline MTLPrimitiveType _ConvertPrimitiveTopology(PrimitiveTopology topology)
    {
        switch (topology)
        {
        case PrimitiveTopology::TRIANGLELIST:   return MTLPrimitiveTypeTriangle;
        case PrimitiveTopology::TRIANGLESTRIP:  return MTLPrimitiveTypeTriangleStrip;
        case PrimitiveTopology::POINTLIST:      return MTLPrimitiveTypePoint;
        case PrimitiveTopology::LINELIST:       return MTLPrimitiveTypeLine;
        case PrimitiveTopology::LINESTRIP:      return MTLPrimitiveTypeLineStrip;
        default:                                return MTLPrimitiveTypeTriangle;
        }
    }

    inline MTLCompareFunction _ConvertComparisonFunc(ComparisonFunc func)
    {
        switch (func)
        {
        case ComparisonFunc::NEVER:             return MTLCompareFunctionNever;
        case ComparisonFunc::LESS:              return MTLCompareFunctionLess;
        case ComparisonFunc::EQUAL:             return MTLCompareFunctionEqual;
        case ComparisonFunc::LESS_EQUAL:        return MTLCompareFunctionLessEqual;
        case ComparisonFunc::GREATER:           return MTLCompareFunctionGreater;
        case ComparisonFunc::NOT_EQUAL:         return MTLCompareFunctionNotEqual;
        case ComparisonFunc::GREATER_EQUAL:     return MTLCompareFunctionGreaterEqual;
        case ComparisonFunc::ALWAYS:            return MTLCompareFunctionAlways;
        default:                                return MTLCompareFunctionNever;
        }
    }

    inline MTLCullMode _ConvertCullMode(CullMode mode)
    {
        switch (mode)
        {
        case CullMode::NONE:    return MTLCullModeNone;
        case CullMode::FRONT:   return MTLCullModeFront;
        case CullMode::BACK:    return MTLCullModeBack;
        default:                return MTLCullModeNone;
        }
    }

    inline MTLBlendFactor _ConvertBlend(Blend blend)
    {
        switch (blend)
        {
        case Blend::ZERO:               return MTLBlendFactorZero;
        case Blend::ONE:                return MTLBlendFactorOne;
        case Blend::SRC_COLOR:          return MTLBlendFactorSourceColor;
        case Blend::INV_SRC_COLOR:      return MTLBlendFactorOneMinusSourceColor;
        case Blend::SRC_ALPHA:          return MTLBlendFactorSourceAlpha;
        case Blend::INV_SRC_ALPHA:      return MTLBlendFactorOneMinusSourceAlpha;
        case Blend::DEST_ALPHA:         return MTLBlendFactorDestinationAlpha;
        case Blend::INV_DEST_ALPHA:     return MTLBlendFactorOneMinusDestinationAlpha;
        case Blend::DEST_COLOR:         return MTLBlendFactorDestinationColor;
        case Blend::INV_DEST_COLOR:     return MTLBlendFactorOneMinusDestinationColor;
        case Blend::SRC_ALPHA_SAT:      return MTLBlendFactorSourceAlphaSaturated;
        case Blend::BLEND_FACTOR:       return MTLBlendFactorBlendColor;
        case Blend::INV_BLEND_FACTOR:   return MTLBlendFactorOneMinusBlendColor;
        case Blend::SRC1_COLOR:         return MTLBlendFactorSource1Color;
        case Blend::INV_SRC1_COLOR:     return MTLBlendFactorOneMinusSource1Color;
        case Blend::SRC1_ALPHA:         return MTLBlendFactorSource1Alpha;
        case Blend::INV_SRC1_ALPHA:     return MTLBlendFactorOneMinusSource1Alpha;
        default:                        return MTLBlendFactorOne;
        }
    }

    inline MTLBlendOperation _ConvertBlendOp(BlendOp op)
    {
        switch (op)
        {
        case BlendOp::ADD:              return MTLBlendOperationAdd;
        case BlendOp::SUBTRACT:         return MTLBlendOperationSubtract;
        case BlendOp::REV_SUBTRACT:     return MTLBlendOperationReverseSubtract;
        case BlendOp::MIN:              return MTLBlendOperationMin;
        case BlendOp::MAX:              return MTLBlendOperationMax;
        default:                        return MTLBlendOperationAdd;
        }
    }

    inline MTLSamplerAddressMode _ConvertTextureAddressMode(TextureAddressMode mode)
    {
        switch (mode)
        {
        case TextureAddressMode::WRAP:          return MTLSamplerAddressModeRepeat;
        case TextureAddressMode::MIRROR:        return MTLSamplerAddressModeMirrorRepeat;
        case TextureAddressMode::CLAMP:         return MTLSamplerAddressModeClampToEdge;
        case TextureAddressMode::BORDER:        return MTLSamplerAddressModeClampToBorderColor;
        case TextureAddressMode::MIRROR_ONCE:   return MTLSamplerAddressModeMirrorClampToEdge;
        default:                                return MTLSamplerAddressModeClampToEdge;
        }
    }

    inline MTLSamplerMinMagFilter _ConvertFilter_MinMag(Filter filter)
    {
        switch (filter)
        {
        case Filter::MIN_MAG_MIP_POINT:
        case Filter::MIN_MAG_POINT_MIP_LINEAR:
        case Filter::COMPARISON_MIN_MAG_MIP_POINT:
        case Filter::COMPARISON_MIN_MAG_POINT_MIP_LINEAR:
        case Filter::MINIMUM_MIN_MAG_MIP_POINT:
        case Filter::MINIMUM_MIN_MAG_POINT_MIP_LINEAR:
        case Filter::MAXIMUM_MIN_MAG_MIP_POINT:
        case Filter::MAXIMUM_MIN_MAG_POINT_MIP_LINEAR:
            return MTLSamplerMinMagFilterNearest;
        default:
            return MTLSamplerMinMagFilterLinear;
        }
    }

    inline MTLSamplerMipFilter _ConvertFilter_Mip(Filter filter)
    {
        switch (filter)
        {
        case Filter::MIN_MAG_MIP_POINT:
        case Filter::MIN_POINT_MAG_LINEAR_MIP_POINT:
        case Filter::MIN_LINEAR_MAG_MIP_POINT:
        case Filter::MIN_MAG_LINEAR_MIP_POINT:
        case Filter::COMPARISON_MIN_MAG_MIP_POINT:
        case Filter::COMPARISON_MIN_POINT_MAG_LINEAR_MIP_POINT:
        case Filter::COMPARISON_MIN_LINEAR_MAG_MIP_POINT:
        case Filter::COMPARISON_MIN_MAG_LINEAR_MIP_POINT:
        case Filter::MINIMUM_MIN_MAG_MIP_POINT:
        case Filter::MINIMUM_MIN_POINT_MAG_LINEAR_MIP_POINT:
        case Filter::MINIMUM_MIN_LINEAR_MAG_MIP_POINT:
        case Filter::MINIMUM_MIN_MAG_LINEAR_MIP_POINT:
        case Filter::MAXIMUM_MIN_MAG_MIP_POINT:
        case Filter::MAXIMUM_MIN_POINT_MAG_LINEAR_MIP_POINT:
        case Filter::MAXIMUM_MIN_LINEAR_MAG_MIP_POINT:
        case Filter::MAXIMUM_MIN_MAG_LINEAR_MIP_POINT:
            return MTLSamplerMipFilterNearest;
        case Filter::ANISOTROPIC:
        case Filter::COMPARISON_ANISOTROPIC:
        case Filter::MINIMUM_ANISOTROPIC:
        case Filter::MAXIMUM_ANISOTROPIC:
        case Filter::MIN_MAG_POINT_MIP_LINEAR:
        case Filter::MIN_POINT_MAG_MIP_LINEAR:
        case Filter::MIN_LINEAR_MAG_POINT_MIP_LINEAR:
        case Filter::MIN_MAG_MIP_LINEAR:
        case Filter::COMPARISON_MIN_MAG_POINT_MIP_LINEAR:
        case Filter::COMPARISON_MIN_POINT_MAG_MIP_LINEAR:
        case Filter::COMPARISON_MIN_LINEAR_MAG_POINT_MIP_LINEAR:
        case Filter::COMPARISON_MIN_MAG_MIP_LINEAR:
        case Filter::MINIMUM_MIN_MAG_POINT_MIP_LINEAR:
        case Filter::MINIMUM_MIN_POINT_MAG_MIP_LINEAR:
        case Filter::MINIMUM_MIN_LINEAR_MAG_POINT_MIP_LINEAR:
        case Filter::MINIMUM_MIN_MAG_MIP_LINEAR:
        case Filter::MAXIMUM_MIN_MAG_POINT_MIP_LINEAR:
        case Filter::MAXIMUM_MIN_POINT_MAG_MIP_LINEAR:
        case Filter::MAXIMUM_MIN_LINEAR_MAG_POINT_MIP_LINEAR:
        case Filter::MAXIMUM_MIN_MAG_MIP_LINEAR:
            return MTLSamplerMipFilterLinear;
        default:
            return MTLSamplerMipFilterNotMipmapped;
        }
    }

    inline MTLStencilOperation _ConvertStencilOp(StencilOp op)
    {
        switch (op)
        {
        case StencilOp::KEEP:       return MTLStencilOperationKeep;
        case StencilOp::ZERO:       return MTLStencilOperationZero;
        case StencilOp::REPLACE:    return MTLStencilOperationReplace;
        case StencilOp::INCR_SAT:   return MTLStencilOperationIncrementClamp;
        case StencilOp::DECR_SAT:   return MTLStencilOperationDecrementClamp;
        case StencilOp::INVERT:     return MTLStencilOperationInvert;
        case StencilOp::INCR:       return MTLStencilOperationIncrementWrap;
        case StencilOp::DECR:       return MTLStencilOperationDecrementWrap;
        default:                    return MTLStencilOperationKeep;
        }
    }

    inline MTLColorWriteMask _ConvertColorWriteMask(ColorWrite mask)
    {
        MTLColorWriteMask result = MTLColorWriteMaskNone;
        if (has_flag(mask, ColorWrite::ENABLE_RED))   result |= MTLColorWriteMaskRed;
        if (has_flag(mask, ColorWrite::ENABLE_GREEN)) result |= MTLColorWriteMaskGreen;
        if (has_flag(mask, ColorWrite::ENABLE_BLUE))  result |= MTLColorWriteMaskBlue;
        if (has_flag(mask, ColorWrite::ENABLE_ALPHA)) result |= MTLColorWriteMaskAlpha;
        return result;
    }

    // ============================================
    // GraphicsDevice_Metal Implementation
    // ============================================

    GraphicsDevice_Metal::~GraphicsDevice_Metal()
    {
        WaitForGPU();

        if (frameSemaphore)
        {
            // Release semaphore
            frameSemaphore = nullptr;
        }

        commandLists.clear();
        activeCommandLists.clear();
        frameAllocators.clear();

        if (commandQueue)
        {
            commandQueue = nil;
        }
        if (device)
        {
            device = nil;
        }
    }

    bool GraphicsDevice_Metal::Initialize(ValidationMode validationMode_, GPUPreference preference)
    {
        this->validationMode = validationMode_;

        // Get the default Metal device
        device = MTLCreateSystemDefaultDevice();
        if (!device)
        {
            NSLog(@"Metal is not supported on this device");
            return false;
        }

        // Create command queue
        commandQueue = [device newCommandQueue];
        if (!commandQueue)
        {
            NSLog(@"Failed to create Metal command queue");
            return false;
        }

        // Create frame semaphore for triple buffering synchronization
        frameSemaphore = dispatch_semaphore_create(BUFFERCOUNT);

        // Initialize command list pool
        commandLists.resize(MAX_COMMANDLISTS);
        frameAllocators.resize(MAX_COMMANDLISTS);

        // Set device info
        adapterName = [[device name] UTF8String];
        driverDescription = "Apple Metal";

        // Check capabilities
        if ([device supportsFamily:MTLGPUFamilyApple7])
        {
            capabilities |= GraphicsDeviceCapability::MESH_SHADER;
        }

        NSLog(@"Metal device initialized: %@", [device name]);
        return true;
    }

    // ============================================
    // Resource Creation
    // ============================================

    bool GraphicsDevice_Metal::CreateSwapChain(const SwapChainDesc* desc, vz::platform::window_type window, SwapChain* swapchain) const
    {
        auto internal_state = std::make_shared<SwapChain_Metal>();
        swapchain->internal_state = internal_state;
        swapchain->desc = *desc;

        // Get or create CAMetalLayer
        NSView* nsView = (__bridge NSView*)window;
        if (!nsView)
        {
            NSLog(@"Invalid window handle for swap chain creation");
            return false;
        }

        // Create CAMetalLayer
        CAMetalLayer* metalLayer = [CAMetalLayer layer];
        metalLayer.device = device;
        metalLayer.pixelFormat = _ConvertFormat(desc->format);
        metalLayer.framebufferOnly = YES;
        metalLayer.drawableSize = CGSizeMake(desc->width, desc->height);

        // Enable VSync
        if (@available(macOS 10.13, *))
        {
            metalLayer.displaySyncEnabled = desc->vsync;
        }

        // Set the layer on the view
        nsView.wantsLayer = YES;
        nsView.layer = metalLayer;

        internal_state->metalLayer = metalLayer;
        internal_state->desc = *desc;
        internal_state->colorSpace = ColorSpace::SRGB;

        // Create back buffer texture wrapper
        internal_state->backBuffer.desc.type = TextureDesc::Type::TEXTURE_2D;
        internal_state->backBuffer.desc.width = desc->width;
        internal_state->backBuffer.desc.height = desc->height;
        internal_state->backBuffer.desc.format = desc->format;
        internal_state->backBuffer.desc.bind_flags = BindFlag::RENDER_TARGET;

        return true;
    }

    bool GraphicsDevice_Metal::CreateBuffer2(const GPUBufferDesc* desc, const std::function<void(void* dest)>& init_callback, GPUBuffer* buffer, const GPUResource* alias, uint64_t alias_offset) const
    {
        auto internal_state = std::make_shared<Resource_Metal>();
        buffer->internal_state = internal_state;
        buffer->type = GPUResource::Type::BUFFER;
        buffer->desc = *desc;

        MTLResourceOptions options = MTLResourceStorageModeShared;

        switch (desc->usage)
        {
        case Usage::DEFAULT:
            options = MTLResourceStorageModePrivate;
            break;
        case Usage::UPLOAD:
            options = MTLResourceStorageModeShared | MTLResourceCPUCacheModeWriteCombined;
            break;
        case Usage::READBACK:
            options = MTLResourceStorageModeShared;
            break;
        }

        if (desc->usage == Usage::UPLOAD || desc->usage == Usage::READBACK)
        {
            // CPU accessible buffer
            internal_state->buffer = [device newBufferWithLength:desc->size options:options];
            if (!internal_state->buffer)
            {
                return false;
            }

            internal_state->mapped_data = [internal_state->buffer contents];
            internal_state->mapped_size = desc->size;
            buffer->mapped_data = internal_state->mapped_data;
            buffer->mapped_size = internal_state->mapped_size;

            if (init_callback && internal_state->mapped_data)
            {
                init_callback(internal_state->mapped_data);
            }
        }
        else
        {
            // GPU only buffer
            if (init_callback)
            {
                // Create staging buffer for initial data
                id<MTLBuffer> stagingBuffer = [device newBufferWithLength:desc->size
                    options:MTLResourceStorageModeShared | MTLResourceCPUCacheModeWriteCombined];
                if (!stagingBuffer)
                {
                    return false;
                }

                init_callback([stagingBuffer contents]);

                // Create GPU buffer
                internal_state->buffer = [device newBufferWithLength:desc->size options:options];
                if (!internal_state->buffer)
                {
                    return false;
                }

                // Copy from staging to GPU buffer
                id<MTLCommandBuffer> cmdBuffer = [commandQueue commandBuffer];
                id<MTLBlitCommandEncoder> blitEncoder = [cmdBuffer blitCommandEncoder];
                [blitEncoder copyFromBuffer:stagingBuffer sourceOffset:0
                    toBuffer:internal_state->buffer destinationOffset:0 size:desc->size];
                [blitEncoder endEncoding];
                [cmdBuffer commit];
                [cmdBuffer waitUntilCompleted];
            }
            else
            {
                internal_state->buffer = [device newBufferWithLength:desc->size options:options];
                if (!internal_state->buffer)
                {
                    return false;
                }
            }
        }

        return true;
    }

    void GraphicsDevice_Metal::UploadToBufferRegion(GPUBuffer* buffer, uint64_t offset, const void* data, uint64_t size) const
    {
        if (!buffer || !buffer->internal_state || !data || size == 0)
            return;

        auto internal_state = to_internal<Resource_Metal>(buffer);
        if (internal_state->mapped_data)
        {
            memcpy((uint8_t*)internal_state->mapped_data + offset, data, size);
        }
    }

    bool GraphicsDevice_Metal::CreateTexture(const TextureDesc* desc, const SubresourceData* initial_data, Texture* texture, const GPUResource* alias, uint64_t alias_offset) const
    {
        auto internal_state = std::make_shared<Texture_Metal>();
        texture->internal_state = internal_state;
        texture->type = GPUResource::Type::TEXTURE;
        texture->desc = *desc;

        MTLTextureDescriptor* texDesc = [[MTLTextureDescriptor alloc] init];

        switch (desc->type)
        {
        case TextureDesc::Type::TEXTURE_1D:
            texDesc.textureType = desc->array_size > 1 ? MTLTextureType1DArray : MTLTextureType1D;
            break;
        case TextureDesc::Type::TEXTURE_2D:
            if (has_flag(desc->misc_flags, ResourceMiscFlag::TEXTURECUBE))
            {
                texDesc.textureType = desc->array_size > 6 ? MTLTextureTypeCubeArray : MTLTextureTypeCube;
            }
            else if (desc->sample_count > 1)
            {
                texDesc.textureType = desc->array_size > 1 ? MTLTextureType2DMultisampleArray : MTLTextureType2DMultisample;
            }
            else
            {
                texDesc.textureType = desc->array_size > 1 ? MTLTextureType2DArray : MTLTextureType2D;
            }
            break;
        case TextureDesc::Type::TEXTURE_3D:
            texDesc.textureType = MTLTextureType3D;
            break;
        }

        texDesc.pixelFormat = _ConvertFormat(desc->format);
        texDesc.width = desc->width;
        texDesc.height = desc->height;
        texDesc.depth = desc->depth;
        texDesc.mipmapLevelCount = desc->mip_levels;
        texDesc.arrayLength = has_flag(desc->misc_flags, ResourceMiscFlag::TEXTURECUBE) ? desc->array_size / 6 : desc->array_size;
        texDesc.sampleCount = desc->sample_count;

        // Set storage mode and usage
        MTLResourceOptions resourceOptions = MTLResourceStorageModePrivate;
        MTLTextureUsage usage = MTLTextureUsageShaderRead;

        if (has_flag(desc->bind_flags, BindFlag::RENDER_TARGET) || has_flag(desc->bind_flags, BindFlag::DEPTH_STENCIL))
        {
            usage |= MTLTextureUsageRenderTarget;
        }
        if (has_flag(desc->bind_flags, BindFlag::UNORDERED_ACCESS))
        {
            usage |= MTLTextureUsageShaderWrite;
        }

        switch (desc->usage)
        {
        case Usage::UPLOAD:
        case Usage::READBACK:
            resourceOptions = MTLResourceStorageModeShared;
            break;
        default:
            resourceOptions = MTLResourceStorageModePrivate;
            break;
        }

        texDesc.storageMode = (MTLStorageMode)(resourceOptions & MTLResourceStorageModeMask);
        texDesc.usage = usage;

        internal_state->texture = [device newTextureWithDescriptor:texDesc];
        if (!internal_state->texture)
        {
            return false;
        }

        internal_state->pixelFormat = texDesc.pixelFormat;
        internal_state->width = desc->width;
        internal_state->height = desc->height;
        internal_state->depth = desc->depth;
        internal_state->mipLevels = desc->mip_levels;
        internal_state->arraySize = desc->array_size;

        // Upload initial data if provided
        if (initial_data && desc->usage != Usage::DEFAULT)
        {
            // Direct upload for shared storage
            for (uint32_t slice = 0; slice < desc->array_size; ++slice)
            {
                for (uint32_t mip = 0; mip < desc->mip_levels; ++mip)
                {
                    uint32_t subresource = slice * desc->mip_levels + mip;
                    const SubresourceData& data = initial_data[subresource];

                    MTLRegion region = MTLRegionMake3D(0, 0, 0,
                        std::max(1u, desc->width >> mip),
                        std::max(1u, desc->height >> mip),
                        std::max(1u, desc->depth >> mip));

                    [internal_state->texture replaceRegion:region
                        mipmapLevel:mip
                        slice:slice
                        withBytes:data.data_ptr
                        bytesPerRow:data.row_pitch
                        bytesPerImage:data.slice_pitch];
                }
            }
        }
        else if (initial_data && desc->usage == Usage::DEFAULT)
        {
            // Use staging buffer and blit for private storage
            id<MTLCommandBuffer> cmdBuffer = [commandQueue commandBuffer];
            id<MTLBlitCommandEncoder> blitEncoder = [cmdBuffer blitCommandEncoder];

            for (uint32_t slice = 0; slice < desc->array_size; ++slice)
            {
                for (uint32_t mip = 0; mip < desc->mip_levels; ++mip)
                {
                    uint32_t subresource = slice * desc->mip_levels + mip;
                    const SubresourceData& data = initial_data[subresource];

                    uint32_t mipWidth = std::max(1u, desc->width >> mip);
                    uint32_t mipHeight = std::max(1u, desc->height >> mip);
                    uint32_t mipDepth = std::max(1u, desc->depth >> mip);

                    size_t bufferSize = data.row_pitch * mipHeight * mipDepth;
                    id<MTLBuffer> stagingBuffer = [device newBufferWithBytes:data.data_ptr
                        length:bufferSize
                        options:MTLResourceStorageModeShared];

                    [blitEncoder copyFromBuffer:stagingBuffer
                        sourceOffset:0
                        sourceBytesPerRow:data.row_pitch
                        sourceBytesPerImage:data.slice_pitch
                        sourceSize:MTLSizeMake(mipWidth, mipHeight, mipDepth)
                        toTexture:internal_state->texture
                        destinationSlice:slice
                        destinationLevel:mip
                        destinationOrigin:MTLOriginMake(0, 0, 0)];
                }
            }

            [blitEncoder endEncoding];
            [cmdBuffer commit];
            [cmdBuffer waitUntilCompleted];
        }

        return true;
    }

    bool GraphicsDevice_Metal::CreateShader(ShaderStage stage, const void* shadercode, size_t shadercode_size, Shader* shader) const
    {
        auto internal_state = std::make_shared<Shader_Metal>();
        shader->internal_state = internal_state;
        shader->stage = stage;
        internal_state->stage = stage;

        NSError* error = nil;
        std::string mslSource;
        std::string entryPointFromSpirv;

        // Check if input is SPIRV bytecode
        if (IsSpirvBytecode(shadercode, shadercode_size))
        {
            // Convert SPIRV to MSL using SPIRV-Cross
            SpirvToMslOptions options;
            options.msl_version = 20100;  // Metal 2.1
            options.platform = 0;  // macOS

            SpirvToMslResult result = ConvertSpirvToMsl(
                static_cast<const uint32_t*>(shadercode),
                shadercode_size,
                options
            );

            if (!result.success)
            {
                NSLog(@"Failed to convert SPIRV to MSL: %s", result.error_message.c_str());
                return false;
            }

            mslSource = result.msl_source;
            entryPointFromSpirv = result.entry_point_name;

            NSLog(@"SPIRV to MSL conversion successful, entry point: %s", entryPointFromSpirv.c_str());
        }

        // If we have MSL source from SPIRV conversion, compile it
        if (!mslSource.empty())
        {
            NSString* source = [NSString stringWithUTF8String:mslSource.c_str()];
            MTLCompileOptions* options = [[MTLCompileOptions alloc] init];
            if (@available(macOS 15.0, *))
            {
                options.mathMode = MTLMathModeFast;
            }
            else
            {
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
                options.fastMathEnabled = YES;
#pragma clang diagnostic pop
            }

            internal_state->library = [device newLibraryWithSource:source options:options error:&error];

            if (!internal_state->library)
            {
                if (error)
                {
                    NSLog(@"Failed to compile MSL from SPIRV: %@", error.localizedDescription);
                    NSLog(@"MSL Source:\n%s", mslSource.c_str());
                }
                return false;
            }

            // Use entry point from SPIRV-Cross
            if (!entryPointFromSpirv.empty())
            {
                NSString* entryPoint = [NSString stringWithUTF8String:entryPointFromSpirv.c_str()];
                internal_state->function = [internal_state->library newFunctionWithName:entryPoint];
                internal_state->entryPoint = entryPointFromSpirv;
            }
        }
        else
        {
            // Not SPIRV - try to load as metallib first (compiled Metal library)
            dispatch_data_t data = dispatch_data_create(shadercode, shadercode_size, nil, DISPATCH_DATA_DESTRUCTOR_DEFAULT);
            internal_state->library = [device newLibraryWithData:data error:&error];

            if (!internal_state->library)
            {
                // If that fails, try to compile as MSL source
                NSString* source = [[NSString alloc] initWithBytes:shadercode
                                                            length:shadercode_size
                                                          encoding:NSUTF8StringEncoding];
                if (source)
                {
                    MTLCompileOptions* options = [[MTLCompileOptions alloc] init];
                    if (@available(macOS 15.0, *))
                    {
                        options.mathMode = MTLMathModeFast;
                    }
                    else
                    {
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
                        options.fastMathEnabled = YES;
#pragma clang diagnostic pop
                    }

                    internal_state->library = [device newLibraryWithSource:source options:options error:&error];
                }
            }
        }

        if (!internal_state->library)
        {
            if (error)
            {
                NSLog(@"Failed to create Metal shader library: %@", error.localizedDescription);
            }
            return false;
        }

        // If we don't have an entry point yet, determine it based on shader stage
        if (!internal_state->function)
        {
            NSString* entryPoint = nil;
            switch (stage)
            {
            case ShaderStage::VS:
                entryPoint = @"vertexMain";
                break;
            case ShaderStage::PS:
                entryPoint = @"fragmentMain";
                break;
            case ShaderStage::CS:
                entryPoint = @"computeMain";
                break;
            default:
                // For other stages, try to get the first function
                NSArray<NSString*>* functionNames = [internal_state->library functionNames];
                if (functionNames.count > 0)
                {
                    entryPoint = functionNames[0];
                }
                break;
            }

            if (entryPoint)
            {
                internal_state->function = [internal_state->library newFunctionWithName:entryPoint];
                internal_state->entryPoint = [entryPoint UTF8String];
            }

            // If we couldn't find the standard entry point, try common alternatives
            if (!internal_state->function)
            {
                NSArray<NSString*>* alternativeNames = nil;
                switch (stage)
                {
                case ShaderStage::VS:
                    alternativeNames = @[@"vertex_main", @"vs_main", @"main_vs", @"vert", @"main0"];
                    break;
                case ShaderStage::PS:
                    alternativeNames = @[@"fragment_main", @"ps_main", @"main_ps", @"frag", @"main0"];
                    break;
                case ShaderStage::CS:
                    alternativeNames = @[@"compute_main", @"cs_main", @"main_cs", @"compute", @"main0"];
                    break;
                default:
                    break;
                }

                for (NSString* name in alternativeNames)
                {
                    internal_state->function = [internal_state->library newFunctionWithName:name];
                    if (internal_state->function)
                    {
                        internal_state->entryPoint = [name UTF8String];
                        break;
                    }
                }
            }
        }

        return internal_state->library != nil;
    }

    bool GraphicsDevice_Metal::CreateSampler(const SamplerDesc* desc, Sampler* sampler) const
    {
        auto internal_state = std::make_shared<Sampler_Metal>();
        sampler->internal_state = internal_state;
        sampler->desc = *desc;

        MTLSamplerDescriptor* samplerDesc = [[MTLSamplerDescriptor alloc] init];

        samplerDesc.minFilter = _ConvertFilter_MinMag(desc->filter);
        samplerDesc.magFilter = _ConvertFilter_MinMag(desc->filter);
        samplerDesc.mipFilter = _ConvertFilter_Mip(desc->filter);

        samplerDesc.sAddressMode = _ConvertTextureAddressMode(desc->address_u);
        samplerDesc.tAddressMode = _ConvertTextureAddressMode(desc->address_v);
        samplerDesc.rAddressMode = _ConvertTextureAddressMode(desc->address_w);

        samplerDesc.lodMinClamp = desc->min_lod;
        samplerDesc.lodMaxClamp = desc->max_lod;
        samplerDesc.maxAnisotropy = std::max(1u, desc->max_anisotropy);

        // Comparison function for comparison samplers
        switch (desc->filter)
        {
        case Filter::COMPARISON_MIN_MAG_MIP_POINT:
        case Filter::COMPARISON_MIN_MAG_POINT_MIP_LINEAR:
        case Filter::COMPARISON_MIN_POINT_MAG_LINEAR_MIP_POINT:
        case Filter::COMPARISON_MIN_POINT_MAG_MIP_LINEAR:
        case Filter::COMPARISON_MIN_LINEAR_MAG_MIP_POINT:
        case Filter::COMPARISON_MIN_LINEAR_MAG_POINT_MIP_LINEAR:
        case Filter::COMPARISON_MIN_MAG_LINEAR_MIP_POINT:
        case Filter::COMPARISON_MIN_MAG_MIP_LINEAR:
        case Filter::COMPARISON_ANISOTROPIC:
            samplerDesc.compareFunction = _ConvertComparisonFunc(desc->comparison_func);
            break;
        default:
            samplerDesc.compareFunction = MTLCompareFunctionNever;
            break;
        }

        // Border color
        switch (desc->border_color)
        {
        case SamplerBorderColor::TRANSPARENT_BLACK:
            samplerDesc.borderColor = MTLSamplerBorderColorTransparentBlack;
            break;
        case SamplerBorderColor::OPAQUE_BLACK:
            samplerDesc.borderColor = MTLSamplerBorderColorOpaqueBlack;
            break;
        case SamplerBorderColor::OPAQUE_WHITE:
            samplerDesc.borderColor = MTLSamplerBorderColorOpaqueWhite;
            break;
        }

        internal_state->sampler = [device newSamplerStateWithDescriptor:samplerDesc];
        return internal_state->sampler != nil;
    }

    bool GraphicsDevice_Metal::CreateQueryHeap(const GPUQueryHeapDesc* desc, GPUQueryHeap* queryheap) const
    {
        // TODO: Implement query heap
        return false;
    }

    bool GraphicsDevice_Metal::CreatePipelineState(const PipelineStateDesc* desc, PipelineState* pso, const RenderPassInfo* renderpass_info) const
    {
        auto internal_state = std::make_shared<PipelineState_Metal>();
        pso->internal_state = internal_state;
        pso->desc = *desc;

        // Check if this is a compute pipeline
        if (desc->vs == nullptr && desc->ps == nullptr && desc->ms == nullptr)
        {
            // Compute pipeline - not implemented yet
            return false;
        }

        // Create render pipeline descriptor
        MTLRenderPipelineDescriptor* pipelineDesc = [[MTLRenderPipelineDescriptor alloc] init];

        // Set shaders
        if (desc->vs && desc->vs->internal_state)
        {
            auto vs_internal = to_internal<Shader_Metal>(desc->vs);
            pipelineDesc.vertexFunction = vs_internal->function;
        }

        if (desc->ps && desc->ps->internal_state)
        {
            auto ps_internal = to_internal<Shader_Metal>(desc->ps);
            pipelineDesc.fragmentFunction = ps_internal->function;
        }

        // Configure vertex descriptor from input layout
        if (desc->il && !desc->il->elements.empty())
        {
            MTLVertexDescriptor* vertexDesc = [[MTLVertexDescriptor alloc] init];

            uint32_t currentOffset[16] = {};
            for (size_t i = 0; i < desc->il->elements.size(); ++i)
            {
                const auto& element = desc->il->elements[i];

                MTLVertexAttributeDescriptor* attr = vertexDesc.attributes[i];
                attr.format = _ConvertFormat_VertexInput(element.format);
                attr.bufferIndex = element.input_slot;

                if (element.aligned_byte_offset == InputLayout::APPEND_ALIGNED_ELEMENT)
                {
                    attr.offset = currentOffset[element.input_slot];
                    currentOffset[element.input_slot] += GetFormatStride(element.format);
                }
                else
                {
                    attr.offset = element.aligned_byte_offset;
                    currentOffset[element.input_slot] = element.aligned_byte_offset + GetFormatStride(element.format);
                }
            }

            // Configure buffer layouts
            for (uint32_t slot = 0; slot < 16; ++slot)
            {
                if (currentOffset[slot] > 0)
                {
                    MTLVertexBufferLayoutDescriptor* layout = vertexDesc.layouts[slot];
                    layout.stride = currentOffset[slot];
                    layout.stepFunction = MTLVertexStepFunctionPerVertex;
                    layout.stepRate = 1;
                }
            }

            pipelineDesc.vertexDescriptor = vertexDesc;
        }

        // Configure render target formats
        if (renderpass_info)
        {
            for (uint32_t i = 0; i < renderpass_info->rt_count; ++i)
            {
                pipelineDesc.colorAttachments[i].pixelFormat = _ConvertFormat(renderpass_info->rt_formats[i]);
            }
            if (renderpass_info->ds_format != Format::UNKNOWN)
            {
                pipelineDesc.depthAttachmentPixelFormat = _ConvertFormat(renderpass_info->ds_format);
                if (IsFormatStencilSupport(renderpass_info->ds_format))
                {
                    pipelineDesc.stencilAttachmentPixelFormat = _ConvertFormat(renderpass_info->ds_format);
                }
            }
            pipelineDesc.rasterSampleCount = renderpass_info->sample_count;
        }
        else
        {
            // Default to single render target with BGRA8 format
            pipelineDesc.colorAttachments[0].pixelFormat = MTLPixelFormatBGRA8Unorm;
        }

        // Configure blend state
        if (desc->bs)
        {
            pipelineDesc.alphaToCoverageEnabled = desc->bs->alpha_to_coverage_enable;

            for (int i = 0; i < 8; ++i)
            {
                const auto& rt_blend = desc->bs->render_target[desc->bs->independent_blend_enable ? i : 0];

                MTLRenderPipelineColorAttachmentDescriptor* attachment = pipelineDesc.colorAttachments[i];
                attachment.blendingEnabled = rt_blend.blend_enable;
                attachment.sourceRGBBlendFactor = _ConvertBlend(rt_blend.src_blend);
                attachment.destinationRGBBlendFactor = _ConvertBlend(rt_blend.dest_blend);
                attachment.rgbBlendOperation = _ConvertBlendOp(rt_blend.blend_op);
                attachment.sourceAlphaBlendFactor = _ConvertBlend(rt_blend.src_blend_alpha);
                attachment.destinationAlphaBlendFactor = _ConvertBlend(rt_blend.dest_blend_alpha);
                attachment.alphaBlendOperation = _ConvertBlendOp(rt_blend.blend_op_alpha);
                attachment.writeMask = _ConvertColorWriteMask(rt_blend.render_target_write_mask);
            }
        }

        // Create pipeline state
        NSError* error = nil;
        internal_state->renderPipeline = [device newRenderPipelineStateWithDescriptor:pipelineDesc error:&error];

        if (!internal_state->renderPipeline)
        {
            if (error)
            {
                NSLog(@"Failed to create render pipeline state: %@", error.localizedDescription);
            }
            return false;
        }

        // Create depth stencil state
        if (desc->dss)
        {
            MTLDepthStencilDescriptor* dsDesc = [[MTLDepthStencilDescriptor alloc] init];

            dsDesc.depthWriteEnabled = desc->dss->depth_write_mask == DepthWriteMask::ALL;
            dsDesc.depthCompareFunction = desc->dss->depth_enable ?
                _ConvertComparisonFunc(desc->dss->depth_func) : MTLCompareFunctionAlways;

            if (desc->dss->stencil_enable)
            {
                MTLStencilDescriptor* frontStencil = [[MTLStencilDescriptor alloc] init];
                frontStencil.stencilCompareFunction = _ConvertComparisonFunc(desc->dss->front_face.stencil_func);
                frontStencil.stencilFailureOperation = _ConvertStencilOp(desc->dss->front_face.stencil_fail_op);
                frontStencil.depthFailureOperation = _ConvertStencilOp(desc->dss->front_face.stencil_depth_fail_op);
                frontStencil.depthStencilPassOperation = _ConvertStencilOp(desc->dss->front_face.stencil_pass_op);
                frontStencil.readMask = desc->dss->stencil_read_mask;
                frontStencil.writeMask = desc->dss->stencil_write_mask;
                dsDesc.frontFaceStencil = frontStencil;

                MTLStencilDescriptor* backStencil = [[MTLStencilDescriptor alloc] init];
                backStencil.stencilCompareFunction = _ConvertComparisonFunc(desc->dss->back_face.stencil_func);
                backStencil.stencilFailureOperation = _ConvertStencilOp(desc->dss->back_face.stencil_fail_op);
                backStencil.depthFailureOperation = _ConvertStencilOp(desc->dss->back_face.stencil_depth_fail_op);
                backStencil.depthStencilPassOperation = _ConvertStencilOp(desc->dss->back_face.stencil_pass_op);
                backStencil.readMask = desc->dss->stencil_read_mask;
                backStencil.writeMask = desc->dss->stencil_write_mask;
                dsDesc.backFaceStencil = backStencil;
            }

            internal_state->depthStencilState = [device newDepthStencilStateWithDescriptor:dsDesc];
        }

        // Store rasterizer state for encoder-time application
        if (desc->rs)
        {
            internal_state->cullMode = _ConvertCullMode(desc->rs->cull_mode);
            internal_state->frontFace = desc->rs->front_counter_clockwise ? MTLWindingCounterClockwise : MTLWindingClockwise;
            internal_state->fillMode = desc->rs->fill_mode == FillMode::WIREFRAME ? MTLTriangleFillModeLines : MTLTriangleFillModeFill;
            internal_state->depthBias = (float)desc->rs->depth_bias;
            internal_state->depthBiasClamp = desc->rs->depth_bias_clamp;
            internal_state->slopeScaledDepthBias = desc->rs->slope_scaled_depth_bias;
            internal_state->depthClipEnable = desc->rs->depth_clip_enable;
        }

        // Store primitive type
        internal_state->primitiveType = _ConvertPrimitiveTopology(desc->pt);

        return true;
    }

    int GraphicsDevice_Metal::CreateSubresource(Texture* texture, SubresourceType type, uint32_t firstSlice, uint32_t sliceCount, uint32_t firstMip, uint32_t mipCount, const Format* format_change, const ImageAspect* aspect, const Swizzle* swizzle, float min_lod_clamp) const
    {
        return -1;
    }

    int GraphicsDevice_Metal::CreateSubresource(GPUBuffer* buffer, SubresourceType type, uint64_t offset, uint64_t size, const Format* format_change, const uint32_t* structuredbuffer_stride_change) const
    {
        return -1;
    }

    bool GraphicsDevice_Metal::OpenSharedResource(const void* device2, const void* srvDescHeap2, const int descriptorIndex, const Texture* textureShared,
        uint64_t& gpuDesciptorHandlerPtr, GPUResource& sharedRes, void** backendResPtr)
    {
        return false;
    }

    void GraphicsDevice_Metal::DeleteSubresources(GPUResource* resource)
    {
    }

    int GraphicsDevice_Metal::GetDescriptorIndex(const GPUResource* resource, SubresourceType type, int subresource) const
    {
        return -1;
    }

    int GraphicsDevice_Metal::GetDescriptorIndex(const Sampler* sampler) const
    {
        return -1;
    }

    // ============================================
    // Command List Management
    // ============================================

    CommandList GraphicsDevice_Metal::BeginCommandList(QUEUE_TYPE queue)
    {
        std::lock_guard<std::mutex> lock(cmdListMutex);

        uint32_t index = nextCommandListIndex++;
        if (index >= commandLists.size())
        {
            commandLists.resize(index + 1);
            frameAllocators.resize(index + 1);
        }

        CommandList_Metal& cmdList = commandLists[index];
        cmdList.Reset();
        cmdList.queueType = queue;

        // Create command buffer
        cmdList.commandBuffer = [commandQueue commandBuffer];
        cmdList.commandBuffer.label = @"CommandList";

        CommandList cmd;
        cmd.internal_state = &cmdList;

        activeCommandLists.push_back(cmd);

        return cmd;
    }

    void GraphicsDevice_Metal::SubmitCommandLists()
    {
        std::lock_guard<std::mutex> lock(cmdListMutex);

        // Wait for a frame slot to become available
        dispatch_semaphore_wait(frameSemaphore, DISPATCH_TIME_FOREVER);

        uint64_t currentFrame = FRAMECOUNT;

        for (auto& cmd : activeCommandLists)
        {
            CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);
            if (cmdList && cmdList->commandBuffer)
            {
                // End any active encoders
                if (cmdList->renderEncoder)
                {
                    [cmdList->renderEncoder endEncoding];
                    cmdList->renderEncoder = nil;
                }
                if (cmdList->computeEncoder)
                {
                    [cmdList->computeEncoder endEncoding];
                    cmdList->computeEncoder = nil;
                }
                if (cmdList->blitEncoder)
                {
                    [cmdList->blitEncoder endEncoding];
                    cmdList->blitEncoder = nil;
                }

                // Present drawable if we have one
                if (cmdList->currentDrawable)
                {
                    [cmdList->commandBuffer presentDrawable:cmdList->currentDrawable];
                    cmdList->currentDrawable = nil;
                }

                // Add completion handler to signal semaphore
                __block dispatch_semaphore_t sem = frameSemaphore;
                __block uint64_t frame = currentFrame;
                __block GraphicsDevice_Metal* self = this;

                [cmdList->commandBuffer addCompletedHandler:^(id<MTLCommandBuffer> buffer) {
                    dispatch_semaphore_signal(sem);
                    self->completedFrameCount = frame;
                    self->allocationHandler.Update(frame);
                }];

                // Commit the command buffer
                [cmdList->commandBuffer commit];
            }
        }

        // Reset for next frame
        activeCommandLists.clear();
        nextCommandListIndex = 0;

        // Reset frame allocators
        for (auto& allocator : frameAllocators)
        {
            allocator.reset();
        }

        FRAMECOUNT++;
    }

    void GraphicsDevice_Metal::WaitForGPU() const
    {
        // Wait for all in-flight frames to complete
        for (uint32_t i = 0; i < BUFFERCOUNT; ++i)
        {
            dispatch_semaphore_wait(frameSemaphore, DISPATCH_TIME_FOREVER);
        }
        for (uint32_t i = 0; i < BUFFERCOUNT; ++i)
        {
            dispatch_semaphore_signal(frameSemaphore);
        }
    }

    void GraphicsDevice_Metal::ClearPipelineStateCache()
    {
    }

    size_t GraphicsDevice_Metal::GetActivePipelineCount() const
    {
        return 0;
    }

    ShaderFormat GraphicsDevice_Metal::GetShaderFormat() const
    {
        return ShaderFormat::SPIRV; // Engine compiles HLSL to SPIRV, we convert to MSL via SPIRV-Cross
    }

    Texture GraphicsDevice_Metal::GetBackBuffer(const SwapChain* swapchain) const
    {
        if (!swapchain || !swapchain->internal_state)
            return Texture{};

        auto internal_state = to_internal<SwapChain_Metal>(swapchain);
        return internal_state->backBuffer;
    }

    ColorSpace GraphicsDevice_Metal::GetSwapChainColorSpace(const SwapChain* swapchain) const
    {
        if (!swapchain || !swapchain->internal_state)
            return ColorSpace::SRGB;

        auto internal_state = to_internal<SwapChain_Metal>(swapchain);
        return internal_state->colorSpace;
    }

    bool GraphicsDevice_Metal::IsSwapChainSupportsHDR(const SwapChain* swapchain) const
    {
        return false;
    }

    uint64_t GraphicsDevice_Metal::GetMinOffsetAlignment(const GPUBufferDesc* desc) const
    {
        return 256;
    }

    GraphicsDevice::MemoryUsage GraphicsDevice_Metal::GetMemoryUsage() const
    {
        MemoryUsage usage{};
        if (device)
        {
            if (@available(macOS 10.13, *))
            {
                usage.budget = [device recommendedMaxWorkingSetSize];
            }
        }
        return usage;
    }

    uint32_t GraphicsDevice_Metal::GetMaxViewportCount() const
    {
        return 16;
    }

    // ============================================
    // Command List Functions
    // ============================================

    void GraphicsDevice_Metal::WaitCommandList(CommandList cmd, CommandList wait_for)
    {
    }

    void GraphicsDevice_Metal::WaitQueue(CommandList cmd, QUEUE_TYPE wait_for)
    {
    }

    void GraphicsDevice_Metal::RenderPassBegin(const SwapChain* swapchain, CommandList cmd)
    {
        if (!swapchain || !swapchain->internal_state || !cmd.internal_state)
            return;

        auto swapchain_internal = to_internal<SwapChain_Metal>(swapchain);
        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        // Get next drawable
        swapchain_internal->currentDrawable = [swapchain_internal->metalLayer nextDrawable];
        if (!swapchain_internal->currentDrawable)
        {
            NSLog(@"Failed to get next drawable");
            return;
        }

        // Create render pass descriptor
        MTLRenderPassDescriptor* renderPassDesc = [MTLRenderPassDescriptor renderPassDescriptor];

        MTLRenderPassColorAttachmentDescriptor* colorAttachment = renderPassDesc.colorAttachments[0];
        colorAttachment.texture = swapchain_internal->currentDrawable.texture;
        colorAttachment.loadAction = MTLLoadActionClear;
        colorAttachment.storeAction = MTLStoreActionStore;
        colorAttachment.clearColor = MTLClearColorMake(
            swapchain_internal->desc.clear_color[0],
            swapchain_internal->desc.clear_color[1],
            swapchain_internal->desc.clear_color[2],
            swapchain_internal->desc.clear_color[3]);

        // Create render encoder
        cmdList->renderEncoder = [cmdList->commandBuffer renderCommandEncoderWithDescriptor:renderPassDesc];
        cmdList->renderEncoder.label = @"SwapChainRenderEncoder";
        cmdList->isInsideRenderPass = true;

        // Store drawable for presentation
        cmdList->currentDrawable = swapchain_internal->currentDrawable;

        // Update render pass info
        cmdList->renderPassInfo.rt_count = 1;
        cmdList->renderPassInfo.rt_formats[0] = swapchain->desc.format;
        cmdList->renderPassInfo.ds_format = Format::UNKNOWN;
        cmdList->renderPassInfo.sample_count = 1;

        // Update backbuffer internal state
        auto backbuffer_internal = std::make_shared<Texture_Metal>();
        backbuffer_internal->texture = swapchain_internal->currentDrawable.texture;
        backbuffer_internal->pixelFormat = swapchain_internal->metalLayer.pixelFormat;
        backbuffer_internal->width = swapchain->desc.width;
        backbuffer_internal->height = swapchain->desc.height;
        swapchain_internal->backBuffer.internal_state = backbuffer_internal;
    }

    void GraphicsDevice_Metal::RenderPassBegin(const RenderPassImage* images, uint32_t image_count, CommandList cmd, RenderPassFlags flags)
    {
        if (!images || image_count == 0 || !cmd.internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        MTLRenderPassDescriptor* renderPassDesc = [MTLRenderPassDescriptor renderPassDescriptor];

        uint32_t colorAttachmentIndex = 0;
        cmdList->renderPassInfo = {};

        for (uint32_t i = 0; i < image_count; ++i)
        {
            const RenderPassImage& image = images[i];
            if (!image.texture || !image.texture->internal_state)
                continue;

            auto tex_internal = to_internal<Texture_Metal>(image.texture);

            switch (image.type)
            {
            case RenderPassImage::Type::RENDERTARGET:
            {
                MTLRenderPassColorAttachmentDescriptor* colorAttachment = renderPassDesc.colorAttachments[colorAttachmentIndex];
                colorAttachment.texture = tex_internal->texture;

                switch (image.loadop)
                {
                case RenderPassImage::LoadOp::LOAD:
                    colorAttachment.loadAction = MTLLoadActionLoad;
                    break;
                case RenderPassImage::LoadOp::CLEAR:
                    colorAttachment.loadAction = MTLLoadActionClear;
                    colorAttachment.clearColor = MTLClearColorMake(
                        image.texture->desc.clear.color[0],
                        image.texture->desc.clear.color[1],
                        image.texture->desc.clear.color[2],
                        image.texture->desc.clear.color[3]);
                    break;
                case RenderPassImage::LoadOp::DONTCARE:
                    colorAttachment.loadAction = MTLLoadActionDontCare;
                    break;
                }

                colorAttachment.storeAction = image.storeop == RenderPassImage::StoreOp::STORE ?
                    MTLStoreActionStore : MTLStoreActionDontCare;

                cmdList->renderPassInfo.rt_formats[colorAttachmentIndex] = image.texture->desc.format;
                cmdList->renderPassInfo.sample_count = image.texture->desc.sample_count;
                colorAttachmentIndex++;
                break;
            }
            case RenderPassImage::Type::DEPTH_STENCIL:
            {
                renderPassDesc.depthAttachment.texture = tex_internal->texture;

                switch (image.loadop)
                {
                case RenderPassImage::LoadOp::LOAD:
                    renderPassDesc.depthAttachment.loadAction = MTLLoadActionLoad;
                    break;
                case RenderPassImage::LoadOp::CLEAR:
                    renderPassDesc.depthAttachment.loadAction = MTLLoadActionClear;
                    renderPassDesc.depthAttachment.clearDepth = image.texture->desc.clear.depth_stencil.depth;
                    break;
                case RenderPassImage::LoadOp::DONTCARE:
                    renderPassDesc.depthAttachment.loadAction = MTLLoadActionDontCare;
                    break;
                }

                renderPassDesc.depthAttachment.storeAction = image.storeop == RenderPassImage::StoreOp::STORE ?
                    MTLStoreActionStore : MTLStoreActionDontCare;

                if (IsFormatStencilSupport(image.texture->desc.format))
                {
                    renderPassDesc.stencilAttachment.texture = tex_internal->texture;
                    renderPassDesc.stencilAttachment.loadAction = renderPassDesc.depthAttachment.loadAction;
                    renderPassDesc.stencilAttachment.storeAction = renderPassDesc.depthAttachment.storeAction;
                    if (image.loadop == RenderPassImage::LoadOp::CLEAR)
                    {
                        renderPassDesc.stencilAttachment.clearStencil = image.texture->desc.clear.depth_stencil.stencil;
                    }
                }

                cmdList->renderPassInfo.ds_format = image.texture->desc.format;
                cmdList->renderPassInfo.sample_count = image.texture->desc.sample_count;
                break;
            }
            default:
                break;
            }
        }

        cmdList->renderPassInfo.rt_count = colorAttachmentIndex;

        cmdList->renderEncoder = [cmdList->commandBuffer renderCommandEncoderWithDescriptor:renderPassDesc];
        cmdList->renderEncoder.label = @"RenderPassEncoder";
        cmdList->isInsideRenderPass = true;
    }

    void GraphicsDevice_Metal::RenderPassEnd(CommandList cmd)
    {
        if (!cmd.internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder)
        {
            [cmdList->renderEncoder endEncoding];
            cmdList->renderEncoder = nil;
        }

        cmdList->isInsideRenderPass = false;
        cmdList->boundPipeline = nullptr;
    }

    void GraphicsDevice_Metal::BindScissorRects(uint32_t numRects, const Rect* rects, CommandList cmd)
    {
        if (!cmd.internal_state || !rects)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder)
        {
            cmdList->scissorRects.resize(numRects);
            for (uint32_t i = 0; i < numRects; ++i)
            {
                cmdList->scissorRects[i].x = rects[i].left;
                cmdList->scissorRects[i].y = rects[i].top;
                cmdList->scissorRects[i].width = rects[i].right - rects[i].left;
                cmdList->scissorRects[i].height = rects[i].bottom - rects[i].top;
            }
            [cmdList->renderEncoder setScissorRects:cmdList->scissorRects.data() count:numRects];
        }
    }

    void GraphicsDevice_Metal::BindViewports(uint32_t NumViewports, const Viewport* pViewports, CommandList cmd)
    {
        if (!cmd.internal_state || !pViewports)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder)
        {
            cmdList->viewports.resize(NumViewports);
            for (uint32_t i = 0; i < NumViewports; ++i)
            {
                cmdList->viewports[i].originX = pViewports[i].top_left_x;
                cmdList->viewports[i].originY = pViewports[i].top_left_y;
                cmdList->viewports[i].width = pViewports[i].width;
                cmdList->viewports[i].height = pViewports[i].height;
                cmdList->viewports[i].znear = pViewports[i].min_depth;
                cmdList->viewports[i].zfar = pViewports[i].max_depth;
            }
            [cmdList->renderEncoder setViewports:cmdList->viewports.data() count:NumViewports];
        }
    }

    void GraphicsDevice_Metal::BindResource(const GPUResource* resource, uint32_t slot, CommandList cmd, int subresource)
    {
        if (!cmd.internal_state || !resource || !resource->internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder)
        {
            if (resource->IsBuffer())
            {
                auto buffer_internal = to_internal<Resource_Metal>(resource);
                [cmdList->renderEncoder setVertexBuffer:buffer_internal->buffer offset:0 atIndex:slot];
                [cmdList->renderEncoder setFragmentBuffer:buffer_internal->buffer offset:0 atIndex:slot];
            }
            else if (resource->IsTexture())
            {
                auto tex_internal = to_internal<Texture_Metal>(resource);
                [cmdList->renderEncoder setVertexTexture:tex_internal->texture atIndex:slot];
                [cmdList->renderEncoder setFragmentTexture:tex_internal->texture atIndex:slot];
            }
        }
    }

    void GraphicsDevice_Metal::BindResources(const GPUResource* const* resources, uint32_t slot, uint32_t count, CommandList cmd)
    {
        for (uint32_t i = 0; i < count; ++i)
        {
            BindResource(resources[i], slot + i, cmd);
        }
    }

    void GraphicsDevice_Metal::BindUAV(const GPUResource* resource, uint32_t slot, CommandList cmd, int subresource)
    {
        // Similar to BindResource but for UAV
        BindResource(resource, slot, cmd, subresource);
    }

    void GraphicsDevice_Metal::BindUAVs(const GPUResource* const* resources, uint32_t slot, uint32_t count, CommandList cmd)
    {
        for (uint32_t i = 0; i < count; ++i)
        {
            BindUAV(resources[i], slot + i, cmd);
        }
    }

    void GraphicsDevice_Metal::BindSampler(const Sampler* sampler, uint32_t slot, CommandList cmd)
    {
        if (!cmd.internal_state || !sampler || !sampler->internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);
        auto sampler_internal = to_internal<Sampler_Metal>(sampler);

        if (cmdList->renderEncoder)
        {
            [cmdList->renderEncoder setVertexSamplerState:sampler_internal->sampler atIndex:slot];
            [cmdList->renderEncoder setFragmentSamplerState:sampler_internal->sampler atIndex:slot];
        }
    }

    void GraphicsDevice_Metal::BindConstantBuffer(const GPUBuffer* buffer, uint32_t slot, CommandList cmd, uint64_t offset)
    {
        if (!cmd.internal_state || !buffer || !buffer->internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);
        auto buffer_internal = to_internal<Resource_Metal>(buffer);

        if (cmdList->renderEncoder)
        {
            [cmdList->renderEncoder setVertexBuffer:buffer_internal->buffer offset:offset atIndex:slot];
            [cmdList->renderEncoder setFragmentBuffer:buffer_internal->buffer offset:offset atIndex:slot];
        }
    }

    void GraphicsDevice_Metal::BindVertexBuffers(const GPUBuffer* const* vertexBuffers, uint32_t slot, uint32_t count, const uint32_t* strides, const uint64_t* offsets, CommandList cmd)
    {
        if (!cmd.internal_state || !vertexBuffers)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder)
        {
            for (uint32_t i = 0; i < count; ++i)
            {
                if (vertexBuffers[i] && vertexBuffers[i]->internal_state)
                {
                    auto buffer_internal = to_internal<Resource_Metal>(vertexBuffers[i]);
                    uint64_t offset = offsets ? offsets[i] : 0;
                    [cmdList->renderEncoder setVertexBuffer:buffer_internal->buffer offset:offset atIndex:slot + i];
                }
            }
        }
    }

    void GraphicsDevice_Metal::BindIndexBuffer(const GPUBuffer* indexBuffer, const IndexBufferFormat format, uint64_t offset, CommandList cmd)
    {
        if (!cmd.internal_state || !indexBuffer || !indexBuffer->internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);
        auto buffer_internal = to_internal<Resource_Metal>(indexBuffer);

        cmdList->boundIndexBuffer = buffer_internal->buffer;
        cmdList->indexType = (format == IndexBufferFormat::UINT16) ? MTLIndexTypeUInt16 : MTLIndexTypeUInt32;
        cmdList->indexBufferOffset = offset;
    }

    void GraphicsDevice_Metal::BindStencilRef(uint32_t value, CommandList cmd)
    {
        if (!cmd.internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder)
        {
            [cmdList->renderEncoder setStencilReferenceValue:value];
        }
    }

    void GraphicsDevice_Metal::BindBlendFactor(float r, float g, float b, float a, CommandList cmd)
    {
        if (!cmd.internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder)
        {
            [cmdList->renderEncoder setBlendColorRed:r green:g blue:b alpha:a];
        }
    }

    void GraphicsDevice_Metal::BindPipelineState(const PipelineState* pso, CommandList cmd)
    {
        if (!cmd.internal_state || !pso || !pso->internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);
        auto pso_internal = to_internal<PipelineState_Metal>(pso);

        cmdList->boundPipeline = pso_internal;

        if (cmdList->renderEncoder)
        {
            if (pso_internal->renderPipeline)
            {
                [cmdList->renderEncoder setRenderPipelineState:pso_internal->renderPipeline];
            }

            if (pso_internal->depthStencilState)
            {
                [cmdList->renderEncoder setDepthStencilState:pso_internal->depthStencilState];
            }

            // Apply rasterizer state
            [cmdList->renderEncoder setCullMode:pso_internal->cullMode];
            [cmdList->renderEncoder setFrontFacingWinding:pso_internal->frontFace];
            [cmdList->renderEncoder setTriangleFillMode:pso_internal->fillMode];
            [cmdList->renderEncoder setDepthBias:pso_internal->depthBias
                slopeScale:pso_internal->slopeScaledDepthBias
                clamp:pso_internal->depthBiasClamp];

            if (@available(macOS 10.11, *))
            {
                [cmdList->renderEncoder setDepthClipMode:pso_internal->depthClipEnable ?
                    MTLDepthClipModeClip : MTLDepthClipModeClamp];
            }
        }
    }

    void GraphicsDevice_Metal::BindComputeShader(const Shader* cs, CommandList cmd)
    {
        // TODO: Implement compute shader binding
    }

    void GraphicsDevice_Metal::BindDepthBounds(float min_bounds, float max_bounds, CommandList cmd)
    {
        // Metal doesn't support depth bounds testing
    }

    // ============================================
    // Draw Commands
    // ============================================

    void GraphicsDevice_Metal::Draw(uint32_t vertexCount, uint32_t startVertexLocation, CommandList cmd)
    {
        if (!cmd.internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder && cmdList->boundPipeline)
        {
            [cmdList->renderEncoder drawPrimitives:cmdList->boundPipeline->primitiveType
                vertexStart:startVertexLocation
                vertexCount:vertexCount];
        }
    }

    void GraphicsDevice_Metal::DrawIndexed(uint32_t indexCount, uint32_t startIndexLocation, int32_t baseVertexLocation, CommandList cmd)
    {
        if (!cmd.internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder && cmdList->boundPipeline && cmdList->boundIndexBuffer)
        {
            uint32_t indexSize = (cmdList->indexType == MTLIndexTypeUInt16) ? 2 : 4;
            uint64_t indexBufferOffset = cmdList->indexBufferOffset + startIndexLocation * indexSize;

            [cmdList->renderEncoder drawIndexedPrimitives:cmdList->boundPipeline->primitiveType
                indexCount:indexCount
                indexType:cmdList->indexType
                indexBuffer:cmdList->boundIndexBuffer
                indexBufferOffset:indexBufferOffset
                instanceCount:1
                baseVertex:baseVertexLocation
                baseInstance:0];
        }
    }

    void GraphicsDevice_Metal::DrawInstanced(uint32_t vertexCount, uint32_t instanceCount, uint32_t startVertexLocation, uint32_t startInstanceLocation, CommandList cmd)
    {
        if (!cmd.internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder && cmdList->boundPipeline)
        {
            [cmdList->renderEncoder drawPrimitives:cmdList->boundPipeline->primitiveType
                vertexStart:startVertexLocation
                vertexCount:vertexCount
                instanceCount:instanceCount
                baseInstance:startInstanceLocation];
        }
    }

    void GraphicsDevice_Metal::DrawIndexedInstanced(uint32_t indexCount, uint32_t instanceCount, uint32_t startIndexLocation, int32_t baseVertexLocation, uint32_t startInstanceLocation, CommandList cmd)
    {
        if (!cmd.internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder && cmdList->boundPipeline && cmdList->boundIndexBuffer)
        {
            uint32_t indexSize = (cmdList->indexType == MTLIndexTypeUInt16) ? 2 : 4;
            uint64_t indexBufferOffset = cmdList->indexBufferOffset + startIndexLocation * indexSize;

            [cmdList->renderEncoder drawIndexedPrimitives:cmdList->boundPipeline->primitiveType
                indexCount:indexCount
                indexType:cmdList->indexType
                indexBuffer:cmdList->boundIndexBuffer
                indexBufferOffset:indexBufferOffset
                instanceCount:instanceCount
                baseVertex:baseVertexLocation
                baseInstance:startInstanceLocation];
        }
    }

    void GraphicsDevice_Metal::DrawInstancedIndirect(const GPUBuffer* args, uint64_t args_offset, CommandList cmd) {}
    void GraphicsDevice_Metal::DrawIndexedInstancedIndirect(const GPUBuffer* args, uint64_t args_offset, CommandList cmd) {}
    void GraphicsDevice_Metal::DrawInstancedIndirectCount(const GPUBuffer* args, uint64_t args_offset, const GPUBuffer* count, uint64_t count_offset, uint32_t max_count, CommandList cmd) {}
    void GraphicsDevice_Metal::DrawIndexedInstancedIndirectCount(const GPUBuffer* args, uint64_t args_offset, const GPUBuffer* count, uint64_t count_offset, uint32_t max_count, CommandList cmd) {}

    void GraphicsDevice_Metal::Dispatch(uint32_t threadGroupCountX, uint32_t threadGroupCountY, uint32_t threadGroupCountZ, CommandList cmd) {}
    void GraphicsDevice_Metal::DispatchIndirect(const GPUBuffer* args, uint64_t args_offset, CommandList cmd) {}

    void GraphicsDevice_Metal::CopyResource(const GPUResource* pDst, const GPUResource* pSrc, CommandList cmd) {}

    void GraphicsDevice_Metal::CopyBuffer(const GPUBuffer* pDst, uint64_t dst_offset, const GPUBuffer* pSrc, uint64_t src_offset, uint64_t size, CommandList cmd)
    {
        if (!cmd.internal_state || !pDst || !pSrc || !pDst->internal_state || !pSrc->internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);
        auto dst_internal = to_internal<Resource_Metal>(pDst);
        auto src_internal = to_internal<Resource_Metal>(pSrc);

        if (!cmdList->blitEncoder)
        {
            cmdList->blitEncoder = [cmdList->commandBuffer blitCommandEncoder];
        }

        [cmdList->blitEncoder copyFromBuffer:src_internal->buffer
            sourceOffset:src_offset
            toBuffer:dst_internal->buffer
            destinationOffset:dst_offset
            size:size];
    }

    void GraphicsDevice_Metal::CopyTexture(const Texture* dst, uint32_t dstX, uint32_t dstY, uint32_t dstZ, uint32_t dstMip, uint32_t dstSlice, const Texture* src, uint32_t srcMip, uint32_t srcSlice, CommandList cmd, const Box* srcbox, ImageAspect dst_aspect, ImageAspect src_aspect) {}

    void GraphicsDevice_Metal::QueryBegin(const GPUQueryHeap* heap, uint32_t index, CommandList cmd) {}
    void GraphicsDevice_Metal::QueryEnd(const GPUQueryHeap* heap, uint32_t index, CommandList cmd) {}
    void GraphicsDevice_Metal::QueryResolve(const GPUQueryHeap* heap, uint32_t index, uint32_t count, const GPUBuffer* dest, uint64_t dest_offset, CommandList cmd) {}
    void GraphicsDevice_Metal::Barrier(const GPUBarrier* barriers, uint32_t numBarriers, CommandList cmd) {}
    void GraphicsDevice_Metal::PushConstants(const void* data, uint32_t size, CommandList cmd, uint32_t offset) {}
    void GraphicsDevice_Metal::ClearUAV(const GPUResource* resource, uint32_t value, CommandList cmd) {}

    void GraphicsDevice_Metal::EventBegin(const char* name, CommandList cmd)
    {
        if (!cmd.internal_state || !name)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder)
        {
            [cmdList->renderEncoder pushDebugGroup:[NSString stringWithUTF8String:name]];
        }
    }

    void GraphicsDevice_Metal::EventEnd(CommandList cmd)
    {
        if (!cmd.internal_state)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder)
        {
            [cmdList->renderEncoder popDebugGroup];
        }
    }

    void GraphicsDevice_Metal::SetMarker(const char* name, CommandList cmd)
    {
        if (!cmd.internal_state || !name)
            return;

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);

        if (cmdList->renderEncoder)
        {
            [cmdList->renderEncoder insertDebugSignpost:[NSString stringWithUTF8String:name]];
        }
    }

    RenderPassInfo GraphicsDevice_Metal::GetRenderPassInfo(CommandList cmd)
    {
        if (!cmd.internal_state)
            return RenderPassInfo{};

        CommandList_Metal* cmdList = static_cast<CommandList_Metal*>(cmd.internal_state);
        return cmdList->renderPassInfo;
    }

    void GraphicsDevice_Metal::Map(GPUResource* resource)
    {
        // Already mapped at creation for UPLOAD/READBACK buffers
    }

    void GraphicsDevice_Metal::Unmap(GPUResource* resource)
    {
        // No action needed for Metal shared memory
    }

    GraphicsDevice::GPULinearAllocator& GraphicsDevice_Metal::GetFrameAllocator(CommandList cmd)
    {
        // Find the command list index
        std::lock_guard<std::mutex> lock(cmdListMutex);
        for (size_t i = 0; i < activeCommandLists.size(); ++i)
        {
            if (activeCommandLists[i].internal_state == cmd.internal_state)
            {
                return frameAllocators[i];
            }
        }
        return frameAllocators[0];
    }

#else
    // Non-Apple platforms - stub implementation
    GraphicsDevice_Metal::~GraphicsDevice_Metal() {}
    bool GraphicsDevice_Metal::Initialize(ValidationMode validationMode_, GPUPreference preference) { return false; }
    bool GraphicsDevice_Metal::CreateSwapChain(const SwapChainDesc* desc, vz::platform::window_type window, SwapChain* swapchain) const { return false; }
    bool GraphicsDevice_Metal::CreateBuffer2(const GPUBufferDesc* desc, const std::function<void(void* dest)>& init_callback, GPUBuffer* buffer, const GPUResource* alias, uint64_t alias_offset) const { return false; }
    void GraphicsDevice_Metal::UploadToBufferRegion(GPUBuffer* buffer, uint64_t offset, const void* data, uint64_t size) const {}
    bool GraphicsDevice_Metal::CreateTexture(const TextureDesc* desc, const SubresourceData* initial_data, Texture* texture, const GPUResource* alias, uint64_t alias_offset) const { return false; }
    bool GraphicsDevice_Metal::CreateShader(ShaderStage stage, const void* shadercode, size_t shadercode_size, Shader* shader) const { return false; }
    bool GraphicsDevice_Metal::CreateSampler(const SamplerDesc* desc, Sampler* sampler) const { return false; }
    bool GraphicsDevice_Metal::CreateQueryHeap(const GPUQueryHeapDesc* desc, GPUQueryHeap* queryheap) const { return false; }
    bool GraphicsDevice_Metal::CreatePipelineState(const PipelineStateDesc* desc, PipelineState* pso, const RenderPassInfo* renderpass_info) const { return false; }
    int GraphicsDevice_Metal::CreateSubresource(Texture* texture, SubresourceType type, uint32_t firstSlice, uint32_t sliceCount, uint32_t firstMip, uint32_t mipCount, const Format* format_change, const ImageAspect* aspect, const Swizzle* swizzle, float min_lod_clamp) const { return -1; }
    int GraphicsDevice_Metal::CreateSubresource(GPUBuffer* buffer, SubresourceType type, uint64_t offset, uint64_t size, const Format* format_change, const uint32_t* structuredbuffer_stride_change) const { return -1; }
    bool GraphicsDevice_Metal::OpenSharedResource(const void* device2, const void* srvDescHeap2, const int descriptorIndex, const Texture* textureShared, uint64_t& gpuDesciptorHandlerPtr, GPUResource& sharedRes, void** backendResPtr) { return false; }
    void GraphicsDevice_Metal::DeleteSubresources(GPUResource* resource) {}
    int GraphicsDevice_Metal::GetDescriptorIndex(const GPUResource* resource, SubresourceType type, int subresource) const { return -1; }
    int GraphicsDevice_Metal::GetDescriptorIndex(const Sampler* sampler) const { return -1; }
    CommandList GraphicsDevice_Metal::BeginCommandList(QUEUE_TYPE queue) { return CommandList{}; }
    void GraphicsDevice_Metal::SubmitCommandLists() { FRAMECOUNT++; }
    void GraphicsDevice_Metal::WaitForGPU() const {}
    void GraphicsDevice_Metal::ClearPipelineStateCache() {}
    size_t GraphicsDevice_Metal::GetActivePipelineCount() const { return 0; }
    ShaderFormat GraphicsDevice_Metal::GetShaderFormat() const { return ShaderFormat::SPIRV; }
    Texture GraphicsDevice_Metal::GetBackBuffer(const SwapChain* swapchain) const { return Texture{}; }
    ColorSpace GraphicsDevice_Metal::GetSwapChainColorSpace(const SwapChain* swapchain) const { return ColorSpace::SRGB; }
    bool GraphicsDevice_Metal::IsSwapChainSupportsHDR(const SwapChain* swapchain) const { return false; }
    uint64_t GraphicsDevice_Metal::GetMinOffsetAlignment(const GPUBufferDesc* desc) const { return 256; }
    GraphicsDevice::MemoryUsage GraphicsDevice_Metal::GetMemoryUsage() const { return MemoryUsage{}; }
    uint32_t GraphicsDevice_Metal::GetMaxViewportCount() const { return 16; }
    void GraphicsDevice_Metal::WaitCommandList(CommandList cmd, CommandList wait_for) {}
    void GraphicsDevice_Metal::WaitQueue(CommandList cmd, QUEUE_TYPE wait_for) {}
    void GraphicsDevice_Metal::RenderPassBegin(const SwapChain* swapchain, CommandList cmd) {}
    void GraphicsDevice_Metal::RenderPassBegin(const RenderPassImage* images, uint32_t image_count, CommandList cmd, RenderPassFlags flags) {}
    void GraphicsDevice_Metal::RenderPassEnd(CommandList cmd) {}
    void GraphicsDevice_Metal::BindScissorRects(uint32_t numRects, const Rect* rects, CommandList cmd) {}
    void GraphicsDevice_Metal::BindViewports(uint32_t NumViewports, const Viewport* pViewports, CommandList cmd) {}
    void GraphicsDevice_Metal::BindResource(const GPUResource* resource, uint32_t slot, CommandList cmd, int subresource) {}
    void GraphicsDevice_Metal::BindResources(const GPUResource* const* resources, uint32_t slot, uint32_t count, CommandList cmd) {}
    void GraphicsDevice_Metal::BindUAV(const GPUResource* resource, uint32_t slot, CommandList cmd, int subresource) {}
    void GraphicsDevice_Metal::BindUAVs(const GPUResource* const* resources, uint32_t slot, uint32_t count, CommandList cmd) {}
    void GraphicsDevice_Metal::BindSampler(const Sampler* sampler, uint32_t slot, CommandList cmd) {}
    void GraphicsDevice_Metal::BindConstantBuffer(const GPUBuffer* buffer, uint32_t slot, CommandList cmd, uint64_t offset) {}
    void GraphicsDevice_Metal::BindVertexBuffers(const GPUBuffer* const* vertexBuffers, uint32_t slot, uint32_t count, const uint32_t* strides, const uint64_t* offsets, CommandList cmd) {}
    void GraphicsDevice_Metal::BindIndexBuffer(const GPUBuffer* indexBuffer, const IndexBufferFormat format, uint64_t offset, CommandList cmd) {}
    void GraphicsDevice_Metal::BindStencilRef(uint32_t value, CommandList cmd) {}
    void GraphicsDevice_Metal::BindBlendFactor(float r, float g, float b, float a, CommandList cmd) {}
    void GraphicsDevice_Metal::BindPipelineState(const PipelineState* pso, CommandList cmd) {}
    void GraphicsDevice_Metal::BindComputeShader(const Shader* cs, CommandList cmd) {}
    void GraphicsDevice_Metal::BindDepthBounds(float min_bounds, float max_bounds, CommandList cmd) {}
    void GraphicsDevice_Metal::Draw(uint32_t vertexCount, uint32_t startVertexLocation, CommandList cmd) {}
    void GraphicsDevice_Metal::DrawIndexed(uint32_t indexCount, uint32_t startIndexLocation, int32_t baseVertexLocation, CommandList cmd) {}
    void GraphicsDevice_Metal::DrawInstanced(uint32_t vertexCount, uint32_t instanceCount, uint32_t startVertexLocation, uint32_t startInstanceLocation, CommandList cmd) {}
    void GraphicsDevice_Metal::DrawIndexedInstanced(uint32_t indexCount, uint32_t instanceCount, uint32_t startIndexLocation, int32_t baseVertexLocation, uint32_t startInstanceLocation, CommandList cmd) {}
    void GraphicsDevice_Metal::DrawInstancedIndirect(const GPUBuffer* args, uint64_t args_offset, CommandList cmd) {}
    void GraphicsDevice_Metal::DrawIndexedInstancedIndirect(const GPUBuffer* args, uint64_t args_offset, CommandList cmd) {}
    void GraphicsDevice_Metal::DrawInstancedIndirectCount(const GPUBuffer* args, uint64_t args_offset, const GPUBuffer* count, uint64_t count_offset, uint32_t max_count, CommandList cmd) {}
    void GraphicsDevice_Metal::DrawIndexedInstancedIndirectCount(const GPUBuffer* args, uint64_t args_offset, const GPUBuffer* count, uint64_t count_offset, uint32_t max_count, CommandList cmd) {}
    void GraphicsDevice_Metal::Dispatch(uint32_t threadGroupCountX, uint32_t threadGroupCountY, uint32_t threadGroupCountZ, CommandList cmd) {}
    void GraphicsDevice_Metal::DispatchIndirect(const GPUBuffer* args, uint64_t args_offset, CommandList cmd) {}
    void GraphicsDevice_Metal::CopyResource(const GPUResource* pDst, const GPUResource* pSrc, CommandList cmd) {}
    void GraphicsDevice_Metal::CopyBuffer(const GPUBuffer* pDst, uint64_t dst_offset, const GPUBuffer* pSrc, uint64_t src_offset, uint64_t size, CommandList cmd) {}
    void GraphicsDevice_Metal::CopyTexture(const Texture* dst, uint32_t dstX, uint32_t dstY, uint32_t dstZ, uint32_t dstMip, uint32_t dstSlice, const Texture* src, uint32_t srcMip, uint32_t srcSlice, CommandList cmd, const Box* srcbox, ImageAspect dst_aspect, ImageAspect src_aspect) {}
    void GraphicsDevice_Metal::QueryBegin(const GPUQueryHeap* heap, uint32_t index, CommandList cmd) {}
    void GraphicsDevice_Metal::QueryEnd(const GPUQueryHeap* heap, uint32_t index, CommandList cmd) {}
    void GraphicsDevice_Metal::QueryResolve(const GPUQueryHeap* heap, uint32_t index, uint32_t count, const GPUBuffer* dest, uint64_t dest_offset, CommandList cmd) {}
    void GraphicsDevice_Metal::Barrier(const GPUBarrier* barriers, uint32_t numBarriers, CommandList cmd) {}
    void GraphicsDevice_Metal::PushConstants(const void* data, uint32_t size, CommandList cmd, uint32_t offset) {}
    void GraphicsDevice_Metal::ClearUAV(const GPUResource* resource, uint32_t value, CommandList cmd) {}
    void GraphicsDevice_Metal::EventBegin(const char* name, CommandList cmd) {}
    void GraphicsDevice_Metal::EventEnd(CommandList cmd) {}
    void GraphicsDevice_Metal::SetMarker(const char* name, CommandList cmd) {}
    RenderPassInfo GraphicsDevice_Metal::GetRenderPassInfo(CommandList cmd) { return RenderPassInfo{}; }
    void GraphicsDevice_Metal::Map(GPUResource* resource) {}
    void GraphicsDevice_Metal::Unmap(GPUResource* resource) {}
    GraphicsDevice::GPULinearAllocator& GraphicsDevice_Metal::GetFrameAllocator(CommandList cmd) { static GPULinearAllocator allocator; return allocator; }
#endif
}
