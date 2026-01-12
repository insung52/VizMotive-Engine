cmake_minimum_required(VERSION 3.15)
project(pyvizmotive)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Python
find_package(Python REQUIRED COMPONENTS Interpreter Development)

# Find pybind11
# Try to get pybind11 CMake directory from Python
execute_process(
    COMMAND ${Python_EXECUTABLE} -c "import pybind11; print(pybind11.get_cmake_dir())"
    OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE PYBIND11_FIND_RESULT
)

if(PYBIND11_FIND_RESULT EQUAL 0)
    message(STATUS "Found pybind11 CMake dir: ${PYBIND11_CMAKE_DIR}")
    list(APPEND CMAKE_PREFIX_PATH ${PYBIND11_CMAKE_DIR})
endif()

find_package(pybind11 REQUIRED)

# VizMotive Engine paths
set(VIZMOTIVE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
set(VIZMOTIVE_INSTALL "${VIZMOTIVE_ROOT}/Install")
set(VIZMOTIVE_INCLUDE "${VIZMOTIVE_INSTALL}")
set(VIZMOTIVE_LIB_DEBUG "${VIZMOTIVE_INSTALL}/lib/VizEngined.lib")
set(VIZMOTIVE_LIB_RELEASE "${VIZMOTIVE_INSTALL}/lib/VizEngine.lib")

# Check if VizEngine library exists
if(NOT EXISTS ${VIZMOTIVE_LIB_DEBUG} AND NOT EXISTS ${VIZMOTIVE_LIB_RELEASE})
    message(FATAL_ERROR "VizEngine library not found. Please build VizMotive engine first.")
endif()

# Check if include directory exists
if(NOT EXISTS ${VIZMOTIVE_INCLUDE})
    message(FATAL_ERROR "VizMotive include directory not found at ${VIZMOTIVE_INCLUDE}")
endif()

# Create Python module
pybind11_add_module(pyvizmotive
    src/pyvizmotive.cpp
    src/bind_types.cpp
    src/bind_engine.cpp
)

# Include directories
target_include_directories(pyvizmotive PRIVATE
    ${VIZMOTIVE_INCLUDE}
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# Link VizEngine library
target_link_libraries(pyvizmotive PRIVATE
    $<$<CONFIG:Debug>:${VIZMOTIVE_LIB_DEBUG}>
    $<$<CONFIG:Release>:${VIZMOTIVE_LIB_RELEASE}>
)

# Copy DLL to output directory (Windows only)
if(WIN32)
    set(VIZMOTIVE_DLL_DEBUG "${VIZMOTIVE_INSTALL}/bin/debug_dll/VizEngined.dll")
    set(VIZMOTIVE_DLL_RELEASE "${VIZMOTIVE_INSTALL}/bin/release_dll/VizEngine.dll")

    add_custom_command(TARGET pyvizmotive POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
        $<$<CONFIG:Debug>:${VIZMOTIVE_DLL_DEBUG}>
        $<$<CONFIG:Release>:${VIZMOTIVE_DLL_RELEASE}>
        $<TARGET_FILE_DIR:pyvizmotive>
        COMMENT "Copying VizEngine DLL to output directory"
    )

    # Copy other required DLLs
    set(VIZMOTIVE_BIN_DEBUG "${VIZMOTIVE_INSTALL}/bin/debug_dll")
    set(VIZMOTIVE_BIN_RELEASE "${VIZMOTIVE_INSTALL}/bin/release_dll")

    foreach(dll_name AssetIO.dll GBackendDX12.dll ShaderEngine.dll dxcompiler.dll dxil.dll)
        add_custom_command(TARGET pyvizmotive POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<$<CONFIG:Debug>:${VIZMOTIVE_BIN_DEBUG}/${dll_name}>
            $<$<CONFIG:Release>:${VIZMOTIVE_BIN_RELEASE}/${dll_name}>
            $<TARGET_FILE_DIR:pyvizmotive>
            COMMENT "Copying ${dll_name} to output directory"
        )
    endforeach()
endif()

# Installation
install(TARGETS pyvizmotive
    LIBRARY DESTINATION ${Python_SITEARCH}
    RUNTIME DESTINATION ${Python_SITEARCH}
)
