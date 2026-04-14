// VXGI SDF Jump Flood Compute Shader
// texture_radiance의 opacity(alpha) 채널에서 SDF를 생성한다.
// Jump Flooding Algorithm (JFA) 방식으로 near-SDF를 근사한다.
//
// texture_sdf 레이아웃: (res, VXGI_CLIPMAP_COUNT*res, res)
//
// MiscCB(g_xTransform) 재사용:
//   g_xTransform._11 = step 크기
//   g_xTransform._12 = 초기화 패스 여부 (>0.5 이면 init)
//   g_xTransform._13 = clipmap_index

#include "../globals.hlsli"
#include "../ShaderInterop_VXGI.h"

// MiscCB는 globals.hlsli → ShaderInterop_Renderer.h 에서 이미 CBUFFER로 선언됨
// (g_xTransform 포함). 별도 선언 불필요.

Texture3D<float>    input_sdf      : register(t0);
Texture3D<half4>    input_radiance : register(t1);  // opacity 소스 (초기화 패스)
RWTexture3D<float>  output_sdf     : register(u0);

[numthreads(8, 8, 8)]
void main(uint3 DTid : SV_DispatchThreadID)
{
	const uint res = GetFrame().vxgi.resolution;
	if (any(DTid >= res))
		return;

	const uint  clip   = (uint)g_xTransform._13;
	const bool  isInit = g_xTransform._12 > 0.5f;
	const int   step   = (int)g_xTransform._11;

	uint3 sdf_coord = uint3(DTid.x, DTid.y + clip * res, DTid.z);

	if (isInit)
	{
		// 초기화: anisotropic face 0의 alpha > 0.1 이면 0(filled), 아니면 max
		uint3 rad_coord = uint3(DTid.x, DTid.y + clip * res, DTid.z);
		half4 rad = input_radiance[rad_coord];
		output_sdf[sdf_coord] = rad.a > 0.1h ? 0.0f : (float)res;
		return;
	}

	// JFA: 이웃 27개(step 거리) 중 최솟값 전파
	float minDist = input_sdf[sdf_coord];
	for (int dz = -1; dz <= 1; dz++)
	for (int dy = -1; dy <= 1; dy++)
	for (int dx = -1; dx <= 1; dx++)
	{
		int3 neighbor = (int3)DTid + int3(dx, dy, dz) * step;
		if (any(neighbor < 0) || any(neighbor >= (int)res))
			continue;

		uint3 nc = uint3((uint)neighbor.x, (uint)neighbor.y + clip * res, (uint)neighbor.z);
		float seed = input_sdf[nc];
		float d = seed + length(float3(dx, dy, dz) * (float)step);
		if (d < minDist)
			minDist = d;
	}

	// 복셀 단위 → 월드 공간 단위 (voxelSize = half-extent, *2 = full voxel size)
	VoxelClipMap clipmap = GetFrame().vxgi.clipmaps[clip];
	output_sdf[sdf_coord] = minDist * clipmap.voxelSize * 2.0f;
}
