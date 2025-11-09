// VizMotive Particle System Sample
#include "vzm2/VzEngineAPIs.h"
#include "vzm2/utils/JobSystem.h"
#include "vzm2/utils/Profiler.h"

#include <iostream>
#include <windowsx.h>
#include <tchar.h>
#include <shellscalingapi.h>

#include "glm/gtc/matrix_transform.hpp"
#include "glm/gtx/transform.hpp"
#include "glm/gtc/constants.hpp"
#include "glm/glm.hpp"
#include "glm/gtc/type_ptr.hpp"

LRESULT WINAPI WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

void EnableDpiAwareness() {
    HMODULE hUser32 = LoadLibrary(TEXT("user32.dll"));
    if (hUser32) {
        typedef BOOL(WINAPI* SetProcessDpiAwarenessContextProc)(DPI_AWARENESS_CONTEXT);
        SetProcessDpiAwarenessContextProc SetProcessDpiAwarenessContextFunc =
            (SetProcessDpiAwarenessContextProc)GetProcAddress(hUser32, "SetProcessDpiAwarenessContext");

        if (SetProcessDpiAwarenessContextFunc) {
            SetProcessDpiAwarenessContextFunc(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
        }
        FreeLibrary(hUser32);
    }
}

HWND createNativeWindow(HINSTANCE hInstance, int nCmdShow, int width, int height) {
    const wchar_t CLASS_NAME[] = L"Particle Sample Window";

    WNDCLASS wc = { };
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = CLASS_NAME;

    RegisterClass(&wc);

    HWND hwnd = CreateWindowEx(
        0,
        CLASS_NAME,
        L"Sample 15 - Particle System",
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, CW_USEDEFAULT, width, height,
        NULL, NULL, hInstance, NULL
    );

    if (hwnd == NULL) {
        std::cerr << "Failed to create window." << std::endl;
        return NULL;
    }

    ShowWindow(hwnd, nCmdShow);
    return hwnd;
}

int APIENTRY wWinMain(_In_ HINSTANCE hInstance,
    _In_opt_ HINSTANCE hPrevInstance,
    _In_ LPWSTR lpCmdLine,
    _In_ int nCmdShow)
{
    UNREFERENCED_PARAMETER(hPrevInstance);
    UNREFERENCED_PARAMETER(lpCmdLine);

    EnableDpiAwareness();

    HWND hwnd = createNativeWindow(hInstance, nCmdShow, 1280, 720);
    if (!hwnd) {
        return -1;
    }

    HDC hdc = GetDC(hwnd);
    if (!hdc) {
        std::cerr << "Failed to get device context." << std::endl;
        return -1;
    }

    RECT rc;
    GetClientRect(hwnd, &rc);
    uint32_t w = rc.right - rc.left;
    uint32_t h = rc.bottom - rc.top;
    float dpi = 96.f;

    // Initialize engine
    vzm::ParamMap<std::string> arguments;
    if (!vzm::InitEngineLib(arguments)) {
        std::cerr << "Failed to initialize engine library." << std::endl;
        return -1;
    }

    // Create scene
    vzm::VzScene* scene = vzm::NewScene("particle scene");

    // Create renderer
    vzm::VzRenderer* renderer = vzm::NewRenderer("particle renderer");
    renderer->SetCanvas(w, h, dpi, hwnd);
    renderer->SetClearColor({ 0.1f, 0.1f, 0.2f, 1.0f });
    renderer->EnableFrameLock(true, false);

    // Create camera
    vzm::VzCamera* camera = vzm::NewCamera("particle camera");
    glm::fvec3 camPos(0, 2, 10);
    glm::fvec3 camAt(0, 0, 0);
    glm::fvec3 camUp(0, 1, 0);
    camera->SetWorldPose(__FC3 camPos, __FC3 camAt, __FC3 camUp);
    camera->SetPerspectiveProjection(0.1f, 100.f, 45.f, (float)w / (float)h);

    // Create particle emitter actor
    // For now, we'll use low-level ECS API since high-level API doesn't have particle actor yet
    using namespace vz;
    using namespace vz::ecs;
    using namespace vz::compfactory;

    // Create entity for particle emitter
    Entity particleEntity = CreateEntity();

    // Add transform component
    TransformComponent* transform = GetTransformComponent(particleEntity);
    if (!transform) {
        std::cerr << "Failed to create transform component." << std::endl;
        return -1;
    }
    transform->SetPosition(XMFLOAT3(0, 0, 0));

    // Add particle component
    EmittedParticleComponent* particle = GetEmittedParticleComponent(particleEntity);
    if (!particle) {
        std::cerr << "Failed to create particle component." << std::endl;
        return -1;
    }

    // Configure particle emitter
    particle->SetEmitCount(50.0f);          // 50 particles per second
    particle->SetMaxParticles(1000);        // Max 1000 particles
    particle->SetLife(3.0f);                // 3 second lifetime
    particle->SetRandomLife(1.0f);          // +/- 1 second randomness
    particle->SetSize(0.5f);                // Starting size
    particle->SetScaleX(1.0f);              // Ending size multiplier
    particle->SetScaleY(1.0f);
    particle->SetVelocity(XMFLOAT3(0, 2.0f, 0));  // Upward velocity
    particle->SetGravity(XMFLOAT3(0, -5.0f, 0));  // Gravity
    particle->SetDrag(0.98f);               // Air resistance
    particle->SetRandomFactor(0.5f);        // Random spread
    particle->SetNormalFactor(1.0f);        // Normal-based emission
    particle->SetRandomColor(0.2f);         // Color variation

    // Enable features
    particle->SetSorted(false);             // No sorting for now
    particle->SetDepthCollisionEnabled(false);  // No depth collision

    // Cast to GPU component and create GPU resources
    vz::GEmittedParticleComponent* gpuParticle = dynamic_cast<vz::GEmittedParticleComponent*>(particle);
    if (gpuParticle) {
        if (!gpuParticle->CreateGPUResources()) {
            std::cerr << "Failed to create particle GPU resources." << std::endl;
            return -1;
        }
        std::cout << "Particle system initialized successfully!" << std::endl;
    }

    // Main loop
    MSG msg = { };
    bool running = true;
    auto lastTime = std::chrono::high_resolution_clock::now();

    std::cout << "=== Particle System Sample ===" << std::endl;
    std::cout << "Press ESC to exit" << std::endl;
    std::cout << "Emitting particles..." << std::endl;

    while (running) {
        // Process messages
        while (PeekMessage(&msg, NULL, 0, 0, PM_REMOVE)) {
            if (msg.message == WM_QUIT) {
                running = false;
            }
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }

        // Calculate delta time
        auto currentTime = std::chrono::high_resolution_clock::now();
        float dt = std::chrono::duration<float>(currentTime - lastTime).count();
        lastTime = currentTime;

        // Update particle system (CPU side)
        if (gpuParticle && transform) {
            gpuParticle->UpdateCPU(*transform, dt);
        }

        // Render
        if (renderer && scene && camera) {
            renderer->Render(scene, camera);
        }

        // Small delay to prevent 100% CPU usage
        Sleep(1);
    }

    // Cleanup
    if (gpuParticle) {
        gpuParticle->DestroyGPUResources();
    }

    vzm::DeinitEngineLib();
    return 0;
}

LRESULT WINAPI WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    switch (msg)
    {
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;

    case WM_KEYDOWN:
        if (wParam == VK_ESCAPE) {
            PostQuitMessage(0);
        }
        return 0;

    default:
        return DefWindowProc(hWnd, msg, wParam, lParam);
    }
}
