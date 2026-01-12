"""
VizMotive Basic Viewer - Test DearPyGui + VizMotive integration
"""
import sys
import os

# Add pyvizmotive to path (relative to this file)
script_dir = os.path.dirname(os.path.abspath(__file__))
engine_root = os.path.dirname(script_dir)
pyvizmotive_path = os.path.join(engine_root, "PythonBindings", "out", "build", "x64-Debug")
sys.path.insert(0, pyvizmotive_path)

# Add DLL path to PATH environment variable
dll_path = pyvizmotive_path
os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")

# Also try to add DLL directory for Python 3.8+
if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(dll_path)
    print(f"Added DLL directory: {dll_path}")

# Change working directory to vz_mcp (for shader paths)
os.chdir(script_dir)
print(f"Working directory: {os.getcwd()}")

import pyvizmotive as vzm
import dearpygui.dearpygui as dpg

class VizMotiveViewer:
    def __init__(self):
        self.engine_initialized = False
        self.scene = None
        self.camera = None
        self.renderer = None

    def init_engine(self):
        """Initialize VizMotive engine"""
        print("Initializing VizMotive engine...")
        result = vzm.init_engine()
        print(f"init_engine() returned: {result}")

        if result:
            self.engine_initialized = True
            print("Engine initialized successfully!")

            # Create basic components
            self.scene = vzm.new_scene("main_scene")
            self.camera = vzm.new_camera("main_camera")
            self.renderer = vzm.new_renderer("main_renderer")

            print(f"Scene: {self.scene}")
            print(f"Camera: {self.camera}")
            print(f"Renderer: {self.renderer}")
        else:
            print("Engine initialization failed!")
            self.engine_initialized = False

    def create_gui(self):
        """Create DearPyGui window"""
        dpg.create_context()

        with dpg.window(label="VizMotive Viewer", tag="main_window", width=800, height=600):
            dpg.add_text("VizMotive Engine Viewer")
            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_text("Engine Status: ")
                dpg.add_text("Not Initialized", tag="engine_status", color=(255, 0, 0))

            dpg.add_button(label="Initialize Engine", callback=self.on_init_engine)

            dpg.add_separator()
            dpg.add_text("Scene Info:")
            dpg.add_text("No scene", tag="scene_info")

        dpg.create_viewport(title="VizMotive Viewer", width=800, height=600)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

    def on_init_engine(self):
        """Button callback to initialize engine"""
        self.init_engine()

        if self.engine_initialized:
            dpg.set_value("engine_status", "Initialized")
            dpg.configure_item("engine_status", color=(0, 255, 0))

            scene_info = f"Scene: {self.scene}\nCamera: {self.camera}\nRenderer: {self.renderer}"
            dpg.set_value("scene_info", scene_info)
        else:
            dpg.set_value("engine_status", "Failed")
            dpg.configure_item("engine_status", color=(255, 0, 0))
            dpg.set_value("scene_info", "Engine initialization failed")

    def run(self):
        """Main loop"""
        self.create_gui()

        # Main loop
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

        # Cleanup
        if self.engine_initialized:
            vzm.deinit_engine()

        dpg.destroy_context()

if __name__ == "__main__":
    print("=" * 60)
    print("VizMotive Basic Viewer")
    print("=" * 60)

    viewer = VizMotiveViewer()
    viewer.run()
