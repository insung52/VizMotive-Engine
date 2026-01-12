#include <pybind11/pybind11.h>
#include "vzm2/VzComponentAPIs.h"
#include "vzm2/VzScene.h"
#include "vzm2/VzCamera.h"
#include "vzm2/VzRenderer.h"

namespace py = pybind11;

void bind_types(py::module& m) {
    // Base component class
    py::class_<vzm::VzBaseComp>(m, "VzBaseComp")
        .def("get_vid", &vzm::VzBaseComp::GetVID, "Get the VID of this component")
        .def("get_name", &vzm::VzBaseComp::GetName, "Get the name of this component");

    // Scene
    py::class_<vzm::VzScene, vzm::VzBaseComp>(m, "VzScene")
        .def("get_vid", &vzm::VzScene::GetVID)
        .def("get_name", &vzm::VzScene::GetName);

    // Camera
    py::class_<vzm::VzCamera, vzm::VzBaseComp>(m, "VzCamera")
        .def("get_vid", &vzm::VzCamera::GetVID)
        .def("get_name", &vzm::VzCamera::GetName)
        .def("set_world_pose", &vzm::VzCamera::SetWorldPose,
             py::arg("pos"), py::arg("view"), py::arg("up"),
             "Set camera world pose")
        .def("set_perspective_projection", &vzm::VzCamera::SetPerspectiveProjection,
             py::arg("zNearP"), py::arg("zFarP"), py::arg("fovInDegree"),
             py::arg("aspectRatio"), py::arg("isVertical") = true,
             "Set perspective projection parameters");

    // Renderer
    py::class_<vzm::VzRenderer, vzm::VzBaseComp>(m, "VzRenderer")
        .def("get_vid", &vzm::VzRenderer::GetVID)
        .def("get_name", &vzm::VzRenderer::GetName)
        .def("set_canvas", &vzm::VzRenderer::SetCanvas,
             py::arg("w"), py::arg("h"), py::arg("dpi"), py::arg("window") = nullptr,
             "Set canvas size and DPI")
        .def("render",
             py::overload_cast<const SceneVID, const CamVID, const float>(&vzm::VzRenderer::Render),
             py::arg("scene_vid"), py::arg("cam_vid"), py::arg("dt") = -1.f,
             "Render the scene");
}
