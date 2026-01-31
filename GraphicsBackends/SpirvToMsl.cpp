#include "SpirvToMsl.h"

#ifdef __APPLE__
#include "spirv_msl.hpp"
#include <sstream>

namespace vz::graphics
{
    // SPIRV magic number (little-endian)
    static constexpr uint32_t SPIRV_MAGIC = 0x07230203;

    bool IsSpirvBytecode(const void* data, size_t size)
    {
        if (data == nullptr || size < 4)
            return false;

        const uint32_t* words = static_cast<const uint32_t*>(data);
        return words[0] == SPIRV_MAGIC;
    }

    SpirvToMslResult ConvertSpirvToMsl(
        const uint32_t* spirv_data,
        size_t spirv_size,
        const SpirvToMslOptions& options)
    {
        SpirvToMslResult result;
        result.success = false;

        if (spirv_data == nullptr || spirv_size == 0)
        {
            result.error_message = "Invalid SPIRV data";
            return result;
        }

        // Verify SPIRV magic number
        if (spirv_data[0] != SPIRV_MAGIC)
        {
            result.error_message = "Invalid SPIRV magic number";
            return result;
        }

        try
        {
            // Create SPIRV-Cross MSL compiler
            size_t word_count = spirv_size / sizeof(uint32_t);
            spirv_cross::CompilerMSL msl_compiler(spirv_data, word_count);

            // Configure MSL options
            spirv_cross::CompilerMSL::Options msl_opts;
            msl_opts.msl_version = options.msl_version;
            msl_opts.platform = static_cast<spirv_cross::CompilerMSL::Options::Platform>(options.platform);
            msl_opts.enable_point_size_builtin = options.enable_point_size_builtin;
            msl_opts.disable_rasterization = options.disable_rasterization;
            msl_opts.capture_output_to_buffer = options.capture_output_to_buffer;
            msl_opts.swizzle_texture_samples = options.swizzle_texture_samples;
            msl_opts.texel_buffer_texture_width = options.texel_buffer_texture_width;
            msl_opts.argument_buffers = (options.argument_buffer_tier > 0);

            msl_compiler.set_msl_options(msl_opts);

            // Get shader resources for binding remapping
            spirv_cross::ShaderResources resources = msl_compiler.get_shader_resources();

            // Remap uniform buffers (constant buffers)
            uint32_t buffer_index = 0;
            for (const auto& ub : resources.uniform_buffers)
            {
                uint32_t set = msl_compiler.get_decoration(ub.id, spv::DecorationDescriptorSet);
                uint32_t binding = msl_compiler.get_decoration(ub.id, spv::DecorationBinding);

                spirv_cross::MSLResourceBinding msl_binding;
                msl_binding.stage = msl_compiler.get_execution_model();
                msl_binding.desc_set = set;
                msl_binding.binding = binding;
                msl_binding.msl_buffer = buffer_index;
                msl_binding.msl_texture = 0;
                msl_binding.msl_sampler = 0;
                msl_compiler.add_msl_resource_binding(msl_binding);

                SpirvToMslResult::ResourceBinding rb;
                rb.spirv_set = set;
                rb.spirv_binding = binding;
                rb.msl_buffer = buffer_index;
                rb.msl_texture = 0;
                rb.msl_sampler = 0;
                result.resource_bindings.push_back(rb);

                buffer_index++;
            }

            // Remap storage buffers
            for (const auto& sb : resources.storage_buffers)
            {
                uint32_t set = msl_compiler.get_decoration(sb.id, spv::DecorationDescriptorSet);
                uint32_t binding = msl_compiler.get_decoration(sb.id, spv::DecorationBinding);

                spirv_cross::MSLResourceBinding msl_binding;
                msl_binding.stage = msl_compiler.get_execution_model();
                msl_binding.desc_set = set;
                msl_binding.binding = binding;
                msl_binding.msl_buffer = buffer_index;
                msl_binding.msl_texture = 0;
                msl_binding.msl_sampler = 0;
                msl_compiler.add_msl_resource_binding(msl_binding);

                SpirvToMslResult::ResourceBinding rb;
                rb.spirv_set = set;
                rb.spirv_binding = binding;
                rb.msl_buffer = buffer_index;
                rb.msl_texture = 0;
                rb.msl_sampler = 0;
                result.resource_bindings.push_back(rb);

                buffer_index++;
            }

            // Remap textures
            uint32_t texture_index = 0;
            for (const auto& img : resources.sampled_images)
            {
                uint32_t set = msl_compiler.get_decoration(img.id, spv::DecorationDescriptorSet);
                uint32_t binding = msl_compiler.get_decoration(img.id, spv::DecorationBinding);

                spirv_cross::MSLResourceBinding msl_binding;
                msl_binding.stage = msl_compiler.get_execution_model();
                msl_binding.desc_set = set;
                msl_binding.binding = binding;
                msl_binding.msl_buffer = 0;
                msl_binding.msl_texture = texture_index;
                msl_binding.msl_sampler = texture_index;
                msl_compiler.add_msl_resource_binding(msl_binding);

                SpirvToMslResult::ResourceBinding rb;
                rb.spirv_set = set;
                rb.spirv_binding = binding;
                rb.msl_buffer = 0;
                rb.msl_texture = texture_index;
                rb.msl_sampler = texture_index;
                result.resource_bindings.push_back(rb);

                texture_index++;
            }

            // Remap separate images
            for (const auto& img : resources.separate_images)
            {
                uint32_t set = msl_compiler.get_decoration(img.id, spv::DecorationDescriptorSet);
                uint32_t binding = msl_compiler.get_decoration(img.id, spv::DecorationBinding);

                spirv_cross::MSLResourceBinding msl_binding;
                msl_binding.stage = msl_compiler.get_execution_model();
                msl_binding.desc_set = set;
                msl_binding.binding = binding;
                msl_binding.msl_buffer = 0;
                msl_binding.msl_texture = texture_index;
                msl_binding.msl_sampler = 0;
                msl_compiler.add_msl_resource_binding(msl_binding);

                SpirvToMslResult::ResourceBinding rb;
                rb.spirv_set = set;
                rb.spirv_binding = binding;
                rb.msl_buffer = 0;
                rb.msl_texture = texture_index;
                rb.msl_sampler = 0;
                result.resource_bindings.push_back(rb);

                texture_index++;
            }

            // Remap separate samplers
            uint32_t sampler_index = 0;
            for (const auto& samp : resources.separate_samplers)
            {
                uint32_t set = msl_compiler.get_decoration(samp.id, spv::DecorationDescriptorSet);
                uint32_t binding = msl_compiler.get_decoration(samp.id, spv::DecorationBinding);

                spirv_cross::MSLResourceBinding msl_binding;
                msl_binding.stage = msl_compiler.get_execution_model();
                msl_binding.desc_set = set;
                msl_binding.binding = binding;
                msl_binding.msl_buffer = 0;
                msl_binding.msl_texture = 0;
                msl_binding.msl_sampler = sampler_index;
                msl_compiler.add_msl_resource_binding(msl_binding);

                SpirvToMslResult::ResourceBinding rb;
                rb.spirv_set = set;
                rb.spirv_binding = binding;
                rb.msl_buffer = 0;
                rb.msl_texture = 0;
                rb.msl_sampler = sampler_index;
                result.resource_bindings.push_back(rb);

                sampler_index++;
            }

            // Compile to MSL
            result.msl_source = msl_compiler.compile();

            // Get entry point name
            auto entry_points = msl_compiler.get_entry_points_and_stages();
            if (!entry_points.empty())
            {
                result.entry_point_name = msl_compiler.get_cleansed_entry_point_name(
                    entry_points[0].name, entry_points[0].execution_model);
            }

            result.success = true;
        }
        catch (const spirv_cross::CompilerError& e)
        {
            result.error_message = std::string("SPIRV-Cross compilation error: ") + e.what();
        }
        catch (const std::exception& e)
        {
            result.error_message = std::string("Exception during SPIRV to MSL conversion: ") + e.what();
        }

        return result;
    }
}

#else
// Non-Apple platforms - stub implementation
namespace vz::graphics
{
    bool IsSpirvBytecode(const void* data, size_t size)
    {
        return false;
    }

    SpirvToMslResult ConvertSpirvToMsl(
        const uint32_t* spirv_data,
        size_t spirv_size,
        const SpirvToMslOptions& options)
    {
        SpirvToMslResult result;
        result.success = false;
        result.error_message = "SPIRV to MSL conversion not supported on this platform";
        return result;
    }
}
#endif
