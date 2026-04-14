#include "../globals.hlsli"
#include "../CommonHF/cube.hlsli"

struct GSOutput
{
	float4 pos : SV_POSITION;
	float4 col : TEXCOORD;
};

[maxvertexcount(36)]
void main(
	point uint input[1] : VERTEXID,
	inout TriangleStream<GSOutput> output
)
{
	uint voxel_index = input[0];
	uint clipmap_index = (uint)g_xColor.x;

	bool all_clips = false;
	if (clipmap_index == VXGI_CLIPMAP_COUNT)
	{
		all_clips = true;
		const uint voxel_count = GetFrame().vxgi.resolution * GetFrame().vxgi.resolution * GetFrame().vxgi.resolution;
		voxel_index = input[0] % voxel_count;
		clipmap_index = input[0] / voxel_count;
	}

	const uint res = GetFrame().vxgi.resolution;
	uint3 coord = unflatten3D(voxel_index, res);
	float3 uvw = (coord + 0.5) * GetFrame().vxgi.resolution_rcp;

	VoxelClipMap clipmap = GetFrame().vxgi.clipmaps[clipmap_index];

	uint3 pixel = coord;
	pixel.y += clipmap_index * res;

	Texture3D<half4> voxels = bindless_textures3D_half4[descriptor_index(GetFrame().vxgi.texture_radiance)];

	// 6개 face의 실제 radiance 읽기
	float4 face_colors[6];
	[unroll]
	for (uint fi = 0; fi < 6; fi++)
		face_colors[fi] = (float4)voxels[pixel + uint3(fi * res, 0, 0)];

	// 6면 모두 alpha == 0이면 빈 복셀 → 스킵
	if (
		face_colors[0].a == 0 &&
		face_colors[1].a == 0 &&
		face_colors[2].a == 0 &&
		face_colors[3].a == 0 &&
		face_colors[4].a == 0 &&
		face_colors[5].a == 0
	)
		return;

	// all_clips 모드: 하위 clipmap과 겹치는 영역 숨김
	if (all_clips && clipmap_index > 0)
	{
		VoxelClipMap clipmap_below = GetFrame().vxgi.clipmaps[clipmap_index - 1];
		float3 P = clipmap.center + (uvw * 2.0 - 1.0) * float3(1, -1, 1) * clipmap.voxelSize * (float)res;
		float3 uvw_below = (P - clipmap_below.center) * GetFrame().vxgi.resolution_rcp / clipmap_below.voxelSize;
		uvw_below = uvw_below * float3(0.5, -0.5, 0.5) + 0.5;
		if (is_saturated(uvw_below))
			return;
	}

	// local space 복셀 중심
	float3 center_local = (uvw * 2.0 - 1.0) * float3(1, -1, 1) * (float)res;

	for (uint i = 0; i < 36; i += 3)
	{
		GSOutput tri[3];
		uint j = 0;
		for (j = 0; j < 3; ++j)
			tri[j].pos.xyz = center_local - CUBE[i + j].xyz;

		// 삼각형 face normal → 해당 방향의 radiance 색상 선택
		float3 facenormal = -normalize(cross(tri[2].pos.xyz - tri[1].pos.xyz, tri[1].pos.xyz - tri[0].pos.xyz));
		float4 color = face_colors[(uint)cubemap_to_uv(facenormal).z];
		if (color.a == 0)
		{
			// alpha 0인 면도 검은색으로 표시 (면이 사라지는 현상 방지)
			color = float4(0, 0, 0, 1);
		}

		if (color.a > 0)
		for (j = 0; j < 3; ++j)
		{
			tri[j].pos.xyz *= clipmap.voxelSize;
			tri[j].pos.xyz += clipmap.center;
			tri[j].pos = mul(g_xTransform, float4(tri[j].pos.xyz, 1));
			tri[j].col = color;
			output.Append(tri[j]);
		}

		output.RestartStrip();
	}
}
