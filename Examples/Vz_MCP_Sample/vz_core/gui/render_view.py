"""
Render View Component
=====================
렌더링 결과를 DearPyGui 텍스처로 표시하는 컴포넌트
"""
import time
import dearpygui.dearpygui as dpg
from ..render_utils import rgba8_to_float


class RenderView:
    """
    렌더링 결과를 표시하는 뷰 컴포넌트

    Features:
    - 텍스처 자동 생성/갱신
    - 해상도 조절 (드래그 리사이즈)
    - FPS 카운터

    Usage:
        render_view = RenderView(parent="render_panel")
        render_view.update(renderer, scene_vid, camera_vid)
    """

    def __init__(self, parent: str = None, width: int = 800, height: int = 600):
        self.parent = parent
        self.render_width = width
        self.render_height = height
        self.min_render_size = 200
        self.max_render_size = 1920

        # Texture state
        self.texture_tag = None
        self.image_tag = None
        self.texture_size = [0, 0]

        # Resize state
        self.resizing = False
        self.resize_start_pos = [0, 0]
        self.resize_start_size = [width, height]

        # FPS tracking
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0.0

        # Canvas state
        self.canvas_initialized = False

    def update(self, renderer, scene_vid: int, camera_vid: int) -> bool:
        """
        렌더링 수행 및 텍스처 업데이트

        Args:
            renderer: VzRenderer instance
            scene_vid: Scene VID
            camera_vid: Camera VID

        Returns:
            성공 여부
        """
        try:
            # Canvas 초기화 (해상도 변경 시)
            if not self.canvas_initialized:
                renderer.resize_canvas(self.render_width, self.render_height, camera_vid)
                self.canvas_initialized = True

            # 렌더링
            renderer.render(scene_vid, camera_vid)

            # 버퍼 가져오기
            buffer_data, w, h = renderer.store_render_target_rgba8()
            width = w if w > 0 else self.render_width
            height = h if h > 0 else self.render_height

            # Float 변환
            img_data = rgba8_to_float(buffer_data, width, height)

            # 텍스처 생성/업데이트
            need_recreate = (self.texture_tag is None or
                            self.texture_size[0] != width or
                            self.texture_size[1] != height)

            if need_recreate:
                self._recreate_texture(img_data, width, height)
            else:
                dpg.set_value(self.texture_tag, img_data)

            # FPS 계산
            self._update_fps()

            return True

        except Exception as e:
            print(f"Render error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _recreate_texture(self, img_data, width: int, height: int):
        """텍스처 재생성"""
        # 기존 텍스처 삭제
        if self.texture_tag is not None:
            if self.image_tag and dpg.does_item_exist(self.image_tag):
                dpg.delete_item(self.image_tag)
            if dpg.does_item_exist(self.texture_tag):
                dpg.delete_item(self.texture_tag)
            self.texture_tag = None
            self.image_tag = None

        # 새 텍스처 생성
        with dpg.texture_registry():
            self.texture_tag = dpg.add_raw_texture(
                width=width, height=height,
                default_value=img_data,
                format=dpg.mvFormat_Float_rgba
            )

        if self.parent:
            self.image_tag = dpg.add_image(self.texture_tag, parent=self.parent, tag="render_image")
        self.texture_size = [width, height]

    def _update_fps(self):
        """FPS 업데이트"""
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_fps_time
        if elapsed >= 1.0:
            self.current_fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_time = current_time

    def resize(self, width: int, height: int):
        """해상도 변경"""
        width = max(self.min_render_size, min(self.max_render_size, width))
        height = max(self.min_render_size, min(self.max_render_size, height))

        if width != self.render_width or height != self.render_height:
            self.render_width = width
            self.render_height = height
            self.canvas_initialized = False

    def is_over_resize_handle(self, mouse_x: float, mouse_y: float) -> bool:
        """리사이즈 핸들 위에 마우스가 있는지 확인"""
        if not dpg.does_item_exist("render_image"):
            return False

        img_pos = dpg.get_item_rect_min("render_image")
        handle_size = 20
        handle_x = img_pos[0] + self.render_width - handle_size
        handle_y = img_pos[1] + self.render_height - handle_size

        return (mouse_x >= handle_x and mouse_x <= img_pos[0] + self.render_width and
                mouse_y >= handle_y and mouse_y <= img_pos[1] + self.render_height)

    def handle_resize_drag(self) -> bool:
        """
        리사이즈 드래그 처리

        Returns:
            리사이즈 중이면 True
        """
        mouse_pos = dpg.get_mouse_pos(local=False)

        if dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
            if not self.resizing:
                if self.is_over_resize_handle(mouse_pos[0], mouse_pos[1]):
                    self.resizing = True
                    self.resize_start_pos = mouse_pos
                    self.resize_start_size = [self.render_width, self.render_height]
            # 리사이즈 중일 때는 아무것도 하지 않음 (미리보기만)
        else:
            if self.resizing:
                # 마우스 릴리즈 - 최종 크기 적용
                dx = mouse_pos[0] - self.resize_start_pos[0]
                dy = mouse_pos[1] - self.resize_start_pos[1]
                new_width = int(self.resize_start_size[0] + dx)
                new_height = int(self.resize_start_size[1] + dy)
                self.resize(new_width, new_height)
                self.resizing = False

        return self.resizing

    def draw_resize_handle(self):
        """리사이즈 핸들 그리기"""
        if not dpg.does_item_exist("render_image") or not dpg.does_item_exist("viewport_drawlist"):
            return

        img_pos = dpg.get_item_rect_min("render_image")
        handle_size = 20
        mouse_pos = dpg.get_mouse_pos(local=False)

        # 리사이즈 미리보기
        if self.resizing:
            dx = mouse_pos[0] - self.resize_start_pos[0]
            dy = mouse_pos[1] - self.resize_start_pos[1]
            preview_width = max(self.min_render_size, min(self.max_render_size, int(self.resize_start_size[0] + dx)))
            preview_height = max(self.min_render_size, min(self.max_render_size, int(self.resize_start_size[1] + dy)))
            x2 = img_pos[0] + preview_width
            y2 = img_pos[1] + preview_height
        else:
            x2 = img_pos[0] + self.render_width
            y2 = img_pos[1] + self.render_height

        is_hovered = self.is_over_resize_handle(mouse_pos[0], mouse_pos[1]) or self.resizing
        color = [255, 200, 100, 255] if is_hovered else [180, 180, 180, 200]

        # 기존 드로잉 삭제
        dpg.delete_item("viewport_drawlist", children_only=True)

        with dpg.draw_layer(parent="viewport_drawlist"):
            # 리사이즈 중 미리보기 사각형
            if self.resizing:
                dpg.draw_rectangle(
                    (img_pos[0], img_pos[1]), (x2, y2),
                    color=[255, 200, 100, 200], thickness=2
                )

            # 대각선 라인 (핸들 표시)
            for i in range(3):
                offset = 4 + i * 5
                dpg.draw_line(
                    (x2 - offset, y2 - 2), (x2 - 2, y2 - offset),
                    color=color, thickness=2
                )

            # 호버 시 삼각형
            if is_hovered:
                dpg.draw_triangle(
                    (x2 - handle_size, y2), (x2, y2 - handle_size), (x2, y2),
                    color=[255, 200, 100, 100], fill=[255, 200, 100, 50]
                )

    def get_resolution(self) -> tuple:
        """현재 해상도 반환"""
        return (self.render_width, self.render_height)

    def get_fps(self) -> float:
        """현재 FPS 반환"""
        return self.current_fps

    def cleanup(self):
        """리소스 정리"""
        if self.texture_tag and dpg.does_item_exist(self.texture_tag):
            dpg.delete_item(self.texture_tag)
        if self.image_tag and dpg.does_item_exist(self.image_tag):
            dpg.delete_item(self.image_tag)
