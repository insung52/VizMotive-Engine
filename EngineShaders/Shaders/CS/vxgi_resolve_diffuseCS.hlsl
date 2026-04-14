// VXGI Resolve Diffuse Compute Shader
// 화면 각 픽셀에서 diffuse cone tracing을 수행하여 2D 텍스처에 기록한다.
// 결과는 shadingHF.hlsli의 texture_vxgi_diffuse_index 경로에서 사용된다.

#include "../globals.hlsli"
#include "../ShaderInterop_VXGI.h"
#include "../CommonHF/voxelConeTracingHF.hlsli"

Texture2D<float>   input_depth  : register(t0);
Texture2D<half4>   input_normal : register(t1);  // encoded world-space normal
RWTexture2D<half4> output       : register(u0);

[numthreads(8, 8, 1)]
void main(uint3 DTid : SV_DispatchThreadID)
{
	const uint2 res = GetCamera().internal_resolution;
	if (any(DTid.xy >= res))
		return;

	float depth = input_depth[DTid.xy];
	if (depth == 0.0f)
	{
		output[DTid.xy] = 0;
		return;
	}

	// 세계 좌표 복원: ShaderCamera.screen_to_world() 사용
	float2 uv = ((float2)DTid.xy + 0.5f) * GetCamera().internal_resolution_rcp;
	float4 clipPos = float4(uv * float2(2, -2) + float2(-1, 1), depth, 1);
	float4 worldPos = mul(GetCamera().inverse_view_projection, clipPos);
	float3 P = worldPos.xyz / worldPos.w;

	// texture_normal은 oct-encoded half2로 저장됨 (screenspaceshadowCS 패턴 참고)
	float3 N = normalize((float3)decode_oct((half2)input_normal[DTid.xy].xy));

	if (GetFrame().vxgi.texture_radiance < 0 || GetFrame().vxgi.resolution == 0)
	{
		output[DTid.xy] = 0;
		return;
	}

	Texture3D<half4> voxels = bindless_textures3D_half4[descriptor_index(GetFrame().vxgi.texture_radiance)];
	float4 result = ConeTraceDiffuse(voxels, P, N);
	output[DTid.xy] = (half4)result;
}
