cmake_minimum_required(VERSION 3.20)
project(ShaderEngineMetal LANGUAGES CXX OBJCXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_OBJCXX_STANDARD 17)

# Output directory
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/../../bin/${CMAKE_SYSTEM_NAME}_${CMAKE_BUILD_TYPE})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/../../bin/${CMAKE_SYSTEM_NAME}_${CMAKE_BUILD_TYPE})

# Source files
set(SHADER_ENGINE_METAL_SOURCES
    ShaderEngineMetal.mm
)

set(SHADER_ENGINE_METAL_HEADERS
    ShaderEngineMetal.h
)

# Create shared library
add_library(ShaderEngineMetal SHARED
    ${SHADER_ENGINE_METAL_SOURCES}
    ${SHADER_ENGINE_METAL_HEADERS}
)

# Include directories
target_include_directories(ShaderEngineMetal PRIVATE
    ${CMAKE_SOURCE_DIR}/../../EngineCore
    ${CMAKE_SOURCE_DIR}/../../EngineCore/Utils
    ${CMAKE_SOURCE_DIR}/../../EngineCore/Utils/DirectXMath
    ${CMAKE_SOURCE_DIR}/../../EngineCore/ThirdParty
    ${CMAKE_SOURCE_DIR}/../../EngineCore/ThirdParty/spdlog
    ${CMAKE_SOURCE_DIR}/../../GraphicsBackends
)

# Compile definitions
target_compile_definitions(ShaderEngineMetal PRIVATE
    BUILD_INTRINSICS_LEVEL=0
)

# macOS frameworks
if(APPLE)
    find_library(FOUNDATION_FRAMEWORK Foundation REQUIRED)
    find_library(METAL_FRAMEWORK Metal REQUIRED)
    find_library(QUARTZCORE_FRAMEWORK QuartzCore REQUIRED)

    target_link_libraries(ShaderEngineMetal PRIVATE
        ${FOUNDATION_FRAMEWORK}
        ${METAL_FRAMEWORK}
        ${QUARTZCORE_FRAMEWORK}
    )

    # Link to VizEngineCore and GBackendMetal
    target_link_directories(ShaderEngineMetal PRIVATE
        ${CMAKE_SOURCE_DIR}/../../bin/${CMAKE_SYSTEM_NAME}_${CMAKE_BUILD_TYPE}
        ${CMAKE_SOURCE_DIR}/../../bin/${CMAKE_SYSTEM_NAME}_${CMAKE_BUILD_TYPE}/Release
    )
    target_link_libraries(ShaderEngineMetal PRIVATE
        VizEngineCore
        GBackendMetal
    )

    # Objective-C++ compile flags
    target_compile_options(ShaderEngineMetal PRIVATE
        -fobjc-arc
    )

    set_target_properties(ShaderEngineMetal PROPERTIES
        MACOSX_RPATH ON
        INSTALL_RPATH "@executable_path"
    )
endif()

# Export symbols
set_target_properties(ShaderEngineMetal PROPERTIES
    DEFINE_SYMBOL "SHADER_ENGINE_METAL_EXPORTS"
    POSITION_INDEPENDENT_CODE ON
    CXX_VISIBILITY_PRESET default
    VISIBILITY_INLINES_HIDDEN OFF
)
