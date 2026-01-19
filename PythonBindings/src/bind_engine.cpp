#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "vzm2/VzEngineAPIs.h"
#include "vzm2/utils/GeometryGenerator.h"

namespace py = pybind11;

void bind_engine(py::module& m) {
    // Engine initialization and deinitialization
    // Wrapper for init_engine with optional render target format
    // format: 0 = R11G11B10_FLOAT (default, HDR), 1 = R8G8B8A8_UNORM (for Python viewer)
    m.def("init_engine", [](int render_target_format) {
        const char* formatName = (render_target_format == 1) ? "R8G8B8A8_UNORM (Python viewer)" : "R11G11B10_FLOAT (HDR)";
        py::print("[pyvizmotive] init_engine with RENDERTARGET_FORMAT =", render_target_format, "(" + std::string(formatName) + ")");
        vzm::ParamMap<std::string> args;
        args.SetParam("RENDERTARGET_FORMAT", render_target_format);
        bool result = vzm::InitEngineLib(args);
        if (result) {
            py::print("[pyvizmotive] Engine initialized successfully!");
        }
        return result;
    }, py::arg("render_target_format") = 0,
       "Initialize the VizMotive engine.\n"
       "Args:\n"
       "  render_target_format: 0=R11G11B10_FLOAT (HDR, default), 1=R8G8B8A8_UNORM (for Python viewer)");

    // Convenience wrapper for Python viewer initialization (uses R8G8B8A8)
    m.def("init_engine_for_python_viewer", []() {
        py::print("[pyvizmotive] init_engine_for_python_viewer - using R8G8B8A8_UNORM format");
        vzm::ParamMap<std::string> args;
        args.SetParam("RENDERTARGET_FORMAT", 1);  // R8G8B8A8_UNORM
        bool result = vzm::InitEngineLib(args);
        if (result) {
            py::print("[pyvizmotive] Engine initialized successfully!");
        }
        return result;
    }, "Initialize the VizMotive engine with R8G8B8A8_UNORM format (optimized for Python viewer)");

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

    m.def("new_geometry", &vzm::NewGeometry,
          py::arg("name"),
          "Create a new geometry",
          py::return_value_policy::reference);

    m.def("new_material", &vzm::NewMaterial,
          py::arg("name"),
          "Create a new material",
          py::return_value_policy::reference);

    m.def("new_actor_static_mesh", &vzm::NewActorStaticMesh,
          py::arg("name"),
          py::arg("geometry_vid"),
          py::arg("material_vid"),
          py::arg("parent_vid") = 0u,
          "Create a new static mesh actor",
          py::return_value_policy::reference);

    m.def("new_light", &vzm::NewLight,
          py::arg("name"),
          py::arg("parent_vid") = 0u,
          "Create a new light",
          py::return_value_policy::reference);

    m.def("new_texture", &vzm::NewTexture,
          py::arg("name"),
          "Create a new texture",
          py::return_value_policy::reference);

    m.def("new_volume", &vzm::NewVolume,
          py::arg("name"),
          "Create a new volume (3D texture)",
          py::return_value_policy::reference);

    m.def("new_archive", &vzm::NewArchive,
          py::arg("name"),
          "Create a new archive for serialization",
          py::return_value_policy::reference);

    // Model loading
    m.def("load_model_file", &vzm::LoadModelFile,
          py::arg("filename"),
          "Load a 3D model file (OBJ, GLTF, etc.) and return root actor",
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

    // Geometry Generation
    m.def("generate_box_geometry", &vz::geogen::GenerateBoxGeometry,
          py::arg("geometry_vid"),
          py::arg("width"),
          py::arg("height"),
          py::arg("depth"),
          py::arg("tessu") = 1,
          py::arg("tessv") = 1,
          py::arg("tessw") = 1,
          "Generate a box geometry");

    m.def("generate_sphere_geometry", &vz::geogen::GenerateSphereGeometry,
          py::arg("geometry_vid"),
          py::arg("radius") = 1.f,
          py::arg("width_segments") = 32u,
          py::arg("height_segments") = 16u,
          py::arg("phi_start") = 0.f,
          py::arg("phi_length") = 0.f,
          py::arg("theta_start") = 0.f,
          py::arg("theta_length") = 0.f,
          "Generate a sphere geometry");

    m.def("generate_icosahedron_geometry", &vz::geogen::GenerateIcosahedronGeometry,
          py::arg("geometry_vid"),
          py::arg("radius") = 1.f,
          py::arg("detail") = 0u,
          "Generate an icosahedron geometry (sphere approximation)");

    // Engine configuration (for DDGI, etc.)
    m.def("set_configure", [](const std::map<std::string, bool>& bool_options, const std::string& section) {
        vzm::ParamMap<std::string> config;
        for (const auto& [key, value] : bool_options) {
            config.SetParam(key, value);
        }
        vzm::SetConfigure(config, section);
    }, py::arg("options"), py::arg("section") = "SHADER_ENGINE_SETTINGS",
       "Set engine configuration options (e.g., DDGI_ENABLED)");
}
