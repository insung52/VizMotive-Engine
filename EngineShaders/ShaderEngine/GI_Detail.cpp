#include "RenderPath3D_Detail.h"

namespace vz::renderer
{
	void GRenderPath3DDetails::Update_VXGI(CommandList cmd)
	{
		GSceneDetails::VXGI& vxgi = scene_Gdetails->vxgi;
		if (!vxgi.texture_radiance.IsValid() || !vxgi.texture_radiance_prev.IsValid() || !vxgi.texture_atomic.IsValid())
			return;

		BindCommonResources(cmd);

		const uint32_t res       = vxgi.res;
		const uint32_t clip_idx  = vxgi.clipmap_to_update;
		const GSceneDetails::VXGI::ClipMap& clipmap = vxgi.clipmaps[clip_idx];

		auto prof_range = profiler::BeginRangeGPU("VXGI", &cmd);
		device->EventBegin("VXGI", cmd);

		VoxelizerCB voxCB;
		voxCB.offsetfromPrevFrame = clipmap.offsetfromPrevFrame;
		voxCB.clipmap_index = (int)clip_idx;

		// ── A: texture_atomic 클리어 ──
		{
			device->EventBegin("Clear Atomic", cmd);
			device->Barrier(GPUBarrier::Image(&vxgi.texture_atomic, vxgi.texture_atomic.desc.layout, ResourceState::UNORDERED_ACCESS), cmd);
			device->ClearUAV(&vxgi.texture_atomic, 0, cmd);
			device->Barrier(GPUBarrier::Memory(&vxgi.texture_atomic), cmd);
			device->EventEnd(cmd);
		}

		// ── B: Offset Previous Radiance CS ──
		// radiance(이전 프레임 출력)를 카메라 이동 오프셋만큼 시프트해 prev_radiance에 기록.
		// 이 덕분에 temporal CS는 prev_radiance[dst]를 단순히 읽을 수 있어 race condition 없음.
		if (shaders[CSTYPE_VXGI_OFFSETPREV].IsValid())
		{
			device->EventBegin("VXGI Offset Prev", cmd);

			// texture_radiance: SR 상태 유지 (읽기 전용)
			// texture_radiance_prev: SR → UAV (쓰기)
			device->Barrier(GPUBarrier::Image(&vxgi.texture_radiance_prev,
				vxgi.texture_radiance_prev.desc.layout, ResourceState::UNORDERED_ACCESS), cmd);

			device->BindComputeShader(&shaders[CSTYPE_VXGI_OFFSETPREV], cmd);
			device->PushConstants(&voxCB, sizeof(voxCB), cmd);

			const GPUResource* srvs[] = { &vxgi.texture_radiance };      // t0
			device->BindResources(srvs, 0, 1, cmd);
			const GPUResource* uavs[] = { &vxgi.texture_radiance_prev };  // u0
			device->BindUAVs(uavs, 0, 1, cmd);

			device->Dispatch((res + 7) / 8, (res + 7) / 8, (res + 7) / 8, cmd);

			// texture_radiance_prev: UAV → SR (이후 voxelization과 temporal CS가 읽음)
			device->Barrier(GPUBarrier::Image(&vxgi.texture_radiance_prev,
				ResourceState::UNORDERED_ACCESS, ResourceState::SHADER_RESOURCE_COMPUTE), cmd);

			device->EventEnd(cmd);
		}

		// ── C: Voxelization (래스터라이즈) ──
		{
			device->EventBegin("Voxelize", cmd);

			device->BindDynamicConstantBuffer(voxCB, CBSLOT_RENDERER_VOXELIZER, cmd);

			ForwardEntityMaskCB forwardMask = {};
			forwardMask.xForwardLightMask.x  = ~0u;
			forwardMask.xForwardLightMask.y  = ~0u;
			forwardMask.xForwardDecalMask    = ~0u;
			forwardMask.xForwardEnvProbeMask = ~0u;
			device->BindDynamicConstantBuffer(forwardMask, CB_GETBINDSLOT(ForwardEntityMaskCB), cmd);

			// u0: texture_atomic (복셀화 결과 기록)
			const GPUResource* uavs[] = { &vxgi.texture_atomic };
			device->BindUAVs(uavs, 0, 1, cmd);

			Viewport vp;
			vp.width  = (float)res;
			vp.height = (float)res;
			device->BindViewports(1, &vp, cmd);

			device->BindShadingRate(ShadingRate::RATE_1X1, cmd);

			DrawScene(visMain, RENDERPASS_VOXELIZE, cmd, DRAWSCENE_OPAQUE);

			device->EventEnd(cmd);
		}

		// ── D: Temporal Blend CS ──
		// input:  t0=prev_radiance(SR), t1=atomic(SR)
		// output: u0=radiance(UAV)
		// 읽기/쓰기 텍스처 완전 분리 → race condition 없음
		if (shaders[CSTYPE_VXGI_TEMPORAL].IsValid())
		{
			device->EventBegin("VXGI Temporal", cmd);

			GPUBarrier barriers[] = {
				GPUBarrier::Image(&vxgi.texture_atomic,   ResourceState::UNORDERED_ACCESS,   ResourceState::SHADER_RESOURCE_COMPUTE),
				GPUBarrier::Image(&vxgi.texture_radiance, vxgi.texture_radiance.desc.layout, ResourceState::UNORDERED_ACCESS),
			};
			device->Barrier(barriers, arraysize(barriers), cmd);

			device->BindComputeShader(&shaders[CSTYPE_VXGI_TEMPORAL], cmd);
			device->PushConstants(&voxCB, sizeof(voxCB), cmd);

			const GPUResource* srvs[] = { &vxgi.texture_radiance_prev, &vxgi.texture_atomic }; // t0, t1
			device->BindResources(srvs, 0, 2, cmd);

			const GPUResource* uavs[] = { &vxgi.texture_radiance }; // u0
			device->BindUAVs(uavs, 0, 1, cmd);

			device->Dispatch((res + 7) / 8, (res + 7) / 8, (res + 7) / 8, cmd);

			device->Barrier(GPUBarrier::Image(&vxgi.texture_radiance,
				ResourceState::UNORDERED_ACCESS, ResourceState::SHADER_RESOURCE_COMPUTE), cmd);

			device->EventEnd(cmd);
		}

		// ── D: SDF Jump Flood CS ──
		if (shaders[CSTYPE_VXGI_SDF_JUMPFLOOD].IsValid() && vxgi.texture_sdf.IsValid())
		{
			device->EventBegin("VXGI SDF JFA", cmd);

			// 초기화 패스: radiance alpha 기반으로 SDF 초기값 설정
			{
				device->Barrier(GPUBarrier::Image(&vxgi.texture_sdf, vxgi.texture_sdf.desc.layout, ResourceState::UNORDERED_ACCESS), cmd);

				MiscCB miscCB = {};
				miscCB.g_xTransform._11 = 1.0f;     // step (init에서는 미사용)
				miscCB.g_xTransform._12 = 1.0f;     // isInit = 1
				miscCB.g_xTransform._13 = (float)clip_idx;
				device->BindDynamicConstantBuffer(miscCB, CB_GETBINDSLOT(MiscCB), cmd);

				device->BindComputeShader(&shaders[CSTYPE_VXGI_SDF_JUMPFLOOD], cmd);

				// t0: 미사용이지만 texture_sdf_temp를 dummy로 바인딩 (texture_sdf 충돌 방지)
				// t1: texture_radiance (init source)
				const GPUResource* srvs[] = {
					&vxgi.texture_sdf_temp,  // t0: dummy (not read in init shader)
					&vxgi.texture_radiance,  // t1: init source
				};
				device->BindResources(srvs, 0, arraysize(srvs), cmd);

				// u0: texture_sdf (write only in init)
				const GPUResource* uavs[] = { &vxgi.texture_sdf };
				device->BindUAVs(uavs, 0, 1, cmd);

				device->Dispatch((res + 7) / 8, (res + 7) / 8, (res + 7) / 8, cmd);
				device->Barrier(GPUBarrier::Memory(&vxgi.texture_sdf), cmd);
			}

			// JFA 패스: step = res/2, res/4, ..., 1
			// 루프 시작 시 texture_sdf = UAV (방금 init에서 씀), texture_sdf_temp = 초기상태
			bool sdf_in_uav = true; // texture_sdf의 현재 상태 추적
			bool tmp_in_uav = false; // texture_sdf_temp의 현재 상태 추적 (초기 layout = SHADER_RESOURCE_COMPUTE)
			for (int step = (int)res / 2; step >= 1; step /= 2)
			{
				GPUBarrier bar[] = {
					GPUBarrier::Image(&vxgi.texture_sdf,      sdf_in_uav ? ResourceState::UNORDERED_ACCESS : ResourceState::SHADER_RESOURCE_COMPUTE, ResourceState::SHADER_RESOURCE_COMPUTE),
					GPUBarrier::Image(&vxgi.texture_sdf_temp, tmp_in_uav ? ResourceState::UNORDERED_ACCESS : ResourceState::SHADER_RESOURCE_COMPUTE, ResourceState::UNORDERED_ACCESS),
				};
				device->Barrier(bar, arraysize(bar), cmd);

				MiscCB miscCB = {};
				miscCB.g_xTransform._11 = (float)step;
				miscCB.g_xTransform._12 = 0.0f;     // isInit = 0
				miscCB.g_xTransform._13 = (float)clip_idx;
				device->BindDynamicConstantBuffer(miscCB, CB_GETBINDSLOT(MiscCB), cmd);

				const GPUResource* srvs[] = {
					&vxgi.texture_sdf,
					&vxgi.texture_radiance,
				};
				device->BindResources(srvs, 0, arraysize(srvs), cmd);

				const GPUResource* uavs[] = { &vxgi.texture_sdf_temp };
				device->BindUAVs(uavs, 0, 1, cmd);

				device->Dispatch((res + 7) / 8, (res + 7) / 8, (res + 7) / 8, cmd);
				device->Barrier(GPUBarrier::Memory(), cmd);

				// ping-pong: swap sdf ↔ sdf_temp
				// 스왑 후: 새 texture_sdf는 방금 쓴 texture_sdf_temp(UAV), 새 texture_sdf_temp는 방금 읽은 texture_sdf(SR)
				std::swap(vxgi.texture_sdf, vxgi.texture_sdf_temp);
				sdf_in_uav = true;  // 새 texture_sdf는 방금 쓴 것 (UAV 상태)
				tmp_in_uav = false; // 새 texture_sdf_temp는 방금 읽은 것 (SR 상태)
			}

			// 루프 후 texture_sdf는 UAV → SR로 전환
			device->Barrier(GPUBarrier::Image(&vxgi.texture_sdf, ResourceState::UNORDERED_ACCESS, ResourceState::SHADER_RESOURCE_COMPUTE), cmd);

			device->EventEnd(cmd);
		}

		// ── G: 다음 클립맵 레벨로 로테이션 ──
		vxgi.clipmap_to_update = (vxgi.clipmap_to_update + 1) % VXGI_CLIPMAP_COUNT;

		profiler::EndRange(prof_range);
		device->EventEnd(cmd);
	}

	void GRenderPath3DDetails::Update_DDGI(CommandList cmd)
	{
		if (!scene_Gdetails->TLAS.IsValid() && !scene_Gdetails->sceneBVH.IsValid())
			return;

		if (renderer::DDGI_RAYCOUNT == 0)
			return;

		GSceneDetails::DDGI& scene_ddgi = scene_Gdetails->ddgi;
		if (!scene_ddgi.rayBuffer.IsValid())
			return;
		
		shader::WaitShaderLoad_RayTracing();

		auto prof_range = profiler::BeginRangeGPU("DDGI", &cmd);
		device->EventBegin("DDGI", cmd);

		if (scene_ddgi.frameIndex == 0)
		{
			device->Barrier(GPUBarrier::Image(&scene_ddgi.depthTexture, ResourceState::SHADER_RESOURCE_COMPUTE, ResourceState::UNORDERED_ACCESS), cmd);
			device->Barrier(GPUBarrier::Buffer(&scene_ddgi.probeBuffer, ResourceState::SHADER_RESOURCE_COMPUTE, ResourceState::UNORDERED_ACCESS), cmd);
			device->Barrier(GPUBarrier::Buffer(&scene_ddgi.varianceBuffer, ResourceState::SHADER_RESOURCE_COMPUTE, ResourceState::UNORDERED_ACCESS), cmd);
			device->ClearUAV(&scene_ddgi.probeBuffer, 0, cmd);
			device->ClearUAV(&scene_ddgi.depthTexture, 0, cmd);
			device->ClearUAV(&scene_ddgi.varianceBuffer, 0, cmd);
			device->ClearUAV(&scene_ddgi.rayallocationBuffer, 0, cmd);
			device->ClearUAV(&scene_ddgi.raycountBuffer, 0, cmd);
			device->ClearUAV(&scene_ddgi.rayBuffer, 0, cmd);
			device->Barrier(GPUBarrier::Memory(), cmd);
			device->Barrier(GPUBarrier::Image(&scene_ddgi.depthTexture, ResourceState::UNORDERED_ACCESS, ResourceState::SHADER_RESOURCE_COMPUTE), cmd);
			device->Barrier(GPUBarrier::Buffer(&scene_ddgi.probeBuffer, ResourceState::UNORDERED_ACCESS, ResourceState::SHADER_RESOURCE_COMPUTE), cmd);
			device->Barrier(GPUBarrier::Buffer(&scene_ddgi.varianceBuffer, ResourceState::UNORDERED_ACCESS, ResourceState::SHADER_RESOURCE_COMPUTE), cmd);
		}

		BindCommonResources(cmd);

		DDGIPushConstants push;
		uint8_t instanceInclusionMask = 0xFF;
		push.instanceInclusionMask = instanceInclusionMask;
		push.frameIndex = scene_ddgi.frameIndex;
		push.rayCount = std::min(renderer::DDGI_RAYCOUNT, DDGI_MAX_RAYCOUNT);
		push.blendSpeed = renderer::DDGI_BLEND_SPEED;

		const uint probe_count = scene_Gdetails->shaderscene.ddgi.probe_count;

		// Ray allocation:
		{
			device->EventBegin("Ray allocation", cmd);

			device->BindComputeShader(&shaders[CSTYPE_DDGI_RAYALLOCATION], cmd);
			device->PushConstants(&push, sizeof(push), cmd);

			const GPUResource* res[] = {
				&scene_ddgi.varianceBuffer,
			};
			device->BindResources(res, 0, arraysize(res), cmd);

			const GPUResource* uavs[] = {
				&scene_ddgi.rayallocationBuffer,
				&scene_ddgi.raycountBuffer,
			};
			device->BindUAVs(uavs, 0, arraysize(uavs), cmd);

			device->ClearUAV(&scene_ddgi.rayallocationBuffer, 0, cmd);
			device->Barrier(GPUBarrier::Memory(&scene_ddgi.rayallocationBuffer), cmd);

			device->Dispatch(probe_count, 1, 1, cmd);

			device->EventEnd(cmd);
		}

		{
			GPUBarrier barriers[] = {
				GPUBarrier::Memory(&scene_ddgi.rayallocationBuffer),
				GPUBarrier::Buffer(&scene_ddgi.raycountBuffer, ResourceState::UNORDERED_ACCESS, ResourceState::SHADER_RESOURCE_COMPUTE),
			};
			device->Barrier(barriers, arraysize(barriers), cmd);
		}

		// Indirect prepare:
		{
			device->EventBegin("Indirect prepare", cmd);

			device->BindComputeShader(&shaders[CSTYPE_DDGI_INDIRECTPREPARE], cmd);

			const GPUResource* uavs[] = {
				&scene_ddgi.rayallocationBuffer,
			};
			device->BindUAVs(uavs, 0, arraysize(uavs), cmd);

			device->Dispatch(1, 1, 1, cmd);

			device->EventEnd(cmd);
		}

		{
			GPUBarrier barriers[] = {
				GPUBarrier::Buffer(&scene_ddgi.rayallocationBuffer, ResourceState::UNORDERED_ACCESS, ResourceState::INDIRECT_ARGUMENT | ResourceState::SHADER_RESOURCE_COMPUTE),
			};
			device->Barrier(barriers, arraysize(barriers), cmd);
		}

		// Raytracing:
		{
			device->EventBegin("Raytrace", cmd);

			device->BindComputeShader(&shaders[CSTYPE_DDGI_RAYTRACE], cmd);
			device->PushConstants(&push, sizeof(push), cmd);

			MiscCB cb = {};
			float angle = random::GetRandom(0.0f, 1.0f) * XM_2PI;
			XMVECTOR axis = XMVectorSet(
				random::GetRandom(-1.0f, 1.0f),
				random::GetRandom(-1.0f, 1.0f),
				random::GetRandom(-1.0f, 1.0f),
				0
			);
			axis = XMVector3Normalize(axis);
			XMStoreFloat4x4(&cb.g_xTransform, XMMatrixRotationAxis(axis, angle));
			device->BindDynamicConstantBuffer(cb, CB_GETBINDSLOT(MiscCB), cmd);

			const GPUResource* res[] = {
				&scene_ddgi.rayallocationBuffer,
				&scene_ddgi.raycountBuffer,
			};
			device->BindResources(res, 0, arraysize(res), cmd);

			const GPUResource* uavs[] = {
				&scene_ddgi.rayBuffer,
			};
			device->BindUAVs(uavs, 0, arraysize(uavs), cmd);

			device->DispatchIndirect(&scene_ddgi.rayallocationBuffer, 0, cmd);

			device->EventEnd(cmd);
		}

		{
			GPUBarrier barriers[] = {
				GPUBarrier::Buffer(&scene_ddgi.rayBuffer, ResourceState::UNORDERED_ACCESS, ResourceState::SHADER_RESOURCE_COMPUTE),
				GPUBarrier::Image(&scene_ddgi.depthTexture, ResourceState::SHADER_RESOURCE_COMPUTE, ResourceState::UNORDERED_ACCESS),
				GPUBarrier::Buffer(&scene_ddgi.varianceBuffer, ResourceState::SHADER_RESOURCE_COMPUTE, ResourceState::UNORDERED_ACCESS),
				//GPUBarrier::Buffer(&scene_ddgi.raycountBuffer, ResourceState::UNORDERED_ACCESS, ResourceState::SHADER_RESOURCE_COMPUTE),
				GPUBarrier::Buffer(&scene_ddgi.probeBuffer, ResourceState::SHADER_RESOURCE_COMPUTE, ResourceState::UNORDERED_ACCESS),
			};
			device->Barrier(barriers, arraysize(barriers), cmd);
		}

		// Update:
		{
			device->EventBegin("Update", cmd);

			device->BindComputeShader(&shaders[CSTYPE_DDGI_UPDATE], cmd);
			device->PushConstants(&push, sizeof(push), cmd);

			const GPUResource* res[] = {
				&scene_ddgi.rayBuffer,
				&scene_ddgi.raycountBuffer,
			};
			device->BindResources(res, 0, arraysize(res), cmd);

			const GPUResource* uavs[] = {
				&scene_ddgi.varianceBuffer,
				&scene_ddgi.probeBuffer,
			};
			device->BindUAVs(uavs, 0, arraysize(uavs), cmd);

			device->Dispatch(probe_count, 1, 1, cmd);

			device->EventEnd(cmd);
		}

		// Update Depth:
		{
			device->EventBegin("Update Depth", cmd);

			device->BindComputeShader(&shaders[CSTYPE_DDGI_UPDATE_DEPTH], cmd);
			device->PushConstants(&push, sizeof(push), cmd);

			const GPUResource* res[] = {
				&scene_ddgi.rayBuffer,
				&scene_ddgi.raycountBuffer,
			};
			device->BindResources(res, 0, arraysize(res), cmd);

			const GPUResource* uavs[] = {
				&scene_ddgi.depthTexture,
				&scene_ddgi.probeBuffer,
			};
			device->BindUAVs(uavs, 0, arraysize(uavs), cmd);

			device->Dispatch(probe_count, 1, 1, cmd);

			device->EventEnd(cmd);
		}

		{
			GPUBarrier barriers[] = {
				GPUBarrier::Buffer(&scene_ddgi.probeBuffer, ResourceState::UNORDERED_ACCESS, ResourceState::SHADER_RESOURCE_COMPUTE),
				GPUBarrier::Image(&scene_ddgi.depthTexture, ResourceState::UNORDERED_ACCESS, ResourceState::SHADER_RESOURCE_COMPUTE),
			};
			device->Barrier(barriers, arraysize(barriers), cmd);
		}

		profiler::EndRange(prof_range);
		device->EventEnd(cmd);
	}
}