// TestShaderEngineMetal - Test the ShaderEngineMetal triangle rendering
// Links directly to GBackendMetal, loads ShaderEngineMetal dynamically

#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <QuartzCore/CAMetalLayer.h>

#include <dlfcn.h>

// Include GraphicsDevice_Metal directly since we link to it
#include "GraphicsDevice_Metal.h"
#include "GBackend/GShaderInterface.h"

using namespace vz::graphics;

// Function pointer types for ShaderEngineMetal
typedef bool (*FP_Initialize)(GraphicsDevice* device);
typedef bool (*FP_LoadRenderer)();
typedef vz::GRenderPath3D* (*FP_NewGRenderPath)(SwapChain& swapChain, Texture& rtRenderFinal);
typedef void (*FP_Deinitialize)();

// Application delegate
@interface AppDelegate : NSObject <NSApplicationDelegate>
{
@public
    GraphicsDevice_Metal* _device;
    SwapChain _swapChain;
    Texture _rtRenderFinal;
    vz::GRenderPath3D* _renderPath;
    bool _initialized;

    // ShaderEngineMetal module
    void* _shaderHandle;
    FP_Initialize _shaderInit;
    FP_LoadRenderer _shaderLoadRenderer;
    FP_NewGRenderPath _shaderNewRenderPath;
    FP_Deinitialize _shaderDeinit;
}
@property (strong) NSWindow* window;
@property (strong) NSTimer* renderTimer;
@end

@implementation AppDelegate

- (BOOL)loadShaderEngine
{
    // Get the executable path
    NSString* execPath = [[NSBundle mainBundle] executablePath];
    NSString* execDir = [execPath stringByDeletingLastPathComponent];

    // Try different paths for the shader library
    NSArray* searchPaths = @[
        [execDir stringByAppendingPathComponent:@"libShaderEngineMetal.dylib"],
        [[[execDir stringByDeletingLastPathComponent] stringByDeletingLastPathComponent] stringByAppendingPathComponent:@"libShaderEngineMetal.dylib"],
        [[[[execDir stringByDeletingLastPathComponent] stringByDeletingLastPathComponent] stringByDeletingLastPathComponent] stringByAppendingPathComponent:@"libShaderEngineMetal.dylib"],
    ];

    NSString* shaderPath = nil;
    for (NSString* path in searchPaths) {
        if ([[NSFileManager defaultManager] fileExistsAtPath:path]) {
            shaderPath = path;
            break;
        }
    }

    if (!shaderPath) {
        NSLog(@"Could not find libShaderEngineMetal.dylib");
        NSLog(@"Searched paths:");
        for (NSString* path in searchPaths) {
            NSLog(@"  %@", path);
        }
        return NO;
    }

    NSLog(@"Loading ShaderEngineMetal from: %@", shaderPath);

    _shaderHandle = dlopen([shaderPath UTF8String], RTLD_NOW | RTLD_LOCAL);
    if (!_shaderHandle) {
        NSLog(@"Failed to load ShaderEngineMetal: %s", dlerror());
        return NO;
    }

    // Get function pointers
    _shaderInit = (FP_Initialize)dlsym(_shaderHandle, "Initialize");
    _shaderLoadRenderer = (FP_LoadRenderer)dlsym(_shaderHandle, "LoadRenderer");
    _shaderNewRenderPath = (FP_NewGRenderPath)dlsym(_shaderHandle, "NewGRenderPath");
    _shaderDeinit = (FP_Deinitialize)dlsym(_shaderHandle, "Deinitialize");

    if (!_shaderInit || !_shaderLoadRenderer || !_shaderNewRenderPath || !_shaderDeinit) {
        NSLog(@"Failed to get shader engine function pointers");
        return NO;
    }

    NSLog(@"ShaderEngineMetal loaded successfully");
    return YES;
}

- (void)applicationDidFinishLaunching:(NSNotification*)notification
{
    _initialized = false;
    _device = nullptr;
    _renderPath = nullptr;
    _shaderHandle = nullptr;

    // Create GraphicsDevice_Metal
    _device = new GraphicsDevice_Metal();
    if (!_device->Initialize(ValidationMode::Disabled, GPUPreference::Discrete)) {
        NSLog(@"Failed to initialize Metal device");
        [NSApp terminate:nil];
        return;
    }
    NSLog(@"Metal device initialized: %s", _device->GetAdapterName().c_str());

    // Load ShaderEngineMetal
    if (![self loadShaderEngine]) {
        NSLog(@"Failed to load shader engine");
        [NSApp terminate:nil];
        return;
    }

    // Create window
    NSRect frame = NSMakeRect(100, 100, 800, 600);
    NSWindowStyleMask style = NSWindowStyleMaskTitled |
                              NSWindowStyleMaskClosable |
                              NSWindowStyleMaskMiniaturizable |
                              NSWindowStyleMaskResizable;

    self.window = [[NSWindow alloc] initWithContentRect:frame
                                              styleMask:style
                                                backing:NSBackingStoreBuffered
                                                  defer:NO];
    [self.window setTitle:@"ShaderEngineMetal Triangle Test"];
    [self.window makeKeyAndOrderFront:nil];

    NSView* contentView = [[NSView alloc] initWithFrame:frame];
    [self.window setContentView:contentView];

    // Create swap chain
    SwapChainDesc swapChainDesc = {};
    swapChainDesc.width = (uint32_t)frame.size.width;
    swapChainDesc.height = (uint32_t)frame.size.height;
    swapChainDesc.buffer_count = 2;
    swapChainDesc.format = Format::B8G8R8A8_UNORM;
    swapChainDesc.vsync = true;
    swapChainDesc.clear_color[0] = 0.1f;
    swapChainDesc.clear_color[1] = 0.1f;
    swapChainDesc.clear_color[2] = 0.2f;
    swapChainDesc.clear_color[3] = 1.0f;

    if (!_device->CreateSwapChain(&swapChainDesc, (__bridge void*)contentView, &_swapChain)) {
        NSLog(@"Failed to create swap chain");
        [NSApp terminate:nil];
        return;
    }
    NSLog(@"SwapChain created: %dx%d", swapChainDesc.width, swapChainDesc.height);

    // Initialize ShaderEngineMetal with our device
    if (!_shaderInit(_device)) {
        NSLog(@"Failed to initialize ShaderEngineMetal");
        [NSApp terminate:nil];
        return;
    }
    NSLog(@"ShaderEngineMetal initialized");

    if (!_shaderLoadRenderer()) {
        NSLog(@"Failed to load renderer");
        [NSApp terminate:nil];
        return;
    }
    NSLog(@"Renderer loaded");

    // Create GRenderPath3D through ShaderEngineMetal
    _renderPath = _shaderNewRenderPath(_swapChain, _rtRenderFinal);
    if (!_renderPath) {
        NSLog(@"Failed to create GRenderPath3D");
        [NSApp terminate:nil];
        return;
    }
    _renderPath->ResizeCanvas(swapChainDesc.width, swapChainDesc.height);
    NSLog(@"GRenderPath3D created and ready for triangle rendering!");

    _initialized = true;

    // Start render timer (60 FPS)
    self.renderTimer = [NSTimer scheduledTimerWithTimeInterval:1.0/60.0
                                                        target:self
                                                      selector:@selector(render)
                                                      userInfo:nil
                                                       repeats:YES];
}

- (void)render
{
    if (!_initialized || !_renderPath)
        return;

    @autoreleasepool {
        float dt = 1.0f / 60.0f;
        _renderPath->Render(dt);
    }
}

- (void)applicationWillTerminate:(NSNotification*)notification
{
    [self.renderTimer invalidate];
    self.renderTimer = nil;

    if (_renderPath) {
        _renderPath->Destroy();
        delete _renderPath;
        _renderPath = nullptr;
    }

    if (_shaderDeinit) {
        _shaderDeinit();
    }

    if (_device) {
        _device->WaitForGPU();
        delete _device;
        _device = nullptr;
    }

    if (_shaderHandle) {
        dlclose(_shaderHandle);
        _shaderHandle = nullptr;
    }

    NSLog(@"Cleanup complete");
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication*)sender
{
    return YES;
}

@end

int main(int argc, const char* argv[])
{
    @autoreleasepool {
        NSApplication* app = [NSApplication sharedApplication];
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];

        AppDelegate* delegate = [[AppDelegate alloc] init];
        [app setDelegate:delegate];

        // Create menu bar
        NSMenu* menubar = [[NSMenu alloc] init];
        NSMenuItem* appMenuItem = [[NSMenuItem alloc] init];
        [menubar addItem:appMenuItem];
        [app setMainMenu:menubar];

        NSMenu* appMenu = [[NSMenu alloc] init];
        NSMenuItem* quitItem = [[NSMenuItem alloc] initWithTitle:@"Quit"
                                                          action:@selector(terminate:)
                                                   keyEquivalent:@"q"];
        [appMenu addItem:quitItem];
        [appMenuItem setSubmenu:appMenu];

        [app activateIgnoringOtherApps:YES];
        [app run];
    }
    return 0;
}
