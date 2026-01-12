#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "vzm2/VzComponentAPIs.h"
#include "vzm2/VzScene.h"
#include "vzm2/VzCamera.h"
#include "vzm2/VzRenderer.h"
#include "vzm2/VzActor.h"
#include "vzm2/VzGeometry.h"
#include "vzm2/VzMaterial.h"
#include "vzm2/VzLight.h"

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
             "Append a child actor to the scene");

    // Camera
    py::class_<vzm::VzCamera, vzm::VzBaseComp>(m, "VzCamera")
        .def("get_vid", &vzm::VzCamera::GetVID)
        .def("get_name", &vzm::VzCamera::GetName)
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
        .def("set_perspective_projection", &vzm::VzCamera::SetPerspectiveProjection,
             py::arg("zNearP"), py::arg("zFarP"), py::arg("fovInDegree"),
             py::arg("aspectRatio"), py::arg("isVertical") = true,
             "Set perspective projection parameters")
        .def("set_visible_layer_mask", &vzm::VzCamera::SetVisibleLayerMask,
             py::arg("mask"),
             "Set visible layer mask for camera");

    // Renderer
    py::class_<vzm::VzRenderer, vzm::VzBaseComp>(m, "VzRenderer")
        .def("get_vid", &vzm::VzRenderer::GetVID)
        .def("get_name", &vzm::VzRenderer::GetName)
        .def("set_canvas", &vzm::VzRenderer::SetCanvas,
             py::arg("w"), py::arg("h"), py::arg("dpi"), py::arg("window") = nullptr,
             "Set canvas size and DPI")
        .def("get_canvas", [](vzm::VzRenderer* renderer) {
            uint32_t w = 0, h = 0;
            float dpi = 0.0f;
            renderer->GetCanvas(&w, &h, &dpi, nullptr);
            return py::make_tuple(w, h, dpi);
        }, "Get canvas size and DPI, returns (width, height, dpi)")
        .def("set_clear_color", [](vzm::VzRenderer* renderer, const std::vector<float>& color) {
            if (color.size() != 4) {
                throw std::runtime_error("Color must have 4 elements (RGBA)");
            }
            vfloat4 vcol{color[0], color[1], color[2], color[3]};
            renderer->SetClearColor(vcol);
        }, py::arg("color"),
             "Set clear color (RGBA)")
        .def("render",
             py::overload_cast<const SceneVID, const CamVID, const float>(&vzm::VzRenderer::Render),
             py::arg("scene_vid"), py::arg("cam_vid"), py::arg("dt") = -1.f,
             "Render the scene")
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
             "Store render target to file");

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
        .def("set_visible_layer_mask", &vzm::VzActor::SetVisibleLayerMask,
             py::arg("mask"), py::arg("include_descendants") = false,
             "Set visible layer mask for actor");

    // Geometry
    py::class_<vzm::VzGeometry, vzm::VzBaseComp>(m, "VzGeometry")
        .def("get_vid", &vzm::VzGeometry::GetVID)
        .def("get_name", &vzm::VzGeometry::GetName);

    // Material
    py::class_<vzm::VzMaterial, vzm::VzBaseComp>(m, "VzMaterial")
        .def("get_vid", &vzm::VzMaterial::GetVID)
        .def("get_name", &vzm::VzMaterial::GetName)
        .def("set_base_color", [](vzm::VzMaterial* material, const std::vector<float>& color) {
            if (color.size() != 4) {
                throw std::runtime_error("Color must have 4 elements (RGBA)");
            }
            vfloat4 vcol{color[0], color[1], color[2], color[3]};
            material->SetBaseColor(vcol);
        }, py::arg("color"),
             "Set base color (RGBA)");

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
        .def("set_light_type", &vzm::VzLight::SetLightType,
             py::arg("type"),
             "Set light type (DIRECTIONAL, POINT, or SPOT)")
        .def("set_position", [](vzm::VzLight* light, const std::vector<float>& position) {
            if (position.size() != 3) {
                throw std::runtime_error("Position must have 3 elements");
            }
            vfloat3 vpos{position[0], position[1], position[2]};
            light->SetPosition(vpos);
        }, py::arg("position"),
             "Set light position")
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
             "Set light color (RGB)");
}
