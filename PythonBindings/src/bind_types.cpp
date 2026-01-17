#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "vzm2/VzEngineAPIs.h"
#include "vzm2/VzComponentAPIs.h"
#include "vzm2/VzScene.h"
#include "vzm2/VzCamera.h"
#include "vzm2/VzRenderer.h"
#include "vzm2/VzActor.h"
#include "vzm2/VzGeometry.h"
#include "vzm2/VzMaterial.h"
#include "vzm2/VzLight.h"
#include "vzm2/VzTexture.h"
#include "vzm2/VzArchive.h"

namespace py = pybind11;

void bind_types(py::module& m) {
    // Math types
    py::class_<vfloat2>(m, "vfloat2")
        .def(py::init<>())
        .def(py::init<float, float>())
        .def_readwrite("x", &vfloat2::x)
        .def_readwrite("y", &vfloat2::y);

    py::class_<vfloat3>(m, "vfloat3")
        .def(py::init<>())
        .def(py::init<float, float, float>())
        .def_readwrite("x", &vfloat3::x)
        .def_readwrite("y", &vfloat3::y)
        .def_readwrite("z", &vfloat3::z);

    py::class_<vfloat4>(m, "vfloat4")
        .def(py::init<>())
        .def(py::init<float, float, float, float>())
        .def_readwrite("x", &vfloat4::x)
        .def_readwrite("y", &vfloat4::y)
        .def_readwrite("z", &vfloat4::z)
        .def_readwrite("w", &vfloat4::w);

    // 4x4 Matrix type
    py::class_<vfloat4x4>(m, "vfloat4x4")
        .def(py::init<>())
        .def("to_list", [](const vfloat4x4& mat) {
            std::vector<std::vector<float>> result(4, std::vector<float>(4));
            for (int i = 0; i < 4; i++) {
                for (int j = 0; j < 4; j++) {
                    result[i][j] = mat.m[i][j];
                }
            }
            return result;
        }, "Convert matrix to nested list [[row0], [row1], [row2], [row3]]")
        .def("__getitem__", [](const vfloat4x4& mat, std::pair<int, int> idx) {
            if (idx.first < 0 || idx.first >= 4 || idx.second < 0 || idx.second >= 4) {
                throw std::out_of_range("Matrix index out of range");
            }
            return mat.m[idx.first][idx.second];
        })
        .def("__setitem__", [](vfloat4x4& mat, std::pair<int, int> idx, float val) {
            if (idx.first < 0 || idx.first >= 4 || idx.second < 0 || idx.second >= 4) {
                throw std::out_of_range("Matrix index out of range");
            }
            mat.m[idx.first][idx.second] = val;
        });


    // Base component class
    py::class_<vzm::VzBaseComp>(m, "VzBaseComp")
        .def("get_vid", &vzm::VzBaseComp::GetVID, "Get the VID of this component")
        .def("get_name", &vzm::VzBaseComp::GetName, "Get the name of this component");

    // Scene
    py::class_<vzm::VzScene, vzm::VzBaseComp>(m, "VzScene")
        .def("get_vid", &vzm::VzScene::GetVID)
        .def("get_name", &vzm::VzScene::GetName)
        .def("append_child", &vzm::VzScene::AppendChild,
             py::arg("child"),
             "Append a child actor to the scene")
        .def("set_option_value_array", &vzm::VzScene::SetOptionValueArray,
             py::arg("option_name"), py::arg("values"),
             "Set scene option values (e.g., DDGI_GRID)");

    // Camera
    py::class_<vzm::VzCamera, vzm::VzBaseComp>(m, "VzCamera")
        .def("get_vid", &vzm::VzCamera::GetVID)
        .def("get_name", &vzm::VzCamera::GetName)
        // Pose setters
        .def("set_world_pose", [](vzm::VzCamera* cam, const std::vector<float>& pos, const std::vector<float>& view, const std::vector<float>& up) {
            if (pos.size() != 3 || view.size() != 3 || up.size() != 3) {
                throw std::runtime_error("Position, view, and up must have 3 elements");
            }
            vfloat3 vpos{pos[0], pos[1], pos[2]};
            vfloat3 vview{view[0], view[1], view[2]};
            vfloat3 vup{up[0], up[1], up[2]};
            cam->SetWorldPose(vpos, vview, vup);
        }, py::arg("pos"), py::arg("view"), py::arg("up"),
             "Set camera world pose")
        .def("set_world_pose_by_hierarchy", &vzm::VzCamera::SetWorldPoseByHierarchy,
             "Set world pose from scene hierarchy")
        // Pose getters
        .def("get_world_pose", [](vzm::VzCamera* cam) {
            vfloat3 pos, view, up;
            cam->GetWorldPose(pos, view, up);
            return py::make_tuple(
                std::vector<float>{pos.x, pos.y, pos.z},
                std::vector<float>{view.x, view.y, view.z},
                std::vector<float>{up.x, up.y, up.z}
            );
        }, "Get camera world pose, returns (pos, view, up)")
        // Projection setters
        .def("set_perspective_projection", &vzm::VzCamera::SetPerspectiveProjection,
             py::arg("zNearP"), py::arg("zFarP"), py::arg("fovInDegree"),
             py::arg("aspectRatio"), py::arg("isVertical") = true,
             "Set perspective projection parameters")
        .def("set_orthogonal_projection", &vzm::VzCamera::SetOrthogonalProjection,
             py::arg("width"), py::arg("height"), py::arg("zNearP"), py::arg("zFarP"),
             py::arg("orthoVerticalSize") = 1.f,
             "Set orthogonal projection parameters")
        .def("set_intrinsics_projection", &vzm::VzCamera::SetIntrinsicsProjection,
             py::arg("width"), py::arg("height"), py::arg("nearP"), py::arg("farP"),
             py::arg("fx"), py::arg("fy"), py::arg("cx"), py::arg("cy"), py::arg("s") = 0.f,
             "Set projection from camera intrinsics")
        // Projection getters
        .def("get_perspective_projection", [](vzm::VzCamera* cam, bool isVertical) {
            float zNearP, zFarP, fovInDegree, aspectRatio;
            cam->GetPerspectiveProjection(&zNearP, &zFarP, &fovInDegree, &aspectRatio, isVertical);
            return py::make_tuple(zNearP, zFarP, fovInDegree, aspectRatio);
        }, py::arg("isVertical") = true,
             "Get perspective projection, returns (zNearP, zFarP, fovInDegree, aspectRatio)")
        .def("get_orthogonal_projection", [](vzm::VzCamera* cam) {
            float zNearP, zFarP, width, height, orthoVerticalSize;
            cam->GetOrthogonalProjection(&zNearP, &zFarP, &width, &height, &orthoVerticalSize);
            return py::make_tuple(zNearP, zFarP, width, height, orthoVerticalSize);
        }, "Get orthogonal projection, returns (zNearP, zFarP, width, height, orthoVerticalSize)")
        // Matrix getters
        .def("get_view_matrix", [](vzm::VzCamera* cam, bool rowMajor) {
            vfloat4x4 view;
            cam->GetViewMatrix(view, rowMajor);
            std::vector<std::vector<float>> result(4, std::vector<float>(4));
            for (int i = 0; i < 4; i++) {
                for (int j = 0; j < 4; j++) {
                    result[i][j] = view.m[i][j];
                }
            }
            return result;
        }, py::arg("rowMajor") = false,
             "Get view matrix as nested list")
        .def("get_projection_matrix", [](vzm::VzCamera* cam, bool rowMajor) {
            vfloat4x4 proj;
            cam->GetProjectionMatrix(proj, rowMajor);
            std::vector<std::vector<float>> result(4, std::vector<float>(4));
            for (int i = 0; i < 4; i++) {
                for (int j = 0; j < 4; j++) {
                    result[i][j] = proj.m[i][j];
                }
            }
            return result;
        }, py::arg("rowMajor") = false,
             "Get projection matrix as nested list")
        // Utility getters
        .def("get_near", &vzm::VzCamera::GetNear, "Get near plane distance")
        .def("get_culling_far", &vzm::VzCamera::GetCullingFar, "Get far plane distance for culling")
        .def("is_ortho", &vzm::VzCamera::IsOrtho, "Check if using orthogonal projection")
        .def("is_set_by_intrinsics", &vzm::VzCamera::IsSetByInstrinsics, "Check if set by intrinsics")
        // Clipper
        .def("enable_clipper", &vzm::VzCamera::EnableClipper,
             py::arg("clipBoxEnabled"), py::arg("clipPlaneEnabled"),
             "Enable clip box and/or clip plane")
        .def("set_clip_plane", [](vzm::VzCamera* cam, const std::vector<float>& plane) {
            if (plane.size() != 4) {
                throw std::runtime_error("Clip plane must have 4 elements (a, b, c, d)");
            }
            vfloat4 vplane{plane[0], plane[1], plane[2], plane[3]};
            cam->SetClipPlane(vplane);
        }, py::arg("plane"),
             "Set clip plane (a, b, c, d) where ax + by + cz + d = 0")
        .def("set_clip_box", [](vzm::VzCamera* cam, const std::vector<std::vector<float>>& box) {
            if (box.size() != 4) {
                throw std::runtime_error("Clip box must be a 4x4 matrix");
            }
            vfloat4x4 vbox;
            for (int i = 0; i < 4; i++) {
                if (box[i].size() != 4) {
                    throw std::runtime_error("Clip box must be a 4x4 matrix");
                }
                for (int j = 0; j < 4; j++) {
                    vbox.m[i][j] = box[i][j];
                }
            }
            cam->SetClipBox(vbox);
        }, py::arg("box"),
             "Set clip box as 4x4 transformation matrix")
        .def("is_clipper_enabled", [](vzm::VzCamera* cam) {
            bool clipBoxEnabled = false, clipPlaneEnabled = false;
            bool result = cam->IsClipperEnabled(&clipBoxEnabled, &clipPlaneEnabled);
            return py::make_tuple(result, clipBoxEnabled, clipPlaneEnabled);
        }, "Check if clipper is enabled, returns (enabled, clipBoxEnabled, clipPlaneEnabled)")
        // DVR (Direct Volume Rendering) - for medical imaging
        .def("set_dvr_type", &vzm::VzCamera::SetDVRType,
             py::arg("type"),
             "Set DVR type (DEFAULT or XRAY_AVERAGE)")
        .def("get_dvr_type", &vzm::VzCamera::GetDVRType, "Get DVR type")
        // Layer mask
        .def("set_visible_layer_mask", &vzm::VzCamera::SetVisibleLayerMask,
             py::arg("mask"), py::arg("include_descendants") = false,
             "Set visible layer mask for camera");

    // DVR Type enum
    py::enum_<vzm::VzCamera::DVR_TYPE>(m, "DVR_TYPE")
        .value("DEFAULT", vzm::VzCamera::DVR_TYPE::DEFAULT)
        .value("XRAY_AVERAGE", vzm::VzCamera::DVR_TYPE::XRAY_AVERAGE)
        .export_values();

    // Tonemap enum
    py::enum_<vzm::VzRenderer::Tonemap>(m, "Tonemap")
        .value("Reinhard", vzm::VzRenderer::Tonemap::Reinhard)
        .value("ACES", vzm::VzRenderer::Tonemap::ACES)
        .export_values();

    // ActorFilter enum (flags)
    py::enum_<vzm::VzRenderer::ActorFilter>(m, "ActorFilter", py::arithmetic())
        .value("MESH_OPAQUE", vzm::VzRenderer::ActorFilter::MESH_OPAQUE)
        .value("MESH_TRANSPARENT", vzm::VzRenderer::ActorFilter::MESH_TRANSPARENT)
        .value("MESH_WATER", vzm::VzRenderer::ActorFilter::MESH_WATER)
        .value("MESH_NAVIGATION", vzm::VzRenderer::ActorFilter::MESH_NAVIGATION)
        .value("COLLIDER", vzm::VzRenderer::ActorFilter::COLLIDER)
        .value("VOLUME", vzm::VzRenderer::ActorFilter::VOLUME)
        .value("RENDERABLE_ALL", vzm::VzRenderer::ActorFilter::RENDERABLE_ALL)
        .export_values();

    // Renderer
    py::class_<vzm::VzRenderer, vzm::VzBaseComp>(m, "VzRenderer")
        .def("get_vid", &vzm::VzRenderer::GetVID)
        .def("get_name", &vzm::VzRenderer::GetName)
        // Canvas
        .def("set_canvas", &vzm::VzRenderer::SetCanvas,
             py::arg("w"), py::arg("h"), py::arg("dpi"), py::arg("window") = nullptr,
             "Set canvas size and DPI")
        .def("resize_canvas", &vzm::VzRenderer::ResizeCanvas,
             py::arg("w"), py::arg("h"), py::arg("cam_vid") = 0u,
             "Resize canvas (preserves dpi and window handler)")
        .def("get_canvas", [](vzm::VzRenderer* renderer) {
            uint32_t w = 0, h = 0;
            float dpi = 0.0f;
            renderer->GetCanvas(&w, &h, &dpi, nullptr);
            return py::make_tuple(w, h, dpi);
        }, "Get canvas size and DPI, returns (width, height, dpi)")
        // Viewport and Scissor
        .def("set_viewport", &vzm::VzRenderer::SetViewport,
             py::arg("x"), py::arg("y"), py::arg("w"), py::arg("h"),
             "Set viewport region")
        .def("get_viewport", [](vzm::VzRenderer* renderer) {
            float x, y, w, h;
            renderer->GetViewport(&x, &y, &w, &h);
            return py::make_tuple(x, y, w, h);
        }, "Get viewport region, returns (x, y, w, h)")
        .def("set_scissor", &vzm::VzRenderer::SetScissor,
             py::arg("left"), py::arg("top"), py::arg("right"), py::arg("bottom"),
             "Set scissor region")
        .def("get_scissor", [](vzm::VzRenderer* renderer) {
            int32_t left, top, right, bottom;
            renderer->GetScissor(&left, &top, &right, &bottom);
            return py::make_tuple(left, top, right, bottom);
        }, "Get scissor region, returns (left, top, right, bottom)")
        .def("use_canvas_as_viewport", &vzm::VzRenderer::UseCanvasAsViewport,
             "Set viewport to full canvas size")
        // Layer mask
        .def("set_layer_mask", &vzm::VzRenderer::SetLayerMask,
             py::arg("layerMask"),
             "Set layer mask for rendering")
        // Clear color
        .def("set_clear_color", [](vzm::VzRenderer* renderer, const std::vector<float>& color) {
            if (color.size() != 4) {
                throw std::runtime_error("Color must have 4 elements (RGBA)");
            }
            vfloat4 vcol{color[0], color[1], color[2], color[3]};
            renderer->SetClearColor(vcol);
        }, py::arg("color"),
             "Set clear color (RGBA)")
        .def("get_clear_color", [](vzm::VzRenderer* renderer) {
            vfloat4 color;
            renderer->GetClearColor(color);
            return std::vector<float>{color.x, color.y, color.z, color.w};
        }, "Get clear color (RGBA)")
        .def("enable_clear", &vzm::VzRenderer::EnableClear,
             py::arg("enabled"),
             "Enable or disable clearing before render")
        // Post-processing
        .def("skip_postprocess", &vzm::VzRenderer::SkipPostprocess,
             py::arg("skip"),
             "Skip post-processing pass")
        .def("set_allow_hdr", &vzm::VzRenderer::SetAllowHDR,
             py::arg("enable"),
             "Enable or disable HDR rendering")
        .def("get_allow_hdr", &vzm::VzRenderer::GetAllowHDR,
             "Check if HDR is enabled")
        .def("set_tonemap", &vzm::VzRenderer::SetTonemap,
             py::arg("tonemap"),
             "Set tonemapping operator (Reinhard or ACES)")
        // Frame lock
        .def("enable_frame_lock", &vzm::VzRenderer::EnableFrameLock,
             py::arg("targetFrameRate") = 60.f,
             "Enable frame lock (set -1 to disable)")
        // Render
        .def("render",
             py::overload_cast<const SceneVID, const CamVID, const float>(&vzm::VzRenderer::Render),
             py::arg("scene_vid"), py::arg("cam_vid"), py::arg("dt") = -1.f,
             "Render the scene")
        // Picking
        .def("picking", [](vzm::VzRenderer* renderer, SceneVID vidScene, CamVID vidCam,
                          const std::vector<float>& pos, uint32_t filterFlags, float toleranceRadius) {
            if (pos.size() != 2) {
                throw std::runtime_error("Position must have 2 elements (x, y)");
            }
            vfloat2 vpos{pos[0], pos[1]};
            vfloat3 worldPosition;
            ActorVID vid = 0;
            int primitiveID = -1;
            int maskValue = 0;
            bool result = renderer->Picking(vidScene, vidCam, vpos, filterFlags, toleranceRadius,
                                           worldPosition, vid, &primitiveID, &maskValue);
            return py::make_tuple(result,
                                  std::vector<float>{worldPosition.x, worldPosition.y, worldPosition.z},
                                  vid, primitiveID, maskValue);
        }, py::arg("scene_vid"), py::arg("cam_vid"), py::arg("pos"),
           py::arg("filterFlags"), py::arg("toleranceRadius"),
             "Pick object at screen position, returns (hit, worldPos, actorVID, primitiveID, maskValue)")
        // Coordinate conversion
        .def("unproj_to_world", [](vzm::VzRenderer* renderer, const std::vector<float>& posOnScreen, CamVID camVid) {
            if (posOnScreen.size() != 2) {
                throw std::runtime_error("Position must have 2 elements (x, y)");
            }
            vfloat2 vpos{posOnScreen[0], posOnScreen[1]};
            vzm::VzCamera* cam = camVid != 0 ? static_cast<vzm::VzCamera*>(vzm::GetComponent(camVid)) : nullptr;
            vfloat3 worldPos = renderer->UnprojToWorld(vpos, cam);
            return std::vector<float>{worldPos.x, worldPos.y, worldPos.z};
        }, py::arg("posOnScreen"), py::arg("cam_vid") = 0u,
             "Convert screen position to world coordinates")
        // Render target
        .def("store_render_target", [](vzm::VzRenderer* renderer) {
            std::vector<uint8_t> buffer;
            uint32_t w = 0, h = 0;
            bool result = renderer->StoreRenderTarget(buffer, &w, &h);
            if (!result) {
                throw std::runtime_error("Failed to store render target");
            }
            return py::make_tuple(py::bytes(reinterpret_cast<const char*>(buffer.data()), buffer.size()), w, h);
        }, "Store render target to memory and return (bytes, width, height)")
        .def("store_render_target_to_file", &vzm::VzRenderer::StoreRenderTargetInfoFile,
             py::arg("filename"),
             "Store render target to file")
        // Debug
        .def("show_debug_buffer", &vzm::VzRenderer::ShowDebugBuffer,
             py::arg("debugMode") = "NONE",
             "Show debug buffer (NONE, PRIMITIVE_ID, etc.)")
        .def("set_render_option_enabled", &vzm::VzRenderer::SetRenderOptionEnabled,
             py::arg("optionName"), py::arg("enabled"),
             "Enable or disable a render option")
        .def("set_render_option_value_array", &vzm::VzRenderer::SetRenderOptionValueArray,
             py::arg("optionName"), py::arg("values"),
             "Set render option values");

    // Actor
    py::class_<vzm::VzActor, vzm::VzBaseComp>(m, "VzActor")
        .def("get_vid", &vzm::VzActor::GetVID)
        .def("get_name", &vzm::VzActor::GetName)
        .def("set_position", [](vzm::VzActor* actor, const std::vector<float>& position) {
            if (position.size() != 3) {
                throw std::runtime_error("Position must have 3 elements");
            }
            vfloat3 vpos{position[0], position[1], position[2]};
            actor->SetPosition(vpos);
        }, py::arg("position"),
             "Set actor position")
        .def("set_scale", [](vzm::VzActor* actor, const std::vector<float>& scale) {
            if (scale.size() != 3) {
                throw std::runtime_error("Scale must have 3 elements");
            }
            vfloat3 vscale{scale[0], scale[1], scale[2]};
            actor->SetScale(vscale);
        }, py::arg("scale"),
             "Set actor scale")
        .def("set_rotation", [](vzm::VzActor* actor, const std::vector<float>& euler_degrees) {
            if (euler_degrees.size() != 3) {
                throw std::runtime_error("Euler angles must have 3 elements (roll, pitch, yaw in degrees)");
            }
            vfloat3 euler{euler_degrees[0], euler_degrees[1], euler_degrees[2]};
            actor->SetEulerAngleZXYInDegree(euler);
        }, py::arg("euler_degrees"),
             "Set actor rotation using Euler angles in degrees (roll, pitch, yaw)")
        .def("set_rotation_quaternion", [](vzm::VzActor* actor, const std::vector<float>& quat) {
            if (quat.size() != 4) {
                throw std::runtime_error("Quaternion must have 4 elements (x, y, z, w)");
            }
            vfloat4 q{quat[0], quat[1], quat[2], quat[3]};
            actor->SetQuaternion(q);
        }, py::arg("quaternion"),
             "Set actor rotation using quaternion (x, y, z, w)")
        .def("get_position", [](vzm::VzActor* actor) {
            vfloat3 pos;
            actor->GetPosition(pos);
            return py::make_tuple(pos.x, pos.y, pos.z);
        }, "Get actor local position")
        .def("get_rotation", [](vzm::VzActor* actor) {
            vfloat4 rot;
            actor->GetRotation(rot);
            return py::make_tuple(rot.x, rot.y, rot.z, rot.w);
        }, "Get actor local rotation as quaternion (x, y, z, w)")
        .def("get_scale", [](vzm::VzActor* actor) {
            vfloat3 scale;
            actor->GetScale(scale);
            return py::make_tuple(scale.x, scale.y, scale.z);
        }, "Get actor local scale")
        .def("get_world_position", [](vzm::VzActor* actor) {
            vfloat3 pos;
            actor->GetWorldPosition(pos);
            return py::make_tuple(pos.x, pos.y, pos.z);
        }, "Get actor world position")
        .def("get_world_rotation", [](vzm::VzActor* actor) {
            vfloat4 rot;
            actor->GetWorldRotation(rot);
            return py::make_tuple(rot.x, rot.y, rot.z, rot.w);
        }, "Get actor world rotation as quaternion (x, y, z, w)")
        .def("get_world_scale", [](vzm::VzActor* actor) {
            vfloat3 scale;
            actor->GetWorldScale(scale);
            return py::make_tuple(scale.x, scale.y, scale.z);
        }, "Get actor world scale")
        .def("set_visible_layer_mask", &vzm::VzActor::SetVisibleLayerMask,
             py::arg("mask"), py::arg("include_descendants") = false,
             "Set visible layer mask for actor")
        .def("enable_unlit", &vzm::VzActor::EnableUnlit,
             py::arg("enabled"), py::arg("include_descendants") = true,
             "Enable unlit rendering (no lighting)");

    // Geometry
    py::class_<vzm::VzGeometry, vzm::VzBaseComp>(m, "VzGeometry")
        .def("get_vid", &vzm::VzGeometry::GetVID)
        .def("get_name", &vzm::VzGeometry::GetName);

    // Material TextureSlot enum
    py::enum_<vzm::VzMaterial::TextureSlot>(m, "TextureSlot")
        .value("BASECOLORMAP", vzm::VzMaterial::TextureSlot::BASECOLORMAP)
        .value("NORMALMAP", vzm::VzMaterial::TextureSlot::NORMALMAP)
        .value("SURFACEMAP", vzm::VzMaterial::TextureSlot::SURFACEMAP)
        .value("EMISSIVEMAP", vzm::VzMaterial::TextureSlot::EMISSIVEMAP)
        .value("DISPLACEMENTMAP", vzm::VzMaterial::TextureSlot::DISPLACEMENTMAP)
        .value("OCCLUSIONMAP", vzm::VzMaterial::TextureSlot::OCCLUSIONMAP)
        .value("TRANSMISSIONMAP", vzm::VzMaterial::TextureSlot::TRANSMISSIONMAP)
        .value("SHEENCOLORMAP", vzm::VzMaterial::TextureSlot::SHEENCOLORMAP)
        .value("SHEENROUGHNESSMAP", vzm::VzMaterial::TextureSlot::SHEENROUGHNESSMAP)
        .value("CLEARCOATMAP", vzm::VzMaterial::TextureSlot::CLEARCOATMAP)
        .value("CLEARCOATROUGHNESSMAP", vzm::VzMaterial::TextureSlot::CLEARCOATROUGHNESSMAP)
        .value("CLEARCOATNORMALMAP", vzm::VzMaterial::TextureSlot::CLEARCOATNORMALMAP)
        .value("SPECULARMAP", vzm::VzMaterial::TextureSlot::SPECULARMAP)
        .value("ANISOTROPYMAP", vzm::VzMaterial::TextureSlot::ANISOTROPYMAP)
        .value("TRANSPARENCYMAP", vzm::VzMaterial::TextureSlot::TRANSPARENCYMAP)
        .export_values();

    // Material ShaderType enum
    py::enum_<vzm::VzMaterial::ShaderType>(m, "ShaderType")
        .value("PHONG", vzm::VzMaterial::ShaderType::PHONG)
        .value("PBR", vzm::VzMaterial::ShaderType::PBR)
        .value("UNLIT", vzm::VzMaterial::ShaderType::UNLIT)
        .value("VOLUMEMAP", vzm::VzMaterial::ShaderType::VOLUMEMAP)
        .export_values();

    // Material
    py::class_<vzm::VzMaterial, vzm::VzBaseComp>(m, "VzMaterial")
        .def("get_vid", &vzm::VzMaterial::GetVID)
        .def("get_name", &vzm::VzMaterial::GetName)
        // Base color
        .def("set_base_color", [](vzm::VzMaterial* material, const std::vector<float>& color) {
            if (color.size() != 4) {
                throw std::runtime_error("Color must have 4 elements (RGBA)");
            }
            vfloat4 vcol{color[0], color[1], color[2], color[3]};
            material->SetBaseColor(vcol);
        }, py::arg("color"),
             "Set base color (RGBA)")
        .def("get_base_color", [](vzm::VzMaterial* material) {
            vfloat4 color = material->GetBaseColor();
            return std::vector<float>{color.x, color.y, color.z, color.w};
        }, "Get base color (RGBA)")
        // Texture
        .def("set_texture", py::overload_cast<const VID, const vzm::VzMaterial::TextureSlot>(&vzm::VzMaterial::SetTexture),
             py::arg("texture_vid"), py::arg("slot"),
             "Set texture for a specific slot")
        // Shader type
        .def("set_shader_type", &vzm::VzMaterial::SetShaderType,
             py::arg("shaderType"),
             "Set shader type (PHONG, PBR, UNLIT, VOLUMEMAP)")
        .def("get_shader_type", &vzm::VzMaterial::GetShaderType,
             "Get shader type")
        // Rendering properties
        .def("set_double_sided", &vzm::VzMaterial::SetDoubleSided,
             py::arg("enabled"),
             "Enable double-sided rendering")
        .def("is_double_sided", &vzm::VzMaterial::IsDoubleSided,
             "Check if double-sided rendering is enabled")
        .def("set_shadow_cast", &vzm::VzMaterial::SetShadowCast,
             py::arg("enabled"),
             "Enable shadow casting")
        .def("is_shadow_cast", &vzm::VzMaterial::IsShadowCast,
             "Check if shadow casting is enabled")
        .def("set_shadow_receive", &vzm::VzMaterial::SetShadowReceive,
             py::arg("enabled"),
             "Enable shadow receiving")
        .def("is_shadow_receive", &vzm::VzMaterial::IsShadowReceive,
             "Check if shadow receiving is enabled")
        .def("set_wireframe", &vzm::VzMaterial::SetWireframe,
             py::arg("enabled"),
             "Enable wireframe rendering")
        // Phong factors
        .def("set_phong_factors", [](vzm::VzMaterial* material, const std::vector<float>& factors) {
            if (factors.size() != 4) {
                throw std::runtime_error("Phong factors must have 4 elements");
            }
            vfloat4 vfactors{factors[0], factors[1], factors[2], factors[3]};
            material->SetPhongFactors(vfactors);
        }, py::arg("factors"),
             "Set Phong shading factors")
        // Gaussian splatting
        .def("set_gaussian_splatting_enabled", &vzm::VzMaterial::SetGaussianSplattingEnabled,
             py::arg("enabled"),
             "Enable Gaussian splatting rendering");

    // ActorStaticMesh (derives from VzActor)
    py::class_<vzm::VzActorStaticMesh, vzm::VzActor>(m, "VzActorStaticMesh")
        .def("get_vid", &vzm::VzActorStaticMesh::GetVID)
        .def("get_name", &vzm::VzActorStaticMesh::GetName);

    // Light Type Enum
    py::enum_<vzm::VzLight::LightType>(m, "LightType")
        .value("DIRECTIONAL", vzm::VzLight::LightType::DIRECTIONAL)
        .value("POINT", vzm::VzLight::LightType::POINT)
        .value("SPOT", vzm::VzLight::LightType::SPOT)
        .export_values();

    // Light
    py::class_<vzm::VzLight, vzm::VzBaseComp>(m, "VzLight")
        .def("get_vid", &vzm::VzLight::GetVID)
        .def("get_name", &vzm::VzLight::GetName)
        // Light type
        .def("set_light_type", &vzm::VzLight::SetLightType,
             py::arg("type"),
             "Set light type (DIRECTIONAL, POINT, or SPOT)")
        // Position
        .def("set_position", [](vzm::VzLight* light, const std::vector<float>& position) {
            if (position.size() != 3) {
                throw std::runtime_error("Position must have 3 elements");
            }
            vfloat3 vpos{position[0], position[1], position[2]};
            light->SetPosition(vpos);
        }, py::arg("position"),
             "Set light position")
        // Spotlight specific
        .def("set_spotlight_cone_angle", &vzm::VzLight::SetSpotlightConeAngle,
             py::arg("outerConeAngle"), py::arg("innerConeAngle") = 0.f,
             "Set spotlight cone angles (outer and inner)")
        // Point light specific
        .def("set_pointlight_length", &vzm::VzLight::SetPointlightLength,
             py::arg("length"),
             "Set point light length")
        // Common properties
        .def("set_range", &vzm::VzLight::SetRange,
             py::arg("range"),
             "Set light range")
        .def("set_intensity", &vzm::VzLight::SetIntensity,
             py::arg("intensity"),
             "Set light intensity")
        .def("set_color", [](vzm::VzLight* light, const std::vector<float>& color) {
            if (color.size() != 3) {
                throw std::runtime_error("Color must have 3 elements (RGB)");
            }
            vfloat3 vcol{color[0], color[1], color[2]};
            light->SetColor(vcol);
        }, py::arg("color"),
             "Set light color (RGB)")
        .def("set_radius", &vzm::VzLight::SetRadius,
             py::arg("radius"),
             "Set light source radius (for area lights)")
        .def("set_length", &vzm::VzLight::SetLength,
             py::arg("length"),
             "Set light source length (for tube lights)")
        // Visualizer
        .def("enable_visualizer", &vzm::VzLight::EnableVisualizer,
             py::arg("enabled"),
             "Enable light visualizer helper")
        // Shadows
        .def("enable_cast_shadow", &vzm::VzLight::EnableCastShadow,
             py::arg("enabled"),
             "Enable shadow casting")
        .def("set_cascade_shadow_map_distances", &vzm::VzLight::SetCascadeShadowMapDistances,
             py::arg("cascadeDistances"),
             "Set cascade shadow map distances (for directional lights)")
        // Layer mask
        .def("set_visible_layer_mask", &vzm::VzLight::SetVisibleLayerMask,
             py::arg("mask"), py::arg("include_descendants") = false,
             "Set visible layer mask for light");

    // Texture Format enum
    py::enum_<vzm::VzTexture::TextureFormat>(m, "TextureFormat")
        .value("UNKNOWN", vzm::VzTexture::TextureFormat::UNKNOWN)
        .value("R32G32B32A32_FLOAT", vzm::VzTexture::TextureFormat::R32G32B32A32_FLOAT)
        .value("R32G32B32A32_UINT", vzm::VzTexture::TextureFormat::R32G32B32A32_UINT)
        .value("R16G16B16A16_FLOAT", vzm::VzTexture::TextureFormat::R16G16B16A16_FLOAT)
        .value("R16G16B16A16_UNORM", vzm::VzTexture::TextureFormat::R16G16B16A16_UNORM)
        .value("R8G8B8A8_UNORM", vzm::VzTexture::TextureFormat::R8G8B8A8_UNORM)
        .value("R8G8B8A8_UNORM_SRGB", vzm::VzTexture::TextureFormat::R8G8B8A8_UNORM_SRGB)
        .value("B8G8R8A8_UNORM", vzm::VzTexture::TextureFormat::B8G8R8A8_UNORM)
        .value("R32_FLOAT", vzm::VzTexture::TextureFormat::R32_FLOAT)
        .value("R16_FLOAT", vzm::VzTexture::TextureFormat::R16_FLOAT)
        .value("R8_UNORM", vzm::VzTexture::TextureFormat::R8_UNORM)
        .export_values();

    // Sampler Type enum
    py::enum_<vzm::VzTexture::SamplerType>(m, "SamplerType")
        .value("SAMPLER_DEFAULT", vzm::VzTexture::SamplerType::SAMPLER_DEFAULT)
        .value("SAMPLER_LINEAR_CLAMP", vzm::VzTexture::SamplerType::SAMPLER_LINEAR_CLAMP)
        .value("SAMPLER_LINEAR_WRAP", vzm::VzTexture::SamplerType::SAMPLER_LINEAR_WRAP)
        .value("SAMPLER_LINEAR_MIRROR", vzm::VzTexture::SamplerType::SAMPLER_LINEAR_MIRROR)
        .value("SAMPLER_POINT_CLAMP", vzm::VzTexture::SamplerType::SAMPLER_POINT_CLAMP)
        .value("SAMPLER_POINT_WRAP", vzm::VzTexture::SamplerType::SAMPLER_POINT_WRAP)
        .value("SAMPLER_POINT_MIRROR", vzm::VzTexture::SamplerType::SAMPLER_POINT_MIRROR)
        .value("SAMPLER_ANISO_CLAMP", vzm::VzTexture::SamplerType::SAMPLER_ANISO_CLAMP)
        .value("SAMPLER_ANISO_WRAP", vzm::VzTexture::SamplerType::SAMPLER_ANISO_WRAP)
        .value("SAMPLER_ANISO_MIRROR", vzm::VzTexture::SamplerType::SAMPLER_ANISO_MIRROR)
        .export_values();

    // Texture
    py::class_<vzm::VzTexture, vzm::VzBaseComp>(m, "VzTexture")
        .def("get_vid", &vzm::VzTexture::GetVID)
        .def("get_name", &vzm::VzTexture::GetName)
        // Create from file
        .def("create_from_image_file", &vzm::VzTexture::CreateTextureFromImageFile,
             py::arg("fileName"),
             "Create texture from image file (PNG, JPG, etc.)")
        // Create from memory
        .def("create_from_memory", &vzm::VzTexture::CreateTextureFromMemory,
             py::arg("name"), py::arg("data"), py::arg("textureFormat"),
             py::arg("w"), py::arg("h"), py::arg("d"),
             "Create texture from memory buffer")
        // Create lookup texture
        .def("create_lookup_texture", &vzm::VzTexture::CreateLookupTexture,
             py::arg("name"), py::arg("data"), py::arg("textureFormat"),
             py::arg("w"), py::arg("h"), py::arg("d") = 1u,
             "Create lookup/LUT texture")
        // Update lookup
        .def("update_lookup", &vzm::VzTexture::UpdateLookup,
             py::arg("data"), py::arg("tableValidBeginX"), py::arg("tableValidEndX"),
             "Update lookup texture data")
        // Validity check
        .def("is_valid", &vzm::VzTexture::IsValid,
             "Check if texture is valid")
        // Size and format
        .def("get_texture_size", [](vzm::VzTexture* tex) {
            uint32_t w = 0, h = 0, d = 0;
            tex->GetTextureSize(&w, &h, &d);
            return py::make_tuple(w, h, d);
        }, "Get texture size, returns (width, height, depth)")
        .def("get_texture_format", &vzm::VzTexture::GetTextureFormat,
             "Get texture format")
        .def("get_resource_name", &vzm::VzTexture::GetResourceName,
             "Get resource name")
        // Sampler
        .def("set_sampler_filter", &vzm::VzTexture::SetSamplerFilter,
             py::arg("filter"),
             "Set sampler filter type");

    // Archive (serialization)
    py::class_<vzm::VzArchive, vzm::VzBaseComp>(m, "VzArchive")
        .def("get_vid", &vzm::VzArchive::GetVID)
        .def("get_name", &vzm::VzArchive::GetName)
        .def("close", &vzm::VzArchive::Close,
             "Close the archive")
        .def("load", py::overload_cast<const VID>(&vzm::VzArchive::Load),
             py::arg("vid"),
             "Load a component from the archive")
        .def("load_multiple", py::overload_cast<const std::vector<VID>>(&vzm::VzArchive::Load),
             py::arg("vids"),
             "Load multiple components from the archive")
        .def("store", py::overload_cast<const VID>(&vzm::VzArchive::Store),
             py::arg("vid"),
             "Store a component to the archive")
        .def("store_multiple", py::overload_cast<const std::vector<VID>>(&vzm::VzArchive::Store),
             py::arg("vids"),
             "Store multiple components to the archive")
        .def("save_file", &vzm::VzArchive::SaveFile,
             py::arg("fileName"), py::arg("saveWhenClose") = false,
             "Save archive to file")
        .def("read_file", &vzm::VzArchive::ReadFile,
             py::arg("fileName"),
             "Read archive from file");
}
