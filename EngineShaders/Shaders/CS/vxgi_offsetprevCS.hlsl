// VXGI Offset Previous Radiance Compute Shader
// 이전 프레임의 radiance 텍스처를 카메라 이동(그리드 스크롤)에 맞춰 시프트하여
// prev_radiance 텍스처에 기록한다.
//
// 이 패스가 먼저 실행된 뒤 temporal CS가 prev_radiance를 읽어 블렌딩한다.
// 덕분에 temporal CS는 단순히 dst 좌표로 prev_radiance를 읽을 수 있어
// race condition이 발생하지 않는다.
//
// 입력  t0: input_radiance  (이전 프레임 temporal CS 결과)
// 출력  u0: output_prev     (시프트 적용된 prev, 이후 temporal CS가 읽음)

#include "../globals.hlsli"
#include "../ShaderInterop_VXGI.h"

PUSHCONSTANT(push, VoxelizerCB);

Texture3D<half4>   input_radiance : register(t0);
RWTexture3D<half4> output_prev    : register(u0);

[numthreads(8, 8, 8)]
void main(uint3 DTid : SV_DispatchThreadID)
{
	const uint res  = GetFrame().vxgi.resolution;
	const uint clip = (uint)push.clipmap_index;

	if (any(DTid >= res))
		return;

	// 현재 복셀(DTid)의 world position이 이전 프레임 그리드에서 어디 있었는지:
	//   prev_dtid = DTid + offsetfromPrevFrame  (우리 부호 규약)
	int3 prev_dtid = (int3)DTid + push.offsetfromPrevFrame;
	bool is_new = !all(prev_dtid >= 0) || !all(prev_dtid < (int)res);

	for (uint i = 0; i < 6 + DIFFUSE_CONE_COUNT; ++i)
	{
		uint3 dst = uint3(DTid.x + i * res, DTid.y + clip * res, DTid.z);

		if (is_new)
		{
			// 이전 프레임 그리드에 없던 복셀 → 0으로 초기화 (ghosting 방지)
			output_prev[dst] = (half4)0;
		}
		else
		{
			uint3 src = uint3((uint)prev_dtid.x + i * res, (uint)prev_dtid.y + clip * res, (uint)prev_dtid.z);
			output_prev[dst] = input_radiance[src];
		}
	}
}
