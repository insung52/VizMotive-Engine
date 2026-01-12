"""
Basic test for pyvizmotive Python bindings
"""
import sys
import os

# Add the build directory to path
build_dir = r"C:\graphics\vizmotive\my\VizMotive-Engine\PythonBindings\out\build\x64-Debug"
sys.path.insert(0, build_dir)

import pyvizmotive as vzm

def test_engine_init():
    """Test engine initialization"""
    print("Testing engine initialization...")
    result = vzm.init_engine()
    print(f"init_engine() returned: {result}")

    valid = vzm.is_valid_engine()
    print(f"is_valid_engine() returned: {valid}")

    vzm.deinit_engine()
    print("Engine deinitialized successfully\n")

def test_scene_creation():
    """Test scene creation"""
    print("Testing scene creation...")
    vzm.init_engine()

    scene = vzm.new_scene("test_scene")
    print(f"new_scene() returned: {scene}")
    print(f"Scene type: {type(scene)}")

    # Get VID by name
    vid = vzm.get_first_vid_by_name("test_scene")
    print(f"Scene VID: {vid}")

    # Get name by VID
    name = vzm.get_name_by_vid(vid)
    print(f"Scene name from VID: {name}")

    vzm.deinit_engine()
    print("Scene creation test successful\n")

def test_camera_and_renderer():
    """Test camera and renderer creation"""
    print("Testing camera and renderer creation...")
    vzm.init_engine()

    scene = vzm.new_scene("main_scene")
    camera = vzm.new_camera("main_camera")
    renderer = vzm.new_renderer("main_renderer")

    print(f"Scene: {scene}")
    print(f"Camera: {camera}")
    print(f"Renderer: {renderer}")

    camera_vid = vzm.get_first_vid_by_name("main_camera")
    renderer_vid = vzm.get_first_vid_by_name("main_renderer")

    print(f"Camera VID: {camera_vid}")
    print(f"Renderer VID: {renderer_vid}")

    vzm.deinit_engine()
    print("Camera and renderer creation test successful\n")

if __name__ == "__main__":
    print("=" * 60)
    print("VizMotive Python Bindings - Basic Tests")
    print("=" * 60 + "\n")

    try:
        test_engine_init()
        test_scene_creation()
        test_camera_and_renderer()

        print("=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
