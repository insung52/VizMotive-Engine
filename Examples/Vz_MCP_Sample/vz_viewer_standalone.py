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
import logging
from datetime import datetime

# Setup logging to file
log_filename = f"viewer_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

# Disable PIL debug logging (too verbose)
logging.getLogger('PIL').setLevel(logging.WARNING)

logger.info(f"=== VizMotive Viewer Started ===")
logger.info(f"Log file: {log_filename}")

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
        self.created_objects = []  # Track VIDs of created objects for cleanup

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
            logger.debug(f"Light created: VID={light.get_vid()}")
            light.set_light_type(vzm.LightType.POINT)
            light.set_position([3.0, 5.0, 3.0])
            light.set_color([1.0, 1.0, 1.0])
            light.set_intensity(30.0)
            light.set_range(20.0)
            light.set_visible_layer_mask(0xF, True)

            self.scene.append_child(light)

            # DEBUG: Create 3 cubes at initialization to test if crash occurs
            logger.info("DEBUG: Creating 3 test cubes at initialization")
            self._create_test_cubes()

    def _create_test_cubes(self):
        """Create 3 test cubes during initialization (like sample14)"""
        test_cubes = [
            {"pos": [0.0, 0.0, 0.0], "color": [1.0, 0.0, 0.0, 1.0]},  # Red
            {"pos": [3.0, 0.0, 0.0], "color": [0.0, 1.0, 0.0, 1.0]},  # Green
            {"pos": [-3.0, 0.0, 0.0], "color": [0.0, 0.0, 1.0, 1.0]}, # Blue
        ]

        for i, cube_data in enumerate(test_cubes):
            try:
                self.object_counter += 1
                name = f"init_cube_{self.object_counter}"
                logger.debug(f"Creating initialization cube #{self.object_counter}: {name}")

                geometry = vzm.new_geometry(f"{name}_geom")
                logger.debug(f"Geometry created: VID={geometry.get_vid()}")
                vzm.generate_box_geometry(geometry.get_vid(), 1.0, 1.0, 1.0)

                material = vzm.new_material(f"{name}_mat")
                logger.debug(f"Material created: VID={material.get_vid()}")
                material.set_base_color(cube_data["color"])

                cube = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
                logger.debug(f"Actor created: VID={cube.get_vid()}")
                cube.set_position(cube_data["pos"])
                cube.set_scale([1.0, 1.0, 1.0])
                cube.set_visible_layer_mask(0xF, True)

                self.scene.append_child(cube)

                self.created_objects.append({
                    'vid': cube.get_vid(),
                    'name': name,
                    'type': 'cube'
                })

                logger.info(f"✓ Init cube #{self.object_counter} created at {cube_data['pos']}")

            except Exception as e:
                logger.error(f"Failed to create initialization cube #{i+1}: {e}", exc_info=True)

        logger.info(f"DEBUG: Initialization complete with {len(self.created_objects)} cubes")

    def process_commands(self):
        """Read and process commands from file"""
        if not COMMAND_FILE.exists():
            return

        try:
            with open(COMMAND_FILE, 'r') as f:
                commands = json.load(f)

            # Process new commands
            new_commands = commands[len(self.processed_commands):]

            if len(new_commands) > 0:
                logger.info(f"Processing {len(new_commands)} new command(s)")

            for cmd in new_commands:
                logger.info(f"Processing command: {cmd['type']}")
                logger.debug(f"Command details: {cmd}")

                if cmd['type'] == 'create_cube':
                    self.create_cube_object(cmd['position'], cmd['size'], cmd['color'])
                elif cmd['type'] == 'create_sphere':
                    self.create_sphere_object(cmd['position'], cmd['radius'], cmd['color'])
                elif cmd['type'] == 'screenshot':
                    self.take_screenshot(cmd['filename'])
                elif cmd['type'] == 'clear_scene':
                    self.clear_scene()

                self.processed_commands.append(cmd)
                logger.debug(f"Command processed successfully. Total processed: {len(self.processed_commands)}")

            # Save processed state
            if len(new_commands) > 0:
                with open(PROCESSED_FILE, 'w') as f:
                    json.dump(self.processed_commands, f)
                logger.debug(f"Processed state saved")

        except Exception as e:
            logger.error(f"Error processing commands: {e}", exc_info=True)

    def create_cube_object(self, position, size, color):
        """Create a cube object in the scene"""
        if not self.engine_initialized:
            return

        try:
            self.object_counter += 1
            name = f"mcp_cube_{self.object_counter}"

            logger.debug(f"Creating cube #{self.object_counter}: {name}")

            geometry = vzm.new_geometry(f"{name}_geom")
            logger.debug(f"Geometry created: VID={geometry.get_vid()}")

            vzm.generate_box_geometry(geometry.get_vid(), size, size, size)
            logger.debug(f"Box geometry generated")

            material = vzm.new_material(f"{name}_mat")
            logger.debug(f"Material created: VID={material.get_vid()}")
            material.set_base_color(color)

            cube = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
            logger.debug(f"Actor created: VID={cube.get_vid()}")
            cube.set_position(position)
            cube.set_scale([1.0, 1.0, 1.0])
            cube.set_visible_layer_mask(0xF, True)

            self.scene.append_child(cube)

            # Track created objects
            self.created_objects.append({
                'vid': cube.get_vid(),
                'name': name,
                'type': 'cube'
            })

            logger.info(f"✓ Cube #{self.object_counter} added successfully (Total objects: {self.object_counter})")
            logger.debug(f"Scene now has {len(self.created_objects)} tracked objects")

        except Exception as e:
            logger.error(f"Failed to create cube: {e}", exc_info=True)

    def create_sphere_object(self, position, radius, color):
        """Create a sphere object in the scene (using icosahedron as sphere not implemented)"""
        if not self.engine_initialized:
            return

        try:
            self.object_counter += 1
            name = f"mcp_sphere_{self.object_counter}"

            logger.debug(f"Creating sphere #{self.object_counter}: {name}")

            geometry = vzm.new_geometry(f"{name}_geom")
            logger.debug(f"Geometry created: VID={geometry.get_vid()}")

            # Note: GenerateSphereGeometry is not implemented in the engine
            # Using icosahedron as a workaround
            vzm.generate_icosahedron_geometry(geometry.get_vid(), radius, 2)  # detail=2 for smoother sphere
            logger.debug(f"Icosahedron geometry generated")

            material = vzm.new_material(f"{name}_mat")
            logger.debug(f"Material created: VID={material.get_vid()}")
            material.set_base_color(color)

            sphere = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
            logger.debug(f"Actor created: VID={sphere.get_vid()}")
            sphere.set_position(position)
            sphere.set_scale([1.0, 1.0, 1.0])
            sphere.set_visible_layer_mask(0xF, True)

            self.scene.append_child(sphere)

            # Track created objects
            self.created_objects.append({
                'vid': sphere.get_vid(),
                'name': name,
                'type': 'sphere'
            })

            logger.info(f"✓ Sphere #{self.object_counter} added successfully (Total objects: {self.object_counter})")
            logger.debug(f"Scene now has {len(self.created_objects)} tracked objects")

        except Exception as e:
            logger.error(f"Failed to create sphere: {e}", exc_info=True)

    def clear_scene(self):
        """Clear all MCP-created objects"""
        if not self.engine_initialized:
            return

        try:
            logger.info(f"Clearing scene with {len(self.created_objects)} objects")

            # Remove all tracked objects
            for obj in self.created_objects:
                logger.debug(f"Removing {obj['type']} '{obj['name']}' (VID: {obj['vid']})")
                vzm.remove_component(obj['vid'], True)  # True = include descendants

            self.created_objects.clear()
            self.object_counter = 0
            logger.info("✓ Scene cleared successfully")

        except Exception as e:
            logger.error(f"Failed to clear scene: {e}", exc_info=True)

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
        try:
            self.create_gui()

            logger.info("Entering main render loop")

            # Main loop - continuous rendering
            while dpg.is_dearpygui_running():
                try:
                    if self.engine_initialized:
                        # Process MCP commands
                        self.process_commands()

                        # Update render
                        self.update_render()

                    dpg.render_dearpygui_frame()

                except Exception as e:
                    logger.error(f"Error in main loop iteration: {e}", exc_info=True)
                    logger.error(f"Current state - Objects: {len(self.created_objects)}, Frame: {getattr(self, 'frame_count', 0)}")
                    # Don't break, try to continue
                    pass

            logger.info("Exiting main render loop")

        except Exception as e:
            logger.critical(f"Fatal error in run(): {e}", exc_info=True)

        finally:
            # Cleanup
            logger.info("Starting cleanup")
            if self.engine_initialized:
                try:
                    vzm.deinit_engine()
                    logger.info("Engine deinitialized")
                except Exception as e:
                    logger.error(f"Error during engine deinit: {e}", exc_info=True)

            try:
                dpg.destroy_context()
                logger.info("DearPyGui context destroyed")
            except Exception as e:
                logger.error(f"Error during DearPyGui cleanup: {e}", exc_info=True)

            logger.info("=== Viewer shutdown complete ===")

    def update_render(self):
        """Update rendering every frame"""
        try:
            # Initialize canvas on first frame
            if not self.canvas_initialized:
                logger.debug("Initializing canvas...")
                self.renderer.resize_canvas(800, 600, self.camera.get_vid())
                self.canvas_initialized = True
                logger.debug("Canvas initialized")

            # Log scene statistics periodically (every 60 frames)
            if hasattr(self, 'frame_count'):
                self.frame_count += 1
            else:
                self.frame_count = 0

            if self.frame_count % 60 == 0:
                logger.debug(f"Frame {self.frame_count}: Rendering scene with {len(self.created_objects)} objects")

            # Detailed logging for debugging 3+ object crash
            obj_count = len(self.created_objects)
            if obj_count >= 3:
                logger.debug(f"[RENDER START] Frame {self.frame_count}, Objects: {obj_count}")

            # Render the scene
            logger.debug(f"Calling renderer.render() with scene VID={self.scene.get_vid()}, camera VID={self.camera.get_vid()}")
            self.renderer.render(self.scene.get_vid(), self.camera.get_vid())
            logger.debug(f"renderer.render() completed")

            if obj_count >= 3:
                logger.debug(f"[RENDER END] Frame {self.frame_count} completed successfully")

            # TEMPORARILY DISABLED: PNG save/load to test if this causes the crash
            # # Save to PNG and read back (workaround for store_render_target bug)
            # temp_file = "mcp_screenshots/_temp_frame.png"
            # os.makedirs("mcp_screenshots", exist_ok=True)

            # logger.debug(f"Calling store_render_target_to_file()")
            # self.renderer.store_render_target_to_file(temp_file)
            # logger.debug(f"store_render_target_to_file() completed")

            # # Read PNG with PIL
            # logger.debug(f"Opening PNG file with PIL")
            # pil_img = Image.open(temp_file)
            # width, height = pil_img.size
            # logger.debug(f"PNG loaded: {width}x{height}")

            # img_data = np.array(pil_img).astype(np.float32) / 255.0

            # # Convert RGB to RGBA if needed
            # if img_data.shape[2] == 3:
            #     alpha = np.ones((height, width, 1), dtype=np.float32)
            #     img_data = np.concatenate([img_data, alpha], axis=2)

            # img_data = img_data.flatten()

            # # Create or update texture
            # if self.texture_tag is None:
            #     logger.debug(f"Creating new DearPyGui texture")
            #     with dpg.texture_registry():
            #         self.texture_tag = dpg.add_raw_texture(
            #             width=width,
            #             height=height,
            #             default_value=img_data,
            #             format=dpg.mvFormat_Float_rgba
            #         )
            #     self.image_tag = dpg.add_image(self.texture_tag, parent="main_window")
            #     logger.debug(f"Texture created")
            # else:
            #     dpg.set_value(self.texture_tag, img_data)

        except Exception as e:
            logger.error(f"Render error on frame {getattr(self, 'frame_count', 0)}: {e}", exc_info=True)
            logger.error(f"Scene state: {len(self.created_objects)} objects in scene")


if __name__ == "__main__":
    print("=" * 60)
    print("VizMotive Standalone Viewer")
    print("=" * 60)
    print(f"Log file: {log_filename}")
    print("=" * 60)

    viewer = VizMotiveViewer()
    viewer.init_engine()
    viewer.run()
