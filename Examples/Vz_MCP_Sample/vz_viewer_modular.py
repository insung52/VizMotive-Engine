"""
VizMotive Modular Viewer
========================
vz_core 모듈을 사용한 리팩토링된 뷰어 예제

이 파일은 vz_core 패키지를 활용하여 코드 중복 없이
깔끔하게 뷰어를 구현하는 방법을 보여줍니다.
"""
import dearpygui.dearpygui as dpg

# vz_core에서 필요한 것만 import
from vz_core import vzm, init_engine, deinit_engine
from vz_core.camera import OrbitCamera
from vz_core.gui import RenderView, ObjectPanel, PropertyPanel, ControlPanel, MouseHandler


class ModularViewer:
    """
    vz_core 모듈을 사용한 모듈화된 뷰어
    """

    def __init__(self):
        self.engine_initialized = False
        self.scene = None
        self.camera = None
        self.renderer = None

        # 컴포넌트들
        self.orbit_cam = OrbitCamera()
        self.render_view = None
        self.object_panel = None
        self.property_panel = None
        self.control_panel = None
        self.mouse_handler = None

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

        # 컴포넌트 초기화 (GUI 생성 전에 객체만 먼저 생성)
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
        with dpg.window(label="VizMotive Modular Viewer", tag="main_window", width=1280, height=800):
            with dpg.group(horizontal=True):
                # 좌측 패널 - 컨트롤
                with dpg.child_window(tag="control_panel", width=280, height=-1):
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

        dpg.create_viewport(title="VizMotive Modular Viewer", width=1300, height=850)
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

    def run(self):
        """메인 루프"""
        self.create_gui()

        while dpg.is_dearpygui_running():
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


if __name__ == "__main__":
    print("=" * 50)
    print("VizMotive Modular Viewer")
    print("  Using vz_core modules for clean code")
    print("=" * 50)

    viewer = ModularViewer()
    if viewer.init_engine():
        viewer.run()
    else:
        print("Failed to initialize engine!")
