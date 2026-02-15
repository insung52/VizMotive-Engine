// STB library implementations
// This file provides the implementation for stb header-only libraries

#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

#define STB_RECT_PACK_IMPLEMENTATION
#include "stb_rect_pack.h"

#define STB_TRUETYPE_IMPLEMENTATION
#include "stb_truetype.h"

#define QOI_IMPLEMENTATION
#include "qoi.h"

#define MINIMP4_IMPLEMENTATION
#include "minimp4.h"
#undef RETURN_ERROR

#define H264_IMPLEMENTATION
#include "h264.h"
