#include "VzEngineAPIs.h"
#include "Components/GComponents.h"
#include "Common/RenderPath3D.h"
#include "Common/Engine_Internal.h"
#include "GBackend/GModuleLoader.h"
#include "Utils/Utils_Internal.h"
#include "Utils/Backlog.h"
#include "Utils/Helpers.h"
#include "Utils/Helpers2.h"
#include "Utils/Profiler.h"

using namespace vz;
using namespace std;
using namespace backlog;

namespace vz
{
	extern GBackendLoader graphicsBackend;
}

namespace vzm
{
#define GET_RENDERPATH(RENDERER, RET) RenderPath3D* RENDERER = (RenderPath3D*)canvas::GetCanvas(componentVID_); \
	if (!RENDERER) {post("RenderPath3D(" + to_string(componentVID_) + ") is INVALID!", LogLevel::Error); return RET;} \
	if (RENDERER->GetType() != "RenderPath3D") {post("RenderPath3D(" + to_string(componentVID_) + ") is NOT RenderPath3D!", LogLevel::Error); return RET;}

	void VzRenderer::SetCanvas(const uint32_t w, const uint32_t h, const float dpi, void* window)
	{
		GET_RENDERPATH(renderer, );
		renderer->SetCanvas(std::max(w, 1u), std::max(h, 1u), dpi, window);
		UpdateTimeStamp();
	}

	void VzRenderer::ResizeCanvas(const uint32_t w, const uint32_t h, const CamVID vidCam)
	{
		GET_RENDERPATH(renderer, );

		uint32_t w1 = std::max(w, 1u);
		uint32_t h1 = std::max(h, 1u);
		renderer->SetCanvas(w1, h1, renderer->GetDPI(), renderer->GetWindow());

		auto resizeCamera = [&w1, &h1](CameraComponent* camera, const uint32_t w, const uint32_t h)
			{
				float z_near, z_far;
				camera->GetNearFar(&z_near, &z_far);
				if (camera->IsOrtho())
				{
					camera->SetOrtho((float)w, (float)h, z_near, z_far, 0);
				}
				else
				{
					if (camera->IsIntrinsicsProjection())
					{
						float w0, h0;
						camera->GetWidthHeight(&w0, &h0);
						const float intrinsicRatioX = w0 / (float)w1;
						const float intrinsicRatioY = h0 / (float)h1;

						//float w0, h0,
						//camera->GetWidthHeight(&w0, &h0);
						float fx0, fy0, cx0, cy0, sc0, zn, zf;
						camera->GetNearFar(&zn, &zf);
						camera->GetIntrinsics(&fx0, &fy0, &cx0, &cy0, &sc0);
						camera->SetIntrinsicsProjection((float)w1, (float)h1, zn, zf, 
							fx0 / intrinsicRatioX, 
							fy0 / intrinsicRatioY, 
							cx0 / intrinsicRatioX, 
							cy0 / intrinsicRatioY, 
							sc0);
					}
					else
					{
						camera->SetPerspective(
							(float)w / (float)h,
							1.f, z_near, z_far, camera->GetFovVertical()
						);
					}
				}
			};

		if (renderer->camera)
		{
			resizeCamera(renderer->camera, w1, h1);
		}

		CameraComponent* user_camera = compfactory::GetCameraComponent(vidCam);
		if (user_camera && user_camera != renderer->camera)
		{
			resizeCamera(user_camera, w1, h1);
		}

		UpdateTimeStamp();
	}

	void VzRenderer::GetCanvas(uint32_t* VZ_NULLABLE w, uint32_t* VZ_NULLABLE h, float* VZ_NULLABLE dpi, void** VZ_NULLABLE window)
	{
		GET_RENDERPATH(renderer, );
		if (w) *w = renderer->GetPhysicalWidth();
		if (h) *h = renderer->GetPhysicalHeight();
		if (dpi) *dpi = renderer->GetDPI();
		if (window) *window = renderer->GetWindow();
	}

	void VzRenderer::SetViewport(const float x, const float y, const float w, const float h)
	{
		GET_RENDERPATH(renderer, );

		renderer->useManualSetViewport = true;

		graphics::Viewport vp;
		vp.top_left_x = x;
		vp.top_left_y = y;
		vp.width = w;
		vp.height = h;
		renderer->SetViewport(vp);
	}

	void VzRenderer::GetViewport(float* VZ_NULLABLE x, float* VZ_NULLABLE y, float* VZ_NULLABLE w, float* VZ_NULLABLE h)
	{
		GET_RENDERPATH(renderer, );
		const graphics::Viewport& vp = renderer->GetViewport();
		if (x) *x = vp.top_left_x;
		if (y) *y = vp.top_left_y;
		if (w) *w = vp.width;
		if (h) *h = vp.height;
	}

	void VzRenderer::SetScissor(const int32_t left, const int32_t top, const int32_t right, const int32_t bottom)
	{
		GET_RENDERPATH(renderer, );

		renderer->useManualSetScissor = true;

		graphics::Rect scissor;
		scissor.left = left;
		scissor.top = top;
		scissor.right = right;
		scissor.bottom = bottom;
		renderer->SetScissor(scissor);
	}

	void VzRenderer::GetScissor(int32_t* VZ_NULLABLE left, int32_t* VZ_NULLABLE top, int32_t* VZ_NULLABLE right, int32_t* VZ_NULLABLE bottom)
	{
		GET_RENDERPATH(renderer, );
		const graphics::Rect& scissor = renderer->GetScissor();
		if (left) *left = scissor.left;
		if (top) *top = scissor.top;
		if (right) *right = scissor.right;
		if (bottom) *bottom = scissor.bottom;
	}

	void VzRenderer::UseCanvasAsViewport()
	{
		GET_RENDERPATH(renderer, );

		renderer->useManualSetViewport = false;

		graphics::Viewport vp;
		vp.top_left_x = 0;
		vp.top_left_y = 0;
		vp.width = (float)renderer->GetPhysicalWidth();
		vp.height = (float)renderer->GetPhysicalHeight();
		renderer->SetViewport(vp);
	}

	void VzRenderer::SetLayerMask(const uint32_t layerMask)
	{
		GET_RENDERPATH(renderer, );
		renderer->SetlayerMask(layerMask);
		UpdateTimeStamp();
	}

	void VzRenderer::SetClearColor(const vfloat4& color)
	{
		GET_RENDERPATH(renderer, );
		memcpy(renderer->clearColor, &color, sizeof(float) * 4);
		UpdateTimeStamp();
	}

	void VzRenderer::EnableClear(const bool enabled)
	{
		GET_RENDERPATH(renderer, );
		renderer->EnableClear(enabled);
		UpdateTimeStamp();
	}

	void VzRenderer::SkipPostprocess(const bool skip)
	{
		GET_RENDERPATH(renderer, );
		renderer->SkipPostprocess(skip);
		UpdateTimeStamp();
	}

	void VzRenderer::GetClearColor(vfloat4& color) const
	{
		GET_RENDERPATH(renderer, );
		memcpy(&color, renderer->clearColor, sizeof(float) * 4);
	}

	void VzRenderer::SetAllowHDR(const bool enable)
	{
		GET_RENDERPATH(renderer, );
		renderer->allowHDR = enable;
	}
	bool VzRenderer::GetAllowHDR() const
	{
		GET_RENDERPATH(renderer, false);
		return renderer->allowHDR;
	}

	void VzRenderer::SetTonemap(const Tonemap tonemap)
	{
		GET_RENDERPATH(renderer, );
	}

	void VzRenderer::EnableFrameLock(const float targetFrameRate)
	{
		GET_RENDERPATH(renderer, );
		renderer->targetFrameRate = targetFrameRate;
	}

	// MUST BE CALLED WITHIN THE SAME THREAD
	bool VzRenderer::Render(const SceneVID vidScene, const CamVID vidCam, const float dt)
	{
		GET_RENDERPATH(renderer, false);

		std::lock_guard<std::recursive_mutex> lock(vzm::GetEngineMutex());

		renderer->scene = scenefactory::GetScene(vidScene);
		renderer->camera = compfactory::GetCameraComponent(vidCam);

		if (!renderer->scene || !renderer->camera)
		{
			return false;
		}

		renderer->deltaTimeSinceLastRender += float(std::max(0.0, renderer->timer.record_elapsed_seconds()));
		if (renderer->targetFrameRate > 0)
		{
			const float target_deltaTime = 1.0f / renderer->targetFrameRate;
			if (renderer->deltaTimeSinceLastRender < target_deltaTime)
			{
				return false; 
			}
			renderer->deltaTimeSinceLastRender -= target_deltaTime;
		}

		if (GetCountPendingSubmitCommand() == 0)
		{
			profiler::BeginFrame();
		}

		float delta_time = renderer->targetFrameRate > 0
			? (1.0f / renderer->targetFrameRate)  // fixed deltaTime
			: renderer->deltaTimeSinceLastRender;  // dynamic deltaTime

		if (renderer->targetFrameRate <= 0)
		{
			renderer->deltaTimeSinceLastRender = 0;  // reset at every frame
		}

		// Update the target Scene of this RenderPath 
		//	this involves Animation updates
		float update_dt = dt > 0 ? dt : delta_time;
		renderer->scene->Update(update_dt);
		renderer->Update(update_dt);
		renderer->Render(update_dt);

		if (!IsPendingSubmitCommand())
		{
			graphics::GraphicsDevice* device = graphics::GetDevice();
			graphics::CommandList cmd = device->BeginCommandList();
			profiler::EndFrame(&cmd); // cmd must be assigned before SubmitCommandLists
			device->SubmitCommandLists();
			vzm::ResetPendingSubmitCommand();
		}
		else
		{
			vzm::CountPendingSubmitCommand();
		}

		renderer->frameCount++;

		return true;
	}

	ChainUnitSCam::ChainUnitSCam(const SceneVID sceneVid, const CamVID camVid) : sceneVid(sceneVid), camVid(camVid)
	{
		VzBaseComp* scene = vzm::GetComponent(sceneVid);
		VzBaseComp* camera = vzm::GetComponent(camVid);
		bool is_valid = scene && camera;
		vzlog_assert(is_valid, "ChainUnitRCam >> Invalid VzComponent!!");
		if (!is_valid)
			return;
		is_valid = scene->GetType() == COMPONENT_TYPE::SCENE &&
			(camera->GetType() == COMPONENT_TYPE::CAMERA || camera->GetType() == COMPONENT_TYPE::SLICER);
		vzlog_assert(is_valid,
			"ChainUnitRCam >> Component Type Matching Error!!");
		if (!is_valid)
			return;
		isValid_ = true;
	}

	void VzRenderer::RenderChain(const std::vector<ChainUnitSCam>& scChain)
	{

	}


	bool VzRenderer::Picking(const SceneVID vidScene, const CamVID vidCam, const vfloat2& pos, const uint32_t filterFlags, const float toleranceRadius,
		vfloat3& worldPosition, ActorVID& vid, int* primitiveID, int* maskValue) const
	{
		GET_RENDERPATH(renderer, false);

		GCameraComponent* camera = (GCameraComponent*)compfactory::GetCameraComponent(vidCam);
		if (camera == nullptr)
		{
			return false;
		}

		renderer->scene = scenefactory::GetScene(vidScene);
		renderer->camera = camera;

		if (!renderer->scene || !renderer->camera)
		{
			return false;
		}

		bool ret = false;
		if (vz::graphicsBackend.API == "DX11")
		{
			camera->isPickingMode = true;
			camera->pickingIO.SetScreenPos(*(XMFLOAT2*)&pos);

			// TODO: MUST BE DEPRECATED!!!
			// Use core-built-in picking based on simple BVH

			renderer->Render(0); // just for picking process

			size_t num_picked_positions = camera->pickingIO.NumPickedPositions();
			ret = num_picked_positions > 0;

			// output setting
			if (ret)
			{
				vid = camera->pickingIO.DataEntities()[0];
				worldPosition = *(vfloat3*)&camera->pickingIO.DataPositions()[0];
				if (primitiveID) *primitiveID = camera->pickingIO.DataPrimitiveIDs()[0];
				if (maskValue) *maskValue = camera->pickingIO.DataMaskValues()[0];
			}

			camera->isPickingMode = false;
			camera->pickingIO.Clear();
		}
		else
		{
			// TODO volume!
			geometrics::Ray ray = renderer->GetPickRay(pos.x, pos.y, *camera);
			Scene::RayIntersectionResult intersect_result = 
				renderer->scene->Intersects(ray, camera->GetEntity(), filterFlags, ~0u, 0, 
					toleranceRadius, renderer->GetPhysicalWidth(), renderer->GetPhysicalHeight());
			if (intersect_result.entity != INVALID_ENTITY)
			{
				ret = true;
				vid = intersect_result.entity;
				worldPosition = *(vfloat3*)&intersect_result.position;
				if (primitiveID) *primitiveID = intersect_result.triIndex;
				if (maskValue) *maskValue = -1;
			}
		}

		return ret;
	}

	vfloat3 VzRenderer::UnprojToWorld(const vfloat2& posOnScreen, const VzCamera* camera)
	{
		GET_RENDERPATH(renderer, {});

		CameraComponent* cam_component = nullptr;
		if (camera != nullptr)
		{
			cam_component = compfactory::GetCameraComponent(camera->GetVID());
		}
		else
		{
			cam_component = renderer->camera;
		}

		if (cam_component == nullptr)
		{
			backlog::post("VzRenderer::Unproj >> Invalid camera!", backlog::LogLevel::Error);
			return {};
		}

		const XMFLOAT4X4& inv_VP = cam_component->GetInvViewProjection();
		XMFLOAT4X4 inv_screen;
		renderer->GetViewportTransforms(nullptr, &inv_screen);

		XMMATRIX xinv_screen = XMLoadFloat4x4(&inv_screen);
		XMMATRIX xinv_VP = XMLoadFloat4x4(&inv_VP);
		XMMATRIX xmat_screen2world = xinv_screen * xinv_VP;

		XMFLOAT3 pos_ss3 = XMFLOAT3(posOnScreen.x, posOnScreen.y, 1.f); // consider reverse z
		XMVECTOR xpos_ss = XMLoadFloat3(&pos_ss3);
		XMVECTOR xpos_ws = XMVector3TransformCoord(xpos_ss, xmat_screen2world);
		vfloat3 pos_ws;
		XMStoreFloat3((XMFLOAT3*)&pos_ws, xpos_ws);
		return pos_ws;
	}

	bool VzRenderer::GetSharedRenderTarget(const void* graphicsDev2, const void* srvDescHeap2, const int descriptorIndex, SharedResourceTarget& resTarget, uint32_t* w, uint32_t* h)
	{
		GET_RENDERPATH(renderer, false);

		if (w) *w = renderer->GetPhysicalWidth();
		if (h) *h = renderer->GetPhysicalHeight();

		//if (graphicsDevice == nullptr) return nullptr;
		//return graphicsDevice->OpenSharedResource(graphicsDev2, const_cast<wi::graphics::Texture*>(&renderer->GetRenderResult()));
		//return graphicsDevice->OpenSharedResource(graphicsDev2, &renderer->rtPostprocess);

		resTarget = {};
		bool ret = renderer->GetSharedRendertargetView(graphicsDev2, srvDescHeap2, descriptorIndex, resTarget.descriptorHandle, &resTarget.resourcePtr);

		return ret;
	}

	bool VzRenderer::StoreRenderTarget(std::vector<uint8_t>& rawBuffer, uint32_t* w, uint32_t* h)
	{
		GET_RENDERPATH(renderer, false);

		const graphics::Texture* rt = renderer->GetLastProcessRT();
		if (rt == nullptr || !rt->IsValid())
		{
			return false;
		}
		if (w) *w = rt->GetDesc().width;
		if (h) *h = rt->GetDesc().height;
		return helper2::saveTextureToMemory(*rt, rawBuffer);
	}

	bool VzRenderer::StoreRenderTargetRGBA8(std::vector<uint8_t>& rgbaBuffer, uint32_t* w, uint32_t* h)
	{
		GET_RENDERPATH(renderer, false);

		const graphics::Texture* rt = renderer->GetLastProcessRT();
		if (rt == nullptr || !rt->IsValid())
		{
			return false;
		}

		graphics::TextureDesc desc = rt->GetDesc();
		if (w) *w = desc.width;
		if (h) *h = desc.height;

		// Read raw texture data
		std::vector<uint8_t> rawBuffer;
		if (!helper2::saveTextureToMemory(*rt, rawBuffer))
		{
			return false;
		}

		// Handle format conversion
		if (desc.format == graphics::Format::R8G8B8A8_UNORM ||
			desc.format == graphics::Format::R8G8B8A8_UNORM_SRGB)
		{
			// Already RGBA8 - direct move, no conversion needed
			rgbaBuffer = std::move(rawBuffer);
		}
		else if (desc.format == graphics::Format::R11G11B10_FLOAT)
		{
			// Convert R11G11B10_FLOAT to RGBA8 using SIMD
			uint32_t pixelCount = desc.width * desc.height;
			rgbaBuffer.resize(pixelCount * 4);

			const uint32_t* dataSrc = (const uint32_t*)rawBuffer.data();
			uint32_t* dataDst = (uint32_t*)rgbaBuffer.data();

			// SIMD constants
			const XMVECTOR scale255 = XMVectorReplicate(255.0f);
			const XMVECTOR alphaFF = XMVectorSetW(XMVectorZero(), 255.0f);

			// Process 4 pixels at a time for better cache utilization
			uint32_t i = 0;
			for (; i + 3 < pixelCount; i += 4)
			{
				// Load and convert 4 pixels
				XMFLOAT3PK pk0, pk1, pk2, pk3;
				pk0.v = dataSrc[i + 0];
				pk1.v = dataSrc[i + 1];
				pk2.v = dataSrc[i + 2];
				pk3.v = dataSrc[i + 3];

				XMVECTOR v0 = XMVectorSaturate(XMLoadFloat3PK(&pk0));
				XMVECTOR v1 = XMVectorSaturate(XMLoadFloat3PK(&pk1));
				XMVECTOR v2 = XMVectorSaturate(XMLoadFloat3PK(&pk2));
				XMVECTOR v3 = XMVectorSaturate(XMLoadFloat3PK(&pk3));

				// Scale to 0-255 and add alpha
				v0 = XMVectorAdd(XMVectorMultiply(v0, scale255), alphaFF);
				v1 = XMVectorAdd(XMVectorMultiply(v1, scale255), alphaFF);
				v2 = XMVectorAdd(XMVectorMultiply(v2, scale255), alphaFF);
				v3 = XMVectorAdd(XMVectorMultiply(v3, scale255), alphaFF);

				// Convert to uint and pack
				XMUINT4 u0, u1, u2, u3;
				XMStoreUInt4(&u0, v0);
				XMStoreUInt4(&u1, v1);
				XMStoreUInt4(&u2, v2);
				XMStoreUInt4(&u3, v3);

				dataDst[i + 0] = u0.x | (u0.y << 8) | (u0.z << 16) | (u0.w << 24);
				dataDst[i + 1] = u1.x | (u1.y << 8) | (u1.z << 16) | (u1.w << 24);
				dataDst[i + 2] = u2.x | (u2.y << 8) | (u2.z << 16) | (u2.w << 24);
				dataDst[i + 3] = u3.x | (u3.y << 8) | (u3.z << 16) | (u3.w << 24);
			}

			// Handle remaining pixels
			for (; i < pixelCount; ++i)
			{
				XMFLOAT3PK pk;
				pk.v = dataSrc[i];
				XMVECTOR V = XMVectorSaturate(XMLoadFloat3PK(&pk));
				V = XMVectorAdd(XMVectorMultiply(V, scale255), alphaFF);
				XMUINT4 u;
				XMStoreUInt4(&u, V);
				dataDst[i] = u.x | (u.y << 8) | (u.z << 16) | (u.w << 24);
			}
		}
		else if (desc.format == graphics::Format::R10G10B10A2_UNORM)
		{
			// Convert R10G10B10A2_UNORM to RGBA8
			uint32_t pixelCount = desc.width * desc.height;
			rgbaBuffer.resize(pixelCount * 4);

			const uint32_t* dataSrc = (const uint32_t*)rawBuffer.data();
			uint8_t* dataDst = rgbaBuffer.data();

			for (uint32_t i = 0; i < pixelCount; ++i)
			{
				uint32_t pixel = dataSrc[i];
				// R10G10B10A2: 10 bits R, 10 bits G, 10 bits B, 2 bits A
				uint32_t r10 = (pixel >> 0) & 0x3FF;
				uint32_t g10 = (pixel >> 10) & 0x3FF;
				uint32_t b10 = (pixel >> 20) & 0x3FF;
				uint32_t a2 = (pixel >> 30) & 0x3;

				dataDst[i * 4 + 0] = (uint8_t)(r10 >> 2);  // 10 bit to 8 bit
				dataDst[i * 4 + 1] = (uint8_t)(g10 >> 2);
				dataDst[i * 4 + 2] = (uint8_t)(b10 >> 2);
				dataDst[i * 4 + 3] = (uint8_t)(a2 * 85);   // 2 bit to 8 bit (0,1,2,3 -> 0,85,170,255)
			}
		}
		else
		{
			// For other formats, just copy the raw buffer (may not display correctly)
			rgbaBuffer = std::move(rawBuffer);
		}

		return true;
	}

	bool VzRenderer::StoreRenderTargetInfoFile(const std::string& fileName)
	{
		GET_RENDERPATH(renderer, false);

		const graphics::Texture* rt = renderer->GetLastProcessRT();
		if (rt == nullptr || !rt->IsValid())
		{
			return false;
		}
		return helper2::saveTextureToFile(*rt, fileName);
	}

	void VzRenderer::ShowDebugBuffer(const std::string& debugMode)
	{
		GET_RENDERPATH(renderer, );
		renderer->ShowDebugBuffer(debugMode);
		renderer->ResetStableCount();
	}

	void VzRenderer::SetRenderOptionEnabled(const std::string& optionName, const bool enabled)
	{
		GET_RENDERPATH(renderer, );
		renderer->SetRenderOptionEnabled(optionName, enabled);
		renderer->ResetStableCount();
	}

	void VzRenderer::SetRenderOptionValueArray(const std::string& optionName, const std::vector<float>& values)
	{
		GET_RENDERPATH(renderer, );
		renderer->SetRenderOptionValueArray(optionName, values);
		renderer->ResetStableCount();
	}
}