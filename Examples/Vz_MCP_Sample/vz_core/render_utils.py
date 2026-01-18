"""
Render Utilities
================
렌더링 관련 유틸리티 함수들
"""
import numpy as np

# Reusable buffer for RGBA8 to float conversion
_float_buffer = None
_float_buffer_size = (0, 0)


def rgba8_to_float(data: bytes, width: int, height: int) -> np.ndarray:
    """
    Convert RGBA8 data to float32 RGBA array for DearPyGui.

    DearPyGui의 raw_texture는 float32 format만 지원하므로,
    uint8 데이터를 0.0-1.0 범위의 float32로 변환합니다.

    Args:
        data: RGBA8 바이트 데이터 (from store_render_target_rgba8)
        width: 이미지 너비
        height: 이미지 높이

    Returns:
        float32 numpy array (flattened, length = width * height * 4)
    """
    global _float_buffer, _float_buffer_size

    # Reuse or allocate buffer
    if _float_buffer_size != (width, height):
        _float_buffer = np.empty(height * width * 4, dtype=np.float32)
        _float_buffer_size = (width, height)

    # Convert uint8 to float32 (0-255 -> 0.0-1.0)
    # Using multiply (faster than divide)
    uint8_data = np.frombuffer(data, dtype=np.uint8)
    np.multiply(uint8_data, 1.0 / 255.0, out=_float_buffer, casting="unsafe")

    return _float_buffer


def clear_buffer_cache():
    """Clear the cached float buffer (for memory cleanup)"""
    global _float_buffer, _float_buffer_size
    _float_buffer = None
    _float_buffer_size = (0, 0)
