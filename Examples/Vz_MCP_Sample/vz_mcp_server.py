"""
VizMotive MCP Server - FastMCP-based server for VizMotive engine control
"""
import sys
import os
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("VizMotive Engine")

@mcp.tool()
def ping() -> str:
    """Test tool to verify MCP server is working"""
    return "pong"

@mcp.tool()
def get_scene_info() -> dict:
    """Get current scene information"""
    return {
        "status": "ready",
        "scene": "main_scene",
        "objects": []
    }

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
