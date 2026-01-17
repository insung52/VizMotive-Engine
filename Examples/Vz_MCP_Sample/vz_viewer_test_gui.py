"""
VizMotive Test Viewer - GUI for testing scene features
- Mouse camera controls (Blender-style)
- Direct render buffer display (no PNG)
- Object selection and editing
"""
import sys
import os
import math
import time

# Add pyvizmotive to path
script_dir = os.path.dirname(os.path.abspath(__file__))
engine_root = os.path.dirname(os.path.dirname(script_dir))
pyvizmotive_path = os.path.join(engine_root, "PythonBindings", "out", "build", "x64-Debug")
sys.path.insert(0, pyvizmotive_path)

dll_path = pyvizmotive_path
os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")
if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(dll_path)

examples_dir = os.path.dirname(script_dir)

# Create Assets junction if needed
assets_junction = os.path.join(engine_root, "Assets")
assets_source = os.path.join(engine_root, "Examples", "Assets")
if not os.path.exists(assets_junction):
    import subprocess
    subprocess.run(["cmd", "/c", "mklink", "/J", assets_junction, assets_source], check=False)

os.chdir(examples_dir)

import pyvizmotive as vzm
import dearpygui.dearpygui as dpg
import numpy as np
import random


def decode_r11g11b10_float(data, width, height):
    """
    Decode R11G11B10_FLOAT format to RGBA8.
    R11G11B10_FLOAT packs RGB into 32 bits:
    - R: bits 0-10 (11 bits, 5-bit exponent, 6-bit mantissa)
    - G: bits 11-21 (11 bits, 5-bit exponent, 6-bit mantissa)
    - B: bits 22-31 (10 bits, 5-bit exponent, 5-bit mantissa)
    """
    # Interpret as uint32
    uint32_data = np.frombuffer(data, dtype=np.uint32).reshape((height, width))

    # Extract components
    r_bits = uint32_data & 0x7FF  # bits 0-10
    g_bits = (uint32_data >> 11) & 0x7FF  # bits 11-21
    b_bits = (uint32_data >> 22) & 0x3FF  # bits 22-31

    def decode_11bit_float(bits):
        """Decode 11-bit float (5-bit exponent, 6-bit mantissa, no sign)"""
        exponent = (bits >> 6) & 0x1F
        mantissa = bits & 0x3F

        result = np.zeros_like(bits, dtype=np.float32)

        # Handle special cases
        zero_mask = (exponent == 0) & (mantissa == 0)
        denorm_mask = (exponent == 0) & (mantissa != 0)
        inf_mask = (exponent == 31) & (mantissa == 0)
        nan_mask = (exponent == 31) & (mantissa != 0)
        normal_mask = ~(zero_mask | denorm_mask | inf_mask | nan_mask)

        # Denormalized
        result[denorm_mask] = (mantissa[denorm_mask] / 64.0) * (2.0 ** -14)

        # Normalized
        result[normal_mask] = (1.0 + mantissa[normal_mask] / 64.0) * (2.0 ** (exponent[normal_mask].astype(np.float32) - 15))

        # Infinity
        result[inf_mask] = np.inf

        return result

    def decode_10bit_float(bits):
        """Decode 10-bit float (5-bit exponent, 5-bit mantissa, no sign)"""
        exponent = (bits >> 5) & 0x1F
        mantissa = bits & 0x1F

        result = np.zeros_like(bits, dtype=np.float32)

        zero_mask = (exponent == 0) & (mantissa == 0)
        denorm_mask = (exponent == 0) & (mantissa != 0)
        inf_mask = (exponent == 31) & (mantissa == 0)
        nan_mask = (exponent == 31) & (mantissa != 0)
        normal_mask = ~(zero_mask | denorm_mask | inf_mask | nan_mask)

        # Denormalized
        result[denorm_mask] = (mantissa[denorm_mask] / 32.0) * (2.0 ** -14)

        # Normalized
        result[normal_mask] = (1.0 + mantissa[normal_mask] / 32.0) * (2.0 ** (exponent[normal_mask].astype(np.float32) - 15))

        # Infinity
        result[inf_mask] = np.inf

        return result

    # Decode to float
    r_float = decode_11bit_float(r_bits)
    g_float = decode_11bit_float(g_bits)
    b_float = decode_10bit_float(b_bits)

    # Simple tone mapping (clamp to 0-1 range) and convert to uint8
    r_uint8 = np.clip(r_float * 255, 0, 255).astype(np.uint8)
    g_uint8 = np.clip(g_float * 255, 0, 255).astype(np.uint8)
    b_uint8 = np.clip(b_float * 255, 0, 255).astype(np.uint8)
    a_uint8 = np.full_like(r_uint8, 255)

    # Stack to RGBA
    rgba = np.stack([r_uint8, g_uint8, b_uint8, a_uint8], axis=-1)

    return rgba

class OrbitCamera:
    """Orbit camera controller (Blender-style)"""
    def __init__(self):
        self.target = [0.0, 0.0, 0.0]
        self.distance = 10.0
        self.azimuth = 45.0  # Horizontal angle (degrees)
        self.elevation = 30.0  # Vertical angle (degrees)

        self.min_distance = 1.0
        self.max_distance = 100.0
        self.min_elevation = -89.0
        self.max_elevation = 89.0

    def get_position(self):
        """Calculate camera position from spherical coordinates"""
        az_rad = math.radians(self.azimuth)
        el_rad = math.radians(self.elevation)

        x = self.target[0] + self.distance * math.cos(el_rad) * math.sin(az_rad)
        y = self.target[1] + self.distance * math.sin(el_rad)
        z = self.target[2] + self.distance * math.cos(el_rad) * math.cos(az_rad)

        return [x, y, z]

    def orbit(self, dx, dy):
        """Orbit camera around target"""
        self.azimuth -= dx * 0.5
        self.elevation += dy * 0.5
        self.elevation = max(self.min_elevation, min(self.max_elevation, self.elevation))

    def pan(self, dx, dy):
        """Pan camera (move target)"""
        az_rad = math.radians(self.azimuth)

        # Right vector
        right_x = math.cos(az_rad)
        right_z = -math.sin(az_rad)

        # Move target
        pan_speed = self.distance * 0.002
        self.target[0] -= dx * right_x * pan_speed
        self.target[2] -= dx * right_z * pan_speed
        self.target[1] += dy * pan_speed

    def zoom(self, delta):
        """Zoom in/out"""
        self.distance *= (1.0 - delta * 0.1)
        self.distance = max(self.min_distance, min(self.max_distance, self.distance))


class TestViewer:
    def __init__(self):
        self.engine_initialized = False
        self.scene = None
        self.camera = None
        self.renderer = None
        self.texture_tag = None
        self.image_tag = None
        self.canvas_initialized = False
        self.object_counter = 0
        self.created_objects = []
        self.lights = []

        # Camera
        self.orbit_cam = OrbitCamera()

        # Mouse state
        self.mouse_down_middle = False
        self.mouse_down_right = False
        self.last_mouse_pos = [0, 0]

        # Render settings
        self.render_width = 800
        self.render_height = 600

        # Selected object
        self.selected_object = None

        # FPS tracking
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0

    def init_engine(self):
        """Initialize VizMotive engine"""
        result = vzm.init_engine()
        if result:
            self.engine_initialized = True

            self.scene = vzm.new_scene("test_scene")
            self.camera = vzm.new_camera("test_camera")
            self.renderer = vzm.new_renderer("test_renderer")

            self.update_camera()
            self.camera.set_perspective_projection(0.01, 100.0, 45.0, 1.0)
            self.camera.set_visible_layer_mask(0xF)

            self.renderer.set_canvas(self.render_width, self.render_height, 96.0)
            self.renderer.set_clear_color([0.15, 0.15, 0.2, 1.0])

            self.create_default_light()
            self.create_floor()

            print("Engine initialized!")
            return True
        return False

    def update_camera(self):
        """Update camera from orbit controller"""
        pos = self.orbit_cam.get_position()
        target = self.orbit_cam.target
        view = [target[0] - pos[0], target[1] - pos[1], target[2] - pos[2]]
        up = [0.0, 1.0, 0.0]
        self.camera.set_world_pose(pos, view, up)

    def create_default_light(self):
        """Create default directional light with shadows"""
        light = vzm.new_light("main_light")
        light.set_light_type(vzm.LightType.DIRECTIONAL)
        light.set_position([5.0, 10.0, 5.0])
        light.set_color([1.0, 1.0, 0.95])
        light.set_intensity(3.0)
        light.enable_cast_shadow(True)
        light.set_visible_layer_mask(0xF, True)
        self.scene.append_child(light)
        self.lights.append({'vid': light.get_vid(), 'name': 'main_light', 'type': 'directional'})

    def create_floor(self):
        """Create floor plane"""
        geometry = vzm.new_geometry("floor_geom")
        vzm.generate_box_geometry(geometry.get_vid(), 20.0, 0.1, 20.0)

        material = vzm.new_material("floor_mat")
        material.set_base_color([0.4, 0.4, 0.45, 1.0])
        material.set_shadow_cast(False)
        material.set_shadow_receive(True)

        floor = vzm.new_actor_static_mesh("floor", geometry.get_vid(), material.get_vid())
        floor.set_position([0.0, -0.5, 0.0])
        floor.set_visible_layer_mask(0xF, True)
        self.scene.append_child(floor)
        self.created_objects.append({'vid': floor.get_vid(), 'name': 'floor', 'type': 'floor', 'mat_vid': material.get_vid()})

    def create_cube(self):
        """Create a cube"""
        self.object_counter += 1
        name = f"cube_{self.object_counter}"
        pos = [random.uniform(-3, 3), random.uniform(0.5, 2), random.uniform(-3, 3)]
        color = [random.random(), random.random(), random.random(), 1.0]

        geometry = vzm.new_geometry(f"{name}_geom")
        vzm.generate_box_geometry(geometry.get_vid(), 1.0, 1.0, 1.0)

        material = vzm.new_material(f"{name}_mat")
        material.set_base_color(color)
        material.set_shadow_cast(True)
        material.set_shadow_receive(True)

        cube = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
        cube.set_position(pos)
        cube.set_visible_layer_mask(0xF, True)
        self.scene.append_child(cube)

        self.created_objects.append({
            'vid': cube.get_vid(),
            'name': name,
            'type': 'cube',
            'mat_vid': material.get_vid()
        })
        self.update_object_list()
        self.select_object(name)

    def create_sphere(self):
        """Create a sphere"""
        self.object_counter += 1
        name = f"sphere_{self.object_counter}"
        pos = [random.uniform(-3, 3), random.uniform(0.5, 2), random.uniform(-3, 3)]
        color = [random.random(), random.random(), random.random(), 1.0]

        geometry = vzm.new_geometry(f"{name}_geom")
        vzm.generate_icosahedron_geometry(geometry.get_vid(), 0.5, 3)

        material = vzm.new_material(f"{name}_mat")
        material.set_base_color(color)
        material.set_shadow_cast(True)
        material.set_shadow_receive(True)

        sphere = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
        sphere.set_position(pos)
        sphere.set_visible_layer_mask(0xF, True)
        self.scene.append_child(sphere)

        self.created_objects.append({
            'vid': sphere.get_vid(),
            'name': name,
            'type': 'sphere',
            'mat_vid': material.get_vid()
        })
        self.update_object_list()
        self.select_object(name)

    def create_point_light(self):
        """Create point light"""
        name = f"point_light_{len(self.lights)}"
        light = vzm.new_light(name)
        light.set_light_type(vzm.LightType.POINT)
        light.set_position([random.uniform(-3, 3), random.uniform(2, 5), random.uniform(-3, 3)])
        light.set_color([1.0, 0.9, 0.8])
        light.set_intensity(15.0)
        light.set_range(15.0)
        light.enable_cast_shadow(True)
        light.set_visible_layer_mask(0xF, True)
        self.scene.append_child(light)
        self.lights.append({'vid': light.get_vid(), 'name': name, 'type': 'point'})

    def select_object(self, name):
        """Select an object and update property panel"""
        self.selected_object = None
        for obj in self.created_objects:
            if obj['name'] == name:
                self.selected_object = obj
                break

        self.update_property_panel()

    def update_property_panel(self):
        """Update property panel with selected object"""
        if self.selected_object is None:
            dpg.set_value("selected_name", "None")
            dpg.configure_item("prop_pos_x", enabled=False)
            dpg.configure_item("prop_pos_y", enabled=False)
            dpg.configure_item("prop_pos_z", enabled=False)
            dpg.configure_item("prop_color", enabled=False)
            dpg.configure_item("prop_shadow_cast", enabled=False)
            dpg.configure_item("prop_shadow_receive", enabled=False)
            return

        obj = self.selected_object
        dpg.set_value("selected_name", f"{obj['name']} ({obj['type']})")

        # Get position
        actor = vzm.get_component(obj['vid'])
        if actor:
            pos = actor.get_position()
            dpg.set_value("prop_pos_x", pos[0])
            dpg.set_value("prop_pos_y", pos[1])
            dpg.set_value("prop_pos_z", pos[2])
            dpg.configure_item("prop_pos_x", enabled=True)
            dpg.configure_item("prop_pos_y", enabled=True)
            dpg.configure_item("prop_pos_z", enabled=True)

        # Get material properties
        if 'mat_vid' in obj:
            mat = vzm.get_component(obj['mat_vid'])
            if mat:
                color = mat.get_base_color()
                # Convert to 0-255 for color picker
                dpg.set_value("prop_color", [int(color[0]*255), int(color[1]*255), int(color[2]*255), 255])
                dpg.configure_item("prop_color", enabled=True)

                dpg.set_value("prop_shadow_cast", mat.is_shadow_cast())
                dpg.set_value("prop_shadow_receive", mat.is_shadow_receive())
                dpg.configure_item("prop_shadow_cast", enabled=True)
                dpg.configure_item("prop_shadow_receive", enabled=True)

    def apply_position(self):
        """Apply position to selected object"""
        if self.selected_object is None:
            return

        actor = vzm.get_component(self.selected_object['vid'])
        if actor:
            pos = [
                dpg.get_value("prop_pos_x"),
                dpg.get_value("prop_pos_y"),
                dpg.get_value("prop_pos_z")
            ]
            actor.set_position(pos)

    def apply_color(self, sender, app_data):
        """Apply color to selected object"""
        if self.selected_object is None or 'mat_vid' not in self.selected_object:
            return

        mat = vzm.get_component(self.selected_object['mat_vid'])
        if mat:
            # app_data is [r, g, b, a] in 0-255 range
            color = [app_data[0]/255.0, app_data[1]/255.0, app_data[2]/255.0, 1.0]
            mat.set_base_color(color)

    def apply_shadow_cast(self, sender, value):
        """Apply shadow cast setting"""
        if self.selected_object is None or 'mat_vid' not in self.selected_object:
            return
        mat = vzm.get_component(self.selected_object['mat_vid'])
        if mat:
            mat.set_shadow_cast(value)

    def apply_shadow_receive(self, sender, value):
        """Apply shadow receive setting"""
        if self.selected_object is None or 'mat_vid' not in self.selected_object:
            return
        mat = vzm.get_component(self.selected_object['mat_vid'])
        if mat:
            mat.set_shadow_receive(value)

    def delete_selected(self):
        """Delete selected object"""
        if self.selected_object is None or self.selected_object['name'] == 'floor':
            return

        vzm.remove_component(self.selected_object['vid'], True)
        self.created_objects.remove(self.selected_object)
        self.selected_object = None
        self.update_object_list()
        self.update_property_panel()

    def clear_objects(self):
        """Clear all objects except floor"""
        for obj in self.created_objects[:]:
            if obj['name'] != 'floor':
                vzm.remove_component(obj['vid'], True)
                self.created_objects.remove(obj)
        self.object_counter = 0
        self.selected_object = None
        self.update_object_list()
        self.update_property_panel()

    def update_object_list(self):
        """Update object listbox"""
        if dpg.does_item_exist("object_list"):
            names = [obj['name'] for obj in self.created_objects]
            dpg.configure_item("object_list", items=names)

    def on_object_selected(self, sender, app_data):
        """Handle object list selection"""
        self.select_object(app_data)

    def toggle_ddgi(self, sender, value):
        """Toggle DDGI"""
        vzm.set_configure({'DDGI_ENABLED': value})
        if value and self.scene:
            self.scene.set_option_value_array('DDGI_GRID', [32.0, 8.0, 32.0])

    def set_light_intensity(self, sender, value):
        """Set main light intensity"""
        if self.lights:
            light = vzm.get_component(self.lights[0]['vid'])
            if light:
                light.set_intensity(value)

    def set_light_shadow(self, sender, value):
        """Toggle main light shadow"""
        if self.lights:
            light = vzm.get_component(self.lights[0]['vid'])
            if light:
                light.enable_cast_shadow(value)

    def take_screenshot(self):
        """Take screenshot"""
        import datetime
        os.makedirs("mcp_screenshots", exist_ok=True)
        filename = f"mcp_screenshots/test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.renderer.store_render_target_to_file(filename)
        print(f"Screenshot: {filename}")

    def handle_mouse(self):
        """Handle mouse input for camera control"""
        # Check if render panel is hovered (render_image may not exist yet)
        panel_hovered = dpg.does_item_exist("render_panel") and dpg.is_item_hovered("render_panel")
        image_hovered = dpg.does_item_exist("render_image") and dpg.is_item_hovered("render_image")
        if not panel_hovered and not image_hovered:
            return

        mouse_pos = dpg.get_mouse_pos()

        # Middle mouse - Orbit or Pan
        if dpg.is_mouse_button_down(dpg.mvMouseButton_Middle):
            if not self.mouse_down_middle:
                self.mouse_down_middle = True
                self.last_mouse_pos = mouse_pos
            else:
                dx = mouse_pos[0] - self.last_mouse_pos[0]
                dy = mouse_pos[1] - self.last_mouse_pos[1]

                if dpg.is_key_down(dpg.mvKey_Shift):
                    self.orbit_cam.pan(dx, dy)
                else:
                    self.orbit_cam.orbit(dx, dy)

                self.update_camera()
                self.last_mouse_pos = mouse_pos
        else:
            self.mouse_down_middle = False

        # Right mouse - Orbit (alternative)
        if dpg.is_mouse_button_down(dpg.mvMouseButton_Right):
            if not self.mouse_down_right:
                self.mouse_down_right = True
                self.last_mouse_pos = mouse_pos
            else:
                dx = mouse_pos[0] - self.last_mouse_pos[0]
                dy = mouse_pos[1] - self.last_mouse_pos[1]
                self.orbit_cam.orbit(dx, dy)
                self.update_camera()
                self.last_mouse_pos = mouse_pos
        else:
            self.mouse_down_right = False

    def handle_scroll(self, sender, app_data):
        """Handle mouse wheel for zoom"""
        self.orbit_cam.zoom(app_data)
        self.update_camera()

    def create_gui(self):
        """Create GUI"""
        dpg.create_context()

        # Mouse wheel handler
        with dpg.handler_registry():
            dpg.add_mouse_wheel_handler(callback=self.handle_scroll)

        with dpg.window(label="VizMotive Test Viewer", tag="main_window", width=1280, height=800):
            with dpg.group(horizontal=True):
                # Left panel - Controls
                with dpg.child_window(width=280, height=-1):
                    # Object Creation
                    dpg.add_text("=== Create Objects ===")
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Cube", callback=lambda: self.create_cube(), width=80)
                        dpg.add_button(label="Sphere", callback=lambda: self.create_sphere(), width=80)
                        dpg.add_button(label="Light", callback=lambda: self.create_point_light(), width=80)
                    dpg.add_separator()

                    # Object List
                    dpg.add_text("=== Scene Objects ===")
                    dpg.add_listbox([], tag="object_list", num_items=8, width=-1,
                                   callback=self.on_object_selected)
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Delete", callback=lambda: self.delete_selected(), width=130)
                        dpg.add_button(label="Clear All", callback=lambda: self.clear_objects(), width=130)
                    dpg.add_separator()

                    # Properties
                    dpg.add_text("=== Selected Object ===")
                    dpg.add_text("None", tag="selected_name")

                    dpg.add_text("Position:")
                    with dpg.group(horizontal=True):
                        dpg.add_input_float(tag="prop_pos_x", width=80, step=0.1,
                                           callback=lambda s,a: self.apply_position(), enabled=False)
                        dpg.add_input_float(tag="prop_pos_y", width=80, step=0.1,
                                           callback=lambda s,a: self.apply_position(), enabled=False)
                        dpg.add_input_float(tag="prop_pos_z", width=80, step=0.1,
                                           callback=lambda s,a: self.apply_position(), enabled=False)

                    dpg.add_text("Color:")
                    dpg.add_color_edit(tag="prop_color", no_alpha=True, width=-1,
                                      callback=self.apply_color, enabled=False)

                    dpg.add_checkbox(label="Shadow Cast", tag="prop_shadow_cast",
                                    callback=self.apply_shadow_cast, enabled=False)
                    dpg.add_checkbox(label="Shadow Receive", tag="prop_shadow_receive",
                                    callback=self.apply_shadow_receive, enabled=False)
                    dpg.add_separator()

                    # Lighting
                    dpg.add_text("=== Main Light ===")
                    dpg.add_checkbox(label="Cast Shadow", default_value=True,
                                    callback=self.set_light_shadow)
                    dpg.add_slider_float(label="Intensity", default_value=3.0,
                                        min_value=0.1, max_value=20.0,
                                        callback=self.set_light_intensity)
                    dpg.add_separator()

                    # Rendering
                    dpg.add_text("=== Rendering ===")
                    dpg.add_checkbox(label="Enable DDGI", callback=self.toggle_ddgi)
                    dpg.add_button(label="Screenshot", callback=lambda: self.take_screenshot(), width=-1)
                    dpg.add_separator()

                    # Info
                    dpg.add_text("=== Controls ===")
                    dpg.add_text("RMB/MMB: Orbit", color=[150, 150, 150])
                    dpg.add_text("Shift+MMB: Pan", color=[150, 150, 150])
                    dpg.add_text("Scroll: Zoom", color=[150, 150, 150])
                    dpg.add_separator()
                    dpg.add_text("FPS: 0", tag="fps_text")

                # Right panel - Render view
                with dpg.child_window(tag="render_panel", width=-1, height=-1):
                    pass  # Image will be added here

        dpg.create_viewport(title="VizMotive Test Viewer", width=1300, height=850)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

    def update_render(self):
        """Update rendering - direct buffer, no PNG"""
        if not self.engine_initialized:
            return

        try:
            if not self.canvas_initialized:
                self.renderer.resize_canvas(self.render_width, self.render_height, self.camera.get_vid())
                self.canvas_initialized = True

            # Render
            self.renderer.render(self.scene.get_vid(), self.camera.get_vid())

            # Get render buffer directly
            buffer_data, w, h = self.renderer.store_render_target()

            # Use known dimensions if returned ones are invalid
            width = w if w > 0 else self.render_width
            height = h if h > 0 else self.render_height

            # Convert bytes to numpy array
            expected_size = width * height * 4
            actual_size = len(buffer_data)

            if actual_size != expected_size:
                # Try to calculate dimensions from buffer size
                total_pixels = actual_size // 4
                # Assume aspect ratio matches our render settings
                aspect = self.render_width / self.render_height
                height = int(math.sqrt(total_pixels / aspect))
                width = total_pixels // height

            # Decode R11G11B10_FLOAT format to RGBA8
            img_array = decode_r11g11b10_float(buffer_data, width, height)

            img_data = img_array.astype(np.float32) / 255.0
            img_data = img_data.flatten()

            if self.texture_tag is None:
                with dpg.texture_registry():
                    self.texture_tag = dpg.add_raw_texture(
                        width=width, height=height,
                        default_value=img_data,
                        format=dpg.mvFormat_Float_rgba
                    )
                self.image_tag = dpg.add_image(self.texture_tag, parent="render_panel", tag="render_image")
            else:
                dpg.set_value(self.texture_tag, img_data)

            # FPS counter
            self.frame_count += 1
            current_time = time.time()
            elapsed = current_time - self.last_fps_time
            if elapsed >= 1.0:
                self.current_fps = self.frame_count / elapsed
                self.frame_count = 0
                self.last_fps_time = current_time
                dpg.set_value("fps_text", f"FPS: {self.current_fps:.1f}")

        except Exception as e:
            print(f"Render error: {e}")
            import traceback
            traceback.print_exc()

    def run(self):
        """Main loop"""
        self.create_gui()
        self.update_object_list()

        while dpg.is_dearpygui_running():
            self.handle_mouse()
            self.update_render()
            dpg.render_dearpygui_frame()

        if self.engine_initialized:
            vzm.deinit_engine()
        dpg.destroy_context()


if __name__ == "__main__":
    print("=" * 50)
    print("VizMotive Test Viewer")
    print("  RMB/MMB: Orbit camera")
    print("  Shift+MMB: Pan camera")
    print("  Scroll: Zoom")
    print("=" * 50)

    viewer = TestViewer()
    if viewer.init_engine():
        viewer.run()
    else:
        print("Failed to initialize engine!")
