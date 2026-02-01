// SimpleShaders.metal - Simple triangle shaders for Metal backend verification
// VizMotive Engine - Phase 5A: Hardcoded triangle rendering

#include <metal_stdlib>
using namespace metal;

struct VertexOut {
    float4 position [[position]];
    float3 color;
};

vertex VertexOut simple_vertex(uint vid [[vertex_id]]) {
    // Hardcoded triangle vertices in NDC
    float2 positions[3] = {
        float2(-0.5, -0.5),  // Bottom-left
        float2( 0.5, -0.5),  // Bottom-right
        float2( 0.0,  0.5)   // Top-center
    };

    // RGB colors for each vertex
    float3 colors[3] = {
        float3(1.0, 0.0, 0.0),  // Red
        float3(0.0, 1.0, 0.0),  // Green
        float3(0.0, 0.0, 1.0)   // Blue
    };

    VertexOut out;
    out.position = float4(positions[vid], 0.0, 1.0);
    out.color = colors[vid];
    return out;
}

fragment float4 simple_fragment(VertexOut in [[stage_in]]) {
    return float4(in.color, 1.0);
}
