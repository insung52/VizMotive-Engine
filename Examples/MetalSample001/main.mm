// MetalSample001 - Basic Scene/Camera/Mesh rendering test for Metal backend
// This sample mirrors Sample001's functionality but for macOS/Metal

#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <QuartzCore/CAMetalLayer.h>

// VizMotive High-level APIs (same as Windows samples)
#include "HighAPIs/VzEngineAPIs.h"

@interface MetalView : NSView
@property (nonatomic, strong) CAMetalLayer* metalLayer;
@end

@implementation MetalView

- (instancetype)initWithFrame:(NSRect)frameRect
{
    self = [super initWithFrame:frameRect];
    if (self) {
        self.wantsLayer = YES;
        self.metalLayer = [CAMetalLayer layer];
        self.metalLayer.device = MTLCreateSystemDefaultDevice();
        self.metalLayer.pixelFormat = MTLPixelFormatRGB10A2Unorm;
        self.metalLayer.framebufferOnly = YES;
        self.layer = self.metalLayer;
    }
    return self;
}

- (BOOL)wantsUpdateLayer { return YES; }

- (void)setFrameSize:(NSSize)newSize
{
    [super setFrameSize:newSize];
    CGFloat scale = self.window.backingScaleFactor;
    self.metalLayer.drawableSize = CGSizeMake(newSize.width * scale, newSize.height * scale);
}

@end

@interface AppDelegate : NSObject <NSApplicationDelegate, NSWindowDelegate>
{
    vzm::VzScene* _scene;
    vzm::VzRenderer* _renderer;
    vzm::VzCamera* _camera;
    vzm::VzGeometry* _geometry;
    vzm::VzMaterial* _material;
    vzm::VzActorStaticMesh* _actor;
    vzm::VzLight* _light;

    bool _initialized;
    float _rotationAngle;
}
@property (strong) NSWindow* window;
@property (strong) MetalView* metalView;
@property (strong) NSTimer* renderTimer;
@end

@implementation AppDelegate

- (void)applicationDidFinishLaunching:(NSNotification*)notification
{
    _initialized = false;
    _rotationAngle = 0.0f;

    // Create window
    NSRect frame = NSMakeRect(100, 100, 800, 600);
    NSWindowStyleMask style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                              NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable;

    self.window = [[NSWindow alloc] initWithContentRect:frame
                                              styleMask:style
                                                backing:NSBackingStoreBuffered
                                                  defer:NO];
    [self.window setTitle:@"MetalSample001 - VizMotive Engine"];
    [self.window setDelegate:self];

    // Create Metal view
    self.metalView = [[MetalView alloc] initWithFrame:frame];
    [self.window setContentView:self.metalView];
    [self.window makeKeyAndOrderFront:nil];

    // Initialize VizMotive Engine
    [self initializeEngine];

    // Start render loop (60 FPS)
    self.renderTimer = [NSTimer scheduledTimerWithTimeInterval:1.0/60.0
                                                        target:self
                                                      selector:@selector(renderFrame)
                                                      userInfo:nil
                                                       repeats:YES];
}

- (void)initializeEngine
{
    NSLog(@"Initializing VizMotive Engine...");

    // Get view dimensions
    NSRect bounds = [self.metalView bounds];
    uint32_t width = (uint32_t)bounds.size.width;
    uint32_t height = (uint32_t)bounds.size.height;
    float dpi = (float)[self.window backingScaleFactor] * 96.0f;

    // Initialize engine library with Metal backend
    vzm::ParamMap<std::string> arguments;
    arguments.SetString("API", "METAL");
    if (!vzm::InitEngineLib(arguments)) {
        NSLog(@"ERROR: Failed to initialize VizMotive engine library");
        [NSApp terminate:nil];
        return;
    }
    NSLog(@"Engine library initialized");

    // Create Scene
    _scene = vzm::NewScene("MetalSample001 Scene");
    if (!_scene) {
        NSLog(@"ERROR: Failed to create scene");
        [NSApp terminate:nil];
        return;
    }
    NSLog(@"Scene created: %s", _scene->GetName().c_str());

    // Create Renderer with canvas
    _renderer = vzm::NewRenderer("MetalSample001 Renderer");
    if (!_renderer) {
        NSLog(@"ERROR: Failed to create renderer");
        [NSApp terminate:nil];
        return;
    }
    _renderer->SetCanvas(width, height, dpi, (__bridge void*)self.metalView);
    _renderer->SetClearColor({0.1f, 0.1f, 0.2f, 1.0f});
    _renderer->EnableFrameLock(60.0f);
    NSLog(@"Renderer created: %dx%d", width, height);

    // Create Camera
    _camera = vzm::NewCamera("Main Camera");
    if (!_camera) {
        NSLog(@"ERROR: Failed to create camera");
        [NSApp terminate:nil];
        return;
    }

    vfloat3 eyePos = {0.0f, 0.0f, 5.0f};
    vfloat3 lookAt = {0.0f, 0.0f, -1.0f};  // view direction, not target point
    vfloat3 upVec = {0.0f, 1.0f, 0.0f};
    _camera->SetWorldPose(eyePos, lookAt, upVec);
    _camera->SetPerspectiveProjection(0.1f, 100.0f, 45.0f, (float)width / (float)height);
    NSLog(@"Camera created and configured");

    // Create Geometry (test triangle)
    _geometry = vzm::NewGeometry("Test Geometry");
    if (!_geometry) {
        NSLog(@"ERROR: Failed to create geometry");
        [NSApp terminate:nil];
        return;
    }
    _geometry->MakeTestTriangle();
    NSLog(@"Geometry created: triangle with %zu parts", _geometry->GetNumParts());

    // Create Material
    _material = vzm::NewMaterial("Test Material");
    if (!_material) {
        NSLog(@"ERROR: Failed to create material");
        [NSApp terminate:nil];
        return;
    }
    _material->SetShaderType(vzm::ShaderType::PBR);
    _material->SetBaseColor({0.8f, 0.2f, 0.2f, 1.0f});  // Red color
    _material->SetDoubleSided(true);
    NSLog(@"Material created: PBR with red base color");

    // Create Actor (mesh instance)
    _actor = vzm::NewActorStaticMesh("Test Actor", _geometry->GetVID(), _material->GetVID());
    if (!_actor) {
        NSLog(@"ERROR: Failed to create actor");
        [NSApp terminate:nil];
        return;
    }
    _actor->SetScale({1.0f, 1.0f, 1.0f});
    _actor->SetPosition({0.0f, 0.0f, 0.0f});
    NSLog(@"Actor created");

    // Create Light
    _light = vzm::NewLight("Main Light");
    if (!_light) {
        NSLog(@"ERROR: Failed to create light");
        [NSApp terminate:nil];
        return;
    }
    _light->SetIntensity(5.0f);
    _light->SetPosition({3.0f, 3.0f, 3.0f});
    NSLog(@"Light created");

    // Add components to scene
    vzm::AppendSceneCompTo(_actor, _scene);
    vzm::AppendSceneCompTo(_light, _scene);
    NSLog(@"Components added to scene");

    _initialized = true;
    NSLog(@"VizMotive Engine initialization complete!");
}

- (void)renderFrame
{
    if (!_initialized || !_renderer || !_scene || !_camera)
        return;

    @autoreleasepool {
        // Rotate the actor
        _rotationAngle += 0.5f;
        if (_rotationAngle >= 360.0f) _rotationAngle -= 360.0f;

        vfloat3 rotation = {0.0f, _rotationAngle, 0.0f};
        _actor->SetEulerAngleZXYInDegree(rotation);

        // Render frame
        float dt = 1.0f / 60.0f;
        _renderer->Render(_scene, _camera, dt);
    }
}

- (void)windowWillClose:(NSNotification*)notification
{
    [self.renderTimer invalidate];
    self.renderTimer = nil;

    _initialized = false;

    // Cleanup VizMotive Engine
    NSLog(@"Cleaning up VizMotive Engine...");

    // Remove components (order matters)
    if (_actor) vzm::RemoveComponent(_actor);
    if (_light) vzm::RemoveComponent(_light);
    if (_camera) vzm::RemoveComponent(_camera);
    if (_geometry) vzm::RemoveComponent(_geometry);
    if (_material) vzm::RemoveComponent(_material);
    if (_scene) vzm::RemoveComponent(_scene);
    if (_renderer) vzm::RemoveComponent(_renderer);

    vzm::DeinitEngineLib();

    NSLog(@"Cleanup complete");
    [NSApp terminate:nil];
}

- (void)windowDidResize:(NSNotification*)notification
{
    if (!_initialized || !_renderer || !_camera)
        return;

    NSRect bounds = [self.metalView bounds];
    uint32_t width = (uint32_t)bounds.size.width;
    uint32_t height = (uint32_t)bounds.size.height;

    if (width > 0 && height > 0) {
        _renderer->ResizeCanvas(width, height);
        _camera->SetPerspectiveProjection(0.1f, 100.0f, 45.0f, (float)width / (float)height);
    }
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
        NSMenu* menuBar = [[NSMenu alloc] init];
        NSMenuItem* appMenuItem = [[NSMenuItem alloc] init];
        [menuBar addItem:appMenuItem];
        [app setMainMenu:menuBar];

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
