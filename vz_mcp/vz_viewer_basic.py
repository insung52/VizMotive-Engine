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
import numpy as np

class VizMotiveViewer:
    def __init__(self):
        self.engine_initialized = False
        self.scene = None
        self.camera = None
        self.renderer = None
        self.texture_tag = None
        self.image_tag = None

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

            # Setup camera
            pos = [0.0, 3.0, 6.0]
            view = [-pos[0], -pos[1], -pos[2]]
            up = [0.0, 1.0, 0.0]
            self.camera.set_world_pose(pos, view, up)
            self.camera.set_perspective_projection(0.01, 50.0, 60.0, 1.0)

            # Setup renderer
            self.renderer.set_canvas(800, 600, 96.0)
            self.renderer.set_clear_color([0.2, 0.2, 0.3, 1.0])

            # Create a cube
            print("Creating cube geometry...")
            geometry = vzm.new_geometry("cube_geometry")
            vzm.generate_box_geometry(geometry.get_vid(), 1.0, 1.0, 1.0)

            material = vzm.new_material("cube_material")
            material.set_base_color([0.8, 0.3, 0.3, 1.0])

            cube = vzm.new_actor_static_mesh("cube", geometry.get_vid(), material.get_vid())
            cube.set_position([0.0, 0.0, 0.0])
            cube.set_scale([1.0, 1.0, 1.0])

            # Add cube to scene
            self.scene.append_child(cube)
            print("Cube created and added to scene!")

            # Create a light
            print("Creating light...")
            light = vzm.new_light("main_light")
            light.set_light_type(vzm.LightType.POINT)  # Set as point light
            light.set_position([3.0, 5.0, 3.0])
            light.set_color([1.0, 1.0, 1.0])  # White light
            light.set_intensity(5.0)
            light.set_range(20.0)

            # Add light to scene
            self.scene.append_child(light)
            print("Light created and added to scene!")

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
            dpg.add_button(label="Render Scene", callback=self.on_render_scene)

            dpg.add_separator()
            dpg.add_text("Scene Info:")
            dpg.add_text("No scene", tag="scene_info")

            dpg.add_separator()
            dpg.add_text("Render Info:")
            dpg.add_text("Not rendered", tag="render_info")

            dpg.add_separator()
            dpg.add_text("Render Output:")
            # Placeholder for render output image
            # Will be created dynamically after first render

        dpg.create_viewport(title="VizMotive Viewer", width=1024, height=768)
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

    def on_render_scene(self):
        """Button callback to render scene"""
        if not self.engine_initialized:
            dpg.set_value("render_info", "Engine not initialized!")
            return

        try:
            print("Rendering scene...")
            result = self.renderer.render(self.scene.get_vid(), self.camera.get_vid())
            print(f"Render result: {result}")

            if result:
                # Get canvas size
                width, height, dpi = self.renderer.get_canvas()
                print(f"Canvas size: {width}x{height}, DPI: {dpi}")

                # Get render target data
                print("Storing render target...")
                data_bytes, _, _ = self.renderer.store_render_target()
                print(f"Got render target: {width}x{height}, {len(data_bytes)} bytes")

                # Convert bytes to numpy array (RGBA format)
                img_data = np.frombuffer(data_bytes, dtype=np.uint8)
                img_data = img_data.reshape((height, width, 4))

                # Convert to float32 normalized [0, 1] for DearPyGui
                img_data = img_data.astype(np.float32) / 255.0

                # Flatten for DearPyGui
                img_data = img_data.flatten()

                # Create or update texture
                if self.texture_tag is None:
                    # First render - create texture and image
                    print("Creating texture and image widget...")
                    with dpg.texture_registry():
                        self.texture_tag = dpg.add_raw_texture(
                            width=width,
                            height=height,
                            default_value=img_data,
                            format=dpg.mvFormat_Float_rgba
                        )
                    print(f"Texture created with tag: {self.texture_tag}")

                    # Add image to main window
                    self.image_tag = dpg.add_image(self.texture_tag, parent="main_window")
                    print(f"Image widget added with tag: {self.image_tag}")
                else:
                    # Update existing texture
                    print(f"Updating texture {self.texture_tag}...")
                    dpg.set_value(self.texture_tag, img_data)
                    print("Texture updated!")

                # Also save to file for debugging
                self.renderer.store_render_target_to_file("debug_render.png")
                print("Saved debug_render.png")

                dpg.set_value("render_info", f"Rendered successfully! ({width}x{height})")
            else:
                dpg.set_value("render_info", "Render failed!")
        except Exception as e:
            print(f"Render error: {e}")
            import traceback
            traceback.print_exc()
            dpg.set_value("render_info", f"Error: {e}")

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
