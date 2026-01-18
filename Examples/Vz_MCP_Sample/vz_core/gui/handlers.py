"""
Input Handlers
==============
마우스/키보드 입력 핸들러
"""
import dearpygui.dearpygui as dpg
from ..camera import OrbitCamera
from .. import vzm


class MouseHandler:
    """
    마우스 입력 핸들러

    Features:
    - 좌클릭: 오브젝트 피킹
    - 우클릭/휠클릭 드래그: 카메라 회전
    - Shift+휠클릭 드래그: 카메라 이동
    - 휠 스크롤: 줌
    """

    def __init__(self, orbit_camera: OrbitCamera, renderer=None, scene=None, camera=None):
        self.orbit_cam = orbit_camera
        self.renderer = renderer
        self.scene = scene
        self.camera = camera

        self.mouse_down_middle = False
        self.mouse_down_right = False
        self.last_mouse_pos = [0, 0]

        self.on_object_picked = None  # callback(vid)
        self.on_camera_changed = None  # callback()

    def set_picking_context(self, renderer, scene, camera):
        """피킹에 필요한 컨텍스트 설정"""
        self.renderer = renderer
        self.scene = scene
        self.camera = camera

    def register_scroll_handler(self):
        """스크롤 핸들러 등록"""
        with dpg.handler_registry():
            dpg.add_mouse_wheel_handler(callback=self._on_scroll)

    def update(self, check_hover_items: list = None):
        """
        매 프레임 호출하여 마우스 입력 처리

        Args:
            check_hover_items: 호버 체크할 아이템 태그 목록 (예: ["render_panel", "render_image"])
        """
        # 호버 체크
        if check_hover_items:
            hovered = False
            for item in check_hover_items:
                if dpg.does_item_exist(item) and dpg.is_item_hovered(item):
                    hovered = True
                    break
            if not hovered:
                return

        mouse_pos = dpg.get_mouse_pos()
        mouse_pos_global = dpg.get_mouse_pos(local=False)

        # 좌클릭 - 피킹
        if dpg.is_mouse_button_clicked(dpg.mvMouseButton_Left):
            self._pick_object(mouse_pos_global[0], mouse_pos_global[1])

        # 휠클릭 - Orbit/Pan
        if dpg.is_mouse_button_down(dpg.mvMouseButton_Middle):
            if not self.mouse_down_middle:
                self.mouse_down_middle = True
                self.last_mouse_pos = mouse_pos
            else:
                dx = mouse_pos[0] - self.last_mouse_pos[0]
                dy = mouse_pos[1] - self.last_mouse_pos[1]

                if dpg.is_key_down(dpg.mvKey_LShift) or dpg.is_key_down(dpg.mvKey_RShift):
                    self.orbit_cam.pan(dx, dy)
                else:
                    self.orbit_cam.orbit(dx, dy)

                self._update_camera()
                self.last_mouse_pos = mouse_pos
        else:
            self.mouse_down_middle = False

        # 우클릭 - Orbit
        if dpg.is_mouse_button_down(dpg.mvMouseButton_Right):
            if not self.mouse_down_right:
                self.mouse_down_right = True
                self.last_mouse_pos = mouse_pos
            else:
                dx = mouse_pos[0] - self.last_mouse_pos[0]
                dy = mouse_pos[1] - self.last_mouse_pos[1]
                self.orbit_cam.orbit(dx, dy)
                self._update_camera()
                self.last_mouse_pos = mouse_pos
        else:
            self.mouse_down_right = False

    def _on_scroll(self, sender, app_data):
        """스크롤 콜백"""
        self.orbit_cam.zoom(app_data)
        self._update_camera()

    def _update_camera(self):
        """카메라 업데이트"""
        if self.camera:
            self.orbit_cam.apply_to_camera(self.camera)
        if self.on_camera_changed:
            self.on_camera_changed()

    def _pick_object(self, screen_x: float, screen_y: float):
        """오브젝트 피킹"""
        if not self.renderer or not self.scene or not self.camera:
            return

        if not dpg.does_item_exist("render_image"):
            return

        img_pos = dpg.get_item_rect_min("render_image")
        rel_x = screen_x - img_pos[0]
        rel_y = screen_y - img_pos[1]

        # 렌더 영역 내부인지 확인
        img_size = dpg.get_item_rect_size("render_image")
        if rel_x < 0 or rel_y < 0 or rel_x >= img_size[0] or rel_y >= img_size[1]:
            return

        try:
            filter_flags = int(vzm.ActorFilter.MESH_OPAQUE) | int(vzm.ActorFilter.MESH_TRANSPARENT)
            result = self.renderer.picking(
                self.scene.get_vid(),
                self.camera.get_vid(),
                [rel_x, rel_y],
                filter_flags,
                0.0
            )

            hit, world_pos, actor_vid, primitive_id, mask_value = result

            if hit and actor_vid != 0 and self.on_object_picked:
                self.on_object_picked(actor_vid)

        except Exception as e:
            print(f"Picking error: {e}")

    def apply_camera_to_engine(self):
        """현재 카메라 상태를 엔진에 적용"""
        if self.camera:
            self.orbit_cam.apply_to_camera(self.camera)
