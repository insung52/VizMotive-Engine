cmake_minimum_required(VERSION 3.20)
project(GBackendMetal LANGUAGES CXX)

# C++ 표준 설정
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 출력 디렉토리 설정
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/../bin/${CMAKE_SYSTEM_NAME}_${CMAKE_BUILD_TYPE})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/../bin/${CMAKE_SYSTEM_NAME}_${CMAKE_BUILD_TYPE})

# 공통 헤더
set(COMMON_HEADERS
    GBackendMetal.h
)

# 플랫폼별 소스 파일
if(APPLE)
    # macOS: Objective-C++ 사용
    enable_language(OBJCXX)
    set(PLATFORM_SOURCES
        GBackendMetal.mm
        GraphicsDevice_Metal.mm
    )
    set(CMAKE_OBJCXX_STANDARD 17)
else()
    # Windows: 스텁 버전
    set(PLATFORM_SOURCES
        GBackendMetal.cpp
    )
endif()

# 동적 라이브러리 생성
add_library(GBackendMetal SHARED
    ${COMMON_HEADERS}
    ${PLATFORM_SOURCES}
)

# 포함 디렉토리
target_include_directories(GBackendMetal PRIVATE
    ${CMAKE_SOURCE_DIR}/../EngineCore
)

# 플랫폼별 설정
if(APPLE)
    # macOS: Metal 프레임워크 링크
    find_library(METAL_FRAMEWORK Metal REQUIRED)
    find_library(METALKIT_FRAMEWORK MetalKit REQUIRED)
    find_library(FOUNDATION_FRAMEWORK Foundation REQUIRED)
    find_library(QUARTZCORE_FRAMEWORK QuartzCore REQUIRED)
    find_library(APPKIT_FRAMEWORK AppKit REQUIRED)

    target_link_libraries(GBackendMetal PRIVATE
        ${METAL_FRAMEWORK}
        ${METALKIT_FRAMEWORK}
        ${FOUNDATION_FRAMEWORK}
        ${QUARTZCORE_FRAMEWORK}
        ${APPKIT_FRAMEWORK}
    )

    # Objective-C++ 컴파일 플래그
    target_compile_options(GBackendMetal PRIVATE
        -fobjc-arc
    )

    # VizEngine 라이브러리 링크 (macOS)
    target_link_directories(GBackendMetal PRIVATE
        ${CMAKE_SOURCE_DIR}/../bin/${CMAKE_SYSTEM_NAME}_${CMAKE_BUILD_TYPE}
    )
    # target_link_libraries(GBackendMetal PRIVATE VizEngine)

elseif(WIN32)
    # Windows 설정
    target_compile_definitions(GBackendMetal PRIVATE
        _WINDOWS
        _USRDLL
    )

    # VizEngine 라이브러리 링크 (Windows)
    target_link_directories(GBackendMetal PRIVATE
        ${CMAKE_SOURCE_DIR}/../bin/x64_$<IF:$<CONFIG:Debug>,Debug,Release>
    )
    target_link_libraries(GBackendMetal PRIVATE
        $<IF:$<CONFIG:Debug>,VizEngined,VizEngine>
    )
endif()

# Export 심볼 설정
set_target_properties(GBackendMetal PROPERTIES
    DEFINE_SYMBOL "GBACKEND_METAL_EXPORTS"
    POSITION_INDEPENDENT_CODE ON
)

if(APPLE)
    set_target_properties(GBackendMetal PROPERTIES
        BUNDLE FALSE
        MACOSX_RPATH ON
        INSTALL_RPATH "@executable_path"
    )

    # MetalTriangleSample executable
    add_executable(MetalTriangleSample
        ${CMAKE_SOURCE_DIR}/../Examples/MetalTriangleSample/main.mm
    )

    target_include_directories(MetalTriangleSample PRIVATE
        ${CMAKE_SOURCE_DIR}
        ${CMAKE_SOURCE_DIR}/../EngineCore
    )

    target_link_libraries(MetalTriangleSample PRIVATE
        ${METAL_FRAMEWORK}
        ${METALKIT_FRAMEWORK}
        ${FOUNDATION_FRAMEWORK}
        ${QUARTZCORE_FRAMEWORK}
        ${APPKIT_FRAMEWORK}
        GBackendMetal
    )

    target_compile_options(MetalTriangleSample PRIVATE
        -fobjc-arc
    )

    set_target_properties(MetalTriangleSample PROPERTIES
        MACOSX_BUNDLE TRUE
        MACOSX_BUNDLE_GUI_IDENTIFIER "com.vizmotive.MetalTriangleSample"
        MACOSX_BUNDLE_BUNDLE_NAME "MetalTriangleSample"
        MACOSX_BUNDLE_BUNDLE_VERSION "1.0"
        MACOSX_BUNDLE_SHORT_VERSION_STRING "1.0"
        XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER "com.vizmotive.MetalTriangleSample"
    )
endif()
