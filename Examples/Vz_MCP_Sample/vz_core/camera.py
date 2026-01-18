"""
Camera Controllers
==================
Blender 스타일 카메라 컨트롤러
"""
import math


class OrbitCamera:
    """
    Orbit camera controller (Blender-style)

    Spherical coordinate system:
    - target: 카메라가 바라보는 중심점
    - distance: target으로부터의 거리
    - azimuth: 수평 회전각 (degrees)
    - elevation: 수직 회전각 (degrees)

    Usage:
        cam = OrbitCamera()
        cam.orbit(dx, dy)  # 마우스 드래그로 회전
        cam.pan(dx, dy)    # Shift+드래그로 이동
        cam.zoom(delta)    # 스크롤로 줌
        pos = cam.get_position()  # 카메라 위치 계산
    """

    def __init__(self):
        self.target = [0.0, 0.0, 0.0]
        self.distance = 10.0
        self.azimuth = 45.0  # Horizontal angle (degrees)
        self.elevation = 30.0  # Vertical angle (degrees)

        self.min_distance = 1.0
        self.max_distance = 100.0
        self.min_elevation = -89.0
        self.max_elevation = 89.0

        # Sensitivity settings
        self.orbit_sensitivity = 0.5
        self.pan_sensitivity = 0.002
        self.zoom_sensitivity = 0.1

    def get_position(self) -> list:
        """Calculate camera position from spherical coordinates"""
        az_rad = math.radians(self.azimuth)
        el_rad = math.radians(self.elevation)

        x = self.target[0] + self.distance * math.cos(el_rad) * math.sin(az_rad)
        y = self.target[1] + self.distance * math.sin(el_rad)
        z = self.target[2] + self.distance * math.cos(el_rad) * math.cos(az_rad)

        return [x, y, z]

    def get_view_direction(self) -> list:
        """Get view direction (normalized)"""
        pos = self.get_position()
        dx = self.target[0] - pos[0]
        dy = self.target[1] - pos[1]
        dz = self.target[2] - pos[2]
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length > 0:
            return [dx/length, dy/length, dz/length]
        return [0.0, 0.0, -1.0]

    def orbit(self, dx: float, dy: float):
        """
        Orbit camera around target

        Args:
            dx: 수평 이동량 (pixels)
            dy: 수직 이동량 (pixels)
        """
        self.azimuth -= dx * self.orbit_sensitivity
        self.elevation += dy * self.orbit_sensitivity
        self.elevation = max(self.min_elevation, min(self.max_elevation, self.elevation))

    def pan(self, dx: float, dy: float):
        """
        Pan camera (move target)

        Args:
            dx: 수평 이동량 (pixels)
            dy: 수직 이동량 (pixels)
        """
        az_rad = math.radians(self.azimuth)

        # Right vector (horizontal plane)
        right_x = math.cos(az_rad)
        right_z = -math.sin(az_rad)

        # Move target
        pan_speed = self.distance * self.pan_sensitivity
        self.target[0] -= dx * right_x * pan_speed
        self.target[2] -= dx * right_z * pan_speed
        self.target[1] += dy * pan_speed

    def zoom(self, delta: float):
        """
        Zoom in/out

        Args:
            delta: 줌 양 (positive = zoom in, negative = zoom out)
        """
        self.distance *= (1.0 - delta * self.zoom_sensitivity)
        self.distance = max(self.min_distance, min(self.max_distance, self.distance))

    def set_target(self, x: float, y: float, z: float):
        """Set camera target position"""
        self.target = [x, y, z]

    def set_distance(self, distance: float):
        """Set distance from target"""
        self.distance = max(self.min_distance, min(self.max_distance, distance))

    def set_angles(self, azimuth: float, elevation: float):
        """Set orbit angles (degrees)"""
        self.azimuth = azimuth
        self.elevation = max(self.min_elevation, min(self.max_elevation, elevation))

    def apply_to_camera(self, camera):
        """
        Apply orbit camera state to VizMotive camera

        Args:
            camera: VzCamera instance
        """
        pos = self.get_position()
        view = self.get_view_direction()
        up = [0.0, 1.0, 0.0]
        camera.set_world_pose(pos, view, up)
