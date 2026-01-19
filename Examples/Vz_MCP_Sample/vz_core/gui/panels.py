"""
GUI Panels
==========
DearPyGui 기반 GUI 패널 컴포넌트들
"""
import dearpygui.dearpygui as dpg
from .. import vzm


class ObjectPanel:
    """
    오브젝트 생성/관리 패널

    Features:
    - Cube, Sphere 생성 버튼
    - Point Light, Directional Light 생성 버튼
    - 오브젝트 목록
    - 삭제/전체삭제 버튼
    """

    def __init__(self, scene, on_object_created=None, on_object_selected=None, on_object_deleted=None):
        self.scene = scene
        self.on_object_created = on_object_created
        self.on_object_selected = on_object_selected
        self.on_object_deleted = on_object_deleted

        self.object_counter = 0
        self.created_objects = []
        self.selected_object = None

    def create(self, parent: str):
        """패널 UI 생성"""
        with dpg.group(parent=parent):
            # Object Creation
            dpg.add_text("=== Create ===")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Cube", callback=lambda: self.create_cube(), width=62)
                dpg.add_button(label="Sphere", callback=lambda: self.create_sphere(), width=62)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Point Light", callback=lambda: self.create_point_light(), width=90)
                dpg.add_button(label="Dir Light", callback=lambda: self.create_directional_light(), width=90)
            dpg.add_separator()

            # Object List
            dpg.add_text("=== Scene Objects ===")
            dpg.add_listbox([], tag="object_list", num_items=8, width=-1,
                           callback=self._on_listbox_selected)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Delete", callback=lambda: self.delete_selected(), width=130)
                dpg.add_button(label="Clear All", callback=lambda: self.clear_objects(), width=130)
            dpg.add_separator()

    def _on_listbox_selected(self, sender, app_data):
        """Listbox 선택 콜백"""
        self.select_object(app_data)
        if self.on_object_selected:
            self.on_object_selected(self.selected_object)

    def create_cube(self):
        """Cube 생성"""
        import random
        self.object_counter += 1
        name = f"cube_{self.object_counter}"
        pos = [random.uniform(-3, 3), random.uniform(0.5, 2), random.uniform(-3, 3)]
        color = [random.random(), random.random(), random.random(), 1.0]

        geometry = vzm.new_geometry(f"{name}_geom")
        vzm.generate_box_geometry(geometry.get_vid(), 1.0, 1.0, 1.0)
        geometry.update_bvh()

        material = vzm.new_material(f"{name}_mat")
        material.set_base_color(color)
        material.set_shadow_cast(True)
        material.set_shadow_receive(True)

        cube = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
        cube.set_position(pos)
        cube.set_visible_layer_mask(0xF, True)
        self.scene.append_child(cube)

        obj_data = {
            'vid': cube.get_vid(),
            'name': name,
            'type': 'cube',
            'mat_vid': material.get_vid()
        }
        self.created_objects.append(obj_data)
        self._update_list()
        self.select_object(name)

        if self.on_object_created:
            self.on_object_created(obj_data)

    def create_sphere(self):
        """Sphere 생성"""
        import random
        self.object_counter += 1
        name = f"sphere_{self.object_counter}"
        pos = [random.uniform(-3, 3), random.uniform(0.5, 2), random.uniform(-3, 3)]
        color = [random.random(), random.random(), random.random(), 1.0]

        geometry = vzm.new_geometry(f"{name}_geom")
        vzm.generate_icosahedron_geometry(geometry.get_vid(), 0.5, 3)
        geometry.update_bvh()

        material = vzm.new_material(f"{name}_mat")
        material.set_base_color(color)
        material.set_shadow_cast(True)
        material.set_shadow_receive(True)

        sphere = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
        sphere.set_position(pos)
        sphere.set_visible_layer_mask(0xF, True)
        self.scene.append_child(sphere)

        obj_data = {
            'vid': sphere.get_vid(),
            'name': name,
            'type': 'sphere',
            'mat_vid': material.get_vid()
        }
        self.created_objects.append(obj_data)
        self._update_list()
        self.select_object(name)

        if self.on_object_created:
            self.on_object_created(obj_data)

    def create_point_light(self):
        """Point Light 생성"""
        import random
        self.object_counter += 1
        name = f"point_light_{self.object_counter}"
        pos = [random.uniform(-3, 3), random.uniform(2, 5), random.uniform(-3, 3)]
        color = [1.0, 0.9, 0.8]
        intensity = 15.0
        range_val = 15.0

        light = vzm.new_light(name)
        light.set_light_type(vzm.LightType.POINT)
        light.set_position(pos)
        light.set_color(color)
        light.set_intensity(intensity)
        light.set_range(range_val)
        light.enable_cast_shadow(True)
        light.set_visible_layer_mask(0xF, True)
        self.scene.append_child(light)

        obj_data = {
            'vid': light.get_vid(),
            'name': name,
            'type': 'point_light',
            'is_light': True,
            'light_type': 'Point',
            'color': color,
            'intensity': intensity,
            'range': range_val,
            'cast_shadow': True,
            'position': pos
        }
        self.created_objects.append(obj_data)
        self._update_list()
        self.select_object(name)

        if self.on_object_created:
            self.on_object_created(obj_data)

    def create_directional_light(self):
        """Directional Light 생성"""
        self.object_counter += 1
        name = f"dir_light_{self.object_counter}"
        pos = [5.0, 10.0, 5.0]
        color = [1.0, 1.0, 0.95]
        intensity = 3.0
        direction_euler = [45.0, 45.0, 0.0]  # pitch=45, yaw=45 (햇빛처럼 비스듬히)

        light = vzm.new_light(name)
        light.set_light_type(vzm.LightType.DIRECTIONAL)
        light.set_position(pos)
        light.set_color(color)
        light.set_intensity(intensity)
        light.enable_cast_shadow(True)
        light.set_visible_layer_mask(0xF, True)
        # 방향 설정
        if hasattr(light, 'set_direction'):
            light.set_direction(direction_euler)
        self.scene.append_child(light)

        obj_data = {
            'vid': light.get_vid(),
            'name': name,
            'type': 'directional_light',
            'is_light': True,
            'light_type': 'Directional',
            'color': color,
            'intensity': intensity,
            'range': 15.0,
            'cast_shadow': True,
            'position': pos,
            'direction_euler': direction_euler
        }
        self.created_objects.append(obj_data)
        self._update_list()
        self.select_object(name)

        if self.on_object_created:
            self.on_object_created(obj_data)

    def create_floor(self):
        """Floor 생성 (초기화용)"""
        geometry = vzm.new_geometry("floor_geom")
        vzm.generate_box_geometry(geometry.get_vid(), 20.0, 0.1, 20.0)
        geometry.update_bvh()

        material = vzm.new_material("floor_mat")
        material.set_base_color([0.4, 0.4, 0.45, 1.0])
        material.set_shadow_cast(False)
        material.set_shadow_receive(True)

        floor = vzm.new_actor_static_mesh("floor", geometry.get_vid(), material.get_vid())
        floor.set_position([0.0, -0.5, 0.0])
        floor.set_visible_layer_mask(0xF, True)
        self.scene.append_child(floor)

        self.created_objects.append({
            'vid': floor.get_vid(),
            'name': 'floor',
            'type': 'floor',
            'mat_vid': material.get_vid()
        })
        self._update_list()

    def select_object(self, name: str):
        """이름으로 오브젝트 선택"""
        self.selected_object = None
        for obj in self.created_objects:
            if obj['name'] == name:
                self.selected_object = obj
                break

        if dpg.does_item_exist("object_list"):
            dpg.set_value("object_list", name)

        if self.on_object_selected:
            self.on_object_selected(self.selected_object)

    def select_object_by_vid(self, vid: int):
        """VID로 오브젝트 선택"""
        for obj in self.created_objects:
            if obj['vid'] == vid:
                self.select_object(obj['name'])
                return True
        return False

    def delete_selected(self):
        """선택된 오브젝트 삭제 (floor 포함)"""
        if self.selected_object is None:
            return

        vzm.remove_component(self.selected_object['vid'], True)
        deleted = self.selected_object
        self.created_objects.remove(self.selected_object)
        self.selected_object = None
        self._update_list()

        if self.on_object_deleted:
            self.on_object_deleted(deleted)

    def clear_objects(self):
        """모든 오브젝트 삭제 (floor 포함)"""
        for obj in self.created_objects[:]:
            vzm.remove_component(obj['vid'], True)
            self.created_objects.remove(obj)
        self.object_counter = 0
        self.selected_object = None
        self._update_list()

    def _update_list(self):
        """Listbox 업데이트"""
        if dpg.does_item_exist("object_list"):
            names = [obj['name'] for obj in self.created_objects]
            dpg.configure_item("object_list", items=names)

    def get_objects(self) -> list:
        """모든 오브젝트 목록 반환"""
        return self.created_objects

    def get_selected(self):
        """선택된 오브젝트 반환"""
        return self.selected_object


class PropertyPanel:
    """
    선택된 오브젝트의 속성 편집 패널

    Features:
    - Position 편집
    - Material Color 편집 (메시)
    - Shadow Cast/Receive 토글 (메시)
    - Light Type/Color/Intensity/Range 편집 (조명)
    """

    def __init__(self, on_property_changed=None):
        self.on_property_changed = on_property_changed
        self.current_object = None

    def create(self, parent: str):
        """패널 UI 생성"""
        with dpg.group(parent=parent):
            dpg.add_text("=== Selected Object ===")
            dpg.add_text("None", tag="selected_name")

            dpg.add_text("Position:")
            with dpg.group(horizontal=True):
                dpg.add_input_float(tag="prop_pos_x", width=80, step=0.1,
                                   callback=lambda s,a: self._apply_position(), enabled=False)
                dpg.add_input_float(tag="prop_pos_y", width=80, step=0.1,
                                   callback=lambda s,a: self._apply_position(), enabled=False)
                dpg.add_input_float(tag="prop_pos_z", width=80, step=0.1,
                                   callback=lambda s,a: self._apply_position(), enabled=False)

            # Rotation (for meshes only, lights use direction)
            with dpg.group(tag="rotation_group", show=False):
                dpg.add_text("Rotation (degrees):")
                with dpg.group(horizontal=True):
                    dpg.add_input_float(tag="prop_rot_x", width=80, step=5.0, label="X",
                                       callback=lambda s,a: self._apply_rotation(), enabled=True)
                    dpg.add_input_float(tag="prop_rot_y", width=80, step=5.0, label="Y",
                                       callback=lambda s,a: self._apply_rotation(), enabled=True)
                    dpg.add_input_float(tag="prop_rot_z", width=80, step=5.0, label="Z",
                                       callback=lambda s,a: self._apply_rotation(), enabled=True)

            # Mesh properties
            with dpg.group(tag="mesh_props_group", show=False):
                dpg.add_text("--- Material ---", color=[150, 200, 150])
                dpg.add_color_edit(tag="prop_color", no_alpha=True, width=-1,
                                  callback=self._apply_color, label="Color")
                dpg.add_checkbox(label="Shadow Cast", tag="prop_shadow_cast",
                                callback=self._apply_shadow_cast)
                dpg.add_checkbox(label="Shadow Receive", tag="prop_shadow_receive",
                                callback=self._apply_shadow_receive)

            # Light properties
            with dpg.group(tag="light_props_group", show=False):
                dpg.add_text("--- Light ---", color=[200, 200, 150])
                dpg.add_combo(["Directional", "Point"], tag="prop_light_type",
                             callback=self._apply_light_type, label="Type", width=120)
                dpg.add_color_edit(tag="prop_light_color", no_alpha=True, width=-1,
                                  callback=self._apply_light_color, label="Color")
                dpg.add_slider_float(tag="prop_light_intensity", label="Intensity",
                                    min_value=0.1, max_value=50.0, default_value=3.0,
                                    callback=self._apply_light_intensity)
                dpg.add_slider_float(tag="prop_light_range", label="Range",
                                    min_value=1.0, max_value=100.0, default_value=15.0,
                                    callback=self._apply_light_range)
                dpg.add_checkbox(label="Cast Shadow", tag="prop_light_shadow",
                                callback=self._apply_light_shadow)

                # Directional light direction controls
                with dpg.group(tag="light_direction_group", show=False):
                    dpg.add_text("Direction (degrees):", color=[180, 180, 150])
                    with dpg.group(horizontal=True):
                        dpg.add_input_float(tag="prop_light_pitch", width=75, step=5.0, label="Pitch",
                                           callback=lambda s,a: self._apply_light_direction())
                        dpg.add_input_float(tag="prop_light_yaw", width=75, step=5.0, label="Yaw",
                                           callback=lambda s,a: self._apply_light_direction())
            dpg.add_separator()

    def update(self, obj):
        """선택된 오브젝트로 패널 업데이트"""
        self.current_object = obj

        dpg.configure_item("mesh_props_group", show=False)
        dpg.configure_item("light_props_group", show=False)
        dpg.configure_item("rotation_group", show=False)

        if obj is None:
            dpg.set_value("selected_name", "None")
            dpg.configure_item("prop_pos_x", enabled=False)
            dpg.configure_item("prop_pos_y", enabled=False)
            dpg.configure_item("prop_pos_z", enabled=False)
            return

        is_light = obj.get('is_light', False)
        dpg.set_value("selected_name", f"{obj['name']} ({obj['type']})")

        # Position
        if is_light and 'position' in obj:
            pos = obj['position']
        else:
            component = vzm.get_component(obj['vid'])
            pos = component.get_position() if component else [0, 0, 0]

        dpg.set_value("prop_pos_x", pos[0])
        dpg.set_value("prop_pos_y", pos[1])
        dpg.set_value("prop_pos_z", pos[2])
        dpg.configure_item("prop_pos_x", enabled=True)
        dpg.configure_item("prop_pos_y", enabled=True)
        dpg.configure_item("prop_pos_z", enabled=True)

        if is_light:
            dpg.configure_item("light_props_group", show=True)
            light_type = obj.get('light_type', 'Point')
            dpg.set_value("prop_light_type", light_type)
            color = obj.get('color', [1.0, 1.0, 1.0])
            dpg.set_value("prop_light_color", [int(c*255) for c in color] + [255])
            dpg.set_value("prop_light_intensity", obj.get('intensity', 3.0))
            dpg.set_value("prop_light_range", obj.get('range', 15.0))
            dpg.configure_item("prop_light_range", enabled=(light_type == 'Point'))
            dpg.set_value("prop_light_shadow", obj.get('cast_shadow', True))

            # Show direction controls only for directional lights
            is_directional = (light_type == 'Directional')
            dpg.configure_item("light_direction_group", show=is_directional)
            if is_directional:
                direction = obj.get('direction_euler', [45.0, 45.0, 0.0])  # default: pitch=45, yaw=45
                dpg.set_value("prop_light_pitch", direction[0])
                dpg.set_value("prop_light_yaw", direction[1])
        elif 'mat_vid' in obj:
            dpg.configure_item("mesh_props_group", show=True)
            dpg.configure_item("rotation_group", show=True)

            # Set rotation values
            rot = obj.get('rotation_euler', [0.0, 0.0, 0.0])
            dpg.set_value("prop_rot_x", rot[0])
            dpg.set_value("prop_rot_y", rot[1])
            dpg.set_value("prop_rot_z", rot[2])

            mat = vzm.get_component(obj['mat_vid'])
            if mat:
                color = mat.get_base_color()
                dpg.set_value("prop_color", [int(c*255) for c in color[:3]] + [255])
                dpg.set_value("prop_shadow_cast", mat.is_shadow_cast())
                dpg.set_value("prop_shadow_receive", mat.is_shadow_receive())

    def _apply_position(self):
        if not self.current_object:
            return
        pos = [dpg.get_value("prop_pos_x"), dpg.get_value("prop_pos_y"), dpg.get_value("prop_pos_z")]
        component = vzm.get_component(self.current_object['vid'])
        if component:
            component.set_position(pos)
            if self.current_object.get('is_light'):
                self.current_object['position'] = pos

    def _apply_rotation(self):
        """회전 적용 (Euler angles in degrees)"""
        if not self.current_object or self.current_object.get('is_light'):
            return

        rot_x = dpg.get_value("prop_rot_x")  # pitch (X축)
        rot_y = dpg.get_value("prop_rot_y")  # yaw (Y축)
        rot_z = dpg.get_value("prop_rot_z")  # roll (Z축)

        # Store euler angles for later retrieval
        self.current_object['rotation_euler'] = [rot_x, rot_y, rot_z]

        # Engine expects [roll, pitch, yaw] in degrees
        component = vzm.get_component(self.current_object['vid'])
        if component and hasattr(component, 'set_rotation'):
            component.set_rotation([rot_z, rot_x, rot_y])  # roll, pitch, yaw

    def _apply_color(self, sender, app_data):
        if not self.current_object or 'mat_vid' not in self.current_object:
            return
        mat = vzm.get_component(self.current_object['mat_vid'])
        if mat:
            mat.set_base_color([app_data[0], app_data[1], app_data[2], 1.0])

    def _apply_shadow_cast(self, sender, value):
        if not self.current_object or 'mat_vid' not in self.current_object:
            return
        mat = vzm.get_component(self.current_object['mat_vid'])
        if mat:
            mat.set_shadow_cast(value)

    def _apply_shadow_receive(self, sender, value):
        if not self.current_object or 'mat_vid' not in self.current_object:
            return
        mat = vzm.get_component(self.current_object['mat_vid'])
        if mat:
            mat.set_shadow_receive(value)

    def _apply_light_type(self, sender, value):
        if not self.current_object or not self.current_object.get('is_light'):
            return
        light = vzm.get_component(self.current_object['vid'])
        if light:
            light_type = vzm.LightType.DIRECTIONAL if value == "Directional" else vzm.LightType.POINT
            light.set_light_type(light_type)
            self.current_object['light_type'] = value
            dpg.configure_item("prop_light_range", enabled=(value == "Point"))
            # Show/hide direction controls
            dpg.configure_item("light_direction_group", show=(value == "Directional"))

    def _apply_light_color(self, sender, app_data):
        if not self.current_object or not self.current_object.get('is_light'):
            return
        light = vzm.get_component(self.current_object['vid'])
        if light:
            color = [app_data[0], app_data[1], app_data[2]]
            light.set_color(color)
            self.current_object['color'] = color

    def _apply_light_intensity(self, sender, value):
        if not self.current_object or not self.current_object.get('is_light'):
            return
        light = vzm.get_component(self.current_object['vid'])
        if light:
            light.set_intensity(value)
            self.current_object['intensity'] = value

    def _apply_light_range(self, sender, value):
        if not self.current_object or not self.current_object.get('is_light'):
            return
        light = vzm.get_component(self.current_object['vid'])
        if light:
            light.set_range(value)
            self.current_object['range'] = value

    def _apply_light_shadow(self, sender, value):
        if not self.current_object or not self.current_object.get('is_light'):
            return
        light = vzm.get_component(self.current_object['vid'])
        if light:
            light.enable_cast_shadow(value)
            self.current_object['cast_shadow'] = value

    def _apply_light_direction(self):
        """Directional light 방향 적용"""
        if not self.current_object or not self.current_object.get('is_light'):
            return
        if self.current_object.get('light_type') != 'Directional':
            return

        pitch = dpg.get_value("prop_light_pitch")  # X축 회전 (상하)
        yaw = dpg.get_value("prop_light_yaw")      # Y축 회전 (좌우)

        # Store for later retrieval
        self.current_object['direction_euler'] = [pitch, yaw, 0.0]

        light = vzm.get_component(self.current_object['vid'])
        if light and hasattr(light, 'set_direction'):
            light.set_direction([pitch, yaw, 0.0])


class ControlPanel:
    """
    렌더링 컨트롤 및 정보 패널

    Features:
    - DDGI 토글
    - 스크린샷 버튼
    - FPS 표시
    - 해상도 표시
    - 조작법 안내
    """

    def __init__(self, scene=None, renderer=None, on_ddgi_toggled=None, on_screenshot=None):
        self.scene = scene
        self.renderer = renderer
        self.on_ddgi_toggled = on_ddgi_toggled
        self.on_screenshot = on_screenshot

    def create(self, parent: str):
        """패널 UI 생성"""
        with dpg.group(parent=parent):
            dpg.add_text("=== Rendering ===")
            dpg.add_checkbox(label="Enable DDGI", tag="ddgi_checkbox", callback=self._toggle_ddgi)
            dpg.add_button(label="Screenshot", callback=self._take_screenshot, width=-1)
            dpg.add_separator()

            dpg.add_text("=== Controls ===")
            dpg.add_text("LMB: Select object", color=[150, 150, 150])
            dpg.add_text("RMB/MMB: Orbit", color=[150, 150, 150])
            dpg.add_text("Shift+MMB: Pan", color=[150, 150, 150])
            dpg.add_text("Scroll: Zoom", color=[150, 150, 150])
            dpg.add_text("Drag corner: Resize", color=[150, 150, 150])
            dpg.add_separator()

            dpg.add_text("FPS: 0", tag="fps_text")
            dpg.add_text("Resolution: 800x600", tag="resolution_text")

    def _toggle_ddgi(self, sender, value):
        vzm.set_configure({'DDGI_ENABLED': value})
        if value and self.scene:
            self.scene.set_option_value_array('DDGI_GRID', [32.0, 8.0, 32.0])
        if self.on_ddgi_toggled:
            self.on_ddgi_toggled(value)

    def _take_screenshot(self):
        if self.on_screenshot:
            self.on_screenshot()
        elif self.renderer:
            import os
            import datetime
            os.makedirs("mcp_screenshots", exist_ok=True)
            filename = f"mcp_screenshots/screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.renderer.store_render_target_to_file(filename)
            print(f"Screenshot: {filename}")

    def update_fps(self, fps: float):
        """FPS 표시 업데이트"""
        if dpg.does_item_exist("fps_text"):
            dpg.set_value("fps_text", f"FPS: {fps:.1f}")

    def update_resolution(self, width: int, height: int, resizing: bool = False):
        """해상도 표시 업데이트"""
        if dpg.does_item_exist("resolution_text"):
            suffix = " (resizing...)" if resizing else ""
            dpg.set_value("resolution_text", f"Resolution: {width}x{height}{suffix}")
