// MeshShaders.metal - Basic mesh rendering shaders for Metal backend
// VizMotive Engine - Phase 5B: Scene-based mesh rendering

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
struct VertexOut {
    float4 position [[position]];
    float3 worldPos;
    float3 normal;
    float2 texcoord;
    float4 color;
};

// ============================================
// Basic Mesh Vertex Shader
// ============================================
vertex VertexOut mesh_vertex(
    VertexIn in [[stage_in]],
    constant CameraConstants& camera [[buffer(0)]],
    constant InstanceConstants& instance [[buffer(1)]])
{
    VertexOut out;

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

// ============================================
// Basic Mesh Fragment Shader (Solid Color)
// ============================================
fragment float4 mesh_fragment_solid(VertexOut in [[stage_in]])
{
    return in.color;
}

// ============================================
// Basic Mesh Fragment Shader (Simple Lighting)
// ============================================
fragment float4 mesh_fragment_lit(
    VertexOut in [[stage_in]],
    constant CameraConstants& camera [[buffer(0)]])
{
    // Simple directional light from above-right
    float3 lightDir = normalize(float3(0.5, 1.0, 0.3));
    float3 normal = normalize(in.normal);

    // Diffuse lighting
    float NdotL = max(dot(normal, lightDir), 0.0);
    float ambient = 0.2;
    float diffuse = NdotL * 0.8;

    float3 finalColor = in.color.rgb * (ambient + diffuse);

    return float4(finalColor, in.color.a);
}

// ============================================
// Debug: Render normals as color
// ============================================
fragment float4 mesh_fragment_debug_normal(VertexOut in [[stage_in]])
{
    float3 normal = normalize(in.normal);
    // Map normal from [-1,1] to [0,1] for visualization
    float3 color = normal * 0.5 + 0.5;
    return float4(color, 1.0);
}

// ============================================
// Wireframe support (for debug rendering)
// ============================================
struct WireframeVertexOut {
    float4 position [[position]];
    float4 color;
};

vertex WireframeVertexOut wireframe_vertex(
    uint vid [[vertex_id]],
    constant float3* positions [[buffer(0)]],
    constant CameraConstants& camera [[buffer(1)]],
    constant InstanceConstants& instance [[buffer(2)]])
{
    WireframeVertexOut out;

    float4 worldPos = instance.world * float4(positions[vid], 1.0);
    out.position = camera.viewProjection * worldPos;
    out.color = instance.color;

    return out;
}

fragment float4 wireframe_fragment(WireframeVertexOut in [[stage_in]])
{
    return in.color;
}

// ============================================
// Simple position-only vertex shader (for depth prepass)
// ============================================
struct PositionOnlyOut {
    float4 position [[position]];
};

vertex PositionOnlyOut depth_prepass_vertex(
    uint vid [[vertex_id]],
    constant float3* positions [[buffer(0)]],
    constant CameraConstants& camera [[buffer(1)]],
    constant float4x4& world [[buffer(2)]])
{
    PositionOnlyOut out;

    float4 worldPos = world * float4(positions[vid], 1.0);
    out.position = camera.viewProjection * worldPos;

    return out;
}
