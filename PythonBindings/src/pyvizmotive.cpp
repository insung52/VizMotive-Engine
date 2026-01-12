#include <pybind11/pybind11.h>

namespace py = pybind11;

// Forward declarations of binding functions
void bind_types(py::module& m);
void bind_engine(py::module& m);

PYBIND11_MODULE(pyvizmotive, m) {
    m.doc() = "VizMotive Engine Python Bindings";

    // Bind types first (VzScene, VzCamera, VzRenderer, etc.)
    bind_types(m);

    // Bind engine initialization and basic functions
    bind_engine(m);
}
