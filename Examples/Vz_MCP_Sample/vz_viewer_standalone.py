"""
VizMotive Standalone Viewer
===========================
MCP 서버와 파일 기반 통신으로 연동되는 GUI 뷰어

Features:
- vz_core 모듈 사용 (최적화된 렌더링)
- 전체 GUI (오브젝트 생성/편집, DDGI 등)
- scene_commands.json에서 명령 읽기
- scene_responses.json으로 응답 전송
"""
import os
import json
import time
from pathlib import Path

# vz_core 모듈 사용
from vz_core import vzm, init_engine, deinit_engine
from vz_core.camera import OrbitCamera
from vz_core.gui import RenderView, ObjectPanel, PropertyPanel, ControlPanel, MouseHandler

import dearpygui.dearpygui as dpg

# 통신용 파일 경로
SCRIPT_DIR = Path(__file__).parent
COMMAND_FILE = SCRIPT_DIR / "scene_commands.json"
RESPONSE_FILE = SCRIPT_DIR / "scene_responses.json"


class StandaloneViewer:
    """
    MCP 서버와 파일 기반 통신으로 연동되는 GUI 뷰어
    """

    def __init__(self):
        self.engine_initialized = False
        self.scene = None
        self.camera = None
        self.renderer = None

        # GUI Components
        self.orbit_cam = OrbitCamera()
        self.render_view = None
        self.object_panel = None
        self.property_panel = None
        self.control_panel = None
        self.mouse_handler = None

        # MCP command processing
        self.processed_commands = []
        self.responses = []
        self.mcp_object_counter = 0

    def init_engine(self) -> bool:
        """엔진 초기화"""
        # 이전 명령 파일 정리
        if COMMAND_FILE.exists():
            COMMAND_FILE.unlink()
        if RESPONSE_FILE.exists():
            RESPONSE_FILE.unlink()

        if not init_engine():
            return False

        self.engine_initialized = True

        # 씬, 카메라, 렌더러 생성
        self.scene = vzm.new_scene("main_scene")
        self.camera = vzm.new_camera("main_camera")
        self.renderer = vzm.new_renderer("main_renderer")

        # 카메라 설정
        self.orbit_cam.apply_to_camera(self.camera)
        self.camera.set_perspective_projection(0.01, 100.0, 45.0, 1.0)
        self.camera.set_visible_layer_mask(0xF)

        # 렌더러 설정
        self.renderer.set_canvas(800, 600, 96.0)
        self.renderer.set_clear_color([0.15, 0.15, 0.2, 1.0])

        print("Engine initialized!")
        return True

    def create_gui(self):
        """GUI 생성"""
        dpg.create_context()

        # 컴포넌트 초기화
        self.render_view = RenderView(parent="render_panel", width=800, height=600)
        self.object_panel = ObjectPanel(
            scene=self.scene,
            on_object_selected=self._on_object_selected
        )
        self.property_panel = PropertyPanel()
        self.control_panel = ControlPanel(
            scene=self.scene,
            renderer=self.renderer
        )
        self.mouse_handler = MouseHandler(
            orbit_camera=self.orbit_cam,
            renderer=self.renderer,
            scene=self.scene,
            camera=self.camera
        )
        self.mouse_handler.on_object_picked = self._on_object_picked
        self.mouse_handler.register_scroll_handler()

        # 메인 윈도우
        with dpg.window(label="VizMotive Standalone Viewer", tag="main_window", width=1280, height=800):
            with dpg.group(horizontal=True):
                # 좌측 패널 - 컨트롤
                with dpg.child_window(tag="control_panel", width=280, height=-1):
                    # MCP 상태 표시
                    dpg.add_text("=== MCP Status ===")
                    dpg.add_text("Waiting for commands...", tag="mcp_status", color=[200, 200, 100])
                    dpg.add_text("Commands: 0", tag="mcp_commands")
                    dpg.add_separator()

                    # 패널들을 순서대로 생성
                    self.object_panel.create(parent="control_panel")
                    self.property_panel.create(parent="control_panel")
                    self.control_panel.create(parent="control_panel")

                # 우측 패널 - 렌더 뷰
                with dpg.child_window(tag="render_panel", width=-1, height=-1):
                    pass

        # 리사이즈 핸들 오버레이
        with dpg.viewport_drawlist(front=True, tag="viewport_drawlist"):
            pass

        # Floor 생성
        self.object_panel.create_floor()

        dpg.create_viewport(title="VizMotive Standalone Viewer", width=1300, height=850)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

    def _on_object_selected(self, obj):
        """오브젝트 선택 콜백"""
        self.property_panel.update(obj)

    def _on_object_picked(self, vid):
        """피킹으로 오브젝트 선택"""
        if self.object_panel.select_object_by_vid(vid):
            self.property_panel.update(self.object_panel.get_selected())

    def write_response(self, cmd_id, success, **kwargs):
        """MCP 서버로 응답 전송"""
        response = {
            '_id': cmd_id,
            'success': success,
            **kwargs
        }
        self.responses.append(response)

        try:
            with open(RESPONSE_FILE, 'w') as f:
                json.dump(self.responses, f, indent=2)
        except Exception as e:
            print(f"Response write error: {e}")

    def process_mcp_commands(self):
        """파일에서 MCP 명령 읽기 및 처리"""
        if not COMMAND_FILE.exists():
            return

        try:
            with open(COMMAND_FILE, 'r') as f:
                commands = json.load(f)

            # 새로운 명령만 처리
            new_commands = commands[len(self.processed_commands):]

            for cmd in new_commands:
                cmd_id = cmd.get('_id', 'unknown')
                cmd_type = cmd.get('type')
                print(f"MCP Command: {cmd_type} (id: {cmd_id})")

                try:
                    self._execute_command(cmd_id, cmd)
                except Exception as e:
                    print(f"Command error: {e}")
                    self.write_response(cmd_id, False, error=str(e))

                self.processed_commands.append(cmd)

            # MCP 상태 업데이트
            if new_commands and dpg.does_item_exist("mcp_commands"):
                dpg.set_value("mcp_commands", f"Commands: {len(self.processed_commands)}")
                dpg.set_value("mcp_status", "Connected")
                dpg.configure_item("mcp_status", color=[100, 255, 100])

        except Exception as e:
            print(f"Command processing error: {e}")

    def _execute_command(self, cmd_id, cmd):
        """MCP 명령 실행"""
        cmd_type = cmd.get('type')

        if cmd_type == 'create_cube':
            self._create_cube(cmd_id, cmd)
        elif cmd_type == 'create_sphere':
            self._create_sphere(cmd_id, cmd)
        elif cmd_type == 'create_light':
            self._create_light(cmd_id, cmd)
        elif cmd_type == 'set_object_position':
            self._set_object_position(cmd_id, cmd)
        elif cmd_type == 'set_object_color':
            self._set_object_color(cmd_id, cmd)
        elif cmd_type == 'set_object_scale':
            self._set_object_scale(cmd_id, cmd)
        elif cmd_type == 'delete_object':
            self._delete_object(cmd_id, cmd)
        elif cmd_type == 'list_objects':
            self._list_objects(cmd_id)
        elif cmd_type == 'clear_scene':
            self._clear_scene(cmd_id)
        elif cmd_type == 'enable_ddgi':
            self._enable_ddgi(cmd_id, cmd)
        elif cmd_type == 'set_render_resolution':
            self._set_render_resolution(cmd_id, cmd)
        elif cmd_type == 'screenshot':
            self._take_screenshot(cmd_id, cmd)
        elif cmd_type == 'set_camera':
            self._set_camera(cmd_id, cmd)
        else:
            self.write_response(cmd_id, False, error=f"Unknown command: {cmd_type}")

    def _create_cube(self, cmd_id, cmd):
        """큐브 생성"""
        pos = cmd['position']
        size = cmd.get('size', 1.0)
        color = cmd.get('color', [1.0, 0.0, 0.0, 1.0])

        self.mcp_object_counter += 1
        name = f"mcp_cube_{self.mcp_object_counter}"

        geometry = vzm.new_geometry(f"{name}_geom")
        vzm.generate_box_geometry(geometry.get_vid(), size, size, size)
        geometry.update_bvh()

        material = vzm.new_material(f"{name}_mat")
        material.set_base_color(color)
        material.set_shadow_cast(True)
        material.set_shadow_receive(True)

        cube = vzm.new_actor_static_mesh(name, geometry.get_vid(), material.get_vid())
        cube.set_position(pos)
        cube.set_visible_layer_mask(0xF, True)
        self.scene.append_child(cube)

        # ObjectPanel에 등록
        obj_data = {
            'vid': cube.get_vid(),
            'name': name,
            'type': 'mcp_cube',
            'mat_vid': material.get_vid()
        }
        self.object_panel.created_objects.append(obj_data)
        self.object_panel._update_list()

        print(f"Created: {name} at {pos}")
        self.write_response(cmd_id, True, name=name)

    def _create_sphere(self, cmd_id, cmd):
        """구 생성"""
        pos = cmd['position']
        radius = cmd.get('radius', 0.5)
        color = cmd.get('color', [0.0, 1.0, 0.0, 1.0])

        self.mcp_object_counter += 1
        name = f"mcp_sphere_{self.mcp_object_counter}"

        geometry = vzm.new_geometry(f"{name}_geom")
        vzm.generate_icosahedron_geometry(geometry.get_vid(), radius, 3)
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
            'type': 'mcp_sphere',
            'mat_vid': material.get_vid()
        }
        self.object_panel.created_objects.append(obj_data)
        self.object_panel._update_list()

        print(f"Created: {name} at {pos}")
        self.write_response(cmd_id, True, name=name)

    def _create_light(self, cmd_id, cmd):
        """조명 생성"""
        pos = cmd['position']
        light_type = cmd.get('light_type', 'point')
        color = cmd.get('color', [1.0, 1.0, 1.0])
        intensity = cmd.get('intensity', 15.0)
        range_val = cmd.get('range', 15.0)

        self.mcp_object_counter += 1
        name = f"mcp_light_{self.mcp_object_counter}"

        light = vzm.new_light(name)
        if light_type == 'directional':
            light.set_light_type(vzm.LightType.DIRECTIONAL)
        else:
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
            'type': f'mcp_{light_type}_light',
            'is_light': True,
            'light_type': 'Directional' if light_type == 'directional' else 'Point',
            'color': color,
            'intensity': intensity,
            'range': range_val,
            'cast_shadow': True,
            'position': pos
        }
        self.object_panel.created_objects.append(obj_data)
        self.object_panel._update_list()

        print(f"Created: {name} at {pos}")
        self.write_response(cmd_id, True, name=name)

    def _set_object_position(self, cmd_id, cmd):
        """오브젝트 위치 변경"""
        name = cmd['name']
        position = cmd['position']

        for obj in self.object_panel.created_objects:
            if obj['name'] == name:
                component = vzm.get_component(obj['vid'])
                if component:
                    component.set_position(position)
                    if obj.get('is_light'):
                        obj['position'] = position
                    self.write_response(cmd_id, True, name=name, position=position)
                    return

        self.write_response(cmd_id, False, error=f"Object '{name}' not found")

    def _set_object_color(self, cmd_id, cmd):
        """오브젝트 색상 변경"""
        name = cmd['name']
        color = cmd['color']

        for obj in self.object_panel.created_objects:
            if obj['name'] == name and 'mat_vid' in obj:
                material = vzm.get_component(obj['mat_vid'])
                if material:
                    material.set_base_color(color)
                    self.write_response(cmd_id, True, name=name, color=color)
                    return

        self.write_response(cmd_id, False, error=f"Object '{name}' not found or has no material")

    def _set_object_scale(self, cmd_id, cmd):
        """오브젝트 스케일 변경"""
        name = cmd['name']
        scale = cmd['scale']

        for obj in self.object_panel.created_objects:
            if obj['name'] == name:
                component = vzm.get_component(obj['vid'])
                if component and hasattr(component, 'set_scale'):
                    component.set_scale(scale)
                    self.write_response(cmd_id, True, name=name, scale=scale)
                    return

        self.write_response(cmd_id, False, error=f"Object '{name}' not found")

    def _delete_object(self, cmd_id, cmd):
        """오브젝트 삭제"""
        name = cmd['name']

        for obj in self.object_panel.created_objects[:]:
            if obj['name'] == name:
                vzm.remove_component(obj['vid'], True)
                self.object_panel.created_objects.remove(obj)
                self.object_panel._update_list()
                self.write_response(cmd_id, True, name=name)
                return

        self.write_response(cmd_id, False, error=f"Object '{name}' not found")

    def _list_objects(self, cmd_id):
        """오브젝트 목록"""
        objects = [{'name': obj['name'], 'type': obj['type']}
                   for obj in self.object_panel.created_objects]
        self.write_response(cmd_id, True, objects=objects)

    def _clear_scene(self, cmd_id):
        """씬 클리어"""
        count = 0
        for obj in self.object_panel.created_objects[:]:
            if obj['name'] != 'floor':
                vzm.remove_component(obj['vid'], True)
                self.object_panel.created_objects.remove(obj)
                count += 1

        self.object_panel._update_list()
        self.mcp_object_counter = 0
        self.write_response(cmd_id, True, removed_count=count)

    def _enable_ddgi(self, cmd_id, cmd):
        """DDGI 설정"""
        enabled = cmd.get('enabled', False)
        grid = cmd.get('grid', [32, 8, 32])

        vzm.set_configure({'DDGI_ENABLED': enabled})
        if enabled and self.scene:
            self.scene.set_option_value_array('DDGI_GRID', [float(g) for g in grid])

        self.write_response(cmd_id, True, enabled=enabled)

    def _set_render_resolution(self, cmd_id, cmd):
        """렌더 해상도 설정"""
        width = cmd['width']
        height = cmd['height']

        self.render_view.resize(width, height)
        self.write_response(cmd_id, True, width=width, height=height)

    def _take_screenshot(self, cmd_id, cmd):
        """스크린샷 저장"""
        filename = cmd.get('filename', 'mcp_screenshots/screenshot.png')
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.renderer.store_render_target_to_file(filename)
        self.write_response(cmd_id, True, filepath=filename)

    def _set_camera(self, cmd_id, cmd):
        """카메라 설정"""
        pos = cmd['position']
        look_at = cmd.get('look_at', [0.0, 0.0, 0.0])

        # OrbitCamera 설정 업데이트
        import math
        dx = pos[0] - look_at[0]
        dy = pos[1] - look_at[1]
        dz = pos[2] - look_at[2]

        self.orbit_cam.distance = math.sqrt(dx*dx + dy*dy + dz*dz)
        self.orbit_cam.target = look_at
        self.orbit_cam.elevation = math.degrees(math.asin(dy / self.orbit_cam.distance))
        self.orbit_cam.azimuth = math.degrees(math.atan2(dx, dz))

        self.orbit_cam.apply_to_camera(self.camera)
        self.write_response(cmd_id, True, position=pos, look_at=look_at)

    def run(self):
        """메인 루프"""
        self.create_gui()

        while dpg.is_dearpygui_running():
            # MCP 명령 처리
            self.process_mcp_commands()

            # 리사이즈 처리
            is_resizing = self.render_view.handle_resize_drag()

            # 마우스 처리
            if not is_resizing:
                self.mouse_handler.update(check_hover_items=["render_panel", "render_image"])

            # 렌더링
            if self.engine_initialized:
                w, h = self.render_view.get_resolution()
                self.camera.set_perspective_projection(0.01, 100.0, 45.0, w / h)
                self.render_view.update(self.renderer, self.scene.get_vid(), self.camera.get_vid())

            # UI 업데이트
            self.render_view.draw_resize_handle()
            self.control_panel.update_fps(self.render_view.get_fps())
            w, h = self.render_view.get_resolution()
            self.control_panel.update_resolution(w, h, is_resizing)

            dpg.render_dearpygui_frame()

        # 정리
        if self.engine_initialized:
            deinit_engine()
        dpg.destroy_context()


if __name__ == "__main__":
    print("=" * 60)
    print("VizMotive Standalone Viewer")
    print("  - Full GUI with vz_core modules")
    print("  - Reads commands from scene_commands.json")
    print("  - Controlled via MCP server")
    print("=" * 60)

    viewer = StandaloneViewer()
    if viewer.init_engine():
        viewer.run()
    else:
        print("Failed to initialize engine!")
