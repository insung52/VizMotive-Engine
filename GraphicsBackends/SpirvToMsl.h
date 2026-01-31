#pragma once

#include <string>
#include <vector>
#include <cstdint>

namespace vz::graphics
{
    // Options for SPIRV to MSL conversion
    struct SpirvToMslOptions
    {
        uint32_t msl_version = 20100;  // Metal 2.1 (macOS 10.14+)
        bool enable_point_size_builtin = false;
        bool disable_rasterization = false;
        bool capture_output_to_buffer = false;
        bool swizzle_texture_samples = false;
        bool texel_buffer_texture_width = 4096;

        // Platform (0 = macOS, 1 = iOS)
        uint32_t platform = 0;

        // Argument buffer tier (0 = tier1, 1 = tier2)
        uint32_t argument_buffer_tier = 0;
    };

    // Result of SPIRV to MSL conversion
    struct SpirvToMslResult
    {
        bool success = false;
        std::string msl_source;
        std::string error_message;

        // Entry point info
        std::string entry_point_name;

        // Resource binding info (for reflection)
        struct ResourceBinding
        {
            uint32_t spirv_binding;
            uint32_t spirv_set;
            uint32_t msl_buffer;
            uint32_t msl_texture;
            uint32_t msl_sampler;
        };
        std::vector<ResourceBinding> resource_bindings;
    };

    // Convert SPIRV bytecode to Metal Shading Language
    // @param spirv_data: Pointer to SPIRV bytecode (must be 4-byte aligned)
    // @param spirv_size: Size of SPIRV bytecode in bytes
    // @param options: Conversion options
    // @return: Conversion result with MSL source or error message
    SpirvToMslResult ConvertSpirvToMsl(
        const uint32_t* spirv_data,
        size_t spirv_size,
        const SpirvToMslOptions& options = SpirvToMslOptions{}
    );

    // Utility to check if data looks like SPIRV bytecode
    bool IsSpirvBytecode(const void* data, size_t size);
}
