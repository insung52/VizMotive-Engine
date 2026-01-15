"""
VizMotive Test Viewer with GUI Buttons
Tests the buffer overflow bug fix by adding meshes directly via GUI buttons
"""

import sys
import os
import numpy as np
from PIL import Image
import dearpygui.dearpygui as dpg
import logging
from datetime import datetime

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
engine_root = os.path.dirname(os.path.dirname(script_dir))
pyvizmotive_path = os.path.join(engine_root, "PythonBindings", "out", "build", "x64-Debug")
sys.path.insert(0, pyvizmotive_path)

# Add DLL path
dll_path = os.path.join(engine_root, "bin", "x64_Debug")
os.environ["PATH"] = dll_path + os.pathsep + os.environ["PATH"]

import pyvizmotive as vzm

# Setup logging
log_filename = f"viewer_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class VizMotiveTestViewer:
    def __init__(self):
        self.engine_initialized = False
        self.scene = None
        self.camera = None
        self.renderer = None
        self.texture_tag = None
        self.image_tag = None
        self.canvas_initialized = False
        self.frame_count = 0
        self.object_counter = 0
        self.created_objects = []

    def init_engine(self):
        """Initialize VizMotive engine"""
        logger.info("=== Initializing VizMotive Engine ===")

        try:
            vzm.init_engine()
            logger.info("✓ Engine initialized")

            # Create scene
            self.scene = vzm.new_scene("test_scene")
            logger.info(f"✓ Scene created (VID: {self.scene.get_vid()})")

            # Create camera
            self.camera = vzm.new_camera("test_camera")
            pos = [5.0, 5.0, 5.0]
            view = [-5.0, -5.0, -5.0]  # Look at origin
            up = [0.0, 1.0, 0.0]
            self.camera.set_world_pose(pos, view, up)
            self.camera.set_perspective_projection(0.01, 50.0, 60.0, 1.0)
            self.camera.set_visible_layer_mask(0xF)
            logger.info(f"✓ Camera created (VID: {self.camera.get_vid()})")

            # Create renderer
            self.renderer = vzm.new_renderer("test_renderer")
            self.renderer.set_canvas(800, 600, 96.0, None)
            self.renderer.set_clear_color([0.2, 0.2, 0.3, 1.0])
            logger.info(f"✓ Renderer created (VID: {self.renderer.get_vid()})")

            # Add point light
            light = vzm.new_light("main_light")
            light.set_light_type(vzm.LightType.POINT)
            light.set_position([3.0, 5.0, 3.0])
            light.set_color([1.0, 1.0, 1.0])
            light.set_intensity(30.0)
            light.set_range(20.0)
            light.set_visible_layer_mask(0xF, True)
            self.scene.append_child(light)
            logger.info("✓ Light added")

            self.engine_initialized = True
            logger.info("=== Engine initialization complete ===")

        except Exception as e:
            logger.error(f"Failed to initialize engine: {e}", exc_info=True)
            raise

    def create_cube(self):
        """Create a cube at random position"""
        if not self.engine_initialized:
            return

        try:
            self.object_counter += 1
            name = f"cube_{self.object_counter}"

            # Random position
            import random
            pos = [random.uniform(-3, 3), random.uniform(-1, 2), random.uniform(-3, 3)]
            color = [random.random(), random.random(), random.random(), 1.0]

            geometry = vzm.new_geometry(f"{name}_geom")
            vzm.generate_box_geometry(geometry.get_vid(), 1.0, 1.0, 1.0)

            material = vzm.new_material(f"{name}_mat")
            material.set_base_color(color)

            cube = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
            cube.set_position(pos)
            cube.set_scale([1.0, 1.0, 1.0])
            cube.set_visible_layer_mask(0xF, True)

            self.scene.append_child(cube)

            self.created_objects.append({
                'vid': cube.get_vid(),
                'name': name,
                'type': 'cube'
            })

            logger.info(f"✓ Cube #{self.object_counter} created (Total: {len(self.created_objects)} objects)")
            dpg.set_value("object_count", f"Objects: {len(self.created_objects)}")

        except Exception as e:
            logger.error(f"Failed to create cube: {e}", exc_info=True)

    def create_sphere(self):
        """Create a sphere at random position"""
        if not self.engine_initialized:
            return

        try:
            self.object_counter += 1
            name = f"sphere_{self.object_counter}"

            # Random position
            import random
            pos = [random.uniform(-3, 3), random.uniform(-1, 2), random.uniform(-3, 3)]
            color = [random.random(), random.random(), random.random(), 1.0]

            geometry = vzm.new_geometry(f"{name}_geom")
            vzm.generate_icosahedron_geometry(geometry.get_vid(), 0.5, 2)

            material = vzm.new_material(f"{name}_mat")
            material.set_base_color(color)

            sphere = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
            sphere.set_position(pos)
            sphere.set_scale([1.0, 1.0, 1.0])
            sphere.set_visible_layer_mask(0xF, True)

            self.scene.append_child(sphere)

            self.created_objects.append({
                'vid': sphere.get_vid(),
                'name': name,
                'type': 'sphere'
            })

            logger.info(f"✓ Sphere #{self.object_counter} created (Total: {len(self.created_objects)} objects)")
            dpg.set_value("object_count", f"Objects: {len(self.created_objects)}")

        except Exception as e:
            logger.error(f"Failed to create sphere: {e}", exc_info=True)

    def clear_scene(self):
        """Clear all created objects"""
        if not self.engine_initialized:
            return

        try:
            logger.info(f"Clearing {len(self.created_objects)} objects")

            for obj in self.created_objects:
                vzm.remove_component(obj['vid'], True)

            self.created_objects.clear()
            self.object_counter = 0

            logger.info("✓ Scene cleared")
            dpg.set_value("object_count", f"Objects: 0")

        except Exception as e:
            logger.error(f"Failed to clear scene: {e}", exc_info=True)

    def create_gui(self):
        """Create DearPyGui window with control buttons"""
        dpg.create_context()

        with dpg.window(label="VizMotive Test Viewer", tag="main_window", width=800, height=700):
            # Control buttons
            with dpg.group(horizontal=True):
                dpg.add_button(label="Add Cube", callback=lambda: self.create_cube(), width=100, height=40)
                dpg.add_button(label="Add Sphere", callback=lambda: self.create_sphere(), width=100, height=40)
                dpg.add_button(label="Clear Scene", callback=lambda: self.clear_scene(), width=100, height=40)

            dpg.add_text("Objects: 0", tag="object_count")
            dpg.add_separator()
            dpg.add_text("Render output will appear below:", color=(255, 255, 0))
            dpg.add_text("Click buttons above to add meshes and test buffer overflow fix!")

        dpg.create_viewport(title="VizMotive Test Viewer", width=820, height=720)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

    def update_render(self):
        """Update rendering every frame"""
        try:
            # Initialize canvas on first frame
            if not self.canvas_initialized:
                self.renderer.set_canvas(800, 600, 96.0, None)
                self.canvas_initialized = True

            self.frame_count += 1

            # Render the scene
            self.renderer.render(self.scene.get_vid(), self.camera.get_vid())

            # Save to PNG and read back
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
                logger.info(f"Display texture created: {width}x{height}")
            else:
                dpg.set_value(self.texture_tag, img_data)

        except Exception as e:
            logger.error(f"Render error: {e}", exc_info=True)

    def run(self):
        """Run the main application loop"""
        logger.info("=== Starting viewer ===")

        try:
            self.create_gui()

            logger.info("=== Entering main loop ===")
            while dpg.is_dearpygui_running():
                try:
                    if self.engine_initialized:
                        self.update_render()

                    dpg.render_dearpygui_frame()

                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                    break

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in run loop: {e}", exc_info=True)
        finally:
            logger.info("=== Cleaning up ===")
            dpg.destroy_context()

            if self.engine_initialized:
                vzm.deinit_engine()
                logger.info("✓ Engine deinitialized")

            logger.info("=== Viewer shutdown complete ===")


if __name__ == "__main__":
    print("=" * 60)
    print("VizMotive Test Viewer - Buffer Overflow Bug Test")
    print("=" * 60)
    print(f"Log file: {log_filename}")
    print("=" * 60)
    print()
    print("Instructions:")
    print("1. Click 'Add Cube' or 'Add Sphere' to create meshes")
    print("2. Before fix: Crash at 3-7 objects depending on initial state")
    print("3. After fix: Should handle 300+ objects without crash")
    print("=" * 60)

    viewer = VizMotiveTestViewer()
    viewer.init_engine()
    viewer.run()
