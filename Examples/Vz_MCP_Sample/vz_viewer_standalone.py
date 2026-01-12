"""
VizMotive Standalone Viewer - Reads commands from file
"""
import sys
import os

# Add pyvizmotive to path (relative to this file)
script_dir = os.path.dirname(os.path.abspath(__file__))
engine_root = os.path.dirname(os.path.dirname(script_dir))
pyvizmotive_path = os.path.join(engine_root, "PythonBindings", "out", "build", "x64-Debug")
sys.path.insert(0, pyvizmotive_path)

# Add DLL path
dll_path = pyvizmotive_path
os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")

if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(dll_path)

# Store directory paths
examples_dir = os.path.dirname(script_dir)

# Create Assets junction if needed
assets_junction = os.path.join(engine_root, "Assets")
assets_source = os.path.join(engine_root, "Examples", "Assets")
if not os.path.exists(assets_junction):
    import subprocess
    subprocess.run(["cmd", "/c", "mklink", "/J", assets_junction, assets_source], check=False)

# Set working directory to Examples
os.chdir(examples_dir)

import pyvizmotive as vzm
import dearpygui.dearpygui as dpg
import numpy as np
from PIL import Image
import json
from pathlib import Path

# Command file path
COMMAND_FILE = Path(script_dir) / "scene_commands.json"
PROCESSED_FILE = Path(script_dir) / "scene_commands_processed.json"

class VizMotiveViewer:
    def __init__(self):
        self.engine_initialized = False
        self.scene = None
        self.camera = None
        self.renderer = None
        self.texture_tag = None
        self.image_tag = None
        self.canvas_initialized = False
        self.object_counter = 0
        self.processed_commands = []

    def init_engine(self):
        """Initialize VizMotive engine"""
        # Clear old command files on startup
        if COMMAND_FILE.exists():
            COMMAND_FILE.unlink()
        if PROCESSED_FILE.exists():
            PROCESSED_FILE.unlink()

        result = vzm.init_engine()

        if result:
            self.engine_initialized = True

            # Create basic components
            self.scene = vzm.new_scene("main_scene")
            self.camera = vzm.new_camera("main_camera")
            self.renderer = vzm.new_renderer("main_renderer")

            # Setup camera
            pos = [0.0, 3.0, 6.0]
            view = [-pos[0], -pos[1], -pos[2]]
            up = [0.0, 1.0, 0.0]
            self.camera.set_world_pose(pos, view, up)
            self.camera.set_perspective_projection(0.01, 50.0, 60.0, 1.0)
            self.camera.set_visible_layer_mask(0xF)

            # Setup renderer
            self.renderer.set_canvas(800, 600, 96.0)
            self.renderer.set_clear_color([0.2, 0.2, 0.3, 1.0])

            # Create a light
            light = vzm.new_light("main_light")
            light.set_light_type(vzm.LightType.POINT)
            light.set_position([3.0, 5.0, 3.0])
            light.set_color([1.0, 1.0, 1.0])
            light.set_intensity(30.0)
            light.set_range(20.0)
            light.set_visible_layer_mask(0xF, True)

            self.scene.append_child(light)

    def process_commands(self):
        """Read and process commands from file"""
        if not COMMAND_FILE.exists():
            return

        try:
            with open(COMMAND_FILE, 'r') as f:
                commands = json.load(f)

            # Process new commands
            new_commands = commands[len(self.processed_commands):]

            for cmd in new_commands:
                if cmd['type'] == 'create_cube':
                    self.create_cube_object(cmd['position'], cmd['size'], cmd['color'])
                elif cmd['type'] == 'create_sphere':
                    self.create_sphere_object(cmd['position'], cmd['radius'], cmd['color'])
                elif cmd['type'] == 'screenshot':
                    self.take_screenshot(cmd['filename'])
                elif cmd['type'] == 'clear_scene':
                    self.clear_scene()

                self.processed_commands.append(cmd)

            # Save processed state
            with open(PROCESSED_FILE, 'w') as f:
                json.dump(self.processed_commands, f)

        except Exception as e:
            print(f"Error processing commands: {e}")

    def create_cube_object(self, position, size, color):
        """Create a cube object in the scene"""
        if not self.engine_initialized:
            return

        self.object_counter += 1
        name = f"mcp_cube_{self.object_counter}"

        geometry = vzm.new_geometry(f"{name}_geom")
        vzm.generate_box_geometry(geometry.get_vid(), size, size, size)

        material = vzm.new_material(f"{name}_mat")
        material.set_base_color(color)

        cube = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
        cube.set_position(position)
        cube.set_scale([1.0, 1.0, 1.0])
        cube.set_visible_layer_mask(0xF, True)

        self.scene.append_child(cube)

    def create_sphere_object(self, position, radius, color):
        """Create a sphere object in the scene"""
        if not self.engine_initialized:
            return

        self.object_counter += 1
        name = f"mcp_sphere_{self.object_counter}"

        geometry = vzm.new_geometry(f"{name}_geom")
        import math
        # Full sphere: phi_length = 2*PI, theta_length = PI
        vzm.generate_sphere_geometry(
            geometry.get_vid(),
            radius,
            32,  # width_segments
            16,  # height_segments
            0.0,  # phi_start
            2.0 * math.pi,  # phi_length (full circle)
            0.0,  # theta_start
            math.pi  # theta_length (half circle, top to bottom)
        )

        material = vzm.new_material(f"{name}_mat")
        material.set_base_color(color)

        sphere = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
        sphere.set_position(position)
        sphere.set_scale([1.0, 1.0, 1.0])
        sphere.set_visible_layer_mask(0xF, True)

        self.scene.append_child(sphere)

    def clear_scene(self):
        """Clear all MCP-created objects"""
        # Note: Actual implementation would need to track and remove objects
        # For now, just reset counter
        self.object_counter = 0

    def take_screenshot(self, filename):
        """Take a screenshot and save to file"""
        if not self.engine_initialized:
            return

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.renderer.store_render_target_to_file(filename)

    def create_gui(self):
        """Create DearPyGui window"""
        dpg.create_context()

        with dpg.window(label="VizMotive Viewer (MCP Controlled)", tag="main_window", width=800, height=600):
            dpg.add_text("VizMotive Engine - Controlled via MCP")
            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_text("Engine Status: ")
                dpg.add_text("Initialized" if self.engine_initialized else "Not Initialized",
                           tag="engine_status",
                           color=(0, 255, 0) if self.engine_initialized else (255, 0, 0))

            dpg.add_separator()
            dpg.add_text("Use Claude Desktop to control this scene!")
            dpg.add_text("Commands are read from scene_commands.json")

        dpg.create_viewport(title="VizMotive Viewer (MCP)", width=1024, height=768)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

    def run(self):
        """Main loop"""
        self.create_gui()

        # Main loop - continuous rendering
        while dpg.is_dearpygui_running():
            if self.engine_initialized:
                # Process MCP commands
                self.process_commands()

                # Update render
                self.update_render()

            dpg.render_dearpygui_frame()

        # Cleanup
        if self.engine_initialized:
            vzm.deinit_engine()

        dpg.destroy_context()

    def update_render(self):
        """Update rendering every frame"""
        try:
            # Initialize canvas on first frame
            if not self.canvas_initialized:
                self.renderer.resize_canvas(800, 600, self.camera.get_vid())
                self.canvas_initialized = True

            # Render the scene
            self.renderer.render(self.scene.get_vid(), self.camera.get_vid())

            # Save to PNG and read back (workaround for store_render_target bug)
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
            pass


if __name__ == "__main__":
    print("=" * 60)
    print("VizMotive Standalone Viewer")
    print("=" * 60)

    viewer = VizMotiveViewer()
    viewer.init_engine()
    viewer.run()
