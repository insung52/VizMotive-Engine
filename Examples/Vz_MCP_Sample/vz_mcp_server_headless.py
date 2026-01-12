"""
VizMotive MCP Server (Headless) - No GUI, controls external viewer
"""
import sys
import os
import subprocess
import json
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

# Shared state file for communication with viewer
STATE_FILE = Path("C:\\graphics\\vizmotive\\my\\VizMotive-Engine\\Examples\\Vz_MCP_Sample\\scene_commands.json")
viewer_process = None

def write_command(cmd):
    """Write command to state file for viewer to read"""
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
    write_command(cmd)
    return f"Cube created at position ({x}, {y}, {z}) with size {size} and color RGB({color_r}, {color_g}, {color_b})"

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
    write_command(cmd)
    return f"Sphere created at position ({x}, {y}, {z}) with radius {radius} and color RGB({color_r}, {color_g}, {color_b})"

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
    write_command(cmd)

    return f"Screenshot will be saved to: {filepath}"

@mcp.tool()
def clear_scene() -> str:
    """Clear all objects from the scene"""
    cmd = {'type': 'clear_scene'}
    write_command(cmd)
    return "Scene cleared"

if __name__ == "__main__":
    # Run the MCP server (stdio mode)
    print("[MCP] Starting headless MCP server...", file=log_file)
    mcp.run()
