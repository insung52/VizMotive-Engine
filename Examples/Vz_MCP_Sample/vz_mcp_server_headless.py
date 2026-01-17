"""
VizMotive MCP Server (Headless) - No GUI, controls external viewer
With bidirectional response mechanism
"""
import sys
import os
import subprocess
import json
import time
import uuid
from pathlib import Path

# CRITICAL: Set encoding BEFORE any other imports to prevent Unicode errors
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["FASTMCP_HIDE_BANNER"] = "1"

# Redirect stdout/stderr to suppress VizMotive engine logs
# MCP uses stdio for JSON-RPC, so engine logs must not pollute stdout
original_stdout = sys.stdout
original_stderr = sys.stderr

# Create log file for debugging
log_file = open("C:\\graphics\\vizmotive\\my\\VizMotive-Engine\\Examples\\Vz_MCP_Sample\\mcp_debug.log", "w", buffering=1, encoding='utf-8')
sys.stderr = log_file  # Redirect stderr to log file

# Import FastMCP after setting environment
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("VizMotive Engine")

# Shared state files for communication with viewer
SCRIPT_DIR = Path("C:\\graphics\\vizmotive\\my\\VizMotive-Engine\\Examples\\Vz_MCP_Sample")
STATE_FILE = SCRIPT_DIR / "scene_commands.json"
RESPONSE_FILE = SCRIPT_DIR / "scene_responses.json"
RESPONSE_TIMEOUT = 5.0  # seconds to wait for response

viewer_process = None

def write_command_and_wait(cmd, wait_for_response=True):
    """Write command to state file and optionally wait for response"""
    # Generate unique command ID
    cmd_id = str(uuid.uuid4())[:8]
    cmd['_id'] = cmd_id
    cmd['_timestamp'] = time.time()

    # Read existing commands
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

    print(f"[MCP] Command written: {cmd}", file=log_file)

    if not wait_for_response:
        return None

    # Wait for response
    start_time = time.time()
    while time.time() - start_time < RESPONSE_TIMEOUT:
        if RESPONSE_FILE.exists():
            try:
                with open(RESPONSE_FILE, 'r') as f:
                    responses = json.load(f)

                # Find response matching our command ID
                for resp in responses:
                    if resp.get('_id') == cmd_id:
                        print(f"[MCP] Response received: {resp}", file=log_file)
                        return resp
            except:
                pass

        time.sleep(0.05)  # 50ms polling interval

    print(f"[MCP] Timeout waiting for response to {cmd_id}", file=log_file)
    return {'_id': cmd_id, 'success': False, 'error': 'Timeout waiting for viewer response'}

@mcp.tool()
def ping() -> str:
    """Test tool to verify MCP server is working"""
    return "pong from VizMotive MCP (headless mode)"

@mcp.tool()
def start_viewer() -> str:
    """Start the VizMotive viewer GUI"""
    global viewer_process

    if viewer_process and viewer_process.poll() is None:
        return "Viewer is already running"

    viewer_path = "C:\\graphics\\vizmotive\\my\\VizMotive-Engine\\Examples\\Vz_MCP_Sample\\vz_viewer_standalone.py"

    # Start viewer as separate process
    viewer_process = subprocess.Popen(
        ["python", viewer_path],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    return f"Viewer started (PID: {viewer_process.pid})"

@mcp.tool()
def get_viewer_status() -> dict:
    """Check if viewer is running"""
    global viewer_process

    if viewer_process is None:
        return {"status": "not_started", "message": "Viewer has not been started yet"}

    if viewer_process.poll() is None:
        return {"status": "running", "pid": viewer_process.pid}
    else:
        return {"status": "stopped", "exit_code": viewer_process.returncode}

@mcp.tool()
def create_cube(x: float, y: float, z: float, size: float = 1.0, color_r: float = 1.0, color_g: float = 0.0, color_b: float = 0.0) -> str:
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
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Cube '{resp.get('name')}' created at ({x}, {y}, {z})"
    elif resp and resp.get('error'):
        return f"✗ Failed to create cube: {resp.get('error')}"
    else:
        return f"Cube creation requested at ({x}, {y}, {z}) - awaiting viewer confirmation"

@mcp.tool()
def create_sphere(x: float, y: float, z: float, radius: float = 1.0, color_r: float = 0.0, color_g: float = 1.0, color_b: float = 0.0) -> str:
    """
    Create a sphere in the scene

    Args:
        x: X position
        y: Y position
        z: Z position
        radius: Sphere radius (default 1.0)
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
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Sphere '{resp.get('name')}' created at ({x}, {y}, {z})"
    elif resp and resp.get('error'):
        return f"✗ Failed to create sphere: {resp.get('error')}"
    else:
        return f"Sphere creation requested at ({x}, {y}, {z}) - awaiting viewer confirmation"

@mcp.tool()
def render_screenshot(filename: str = None) -> str:
    """
    Render and save a screenshot

    Args:
        filename: Optional custom filename (without path)

    Returns:
        Path to the saved screenshot
    """
    import datetime

    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"

    filepath = f"mcp_screenshots/{filename}"

    cmd = {
        'type': 'screenshot',
        'filename': filepath
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Screenshot saved to: {resp.get('filepath', filepath)}"
    elif resp and resp.get('error'):
        return f"✗ Screenshot failed: {resp.get('error')}"
    else:
        return f"Screenshot requested: {filepath}"

@mcp.tool()
def clear_scene() -> str:
    """Clear all objects from the scene"""
    cmd = {'type': 'clear_scene'}
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Scene cleared. Removed {resp.get('removed_count', 0)} objects."
    elif resp and resp.get('error'):
        return f"✗ Failed to clear scene: {resp.get('error')}"
    else:
        return "Scene clear requested"

# ============ Camera Tools ============

@mcp.tool()
def set_camera_position(x: float, y: float, z: float, look_at_x: float = 0.0, look_at_y: float = 0.0, look_at_z: float = 0.0) -> str:
    """
    Set camera position and look-at target

    Args:
        x, y, z: Camera position
        look_at_x, look_at_y, look_at_z: Point to look at (default: origin)
    """
    cmd = {
        'type': 'set_camera',
        'position': [x, y, z],
        'look_at': [look_at_x, look_at_y, look_at_z]
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Camera set to position ({x}, {y}, {z}) looking at ({look_at_x}, {look_at_y}, {look_at_z})"
    elif resp and resp.get('error'):
        return f"✗ Failed to set camera: {resp.get('error')}"
    else:
        return f"Camera move requested to ({x}, {y}, {z})"

@mcp.tool()
def get_camera_info() -> str:
    """Get current camera position and settings"""
    cmd = {'type': 'get_camera_info'}
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        pos = resp.get('position', [0, 0, 0])
        view = resp.get('view', [0, 0, -1])
        return f"Camera: position=({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}), view=({view[0]:.2f}, {view[1]:.2f}, {view[2]:.2f})"
    elif resp and resp.get('error'):
        return f"✗ Failed to get camera info: {resp.get('error')}"
    else:
        return "Camera info request timed out"

# ============ Light Tools ============

@mcp.tool()
def create_light(name: str, light_type: str = "point", x: float = 0.0, y: float = 5.0, z: float = 0.0,
                 color_r: float = 1.0, color_g: float = 1.0, color_b: float = 1.0,
                 intensity: float = 10.0, range_val: float = 20.0) -> str:
    """
    Create a light in the scene

    Args:
        name: Light name
        light_type: "point", "directional", or "spot"
        x, y, z: Light position
        color_r, color_g, color_b: Light color (0.0-1.0)
        intensity: Light intensity
        range_val: Light range (for point/spot lights)
    """
    cmd = {
        'type': 'create_light',
        'name': name,
        'light_type': light_type,
        'position': [x, y, z],
        'color': [color_r, color_g, color_b],
        'intensity': intensity,
        'range': range_val
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Light '{name}' ({light_type}) created at ({x}, {y}, {z})"
    elif resp and resp.get('error'):
        return f"✗ Failed to create light: {resp.get('error')}"
    else:
        return f"Light creation requested: {name}"

@mcp.tool()
def set_light_properties(name: str, intensity: float = None, color_r: float = None,
                         color_g: float = None, color_b: float = None,
                         cast_shadow: bool = None) -> str:
    """
    Modify light properties

    Args:
        name: Light name to modify
        intensity: New intensity (optional)
        color_r, color_g, color_b: New color components (optional)
        cast_shadow: Enable/disable shadow casting (optional)
    """
    cmd = {
        'type': 'set_light_properties',
        'name': name,
        'intensity': intensity,
        'color': [color_r, color_g, color_b] if color_r is not None else None,
        'cast_shadow': cast_shadow
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Light '{name}' properties updated"
    elif resp and resp.get('error'):
        return f"✗ Light '{name}' not found or update failed: {resp.get('error')}"
    else:
        return f"Light update requested: {name}"

# ============ Material Tools ============

@mcp.tool()
def set_object_color(name: str, r: float, g: float, b: float, a: float = 1.0) -> str:
    """
    Set the color of an object's material

    Args:
        name: Object name (e.g., 'mcp_cube_1' or 'mcp_sphere_2')
        r, g, b, a: RGBA color values (0.0-1.0)
    """
    cmd = {
        'type': 'set_object_color',
        'name': name,
        'color': [r, g, b, a]
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Object '{name}' color changed to RGBA({r}, {g}, {b}, {a})"
    elif resp and resp.get('error'):
        return f"✗ Failed to set color for '{name}': {resp.get('error')}"
    else:
        return f"Color change requested for '{name}'"

@mcp.tool()
def set_material_properties(name: str, wireframe: bool = None, double_sided: bool = None,
                            shader_type: str = None, shadow_cast: bool = None,
                            shadow_receive: bool = None) -> str:
    """
    Set material rendering properties

    Args:
        name: Object name
        wireframe: Enable wireframe mode
        double_sided: Enable double-sided rendering
        shader_type: "pbr", "phong", or "unlit"
        shadow_cast: Enable shadow casting from this object
        shadow_receive: Enable shadow receiving on this object
    """
    cmd = {
        'type': 'set_material_properties',
        'name': name,
        'wireframe': wireframe,
        'double_sided': double_sided,
        'shader_type': shader_type,
        'shadow_cast': shadow_cast,
        'shadow_receive': shadow_receive
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Material properties updated for '{name}'"
    elif resp and resp.get('error'):
        return f"✗ Failed to update material for '{name}': {resp.get('error')}"
    else:
        return f"Material update requested for '{name}'"

# ============ Transform Tools ============

@mcp.tool()
def set_object_position(name: str, x: float, y: float, z: float) -> str:
    """
    Move an object to a new position

    Args:
        name: Object name (e.g., 'mcp_cube_1')
        x, y, z: New position
    """
    cmd = {
        'type': 'set_object_position',
        'name': name,
        'position': [x, y, z]
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Object '{name}' moved to ({x}, {y}, {z})"
    elif resp and resp.get('error'):
        return f"✗ Object '{name}' not found: {resp.get('error')}"
    else:
        return f"Move requested for '{name}'"

@mcp.tool()
def set_object_scale(name: str, sx: float, sy: float, sz: float) -> str:
    """
    Scale an object

    Args:
        name: Object name
        sx, sy, sz: Scale factors
    """
    cmd = {
        'type': 'set_object_scale',
        'name': name,
        'scale': [sx, sy, sz]
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Object '{name}' scaled to ({sx}, {sy}, {sz})"
    elif resp and resp.get('error'):
        return f"✗ Object '{name}' not found: {resp.get('error')}"
    else:
        return f"Scale requested for '{name}'"

# ============ Scene Management ============

@mcp.tool()
def list_objects() -> str:
    """List all objects currently in the scene"""
    cmd = {'type': 'list_objects'}
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        objects = resp.get('objects', [])
        if not objects:
            return "Scene is empty - no objects created yet."

        lines = ["Objects in scene:"]
        for obj in objects:
            lines.append(f"  - {obj['name']} ({obj['type']})")
        lines.append(f"Total: {len(objects)} objects")
        return "\n".join(lines)
    elif resp and resp.get('error'):
        return f"✗ Failed to list objects: {resp.get('error')}"
    else:
        return "Object list request timed out"

@mcp.tool()
def delete_object(name: str) -> str:
    """
    Delete an object from the scene

    Args:
        name: Object name to delete
    """
    cmd = {
        'type': 'delete_object',
        'name': name
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Object '{name}' deleted successfully"
    elif resp and resp.get('error'):
        return f"✗ Object '{name}' not found: {resp.get('error')}"
    else:
        return f"Delete requested for '{name}'"

# ============ Model Loading ============

@mcp.tool()
def load_model(filepath: str, name: str = None) -> str:
    """
    Load a 3D model file (OBJ, GLTF, etc.)

    Args:
        filepath: Path to the model file
        name: Optional name for the loaded model
    """
    cmd = {
        'type': 'load_model',
        'filepath': filepath,
        'name': name
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Model '{resp.get('name', name or filepath)}' loaded successfully"
    elif resp and resp.get('error'):
        return f"✗ Failed to load model: {resp.get('error')}"
    else:
        return f"Model load requested: {filepath}"

# ============ Render Settings ============

@mcp.tool()
def set_render_settings(hdr: bool = None, tonemap: str = None, clear_color: list = None) -> str:
    """
    Configure render settings

    Args:
        hdr: Enable/disable HDR rendering
        tonemap: "reinhard" or "aces"
        clear_color: Background color [r, g, b, a]
    """
    cmd = {
        'type': 'set_render_settings',
        'hdr': hdr,
        'tonemap': tonemap,
        'clear_color': clear_color
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Render settings updated"
    elif resp and resp.get('error'):
        return f"✗ Failed to update render settings: {resp.get('error')}"
    else:
        return "Render settings update requested"

# ============ Rotation Tools ============

@mcp.tool()
def set_object_rotation(name: str, roll: float, pitch: float, yaw: float) -> str:
    """
    Rotate an object using Euler angles in degrees

    Args:
        name: Object name (e.g., 'mcp_cube_1')
        roll: Rotation around Z axis (degrees)
        pitch: Rotation around X axis (degrees)
        yaw: Rotation around Y axis (degrees)
    """
    cmd = {
        'type': 'set_object_rotation',
        'name': name,
        'rotation': [roll, pitch, yaw]
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Object '{name}' rotated to (roll={roll}°, pitch={pitch}°, yaw={yaw}°)"
    elif resp and resp.get('error'):
        return f"✗ Object '{name}' not found: {resp.get('error')}"
    else:
        return f"Rotation requested for '{name}'"

@mcp.tool()
def get_object_transform(name: str) -> str:
    """
    Get object's position, rotation, and scale

    Args:
        name: Object name
    """
    cmd = {
        'type': 'get_object_transform',
        'name': name
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        pos = resp.get('position', [0, 0, 0])
        rot = resp.get('rotation', [0, 0, 0, 1])
        scale = resp.get('scale', [1, 1, 1])
        return f"Object '{name}':\n  Position: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})\n  Rotation (quat): ({rot[0]:.3f}, {rot[1]:.3f}, {rot[2]:.3f}, {rot[3]:.3f})\n  Scale: ({scale[0]:.2f}, {scale[1]:.2f}, {scale[2]:.2f})"
    elif resp and resp.get('error'):
        return f"✗ Object '{name}' not found: {resp.get('error')}"
    else:
        return f"Transform query timed out for '{name}'"

# ============ Resolution & DDGI ============

@mcp.tool()
def set_render_resolution(width: int, height: int) -> str:
    """
    Set render resolution

    Args:
        width: Render width in pixels
        height: Render height in pixels
    """
    cmd = {
        'type': 'set_render_resolution',
        'width': width,
        'height': height
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        return f"✓ Render resolution set to {width}x{height}"
    elif resp and resp.get('error'):
        return f"✗ Failed to set resolution: {resp.get('error')}"
    else:
        return f"Resolution change requested: {width}x{height}"

@mcp.tool()
def enable_ddgi(enabled: bool, grid_x: int = 32, grid_y: int = 8, grid_z: int = 32) -> str:
    """
    Enable/disable DDGI (Dynamic Diffuse Global Illumination)

    Args:
        enabled: True to enable, False to disable
        grid_x: DDGI grid X resolution (default 32)
        grid_y: DDGI grid Y resolution (default 8)
        grid_z: DDGI grid Z resolution (default 32)
    """
    cmd = {
        'type': 'enable_ddgi',
        'enabled': enabled,
        'grid': [grid_x, grid_y, grid_z]
    }
    resp = write_command_and_wait(cmd)

    if resp and resp.get('success'):
        status = "enabled" if enabled else "disabled"
        if enabled:
            return f"✓ DDGI {status} with grid ({grid_x}, {grid_y}, {grid_z})"
        return f"✓ DDGI {status}"
    elif resp and resp.get('error'):
        return f"✗ Failed to configure DDGI: {resp.get('error')}"
    else:
        return f"DDGI configuration requested"

if __name__ == "__main__":
    # Run the MCP server (stdio mode)
    print("[MCP] Starting headless MCP server with response handling...", file=log_file)
    mcp.run()
