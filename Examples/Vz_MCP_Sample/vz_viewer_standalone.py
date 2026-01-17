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
RESPONSE_FILE = Path(script_dir) / "scene_responses.json"

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
        self.responses = []  # Track responses to send back to MCP server

    def write_response(self, cmd_id, success, **kwargs):
        """Write response to response file for MCP server to read"""
        response = {
            '_id': cmd_id,
            'success': success,
            **kwargs
        }
        self.responses.append(response)

        # Write all responses to file
        try:
            with open(RESPONSE_FILE, 'w') as f:
                json.dump(self.responses, f, indent=2)
            logger.debug(f"Response written: {response}")
        except Exception as e:
            logger.error(f"Failed to write response: {e}")

    def init_engine(self):
        """Initialize VizMotive engine"""
        # Clear old command files on startup
        if COMMAND_FILE.exists():
            COMMAND_FILE.unlink()
        if PROCESSED_FILE.exists():
            PROCESSED_FILE.unlink()
        if RESPONSE_FILE.exists():
            RESPONSE_FILE.unlink()

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
                cmd_id = cmd.get('_id', 'unknown')
                logger.info(f"Processing command: {cmd['type']} (id: {cmd_id})")

                try:
                    if cmd['type'] == 'create_cube':
                        self.create_cube_object(cmd_id, cmd['position'], cmd['size'], cmd['color'])
                    elif cmd['type'] == 'create_sphere':
                        self.create_sphere_object(cmd_id, cmd['position'], cmd['radius'], cmd['color'])
                    elif cmd['type'] == 'screenshot':
                        self.take_screenshot(cmd_id, cmd['filename'])
                    elif cmd['type'] == 'clear_scene':
                        self.clear_scene(cmd_id)
                    elif cmd['type'] == 'set_camera':
                        self.set_camera(cmd_id, cmd['position'], cmd['look_at'])
                    elif cmd['type'] == 'get_camera_info':
                        self.get_camera_info(cmd_id)
                    elif cmd['type'] == 'create_light':
                        self.create_light_object(cmd_id, cmd)
                    elif cmd['type'] == 'set_light_properties':
                        self.set_light_properties(cmd_id, cmd)
                    elif cmd['type'] == 'set_object_color':
                        self.set_object_color(cmd_id, cmd['name'], cmd['color'])
                    elif cmd['type'] == 'set_material_properties':
                        self.set_material_properties(cmd_id, cmd)
                    elif cmd['type'] == 'set_object_position':
                        self.set_object_position(cmd_id, cmd['name'], cmd['position'])
                    elif cmd['type'] == 'set_object_scale':
                        self.set_object_scale(cmd_id, cmd['name'], cmd['scale'])
                    elif cmd['type'] == 'list_objects':
                        self.list_objects(cmd_id)
                    elif cmd['type'] == 'delete_object':
                        self.delete_object(cmd_id, cmd['name'])
                    elif cmd['type'] == 'load_model':
                        self.load_model(cmd_id, cmd['filepath'], cmd.get('name'))
                    elif cmd['type'] == 'set_render_settings':
                        self.set_render_settings(cmd_id, cmd)
                    elif cmd['type'] == 'set_object_rotation':
                        self.set_object_rotation(cmd_id, cmd['name'], cmd['rotation'])
                    elif cmd['type'] == 'get_object_transform':
                        self.get_object_transform(cmd_id, cmd['name'])
                    elif cmd['type'] == 'set_render_resolution':
                        self.set_render_resolution(cmd_id, cmd['width'], cmd['height'])
                    elif cmd['type'] == 'enable_ddgi':
                        self.enable_ddgi(cmd_id, cmd['enabled'], cmd.get('grid', [32, 8, 32]))
                    else:
                        self.write_response(cmd_id, False, error=f"Unknown command type: {cmd['type']}")
                except Exception as e:
                    logger.error(f"Command {cmd['type']} failed: {e}", exc_info=True)
                    self.write_response(cmd_id, False, error=str(e))

                self.processed_commands.append(cmd)

            # Save processed state
            if len(new_commands) > 0:
                with open(PROCESSED_FILE, 'w') as f:
                    json.dump(self.processed_commands, f)

        except Exception as e:
            logger.error(f"Error processing commands: {e}", exc_info=True)

    def create_cube_object(self, cmd_id, position, size, color):
        """Create a cube object in the scene"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            self.object_counter += 1
            name = f"mcp_cube_{self.object_counter}"

            geometry = vzm.new_geometry(f"{name}_geom")
            vzm.generate_box_geometry(geometry.get_vid(), size, size, size)

            material = vzm.new_material(f"{name}_mat")
            material.set_base_color(color)
            material.set_shadow_cast(True)
            material.set_shadow_receive(True)

            cube = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
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

            logger.info(f"✓ Cube '{name}' created (Total: {len(self.created_objects)} objects)")
            self.write_response(cmd_id, True, name=name, total_objects=len(self.created_objects))

        except Exception as e:
            logger.error(f"Failed to create cube: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def create_sphere_object(self, cmd_id, position, radius, color):
        """Create a sphere object in the scene (using icosahedron as sphere not implemented)"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            self.object_counter += 1
            name = f"mcp_sphere_{self.object_counter}"

            geometry = vzm.new_geometry(f"{name}_geom")
            # Note: GenerateSphereGeometry is not implemented in the engine
            # Using icosahedron as a workaround
            vzm.generate_icosahedron_geometry(geometry.get_vid(), radius, 2)  # detail=2 for smoother sphere

            material = vzm.new_material(f"{name}_mat")
            material.set_base_color(color)
            material.set_shadow_cast(True)
            material.set_shadow_receive(True)

            sphere = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
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

            logger.info(f"✓ Sphere '{name}' created (Total: {len(self.created_objects)} objects)")
            self.write_response(cmd_id, True, name=name, total_objects=len(self.created_objects))

        except Exception as e:
            logger.error(f"Failed to create sphere: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def clear_scene(self, cmd_id):
        """Clear all MCP-created objects"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            removed_count = len(self.created_objects)
            logger.info(f"Clearing scene with {removed_count} objects")

            # Remove all tracked objects
            for obj in self.created_objects:
                logger.debug(f"Removing {obj['type']} '{obj['name']}' (VID: {obj['vid']})")
                vzm.remove_component(obj['vid'], True)  # True = include descendants

            self.created_objects.clear()
            self.object_counter = 0
            logger.info("✓ Scene cleared successfully")
            self.write_response(cmd_id, True, removed_count=removed_count)

        except Exception as e:
            logger.error(f"Failed to clear scene: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def set_camera(self, cmd_id, position, look_at):
        """Set camera position and look-at target"""
        if not self.engine_initialized or not self.camera:
            self.write_response(cmd_id, False, error="Engine or camera not initialized")
            return

        try:
            pos = position
            # Calculate view direction from position to look_at
            view = [look_at[0] - pos[0], look_at[1] - pos[1], look_at[2] - pos[2]]
            up = [0.0, 1.0, 0.0]
            self.camera.set_world_pose(pos, view, up)
            logger.info(f"✓ Camera set to position {position} looking at {look_at}")
            self.write_response(cmd_id, True, position=position, look_at=look_at)
        except Exception as e:
            logger.error(f"Failed to set camera: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def get_camera_info(self, cmd_id):
        """Get current camera info"""
        if not self.engine_initialized or not self.camera:
            self.write_response(cmd_id, False, error="Engine or camera not initialized")
            return

        try:
            pos, view, up = self.camera.get_world_pose()
            logger.info(f"Camera Position: {pos}")
            logger.info(f"Camera View: {view}")
            logger.info(f"Camera Up: {up}")
            self.write_response(cmd_id, True, position=list(pos), view=list(view), up=list(up))
        except Exception as e:
            logger.error(f"Failed to get camera info: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def create_light_object(self, cmd_id, cmd):
        """Create a light in the scene"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            name = cmd['name']
            light_type = cmd.get('light_type', 'point')
            position = cmd.get('position', [0.0, 5.0, 0.0])
            color = cmd.get('color', [1.0, 1.0, 1.0])
            intensity = cmd.get('intensity', 10.0)
            range_val = cmd.get('range', 20.0)

            light = vzm.new_light(name)

            # Set light type
            if light_type == 'directional':
                light.set_light_type(vzm.LightType.DIRECTIONAL)
            elif light_type == 'spot':
                light.set_light_type(vzm.LightType.SPOT)
            else:
                light.set_light_type(vzm.LightType.POINT)

            light.set_position(position)
            light.set_color(color)
            light.set_intensity(intensity)
            light.set_range(range_val)
            light.set_visible_layer_mask(0xF, True)

            self.scene.append_child(light)

            self.created_objects.append({
                'vid': light.get_vid(),
                'name': name,
                'type': 'light'
            })

            logger.info(f"✓ Light '{name}' ({light_type}) created at {position}")
            self.write_response(cmd_id, True, name=name, light_type=light_type)

        except Exception as e:
            logger.error(f"Failed to create light: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def set_light_properties(self, cmd_id, cmd):
        """Modify existing light properties"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            name = cmd['name']
            vid = vzm.get_first_vid_by_name(name)
            if vid == 0:
                logger.warning(f"Light '{name}' not found")
                self.write_response(cmd_id, False, error=f"Light '{name}' not found")
                return

            light = vzm.get_component(vid)
            if light is None:
                logger.warning(f"Could not get light component for '{name}'")
                self.write_response(cmd_id, False, error=f"Could not get light component for '{name}'")
                return

            if cmd.get('intensity') is not None:
                light.set_intensity(cmd['intensity'])
            if cmd.get('color') is not None:
                light.set_color(cmd['color'])
            if cmd.get('cast_shadow') is not None:
                light.enable_cast_shadow(cmd['cast_shadow'])

            logger.info(f"✓ Light '{name}' properties updated")
            self.write_response(cmd_id, True, name=name)

        except Exception as e:
            logger.error(f"Failed to set light properties: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def set_object_color(self, cmd_id, name, color):
        """Set object material color"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            # Find the material by name (convention: object_name + "_mat")
            mat_vid = vzm.get_first_vid_by_name(f"{name}_mat")
            if mat_vid == 0:
                # Try exact name match
                mat_vid = vzm.get_first_vid_by_name(name)

            if mat_vid == 0:
                logger.warning(f"Material for '{name}' not found")
                self.write_response(cmd_id, False, error=f"Material for '{name}' not found. Use list_objects() to see available objects.")
                return

            material = vzm.get_component(mat_vid)
            if material:
                material.set_base_color(color)
                logger.info(f"✓ Color set for '{name}': RGBA{color}")
                self.write_response(cmd_id, True, name=name, color=color)
            else:
                logger.warning(f"Could not get material component for '{name}'")
                self.write_response(cmd_id, False, error=f"Could not get material component for '{name}'")

        except Exception as e:
            logger.error(f"Failed to set object color: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def set_material_properties(self, cmd_id, cmd):
        """Set material rendering properties"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            name = cmd['name']
            mat_vid = vzm.get_first_vid_by_name(f"{name}_mat")
            if mat_vid == 0:
                mat_vid = vzm.get_first_vid_by_name(name)

            if mat_vid == 0:
                logger.warning(f"Material for '{name}' not found")
                self.write_response(cmd_id, False, error=f"Material for '{name}' not found")
                return

            material = vzm.get_component(mat_vid)
            if material is None:
                logger.warning(f"Could not get material component for '{name}'")
                self.write_response(cmd_id, False, error=f"Could not get material component for '{name}'")
                return

            if cmd.get('wireframe') is not None:
                material.set_wireframe(cmd['wireframe'])
            if cmd.get('double_sided') is not None:
                material.set_double_sided(cmd['double_sided'])
            if cmd.get('shader_type') is not None:
                shader_map = {
                    'pbr': vzm.ShaderType.PBR,
                    'phong': vzm.ShaderType.PHONG,
                    'unlit': vzm.ShaderType.UNLIT
                }
                if cmd['shader_type'] in shader_map:
                    material.set_shader_type(shader_map[cmd['shader_type']])
            if cmd.get('shadow_cast') is not None:
                material.set_shadow_cast(cmd['shadow_cast'])
            if cmd.get('shadow_receive') is not None:
                material.set_shadow_receive(cmd['shadow_receive'])

            logger.info(f"✓ Material properties updated for '{name}'")
            self.write_response(cmd_id, True, name=name)

        except Exception as e:
            logger.error(f"Failed to set material properties: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def set_object_position(self, cmd_id, name, position):
        """Move an object to a new position"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            vid = vzm.get_first_vid_by_name(name)
            if vid == 0:
                logger.warning(f"Object '{name}' not found")
                self.write_response(cmd_id, False, error=f"Object '{name}' not found. Use list_objects() to see available objects.")
                return

            obj = vzm.get_component(vid)
            if obj and hasattr(obj, 'set_position'):
                obj.set_position(position)
                logger.info(f"✓ Object '{name}' moved to {position}")
                self.write_response(cmd_id, True, name=name, position=position)
            else:
                logger.warning(f"Object '{name}' has no set_position method")
                self.write_response(cmd_id, False, error=f"Object '{name}' cannot be moved (no set_position method)")

        except Exception as e:
            logger.error(f"Failed to set object position: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def set_object_scale(self, cmd_id, name, scale):
        """Scale an object"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            vid = vzm.get_first_vid_by_name(name)
            if vid == 0:
                logger.warning(f"Object '{name}' not found")
                self.write_response(cmd_id, False, error=f"Object '{name}' not found. Use list_objects() to see available objects.")
                return

            obj = vzm.get_component(vid)
            if obj and hasattr(obj, 'set_scale'):
                obj.set_scale(scale)
                logger.info(f"✓ Object '{name}' scaled to {scale}")
                self.write_response(cmd_id, True, name=name, scale=scale)
            else:
                logger.warning(f"Object '{name}' has no set_scale method")
                self.write_response(cmd_id, False, error=f"Object '{name}' cannot be scaled (no set_scale method)")

        except Exception as e:
            logger.error(f"Failed to set object scale: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def set_object_rotation(self, cmd_id, name, rotation):
        """Set object rotation using euler angles (roll, pitch, yaw in degrees)"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            vid = vzm.get_first_vid_by_name(name)
            if vid == 0:
                logger.warning(f"Object '{name}' not found")
                self.write_response(cmd_id, False, error=f"Object '{name}' not found. Use list_objects() to see available objects.")
                return

            obj = vzm.get_component(vid)
            if obj and hasattr(obj, 'set_rotation'):
                obj.set_rotation(rotation)
                logger.info(f"✓ Object '{name}' rotated to {rotation} degrees (roll, pitch, yaw)")
                self.write_response(cmd_id, True, name=name, rotation=rotation)
            else:
                logger.warning(f"Object '{name}' has no set_rotation method")
                self.write_response(cmd_id, False, error=f"Object '{name}' cannot be rotated (no set_rotation method)")

        except Exception as e:
            logger.error(f"Failed to set object rotation: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def get_object_transform(self, cmd_id, name):
        """Get object's full transform (position, rotation, scale)"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            vid = vzm.get_first_vid_by_name(name)
            if vid == 0:
                logger.warning(f"Object '{name}' not found")
                self.write_response(cmd_id, False, error=f"Object '{name}' not found. Use list_objects() to see available objects.")
                return

            obj = vzm.get_component(vid)
            if obj is None:
                self.write_response(cmd_id, False, error=f"Could not get component for '{name}'")
                return

            # Get local transform
            position = list(obj.get_position()) if hasattr(obj, 'get_position') else None
            rotation = list(obj.get_rotation()) if hasattr(obj, 'get_rotation') else None
            scale = list(obj.get_scale()) if hasattr(obj, 'get_scale') else None

            # Get world transform if available
            world_position = list(obj.get_world_position()) if hasattr(obj, 'get_world_position') else None
            world_rotation = list(obj.get_world_rotation()) if hasattr(obj, 'get_world_rotation') else None
            world_scale = list(obj.get_world_scale()) if hasattr(obj, 'get_world_scale') else None

            logger.info(f"✓ Transform for '{name}':")
            logger.info(f"  Position: {position}")
            logger.info(f"  Rotation (quaternion): {rotation}")
            logger.info(f"  Scale: {scale}")

            self.write_response(cmd_id, True,
                              name=name,
                              position=position,
                              rotation=rotation,
                              scale=scale,
                              world_position=world_position,
                              world_rotation=world_rotation,
                              world_scale=world_scale)

        except Exception as e:
            logger.error(f"Failed to get object transform: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def set_render_resolution(self, cmd_id, width, height):
        """Set render canvas resolution"""
        if not self.engine_initialized or not self.renderer:
            self.write_response(cmd_id, False, error="Engine or renderer not initialized")
            return

        try:
            # Resize renderer canvas
            if self.camera:
                self.renderer.resize_canvas(width, height, self.camera.get_vid())

            # Reset texture so it gets recreated with new size on next frame
            if self.texture_tag is not None:
                try:
                    dpg.delete_item(self.image_tag)
                    dpg.delete_item(self.texture_tag)
                except:
                    pass
                self.texture_tag = None
                self.image_tag = None

            logger.info(f"✓ Render resolution set to {width}x{height}")
            self.write_response(cmd_id, True, width=width, height=height)

        except Exception as e:
            logger.error(f"Failed to set render resolution: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def enable_ddgi(self, cmd_id, enabled, grid):
        """Enable/disable DDGI (Dynamic Diffuse Global Illumination)"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            # Set DDGI enabled in engine config (this is the only required call)
            vzm.set_configure({'DDGI_ENABLED': enabled})

            # Set DDGI grid if scene exists and DDGI is enabled
            if self.scene and enabled:
                # Convert grid to float array as required by engine
                grid_float = [float(g) for g in grid]
                self.scene.set_option_value_array('DDGI_GRID', grid_float)
                logger.info(f"✓ DDGI enabled with grid {grid}")
            else:
                logger.info("✓ DDGI disabled")

            self.write_response(cmd_id, True, enabled=enabled, grid=grid if enabled else None)

        except Exception as e:
            logger.error(f"Failed to configure DDGI: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def list_objects(self, cmd_id):
        """List all objects in the scene"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        logger.info("=== Scene Objects ===")
        for i, obj in enumerate(self.created_objects):
            logger.info(f"  [{i}] {obj['type']}: '{obj['name']}' (VID: {obj['vid']})")
        logger.info(f"=== Total: {len(self.created_objects)} objects ===")

        # Return object list in response
        objects = [{'name': obj['name'], 'type': obj['type']} for obj in self.created_objects]
        self.write_response(cmd_id, True, objects=objects, total=len(objects))

    def delete_object(self, cmd_id, name):
        """Delete an object from the scene"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            # Find in tracked objects
            obj_to_remove = None
            for obj in self.created_objects:
                if obj['name'] == name:
                    obj_to_remove = obj
                    break

            if obj_to_remove:
                vzm.remove_component(obj_to_remove['vid'], True)
                self.created_objects.remove(obj_to_remove)
                logger.info(f"✓ Object '{name}' deleted")
                self.write_response(cmd_id, True, name=name)
            else:
                # Try to find by VID directly
                vid = vzm.get_first_vid_by_name(name)
                if vid != 0:
                    vzm.remove_component(vid, True)
                    logger.info(f"✓ Object '{name}' deleted (not in tracked list)")
                    self.write_response(cmd_id, True, name=name)
                else:
                    logger.warning(f"Object '{name}' not found")
                    self.write_response(cmd_id, False, error=f"Object '{name}' not found. Use list_objects() to see available objects.")

        except Exception as e:
            logger.error(f"Failed to delete object: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def load_model(self, cmd_id, filepath, name=None):
        """Load a 3D model file"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            logger.info(f"Loading model from: {filepath}")
            actor = vzm.load_model_file(filepath)

            if actor:
                actor.set_visible_layer_mask(0xF, True)
                self.scene.append_child(actor)

                model_name = name or os.path.basename(filepath)
                self.created_objects.append({
                    'vid': actor.get_vid(),
                    'name': model_name,
                    'type': 'model'
                })

                logger.info(f"✓ Model '{model_name}' loaded successfully")
                self.write_response(cmd_id, True, name=model_name, filepath=filepath)
            else:
                logger.error(f"Failed to load model: {filepath}")
                self.write_response(cmd_id, False, error=f"Failed to load model from '{filepath}'")

        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def set_render_settings(self, cmd_id, cmd):
        """Configure render settings"""
        if not self.engine_initialized or not self.renderer:
            self.write_response(cmd_id, False, error="Engine or renderer not initialized")
            return

        try:
            if cmd.get('clear_color') is not None:
                self.renderer.set_clear_color(cmd['clear_color'])
                logger.info(f"Clear color set to {cmd['clear_color']}")

            if cmd.get('hdr') is not None:
                self.renderer.set_allow_hdr(cmd['hdr'])
                logger.info(f"HDR {'enabled' if cmd['hdr'] else 'disabled'}")

            if cmd.get('tonemap') is not None:
                tonemap_map = {
                    'reinhard': vzm.Tonemap.Reinhard,
                    'aces': vzm.Tonemap.ACES
                }
                if cmd['tonemap'] in tonemap_map:
                    self.renderer.set_tonemap(tonemap_map[cmd['tonemap']])
                    logger.info(f"Tonemap set to {cmd['tonemap']}")

            logger.info("✓ Render settings updated")
            self.write_response(cmd_id, True)

        except Exception as e:
            logger.error(f"Failed to set render settings: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

    def take_screenshot(self, cmd_id, filename):
        """Take a screenshot and save to file"""
        if not self.engine_initialized:
            self.write_response(cmd_id, False, error="Engine not initialized")
            return

        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            self.renderer.store_render_target_to_file(filename)
            logger.info(f"✓ Screenshot saved to {filename}")
            self.write_response(cmd_id, True, filepath=filename)
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}", exc_info=True)
            self.write_response(cmd_id, False, error=str(e))

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
                logger.info(f"Display texture created: {width}x{height}")
            else:
                dpg.set_value(self.texture_tag, img_data)

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
