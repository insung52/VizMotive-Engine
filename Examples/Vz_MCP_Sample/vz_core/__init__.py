"""
VizMotive Core Library
======================
공통 모듈 패키지 - 경로 설정, 엔진 초기화, GUI 컴포넌트

Usage:
    from vz_core import vzm, init_engine
    from vz_core.camera import OrbitCamera
    from vz_core.render_utils import rgba8_to_float
"""
import sys
import os

# 경로 설정 (이 파일 기준으로 계산)
_package_dir = os.path.dirname(os.path.abspath(__file__))
_sample_dir = os.path.dirname(_package_dir)  # Vz_MCP_Sample
_examples_dir = os.path.dirname(_sample_dir)  # Examples
_engine_root = os.path.dirname(_examples_dir)  # VizMotive-Engine

# pyvizmotive 경로 추가
_pyvizmotive_path = os.path.join(_engine_root, "PythonBindings", "out", "build", "x64-Debug")
if _pyvizmotive_path not in sys.path:
    sys.path.insert(0, _pyvizmotive_path)

# DLL 경로 설정
os.environ["PATH"] = _pyvizmotive_path + os.pathsep + os.environ.get("PATH", "")
if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(_pyvizmotive_path)

# Assets junction 생성 (필요시)
_assets_junction = os.path.join(_engine_root, "Assets")
_assets_source = os.path.join(_engine_root, "Examples", "Assets")
if not os.path.exists(_assets_junction):
    import subprocess
    subprocess.run(["cmd", "/c", "mklink", "/J", _assets_junction, _assets_source], check=False)

# 작업 디렉토리를 Examples로 설정 (Shaders 로드용)
os.chdir(_examples_dir)

# pyvizmotive import
import pyvizmotive as vzm

# 경로 정보 export
ENGINE_ROOT = _engine_root
EXAMPLES_DIR = _examples_dir
SAMPLE_DIR = _sample_dir


def init_engine(headless: bool = False, use_rgba8: bool = True) -> bool:
    """
    VizMotive 엔진 초기화

    Args:
        headless: True면 헤드리스 모드로 초기화 (현재 미구현)
        use_rgba8: True면 R8G8B8A8_UNORM 포맷 사용 (Python 뷰어용, GPU->CPU 복사 최적화)
                   False면 R11G11B10_FLOAT 포맷 사용 (HDR, 기본 C++ 샘플용)

    Returns:
        성공 여부
    """
    # Python 뷰어에서는 R8G8B8A8 사용 (변환 없이 바로 표시 가능)
    # C++ 샘플에서는 R11G11B10_FLOAT 사용 (HDR 지원)
    render_target_format = 1 if use_rgba8 else 0
    return vzm.init_engine(render_target_format)


def deinit_engine():
    """엔진 종료"""
    vzm.deinit_engine()


# 편의를 위한 re-export
from .camera import OrbitCamera
from .render_utils import rgba8_to_float

__all__ = [
    'vzm',
    'init_engine',
    'deinit_engine',
    'ENGINE_ROOT',
    'EXAMPLES_DIR',
    'SAMPLE_DIR',
    'OrbitCamera',
    'rgba8_to_float',
]
