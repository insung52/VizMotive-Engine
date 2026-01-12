#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "vzm2/VzEngineAPIs.h"

namespace py = pybind11;

void bind_engine(py::module& m) {
    // Engine initialization and deinitialization
    // Wrapper for init_engine without arguments
    m.def("init_engine", []() {
        vzm::ParamMap<std::string> empty_args;
        return vzm::InitEngineLib(empty_args);
    }, "Initialize the VizMotive engine");

    m.def("deinit_engine", &vzm::DeinitEngineLib,
          "Deinitialize the VizMotive engine");

    m.def("is_valid_engine", &vzm::IsValidEngineLib,
          "Check if the engine is valid and initialized");

    // Component creation functions
    m.def("new_scene", &vzm::NewScene,
          py::arg("name"),
          "Create a new scene",
          py::return_value_policy::reference);

    m.def("new_renderer", &vzm::NewRenderer,
          py::arg("name"),
          "Create a new renderer",
          py::return_value_policy::reference);

    m.def("new_camera", &vzm::NewCamera,
          py::arg("name"),
          py::arg("parent_vid") = 0u,
          "Create a new camera",
          py::return_value_policy::reference);

    // Component query functions
    m.def("get_first_vid_by_name", &vzm::GetFirstVidByName,
          py::arg("name"),
          "Get the first VID by name");

    m.def("get_component", &vzm::GetComponent,
          py::arg("vid"),
          "Get component by VID",
          py::return_value_policy::reference);

    m.def("get_name_by_vid", &vzm::GetNameByVid,
          py::arg("vid"),
          "Get name by VID");

    // Component removal
    m.def("remove_component",
          py::overload_cast<const VID, const bool>(&vzm::RemoveComponent),
          py::arg("vid"),
          py::arg("include_descendants") = false,
          "Remove a component by VID");
}
