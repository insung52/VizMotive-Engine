"""
VizMotive Viewer with MCP Server - Integrated viewer and MCP server
"""
import sys
import os
import threading
import queue

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
from fastmcp import FastMCP

# Global scene state (shared between viewer and MCP)
class SceneState:
    def __init__(self):
        self.viewer = None  # Will be set to VizMotiveViewer instance
        self.command_queue = queue.Queue()  # Commands from MCP to viewer
        self.lock = threading.Lock()

scene_state = SceneState()

# Initialize FastMCP server
mcp = FastMCP("VizMotive Engine")

@mcp.tool()
def ping() -> str:
    """Test tool to verify MCP server is working"""
    return "pong"

@mcp.tool()
def get_scene_info() -> dict:
    """Get current scene information"""
    with scene_state.lock:
        if scene_state.viewer and scene_state.viewer.engine_initialized:
            return {
                "status": "ready",
                "scene": "main_scene",
                "engine": "initialized"
            }
        else:
            return {
                "status": "not_ready",
                "engine": "not_initialized"
            }

@mcp.tool()
def create_cube(x: float, y: float, z: float, size: float = 1.0, color_r: float = 1.0, color_g: float = 0.0, color_b: float = 0.0) -> str:
    """
    Create a cube in the scene

    Args:
        x: X position
        y: Y position
        z: Z position
        size: Cube size (default 1.0)
        color_r: Red component (0.0-1.0)
        color_g: Green component (0.0-1.0)
        color_b: Blue component (0.0-1.0)

    Returns:
        Success message with cube details
    """
    # Queue command for viewer thread to execute
    cmd = {
        'type': 'create_cube',
        'position': [x, y, z],
        'size': size,
        'color': [color_r, color_g, color_b, 1.0]
    }
    scene_state.command_queue.put(cmd)
    return f"Cube queued at position ({x}, {y}, {z}) with size {size} and color RGB({color_r}, {color_g}, {color_b})"

@mcp.tool()
def create_sphere(x: float, y: float, z: float, radius: float = 1.0, color_r: float = 0.0, color_g: float = 1.0, color_b: float = 0.0) -> str:
    """
    Create a sphere in the scene

    Args:
        x: X position
        y: Y position
        z: Z position
        radius: Sphere radius (default 1.0)
        color_r: Red component (0.0-1.0)
        color_g: Green component (0.0-1.0)
        color_b: Blue component (0.0-1.0)

    Returns:
        Success message with sphere details
    """
    cmd = {
        'type': 'create_sphere',
        'position': [x, y, z],
        'radius': radius,
        'color': [color_r, color_g, color_b, 1.0]
    }
    scene_state.command_queue.put(cmd)
    return f"Sphere queued at position ({x}, {y}, {z}) with radius {radius} and color RGB({color_r}, {color_g}, {color_b})"

@mcp.tool()
def render_screenshot() -> str:
    """
    Render and save a screenshot

    Returns:
        Path to the saved screenshot
    """
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mcp_screenshots/screenshot_{timestamp}.png"

    cmd = {
        'type': 'screenshot',
        'filename': filename
    }
    scene_state.command_queue.put(cmd)

    # Wait a bit for the screenshot to be taken
    import time
    time.sleep(0.5)

    return f"Screenshot saved to: {filename}"


# Viewer class (same as before but with command processing)
class VizMotiveViewer:
    def __init__(self):
        self.engine_initialized = False
        self.scene = None
        self.camera = None
        self.renderer = None
        self.texture_tag = None
        self.image_tag = None
        self.canvas_initialized = False
        self.object_counter = 0  # For unique object names

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
            self.camera.set_visible_layer_mask(0xF)

            # Setup renderer
            self.renderer.set_canvas(800, 600, 96.0)
            self.renderer.set_clear_color([0.2, 0.2, 0.3, 1.0])

            # Create a light
            print("Creating light...")
            light = vzm.new_light("main_light")
            light.set_light_type(vzm.LightType.POINT)
            light.set_position([3.0, 5.0, 3.0])
            light.set_color([1.0, 1.0, 1.0])
            light.set_intensity(30.0)
            light.set_range(20.0)
            light.set_visible_layer_mask(0xF, True)

            self.scene.append_child(light)
            print("Light created and added to scene!")

        else:
            print("Engine initialization failed!")
            self.engine_initialized = False

    def process_mcp_commands(self):
        """Process commands from MCP server"""
        while not scene_state.command_queue.empty():
            try:
                cmd = scene_state.command_queue.get_nowait()

                if cmd['type'] == 'create_cube':
                    self.create_cube_object(cmd['position'], cmd['size'], cmd['color'])
                elif cmd['type'] == 'create_sphere':
                    self.create_sphere_object(cmd['position'], cmd['radius'], cmd['color'])
                elif cmd['type'] == 'screenshot':
                    self.take_screenshot(cmd['filename'])

            except queue.Empty:
                break

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
        print(f"Created {name} at {position}")

    def create_sphere_object(self, position, radius, color):
        """Create a sphere object in the scene"""
        if not self.engine_initialized:
            return

        self.object_counter += 1
        name = f"mcp_sphere_{self.object_counter}"

        geometry = vzm.new_geometry(f"{name}_geom")
        vzm.generate_sphere_geometry(geometry.get_vid(), radius)

        material = vzm.new_material(f"{name}_mat")
        material.set_base_color(color)

        sphere = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
        sphere.set_position(position)
        sphere.set_scale([1.0, 1.0, 1.0])
        sphere.set_visible_layer_mask(0xF, True)

        self.scene.append_child(sphere)
        print(f"Created {name} at {position}")

    def take_screenshot(self, filename):
        """Take a screenshot and save to file"""
        if not self.engine_initialized:
            return

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.renderer.store_render_target_to_file(filename)
        print(f"Screenshot saved: {filename}")

    def create_gui(self):
        """Create DearPyGui window"""
        dpg.create_context()

        with dpg.window(label="VizMotive Viewer with MCP", tag="main_window", width=800, height=600):
            dpg.add_text("VizMotive Engine Viewer with MCP Server")
            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_text("Engine Status: ")
                dpg.add_text("Initialized" if self.engine_initialized else "Not Initialized",
                           tag="engine_status",
                           color=(0, 255, 0) if self.engine_initialized else (255, 0, 0))

            dpg.add_separator()
            dpg.add_text("MCP Server: Running on stdio")
            dpg.add_text("Use Claude Desktop to control the scene!")

        dpg.create_viewport(title="VizMotive Viewer with MCP", width=1024, height=768)
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
                self.process_mcp_commands()

                # Update render
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


def run_mcp_server():
    """Run MCP server in a separate thread"""
    print("Starting MCP server thread...")
    mcp.run()


if __name__ == "__main__":
    print("=" * 60)
    print("VizMotive Viewer with MCP Server")
    print("=" * 60)

    # Create viewer
    viewer = VizMotiveViewer()
    scene_state.viewer = viewer

    # Initialize engine
    viewer.init_engine()

    # Start MCP server in a separate thread
    mcp_thread = threading.Thread(target=run_mcp_server, daemon=True)
    mcp_thread.start()

    # Run viewer (blocking)
    viewer.run()
