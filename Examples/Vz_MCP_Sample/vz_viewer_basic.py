"""
VizMotive Basic Viewer - Test DearPyGui + VizMotive integration
"""
import sys
import os

# Add pyvizmotive to path (relative to this file)
script_dir = os.path.dirname(os.path.abspath(__file__))
engine_root = os.path.dirname(os.path.dirname(script_dir))  # vz_mcp is now in Examples, so go up two levels
pyvizmotive_path = os.path.join(engine_root, "PythonBindings", "out", "build", "x64-Debug")
sys.path.insert(0, pyvizmotive_path)

# Add DLL path to PATH environment variable
dll_path = pyvizmotive_path
os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")

# Also try to add DLL directory for Python 3.8+
if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(dll_path)
    print(f"Added DLL directory: {dll_path}")

# Store directory paths
examples_dir = os.path.dirname(script_dir)

# Create Assets junction if it doesn't exist (for engine initialization)
assets_junction = os.path.join(engine_root, "Assets")
assets_source = os.path.join(engine_root, "Examples", "Assets")
if not os.path.exists(assets_junction):
    import subprocess
    print(f"Creating Assets junction: {assets_junction} -> {assets_source}")
    subprocess.run(["cmd", "/c", "mklink", "/J", assets_junction, assets_source], check=False)

# Set working directory to Examples (for Shaders)
os.chdir(examples_dir)
print(f"Working directory: {os.getcwd()}")

import pyvizmotive as vzm
import dearpygui.dearpygui as dpg
import numpy as np
from PIL import Image
import io

class VizMotiveViewer:
    def __init__(self):
        self.engine_initialized = False
        self.scene = None
        self.camera = None
        self.renderer = None
        self.texture_tag = None
        self.image_tag = None
        self.canvas_initialized = False  # Track if canvas has been resized

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
            self.camera.set_visible_layer_mask(0xF)  # Camera can see all layers

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
            cube.set_visible_layer_mask(0xF, True)  # Make cube visible on layer 0xF

            # Add cube to scene
            self.scene.append_child(cube)
            print("Cube created and added to scene!")

            # Create a light
            print("Creating light...")
            light = vzm.new_light("main_light")
            light.set_light_type(vzm.LightType.POINT)  # Set as point light
            light.set_position([3.0, 5.0, 3.0])
            light.set_color([1.0, 1.0, 1.0])  # White light
            light.set_intensity(30.0)
            light.set_range(20.0)
            light.set_visible_layer_mask(0xF, True)  # Make light affect layer 0xF

            # Add light to scene
            self.scene.append_child(light)
            print("Light created and added to scene!")

            # Second cube (yellow)
            print("\n=== Creating yellow cube ===")
            test_geometry = vzm.new_geometry("test_cube_geometry")
            vzm.generate_box_geometry(test_geometry.get_vid(), 0.5, 0.5, 0.5)

            test_material = vzm.new_material("test_cube_material")
            test_material.set_base_color([1.0, 1.0, 0.0, 1.0])  # Bright yellow

            test_cube = vzm.new_actor_static_mesh("test_cube", test_geometry.get_vid(), test_material.get_vid())
            test_cube.set_position([2.0, 0.0, 0.0])
            test_cube.set_scale([1.0, 1.0, 1.0])
            test_cube.set_visible_layer_mask(0xF, True)

            self.scene.append_child(test_cube)
            print("Yellow cube created with lighting enabled (at position [2, 0, 0])")
            print("Red cube also has lighting enabled")

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
            dpg.add_button(label="Save Screenshot", callback=self.on_save_screenshot)

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
    
    def on_save_screenshot(self):
        """Button callback to save current frame to file (for MCP)"""
        if not self.engine_initialized:
            dpg.set_value("render_info", "Engine not initialized!")
            return

        try:
            import datetime, os

            # 스크린샷 저장 폴더 지정
            folder = "mcp_screenshots"
            os.makedirs(folder, exist_ok=True)  # 폴더 없으면 자동 생성

            # 파일 이름 생성
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(folder, f"screenshot_{timestamp}.png")

            # Save current render target to file
            self.renderer.store_render_target_to_file(filename)
            print(f"Screenshot saved: {filename}")

            dpg.set_value("render_info", f"Screenshot saved: {filename}")
        except Exception as e:
            print(f"Screenshot error: {e}")
            dpg.set_value("render_info", f"Error: {e}")

    def run(self):
        """Main loop"""
        self.create_gui()

        # Main loop - continuous rendering like Blender MCP
        while dpg.is_dearpygui_running():
            # Render VizMotive scene every frame (if engine is initialized)
            if self.engine_initialized:
                self.update_render()

            dpg.render_dearpygui_frame()

        # Cleanup
        if self.engine_initialized:
            vzm.deinit_engine()

        dpg.destroy_context()

    def update_render(self):
        """Update rendering every frame (real-time preview)"""
        try:
            # Initialize canvas on first frame (after GUI is ready)
            if not self.canvas_initialized:
                print("First frame: Initializing canvas to 800x600...")
                self.renderer.resize_canvas(800, 600, self.camera.get_vid())
                self.canvas_initialized = True

            # Render the scene
            self.renderer.render(self.scene.get_vid(), self.camera.get_vid())

            # TEST: Save to PNG and read back
            temp_file = "mcp_screenshots/_temp_frame.png"
            os.makedirs("mcp_screenshots", exist_ok=True)
            self.renderer.store_render_target_to_file(temp_file)

            # Read PNG with PIL
            pil_img = Image.open(temp_file)
            width, height = pil_img.size
            img_data = np.array(pil_img).astype(np.float32) / 255.0

            # Convert RGB to RGBA if needed
            if img_data.shape[2] == 3:
                alpha = np.ones((height, width, 1), dtype=np.float32)
                img_data = np.concatenate([img_data, alpha], axis=2)

            img_data = img_data.flatten()

            # Create or update texture
            if self.texture_tag is None:
                with dpg.texture_registry():
                    self.texture_tag = dpg.add_raw_texture(
                        width=width,
                        height=height,
                        default_value=img_data,
                        format=dpg.mvFormat_Float_rgba
                    )
                self.image_tag = dpg.add_image(self.texture_tag, parent="main_window")
            else:
                dpg.set_value(self.texture_tag, img_data)

        except Exception as e:
            # Silently ignore errors in continuous rendering
            pass

if __name__ == "__main__":
    print("=" * 60)
    print("VizMotive Basic Viewer")
    print("=" * 60)

    viewer = VizMotiveViewer()
    viewer.run()
