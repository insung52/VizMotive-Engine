"""
VizMotive Viewer with MCP Server
================================
MCP 서버와 통합된 GUI 뷰어

Features:
- 전체 GUI (오브젝트 생성/편집, 속성 패널, DDGI 등)
- MCP를 통한 원격 오브젝트 생성
- 최적화된 RGBA8 렌더링
"""
import sys
import os
import threading
import queue
import time

# vz_core 모듈 사용
from vz_core import vzm, init_engine, deinit_engine
from vz_core.camera import OrbitCamera
from vz_core.gui import RenderView, ObjectPanel, PropertyPanel, ControlPanel, MouseHandler

import dearpygui.dearpygui as dpg
from fastmcp import FastMCP


# Global scene state (shared between viewer and MCP)
class SceneState:
    def __init__(self):
        self.viewer = None  # Will be set to MCPViewer instance
        self.command_queue = queue.Queue()  # Commands from MCP to viewer
        self.response_queue = queue.Queue()  # Responses from viewer to MCP
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
    """Get current scene information including list of objects"""
    with scene_state.lock:
        if scene_state.viewer and scene_state.viewer.engine_initialized:
            objects = []
            if scene_state.viewer.object_panel:
                for obj in scene_state.viewer.object_panel.get_objects():
                    objects.append({
                        'name': obj['name'],
                        'type': obj['type'],
                        'vid': obj['vid']
                    })
            return {
                "status": "ready",
                "scene": "main_scene",
                "engine": "initialized",
                "objects": objects
            }
        else:
            return {
                "status": "not_ready",
                "engine": "not_initialized"
            }


@mcp.tool()
def create_cube(x: float, y: float, z: float, size: float = 1.0,
                color_r: float = 1.0, color_g: float = 0.0, color_b: float = 0.0) -> str:
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
    cmd = {
        'type': 'create_cube',
        'position': [x, y, z],
        'size': size,
        'color': [color_r, color_g, color_b, 1.0]
    }
    scene_state.command_queue.put(cmd)
    return f"Cube created at position ({x}, {y}, {z}) with size {size} and color RGB({color_r}, {color_g}, {color_b})"


@mcp.tool()
def create_sphere(x: float, y: float, z: float, radius: float = 0.5,
                  color_r: float = 0.0, color_g: float = 1.0, color_b: float = 0.0) -> str:
    """
    Create a sphere in the scene

    Args:
        x: X position
        y: Y position
        z: Z position
        radius: Sphere radius (default 0.5)
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
    return f"Sphere created at position ({x}, {y}, {z}) with radius {radius} and color RGB({color_r}, {color_g}, {color_b})"


@mcp.tool()
def create_light(x: float, y: float, z: float, light_type: str = "point",
                 color_r: float = 1.0, color_g: float = 1.0, color_b: float = 1.0,
                 intensity: float = 15.0, range_val: float = 15.0) -> str:
    """
    Create a light in the scene

    Args:
        x: X position
        y: Y position
        z: Z position
        light_type: "point" or "directional"
        color_r: Red component (0.0-1.0)
        color_g: Green component (0.0-1.0)
        color_b: Blue component (0.0-1.0)
        intensity: Light intensity
        range_val: Light range (for point lights)

    Returns:
        Success message
    """
    cmd = {
        'type': 'create_light',
        'position': [x, y, z],
        'light_type': light_type,
        'color': [color_r, color_g, color_b],
        'intensity': intensity,
        'range': range_val
    }
    scene_state.command_queue.put(cmd)
    return f"{light_type.capitalize()} light created at ({x}, {y}, {z})"


@mcp.tool()
def set_ddgi(enabled: bool) -> str:
    """
    Enable or disable DDGI (Dynamic Diffuse Global Illumination)

    Args:
        enabled: True to enable, False to disable

    Returns:
        Status message
    """
    cmd = {
        'type': 'set_ddgi',
        'enabled': enabled
    }
    scene_state.command_queue.put(cmd)
    return f"DDGI {'enabled' if enabled else 'disabled'}"


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
    time.sleep(0.3)  # Wait for screenshot
    return f"Screenshot saved to: {filename}"


@mcp.tool()
def clear_scene() -> str:
    """
    Clear all objects from the scene (except floor)

    Returns:
        Status message
    """
    cmd = {'type': 'clear_scene'}
    scene_state.command_queue.put(cmd)
    return "Scene cleared"


class MCPViewer:
    """
    MCP 서버와 통합된 GUI 뷰어
    """

    def __init__(self):
        self.engine_initialized = False
        self.scene = None
        self.camera = None
        self.renderer = None

        # Components
        self.orbit_cam = OrbitCamera()
        self.render_view = None
        self.object_panel = None
        self.property_panel = None
        self.control_panel = None
        self.mouse_handler = None

        # MCP object counter
        self.mcp_object_counter = 0

    def init_engine(self) -> bool:
        """엔진 초기화"""
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
        with dpg.window(label="VizMotive MCP Viewer", tag="main_window", width=1280, height=800):
            with dpg.group(horizontal=True):
                # 좌측 패널 - 컨트롤
                with dpg.child_window(tag="control_panel", width=280, height=-1):
                    # MCP 상태 표시
                    dpg.add_text("=== MCP Server ===")
                    dpg.add_text("Status: Running", tag="mcp_status", color=[100, 255, 100])
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

        dpg.create_viewport(title="VizMotive MCP Viewer", width=1300, height=850)
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

    def process_mcp_commands(self):
        """MCP 명령 처리"""
        commands_processed = 0
        while not scene_state.command_queue.empty():
            try:
                cmd = scene_state.command_queue.get_nowait()
                self._execute_command(cmd)
                commands_processed += 1
            except queue.Empty:
                break

        # MCP 명령 카운터 업데이트
        if commands_processed > 0 and dpg.does_item_exist("mcp_commands"):
            self.mcp_object_counter += commands_processed
            dpg.set_value("mcp_commands", f"Commands: {self.mcp_object_counter}")

    def _execute_command(self, cmd):
        """MCP 명령 실행"""
        cmd_type = cmd.get('type')

        if cmd_type == 'create_cube':
            self._create_mcp_cube(cmd)
        elif cmd_type == 'create_sphere':
            self._create_mcp_sphere(cmd)
        elif cmd_type == 'create_light':
            self._create_mcp_light(cmd)
        elif cmd_type == 'set_ddgi':
            self._set_ddgi(cmd)
        elif cmd_type == 'screenshot':
            self._take_screenshot(cmd)
        elif cmd_type == 'clear_scene':
            self.object_panel.clear_objects()

    def _create_mcp_cube(self, cmd):
        """MCP로 큐브 생성"""
        pos = cmd['position']
        size = cmd.get('size', 1.0)
        color = cmd.get('color', [1.0, 0.0, 0.0, 1.0])

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

        print(f"MCP: Created {name} at {pos}")

    def _create_mcp_sphere(self, cmd):
        """MCP로 구 생성"""
        pos = cmd['position']
        radius = cmd.get('radius', 0.5)
        color = cmd.get('color', [0.0, 1.0, 0.0, 1.0])

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

        # ObjectPanel에 등록
        obj_data = {
            'vid': sphere.get_vid(),
            'name': name,
            'type': 'mcp_sphere',
            'mat_vid': material.get_vid()
        }
        self.object_panel.created_objects.append(obj_data)
        self.object_panel._update_list()

        print(f"MCP: Created {name} at {pos}")

    def _create_mcp_light(self, cmd):
        """MCP로 조명 생성"""
        pos = cmd['position']
        light_type = cmd.get('light_type', 'point')
        color = cmd.get('color', [1.0, 1.0, 1.0])
        intensity = cmd.get('intensity', 15.0)
        range_val = cmd.get('range', 15.0)

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

        # ObjectPanel에 등록
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

        print(f"MCP: Created {name} at {pos}")

    def _set_ddgi(self, cmd):
        """DDGI 설정"""
        enabled = cmd.get('enabled', False)
        vzm.set_configure({'DDGI_ENABLED': enabled})
        if enabled and self.scene:
            self.scene.set_option_value_array('DDGI_GRID', [32.0, 8.0, 32.0])
        print(f"MCP: DDGI {'enabled' if enabled else 'disabled'}")

    def _take_screenshot(self, cmd):
        """스크린샷 저장"""
        filename = cmd.get('filename', 'mcp_screenshots/screenshot.png')
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.renderer.store_render_target_to_file(filename)
        print(f"MCP: Screenshot saved to {filename}")

    def run(self):
        """메인 루프"""
        self.create_gui()

        while dpg.is_dearpygui_running():
            # MCP 명령 처리
            self.process_mcp_commands()

            # 리사이즈 처리
            is_resizing = self.render_view.handle_resize_drag()

            # 마우스 처리 (리사이즈 중이 아닐 때만)
            if not is_resizing:
                self.mouse_handler.update(check_hover_items=["render_panel", "render_image"])

            # 렌더링
            if self.engine_initialized:
                # 카메라 aspect ratio 업데이트
                w, h = self.render_view.get_resolution()
                self.camera.set_perspective_projection(0.01, 100.0, 45.0, w / h)

                # 렌더링 수행
                self.render_view.update(self.renderer, self.scene.get_vid(), self.camera.get_vid())

            # 리사이즈 핸들 그리기
            self.render_view.draw_resize_handle()

            # UI 업데이트
            self.control_panel.update_fps(self.render_view.get_fps())
            w, h = self.render_view.get_resolution()
            self.control_panel.update_resolution(w, h, is_resizing)

            dpg.render_dearpygui_frame()

        # 정리
        if self.engine_initialized:
            deinit_engine()
        dpg.destroy_context()


def run_mcp_server():
    """Run MCP server in a separate thread"""
    print("Starting MCP server...")
    mcp.run()


if __name__ == "__main__":
    print("=" * 60)
    print("VizMotive MCP Viewer")
    print("  - Full GUI with object creation and editing")
    print("  - MCP server for remote control")
    print("  - Connect via Claude Desktop or MCP client")
    print("=" * 60)

    # Create viewer
    viewer = MCPViewer()
    scene_state.viewer = viewer

    # Initialize engine
    if not viewer.init_engine():
        print("Failed to initialize engine!")
        sys.exit(1)

    # Start MCP server in a separate thread
    mcp_thread = threading.Thread(target=run_mcp_server, daemon=True)
    mcp_thread.start()

    # Run viewer (blocking)
    viewer.run()
