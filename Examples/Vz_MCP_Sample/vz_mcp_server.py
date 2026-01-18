"""
VizMotive MCP Server
====================
Claude Desktop용 MCP 서버 (headless)
뷰어는 start_viewer 명령으로 별도 실행

Features:
- 파일 기반 통신으로 뷰어와 연동
- stdout 오염 방지
- GUI 뷰어 원격 제어
"""
import sys
import os
import subprocess
import json
import time
import uuid
from pathlib import Path

# CRITICAL: stdout 오염 방지 - MCP는 JSON-RPC에 stdout 사용
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["FASTMCP_HIDE_BANNER"] = "1"

# 로그 파일로 stderr 리다이렉트
SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / "mcp_server.log"
log_file = open(LOG_FILE, "w", buffering=1, encoding='utf-8')
sys.stderr = log_file

from fastmcp import FastMCP

# MCP 서버 초기화
mcp = FastMCP("VizMotive Engine")

# 통신용 파일 경로
STATE_FILE = SCRIPT_DIR / "scene_commands.json"
RESPONSE_FILE = SCRIPT_DIR / "scene_responses.json"
RESPONSE_TIMEOUT = 5.0

viewer_process = None


def log(msg):
    """로그 파일에 기록"""
    print(f"[MCP] {msg}", file=log_file, flush=True)


def write_command_and_wait(cmd, wait_for_response=True):
    """명령을 파일에 쓰고 응답 대기"""
    cmd_id = str(uuid.uuid4())[:8]
    cmd['_id'] = cmd_id
    cmd['_timestamp'] = time.time()

    # 기존 명령 읽기
    commands = []
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                commands = json.load(f)
        except:
            commands = []

    commands.append(cmd)

    with open(STATE_FILE, 'w') as f:
        json.dump(commands, f, indent=2)

    log(f"Command: {cmd}")

    if not wait_for_response:
        return None

    # 응답 대기
    start_time = time.time()
    while time.time() - start_time < RESPONSE_TIMEOUT:
        if RESPONSE_FILE.exists():
            try:
                with open(RESPONSE_FILE, 'r') as f:
                    responses = json.load(f)

                for resp in responses:
                    if resp.get('_id') == cmd_id:
                        log(f"Response: {resp}")
                        return resp
            except:
                pass

        time.sleep(0.05)

    log(f"Timeout for {cmd_id}")
    return {'_id': cmd_id, 'success': False, 'error': 'Timeout - viewer may not be running'}


# ============ 기본 도구 ============

@mcp.tool()
def ping() -> str:
    """MCP 서버 연결 테스트"""
    return "pong from VizMotive MCP Server"


@mcp.tool()
def start_viewer() -> str:
    """
    GUI 뷰어 시작

    Returns:
        뷰어 시작 상태
    """
    global viewer_process

    if viewer_process and viewer_process.poll() is None:
        return "Viewer is already running"

    viewer_path = SCRIPT_DIR / "vz_viewer_standalone.py"

    viewer_process = subprocess.Popen(
        ["python", str(viewer_path)],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    log(f"Viewer started: PID {viewer_process.pid}")
    return f"Viewer started (PID: {viewer_process.pid})"


@mcp.tool()
def get_viewer_status() -> dict:
    """뷰어 실행 상태 확인"""
    global viewer_process

    if viewer_process is None:
        return {"status": "not_started", "message": "Use start_viewer() to launch the GUI"}

    if viewer_process.poll() is None:
        return {"status": "running", "pid": viewer_process.pid}
    else:
        return {"status": "stopped", "exit_code": viewer_process.returncode}


# ============ 오브젝트 생성 ============

@mcp.tool()
def create_cube(x: float, y: float, z: float, size: float = 1.0,
                color_r: float = 1.0, color_g: float = 0.0, color_b: float = 0.0) -> str:
    """
    큐브 생성

    Args:
        x, y, z: 위치
        size: 크기 (기본 1.0)
        color_r, color_g, color_b: RGB 색상 (0.0-1.0)
    """
    cmd = {
        'type': 'create_cube',
        'position': [x, y, z],
        'size': size,
        'color': [color_r, color_g, color_b, 1.0]
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"Cube '{resp.get('name')}' created at ({x}, {y}, {z})"
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return f"Cube requested at ({x}, {y}, {z})"


@mcp.tool()
def create_sphere(x: float, y: float, z: float, radius: float = 0.5,
                  color_r: float = 0.0, color_g: float = 1.0, color_b: float = 0.0) -> str:
    """
    구 생성

    Args:
        x, y, z: 위치
        radius: 반지름 (기본 0.5)
        color_r, color_g, color_b: RGB 색상 (0.0-1.0)
    """
    cmd = {
        'type': 'create_sphere',
        'position': [x, y, z],
        'radius': radius,
        'color': [color_r, color_g, color_b, 1.0]
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"Sphere '{resp.get('name')}' created at ({x}, {y}, {z})"
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return f"Sphere requested at ({x}, {y}, {z})"


@mcp.tool()
def create_light(x: float, y: float, z: float, light_type: str = "point",
                 color_r: float = 1.0, color_g: float = 1.0, color_b: float = 1.0,
                 intensity: float = 15.0, range_val: float = 15.0) -> str:
    """
    조명 생성

    Args:
        x, y, z: 위치
        light_type: "point" 또는 "directional"
        color_r, color_g, color_b: RGB 색상
        intensity: 밝기
        range_val: 범위 (point light용)
    """
    cmd = {
        'type': 'create_light',
        'position': [x, y, z],
        'light_type': light_type,
        'color': [color_r, color_g, color_b],
        'intensity': intensity,
        'range': range_val
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"{light_type.capitalize()} light created at ({x}, {y}, {z})"
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return f"Light requested"


# ============ 오브젝트 조작 ============

@mcp.tool()
def set_object_position(name: str, x: float, y: float, z: float) -> str:
    """오브젝트 위치 변경"""
    cmd = {
        'type': 'set_object_position',
        'name': name,
        'position': [x, y, z]
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"Object '{name}' moved to ({x}, {y}, {z})"
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return f"Move requested"


@mcp.tool()
def set_object_color(name: str, r: float, g: float, b: float) -> str:
    """오브젝트 색상 변경"""
    cmd = {
        'type': 'set_object_color',
        'name': name,
        'color': [r, g, b, 1.0]
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"Object '{name}' color set to RGB({r}, {g}, {b})"
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return f"Color change requested"


@mcp.tool()
def set_object_scale(name: str, sx: float, sy: float, sz: float) -> str:
    """오브젝트 스케일 변경"""
    cmd = {
        'type': 'set_object_scale',
        'name': name,
        'scale': [sx, sy, sz]
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"Object '{name}' scaled to ({sx}, {sy}, {sz})"
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return f"Scale requested"


@mcp.tool()
def set_object_rotation(name: str, pitch: float = 0.0, yaw: float = 0.0, roll: float = 0.0) -> str:
    """
    Rotate an object using Euler angles in degrees.

    Args:
        name: Object name (e.g., 'mcp_cube_1', 'mcp_sphere_2')
        pitch: X-axis rotation in degrees (tilts forward/backward)
        yaw: Y-axis rotation in degrees (turns left/right)
        roll: Z-axis rotation in degrees (tilts sideways)

    Example: set_object_rotation("mcp_cube_1", pitch=45, yaw=30, roll=0)
    """
    cmd = {
        'type': 'set_object_rotation',
        'name': name,
        'rotation': [roll, pitch, yaw]  # Internal order: roll, pitch, yaw
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"Object '{name}' rotated: pitch={pitch}deg, yaw={yaw}deg, roll={roll}deg"
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return f"Rotation requested"


@mcp.tool()
def delete_object(name: str) -> str:
    """오브젝트 삭제"""
    cmd = {
        'type': 'delete_object',
        'name': name
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"Object '{name}' deleted"
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return f"Delete requested"


# ============ 씬 관리 ============

@mcp.tool()
def list_objects() -> str:
    """씬의 모든 오브젝트 목록"""
    cmd = {'type': 'list_objects'}
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        objects = resp.get('objects', [])
        if not objects:
            return "Scene is empty"

        lines = ["Objects in scene:"]
        for obj in objects:
            lines.append(f"  - {obj['name']} ({obj['type']})")
        return "\n".join(lines)
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return "Request timed out"


@mcp.tool()
def clear_scene(include_floor: bool = True) -> str:
    """
    씬의 모든 오브젝트 삭제

    Args:
        include_floor: True면 floor도 삭제 (기본값: True)
    """
    cmd = {'type': 'clear_scene', 'include_floor': include_floor}
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"Scene cleared. Removed {resp.get('removed_count', 0)} objects."
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return "Clear requested"


# ============ 렌더링 설정 ============

@mcp.tool()
def enable_ddgi(enabled: bool, grid_x: int = 32, grid_y: int = 8, grid_z: int = 32) -> str:
    """
    DDGI (Dynamic Diffuse Global Illumination) 활성화/비활성화

    Args:
        enabled: True=켜기, False=끄기
        grid_x, grid_y, grid_z: DDGI 그리드 해상도
    """
    cmd = {
        'type': 'enable_ddgi',
        'enabled': enabled,
        'grid': [grid_x, grid_y, grid_z]
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"DDGI {'enabled' if enabled else 'disabled'}"
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return "DDGI setting requested"


@mcp.tool()
def set_render_resolution(width: int, height: int) -> str:
    """렌더 해상도 설정"""
    cmd = {
        'type': 'set_render_resolution',
        'width': width,
        'height': height
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"Resolution set to {width}x{height}"
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return "Resolution change requested"


@mcp.tool()
def render_screenshot(filename: str = None) -> str:
    """스크린샷 저장"""
    import datetime

    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"

    # 절대 경로로 변환
    screenshots_dir = SCRIPT_DIR / "mcp_screenshots"
    filepath = str(screenshots_dir / filename)

    cmd = {
        'type': 'screenshot',
        'filename': filepath
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"Screenshot saved: {resp.get('filepath', filepath)}"
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return f"Screenshot requested: {filepath}"


# ============ 카메라 ============

@mcp.tool()
def set_camera_position(x: float, y: float, z: float,
                        look_at_x: float = 0.0, look_at_y: float = 0.0, look_at_z: float = 0.0) -> str:
    """카메라 위치 및 타겟 설정"""
    cmd = {
        'type': 'set_camera',
        'position': [x, y, z],
        'look_at': [look_at_x, look_at_y, look_at_z]
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"Camera set to ({x}, {y}, {z}) looking at ({look_at_x}, {look_at_y}, {look_at_z})"
    elif resp and resp.get('error'):
        return f"Failed: {resp.get('error')}"
    return "Camera move requested"


if __name__ == "__main__":
    log("Starting VizMotive MCP Server...")
    mcp.run()
