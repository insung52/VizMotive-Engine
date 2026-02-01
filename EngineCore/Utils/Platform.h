#pragma once
// This file includes platform, os specific libraries and supplies common platform specific resources

#include <unordered_map>
#include <string>
#include <vector>

#ifdef _WIN32

#ifndef NOMINMAX
#define NOMINMAX
#endif // NOMINMAX
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <SDKDDKVer.h>
#include <windows.h>
#include <tchar.h>

#if WINAPI_FAMILY
#define PLATFORM_WINDOWS_DESKTOP
#endif // WINAPI_FAMILY_GAMES
#define vzLoadLibrary(name) LoadLibraryA(name)
#define vzGetProcAddress(handle,name) GetProcAddress(handle, name)

#elif defined(__APPLE__)
#define PLATFORM_MACOS
#include <dlfcn.h>
#define vzLoadLibrary(name) dlopen(name, RTLD_LAZY)
#define vzGetProcAddress(handle,name) dlsym(handle, name)
typedef void* HMODULE;

#else
#define PLATFORM_LINUX
#include <dlfcn.h>
#define vzLoadLibrary(name) dlopen(name, RTLD_LAZY)
#define vzGetProcAddress(handle,name) dlsym(handle, name)
typedef void* HMODULE;
#endif // _WIN32

#ifdef SDL2
#include <SDL2/SDL.h>
#include <SDL_vulkan.h>
#include "sdl2.h"
#endif


namespace vz::platform
{
#ifdef _WIN32
	using window_type = HWND;
	using error_type = HRESULT;
#elif defined(PLATFORM_MACOS)
	using window_type = void*;  // NSWindow* or CAMetalLayer*
	using error_type = int;
#elif SDL2
	using window_type = SDL_Window*;
	using error_type = int;
#else
	using window_type = void*;
	using error_type = int;
#endif // _WIN32

	inline void Exit()
	{
#ifdef _WIN32
		PostQuitMessage(0);
#endif // _WIN32
#ifdef SDL2
		SDL_Event quit_event;
		quit_event.type = SDL_QUIT;
		SDL_PushEvent(&quit_event);
#endif
	}

	struct WindowProperties
	{
		int width = 0;
		int height = 0;
		float dpi = 96;
	};
	inline void GetWindowProperties(window_type window, WindowProperties* dest)
	{
#ifdef PLATFORM_WINDOWS_DESKTOP
		dest->dpi = (float)GetDpiForWindow(window);
#endif // WINDOWS_DESKTOP

#ifdef PLATFORM_XBOX
		dest->dpi = 96.f;
#endif // PLATFORM_XBOX

#if defined(PLATFORM_WINDOWS_DESKTOP) || defined(PLATFORM_XBOX)
		RECT rect;
		GetClientRect(window, &rect);
		dest->width = int(rect.right - rect.left);
		dest->height = int(rect.bottom - rect.top);
#endif // PLATFORM_WINDOWS_DESKTOP || PLATFORM_XBOX

#ifdef PLATFORM_MACOS
		// On macOS, window properties are typically obtained via Objective-C
		// For now, use default values; actual implementation should query NSWindow/CAMetalLayer
		dest->dpi = 96.f * 2.f;  // Retina display default
		dest->width = 0;
		dest->height = 0;
#endif // PLATFORM_MACOS

#ifdef PLATFORM_LINUX
		int window_width, window_height;
		SDL_GetWindowSize(window, &window_width, &window_height);
		SDL_Vulkan_GetDrawableSize(window, &dest->width, &dest->height);
		dest->dpi = ((float)dest->width / (float)window_width) * 96.f;
#endif // PLATFORM_LINUX
	}

	template <typename T>
	T LoadModule(std::string moduleName, std::string functionName, std::unordered_map<std::string, HMODULE>& importedModules)
	{
		HMODULE hMouleLib = NULL;
		auto it = importedModules.find(moduleName);
		if (it == importedModules.end())
		{
#if defined(PLATFORM_MACOS) || defined(PLATFORM_LINUX)
			// On macOS/Linux, try multiple paths with lib prefix and .dylib/.so extension
			std::vector<std::string> searchPaths;
#if defined(PLATFORM_MACOS)
			std::string libName = "lib" + moduleName + ".dylib";
#else
			std::string libName = "lib" + moduleName + ".so";
#endif
			// Try: current directory, @executable_path, absolute name
			searchPaths.push_back("./" + libName);
			searchPaths.push_back(libName);
			searchPaths.push_back("@executable_path/" + libName);
			searchPaths.push_back("@loader_path/" + libName);

			for (const auto& path : searchPaths)
			{
				hMouleLib = vzLoadLibrary(path.c_str());
				if (hMouleLib != NULL)
					break;
			}
#else
			hMouleLib = vzLoadLibrary(moduleName.c_str());
#endif
			if (hMouleLib != NULL)
				importedModules[moduleName] = hMouleLib;
		}
		else
			hMouleLib = it->second;
		if (hMouleLib == NULL)
		{
			return NULL;
		}

		T lpdll_function = NULL;
		lpdll_function = (T)vzGetProcAddress(hMouleLib, functionName.c_str());
		return lpdll_function;
	}
}
