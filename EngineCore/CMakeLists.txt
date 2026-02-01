cmake_minimum_required(VERSION 3.20)
project(VizEngineCore LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Output directory
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/../bin/${CMAKE_SYSTEM_NAME}_${CMAKE_BUILD_TYPE})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/../bin/${CMAKE_SYSTEM_NAME}_${CMAKE_BUILD_TYPE})
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/../bin/${CMAKE_SYSTEM_NAME}_${CMAKE_BUILD_TYPE})

# Source files
set(UTILS_SOURCES
    Utils/Helpers2.cpp
    Utils/Profiler.cpp
    Utils/GeometryGenerator.cpp
    Utils/JobSystem.cpp
    Utils/Config.cpp
    Utils/Backlog.cpp
    Utils/SimpleCollision.cpp
    Utils/EventHandler.cpp
)

set(HIGHAPIS_SOURCES
    HighAPIs/VzComponentAPIs.cpp
    HighAPIs/VzAnimation.cpp
    HighAPIs/VzScene.cpp
    HighAPIs/VzEngineManager.cpp
    HighAPIs/VzArchive.cpp
    HighAPIs/VzLight.cpp
    HighAPIs/VzRenderer.cpp
    HighAPIs/VzActor.cpp
    HighAPIs/VzMaterial.cpp
    HighAPIs/VzGeometry.cpp
    HighAPIs/VzTexture.cpp
    HighAPIs/VzCamera.cpp
)

set(COMPONENTS_SOURCES
    Components/EnvironmentComponent.cpp
    Components/GeometryComponent.cpp
    Components/Scene.cpp
    Components/ComponentRefReset.cpp
    Components/TextureComponent.cpp
    Components/AnimationComponent.cpp
    Components/BasicComponents.cpp
    Components/ComponentSerializer.cpp
    Components/CameraComponent.cpp
    Components/MaterialComponent.cpp
    Components/SlicerComponent.cpp
    Components/RenderableComponent.cpp
    Components/ComponentFactory.cpp
    Components/SpriteComponent.cpp
)

set(COMMON_SOURCES
    Common/Initializer.cpp
    Common/Canvas.cpp
    Common/Version.cpp
    Common/RenderPath3D.cpp
    Common/RenderPath2D.cpp
    Common/ResourceManager.cpp
    Common/Archive.cpp
)

# ThirdParty sources
set(THIRDPARTY_SOURCES
    # meshoptimizer
    ThirdParty/meshoptimizer/allocator.cpp
    ThirdParty/meshoptimizer/clusterizer.cpp
    ThirdParty/meshoptimizer/indexcodec.cpp
    ThirdParty/meshoptimizer/indexgenerator.cpp
    ThirdParty/meshoptimizer/overdrawanalyzer.cpp
    ThirdParty/meshoptimizer/overdrawoptimizer.cpp
    ThirdParty/meshoptimizer/simplifier.cpp
    ThirdParty/meshoptimizer/spatialorder.cpp
    ThirdParty/meshoptimizer/stripifier.cpp
    ThirdParty/meshoptimizer/vcacheanalyzer.cpp
    ThirdParty/meshoptimizer/vcacheoptimizer.cpp
    ThirdParty/meshoptimizer/vertexcodec.cpp
    ThirdParty/meshoptimizer/vertexfilter.cpp
    ThirdParty/meshoptimizer/vfetchanalyzer.cpp
    ThirdParty/meshoptimizer/vfetchoptimizer.cpp
    # stb, qoi implementations
    ThirdParty/stb_image.cpp
    # lodepng
    ThirdParty/lodepng.cpp
    # mikktspace
    ThirdParty/mikktspace.c
    # zstd (for basis_universal)
    ThirdParty/basis_universal/zstd/zstd.c
    # basis_universal transcoder
    ThirdParty/basis_universal/transcoder/basisu_transcoder.cpp
    # basis_universal encoder
    ThirdParty/basis_universal/encoder/basisu_backend.cpp
    ThirdParty/basis_universal/encoder/basisu_basis_file.cpp
    ThirdParty/basis_universal/encoder/basisu_bc7enc.cpp
    ThirdParty/basis_universal/encoder/basisu_comp.cpp
    ThirdParty/basis_universal/encoder/basisu_enc.cpp
    ThirdParty/basis_universal/encoder/basisu_etc.cpp
    ThirdParty/basis_universal/encoder/basisu_frontend.cpp
    ThirdParty/basis_universal/encoder/basisu_gpu_texture.cpp
    ThirdParty/basis_universal/encoder/basisu_pvrtc1_4.cpp
    ThirdParty/basis_universal/encoder/basisu_resample_filters.cpp
    ThirdParty/basis_universal/encoder/basisu_resampler.cpp
    ThirdParty/basis_universal/encoder/basisu_ssim.cpp
    ThirdParty/basis_universal/encoder/basisu_uastc_enc.cpp
    ThirdParty/basis_universal/encoder/basisu_opencl.cpp
    ThirdParty/basis_universal/encoder/jpgd.cpp
    ThirdParty/basis_universal/encoder/pvpngreader.cpp

    # SSE kernels (includes stubs when SSE disabled)
    ThirdParty/basis_universal/encoder/basisu_kernels_sse.cpp
)

# Create library
add_library(VizEngineCore SHARED
    ${UTILS_SOURCES}
    ${HIGHAPIS_SOURCES}
    ${COMPONENTS_SOURCES}
    ${COMMON_SOURCES}
    ${THIRDPARTY_SOURCES}
)

# Include directories
target_include_directories(VizEngineCore PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/Utils
    ${CMAKE_CURRENT_SOURCE_DIR}/Utils/DirectXMath
    ${CMAKE_CURRENT_SOURCE_DIR}/ThirdParty
    ${CMAKE_CURRENT_SOURCE_DIR}/ThirdParty/spdlog
    ${CMAKE_CURRENT_SOURCE_DIR}/ThirdParty/basis_universal/transcoder
    ${CMAKE_CURRENT_SOURCE_DIR}/ThirdParty/basis_universal/encoder
)

# Platform-specific settings
if(APPLE)
    target_compile_definitions(VizEngineCore PRIVATE
        PLATFORM_MACOS
        BUILD_INTRINSICS_LEVEL=0  # Disable SIMD intrinsics for DirectXMath compatibility
        BASISU_NO_ITERATOR_DEBUG_LEVEL
        BASISU_SUPPORT_SSE=0      # Disable SSE for ARM
        BASISU_SUPPORT_OPENCL=0   # Disable OpenCL
    )

    # Frameworks
    find_library(FOUNDATION_FRAMEWORK Foundation REQUIRED)
    find_library(COREFOUNDATION_FRAMEWORK CoreFoundation REQUIRED)

    target_link_libraries(VizEngineCore PRIVATE
        ${FOUNDATION_FRAMEWORK}
        ${COREFOUNDATION_FRAMEWORK}
    )

    set_target_properties(VizEngineCore PROPERTIES
        MACOSX_RPATH ON
        INSTALL_RPATH "@executable_path"
    )
endif()

# Export symbols
set_target_properties(VizEngineCore PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)

# Simple test executable
add_executable(TestMetalBackend
    ${CMAKE_SOURCE_DIR}/../Examples/TestMetalBackend/main.cpp
)

target_include_directories(TestMetalBackend PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(TestMetalBackend PRIVATE
    VizEngineCore
)

if(APPLE)
    find_library(APPKIT_FRAMEWORK AppKit REQUIRED)
    target_link_libraries(TestMetalBackend PRIVATE
        ${APPKIT_FRAMEWORK}
        ${FOUNDATION_FRAMEWORK}
    )

    set_target_properties(TestMetalBackend PROPERTIES
        MACOSX_RPATH ON
        INSTALL_RPATH "@executable_path"
    )
endif()
