import os
import sys
import platform
from pathlib import Path
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext


class get_pybind_include:
    """Helper class to determine the pybind11 include path"""
    def __str__(self):
        import pybind11
        return pybind11.get_include()


# Get VizMotive paths
vizmotive_root = Path(__file__).parent.parent
vizmotive_install = vizmotive_root / "Install"
vizmotive_include = vizmotive_install / "vzm2"
vizmotive_lib_dir = vizmotive_install / "lib"
vizmotive_bin_debug = vizmotive_install / "bin" / "debug_dll"
vizmotive_bin_release = vizmotive_install / "bin" / "release_dll"

# Check if VizEngine exists
if not vizmotive_include.exists():
    raise RuntimeError(f"VizEngine include directory not found: {vizmotive_include}")

if not vizmotive_lib_dir.exists():
    raise RuntimeError(f"VizEngine lib directory not found: {vizmotive_lib_dir}")


ext_modules = [
    Extension(
        'pyvizmotive',
        sources=[
            'src/pyvizmotive.cpp',
            'src/bind_engine.cpp',
        ],
        include_dirs=[
            get_pybind_include(),
            str(vizmotive_include),
        ],
        library_dirs=[
            str(vizmotive_lib_dir),
        ],
        libraries=['VizEngine'],  # Will use VizEngine.lib for Release
        language='c++',
    ),
]


class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""

    def build_extensions(self):
        # Compiler-specific options
        if platform.system() == 'Windows':
            for ext in self.extensions:
                ext.extra_compile_args = ['/std:c++17', '/EHsc']
                # Use debug library for debug builds
                if self.debug:
                    ext.libraries = ['VizEngined']
        else:
            for ext in self.extensions:
                ext.extra_compile_args = ['-std=c++17']

        build_ext.build_extensions(self)

    def copy_extensions_to_source(self):
        """Copy built extensions and DLLs to source directory"""
        build_ext.copy_extensions_to_source(self)

        # Copy VizEngine DLLs to the same directory as the pyd file
        if platform.system() == 'Windows':
            for ext in self.extensions:
                fullname = self.get_ext_fullname(ext.name)
                filename = self.get_ext_filename(fullname)
                dest_dir = Path(self.get_ext_fullpath(fullname)).parent

                # Determine which DLL directory to use
                dll_dir = vizmotive_bin_debug if self.debug else vizmotive_bin_release

                # List of required DLLs
                required_dlls = [
                    'VizEngined.dll' if self.debug else 'VizEngine.dll',
                    'AssetIO.dll',
                    'GBackendDX12.dll',
                    'ShaderEngine.dll',
                    'dxcompiler.dll',
                    'dxil.dll',
                ]

                # Copy each DLL
                import shutil
                for dll_name in required_dlls:
                    dll_path = dll_dir / dll_name
                    if dll_path.exists():
                        dest_path = dest_dir / dll_name
                        print(f"Copying {dll_path} -> {dest_path}")
                        shutil.copy2(dll_path, dest_path)
                    else:
                        print(f"Warning: {dll_path} not found, skipping...")


setup(
    name='pyvizmotive',
    version='0.1.0',
    author='VizMotive Team',
    description='Python bindings for VizMotive Engine',
    long_description='',
    ext_modules=ext_modules,
    cmdclass={'build_ext': BuildExt},
    zip_safe=False,
    python_requires='>=3.10',
)
