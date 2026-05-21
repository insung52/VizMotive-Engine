// VXGI Temporal Blend Compute Shader
// offsetprevCS가 시프트해 놓은 prev_radiance와 이번 프레임 atomic 데이터를 블렌딩하여
// output_radiance를 업데이트한다.
//
// 읽기 전용 입력:
//   t0: input_prev_radiance  (offsetprevCS 결과, 그리드 시프트 반영됨)
//   t1: input_atomic         (이번 프레임 복셀화 결과)
// 쓰기 전용 출력:
//   u0: output_radiance      (이번 프레임 최종 radiance)
//
// 읽기/쓰기 텍스처 분리로 race condition 완전 제거.
// cone 슬라이스는 로컬 배열에서 계산하므로 동기화 불필요.

#include "../globals.hlsli"
#include "../ShaderInterop_VXGI.h"
#include "../CommonHF/voxelHF.hlsli"
#include "../CommonHF/voxelConeTracingHF.hlsli"

PUSHCONSTANT(push, VoxelizerCB);

Texture3D<half4>    input_prev_radiance : register(t0);
Texture3D<uint>     input_atomic        : register(t1);
RWTexture3D<half4>  output_radiance     : register(u0);

static const float BLEND_SPEED = 0.05f;

[numthreads(8, 8, 8)]
void main(uint3 DTid : SV_DispatchThreadID)
{
	const uint res  = GetFrame().vxgi.resolution;
	const uint clip = (uint)push.clipmap_index;
	VoxelClipMap clipmap = GetFrame().vxgi.clipmaps[clip];

	if (any(DTid >= res))
		return;

	// input_prev_radiance는 offsetprevCS가 이미 그리드 시프트를 반영해 썼음.
	// [oc] 좌표로 그냥 읽으면 world-position 정렬된 이전 프레임 데이터 (또는 새 복셀이면 0).

	// 카메라 이동으로 그리드가 스크롤됐을 때, 이번 프레임에 새로 들어온 복셀인지 판별.
	// 새 복셀(is_new_voxel=true)은 이전 프레임 데이터가 없으므로 temporal blend 스킵 →
	// newVal을 즉시 사용해 검정에서 서서히 밝아지는 현상(pop-in) 방지.
	int3 prev_dtid = (int3)DTid + push.offsetfromPrevFrame;
	bool is_new_voxel = any(prev_dtid < 0) || any(prev_dtid >= (int)res);

	// 6개 anisotropic face radiance를 로컬 배열에 보관 → cone 계산 시 텍스처 읽기 불필요
	half4 aniso_colors[6];

	// ── anisotropic 6면 처리 ──
	for (uint face = 0; face < 6; face++)
	{
		uint3 ac = uint3(DTid.x + face * res, DTid.y, DTid.z * VOXELIZATION_CHANNEL_COUNT);
		uint frag = input_atomic[ac + uint3(0, 0, VOXELIZATION_CHANNEL_FRAGMENT_COUNTER)];

		uint3 oc = uint3(DTid.x + face * res, DTid.y + clip * res, DTid.z);

		half4 radiance = (half4)0;

		if (frag > 0)
		{
			float inv = 1.0f / (float)frag;
			float3 basecolor = float3(
				UnpackVoxelChannel(input_atomic[ac + uint3(0, 0, VOXELIZATION_CHANNEL_BASECOLOR_R)]),
				UnpackVoxelChannel(input_atomic[ac + uint3(0, 0, VOXELIZATION_CHANNEL_BASECOLOR_G)]),
				UnpackVoxelChannel(input_atomic[ac + uint3(0, 0, VOXELIZATION_CHANNEL_BASECOLOR_B)])) * inv;
			float alpha = UnpackVoxelChannel(input_atomic[ac + uint3(0, 0, VOXELIZATION_CHANNEL_BASECOLOR_A)]) * inv;
			float3 emissive = float3(
				UnpackVoxelChannel(input_atomic[ac + uint3(0, 0, VOXELIZATION_CHANNEL_EMISSIVE_R)]),
				UnpackVoxelChannel(input_atomic[ac + uint3(0, 0, VOXELIZATION_CHANNEL_EMISSIVE_G)]),
				UnpackVoxelChannel(input_atomic[ac + uint3(0, 0, VOXELIZATION_CHANNEL_EMISSIVE_B)])) * inv;
			float3 directlight = float3(
				UnpackVoxelChannel(input_atomic[ac + uint3(0, 0, VOXELIZATION_CHANNEL_DIRECTLIGHT_R)]),
				UnpackVoxelChannel(input_atomic[ac + uint3(0, 0, VOXELIZATION_CHANNEL_DIRECTLIGHT_G)]),
				UnpackVoxelChannel(input_atomic[ac + uint3(0, 0, VOXELIZATION_CHANNEL_DIRECTLIGHT_B)])) * inv;

			// 표면 법선 복원 (간접광 cone tracing에 필요)
			float2 N_packed = float2(
				UnpackVoxelChannel(input_atomic[ac + uint3(0, 0, VOXELIZATION_CHANNEL_NORMAL_R)]),
				UnpackVoxelChannel(input_atomic[ac + uint3(0, 0, VOXELIZATION_CHANNEL_NORMAL_G)])) * inv;
			float3 N = (float3)decode_oct(N_packed * 2 - 1);

			// 이전 프레임 voxel radiance로 간접광 계산 (multi-bounce)
			float3 P = GetFrame().vxgi.clipmap_to_world((DTid + 0.5) * GetFrame().vxgi.resolution_rcp, clipmap);
			float4 trace = ConeTraceDiffuse(input_prev_radiance, P, N);
			float3 indirect = trace.rgb;
			indirect += (float3)GetAmbientColor() * (1 - trace.a); // cone이 닿지 않은 영역은 ambient로 보완

			float4 newVal = float4(basecolor * (directlight / PI + indirect) + emissive, alpha);

			if (is_new_voxel)
			{
				// 새로 진입한 복셀: 이전 프레임 데이터 없음 → 즉시 newVal 사용 (pop-in 방지)
				radiance = (half4)newVal;
			}
			else
			{
				// 기존 복셀: temporal blend로 안정화
				float4 prev = (float4)input_prev_radiance[oc];
				radiance = (half4)lerp(prev, newVal, BLEND_SPEED);
			}
		}
		else
		{
			// 이번 프레임에 geometry 없음 → 즉시 0으로 초기화.
			// prev를 보존하면 메시가 이동한 경로에 ghost 복셀이 영구 잔류함.
			radiance = (half4)0;
		}

		output_radiance[oc] = radiance;
		aniso_colors[face] = radiance;
	}

	// ── precomputed cone direction 슬라이스 계산 ──
	// 로컬 aniso_colors 배열에서 읽으므로 텍스처 동기화 불필요
	for (uint ci = 0; ci < DIFFUSE_CONE_COUNT; ci++)
	{
		float3 cone_dir = DIFFUSE_CONE_DIRECTIONS[ci];
		float3 weights  = abs(cone_dir);

		uint face_x = cone_dir.x > 0 ? 0 : 1;
		uint face_y = cone_dir.y > 0 ? 2 : 3;
		uint face_z = cone_dir.z > 0 ? 4 : 5;

		half4 sam =
			aniso_colors[face_x] * (half)weights.x +
			aniso_colors[face_y] * (half)weights.y +
			aniso_colors[face_z] * (half)weights.z;

		uint3 oc_cone = uint3(DTid.x + (6 + ci) * res, DTid.y + clip * res, DTid.z);
		output_radiance[oc_cone] = sam;
	}
}
