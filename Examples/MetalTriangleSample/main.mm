// MetalTriangleSample - Basic triangle rendering test for Metal backend
// This sample creates a window and renders a colored triangle using the GBackendMetal library

#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <QuartzCore/CAMetalLayer.h>

#include "GraphicsDevice_Metal.h"

using namespace vz::graphics;

// Vertex structure: position (x, y) and color (r, g, b)
struct Vertex
{
    float position[2];
    float color[3];
};

// Metal Shading Language (MSL) shader source
static const char* g_ShaderSource = R"(
#include <metal_stdlib>
using namespace metal;

struct VertexIn
{
    float2 position [[attribute(0)]];
    float3 color    [[attribute(1)]];
};

struct VertexOut
{
    float4 position [[position]];
    float3 color;
};

vertex VertexOut vertexMain(VertexIn in [[stage_in]])
{
    VertexOut out;
    out.position = float4(in.position, 0.0, 1.0);
    out.color = in.color;
    return out;
}

fragment float4 fragmentMain(VertexOut in [[stage_in]])
{
    return float4(in.color, 1.0);
}
)";

// Application delegate
@interface AppDelegate : NSObject <NSApplicationDelegate>
{
@public
    // Graphics resources as instance variables (not properties)
    GraphicsDevice_Metal* _device;
    SwapChain _swapChain;
    GPUBuffer _vertexBuffer;
    Shader _vertexShader;
    Shader _pixelShader;
    PipelineState _pipelineState;
    bool _initialized;
}
@property (strong) NSWindow* window;
@property (strong) NSTimer* renderTimer;
@end

@implementation AppDelegate

- (void)applicationDidFinishLaunching:(NSNotification*)notification
{
    _initialized = false;
    _device = nullptr;

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
    [self.window setTitle:@"Metal Triangle Sample"];
    [self.window makeKeyAndOrderFront:nil];

    // Create content view
    NSView* contentView = [[NSView alloc] initWithFrame:frame];
    [self.window setContentView:contentView];

    // Initialize graphics device
    _device = new GraphicsDevice_Metal();
    if (!_device->Initialize(ValidationMode::Disabled, GPUPreference::Discrete))
    {
        NSLog(@"Failed to initialize Metal device");
        [NSApp terminate:nil];
        return;
    }

    NSLog(@"Metal device initialized: %s", _device->GetAdapterName().c_str());

    // Create swap chain
    SwapChainDesc swapChainDesc = {};
    swapChainDesc.width = (uint32_t)frame.size.width;
    swapChainDesc.height = (uint32_t)frame.size.height;
    swapChainDesc.buffer_count = 2;
    swapChainDesc.format = Format::B8G8R8A8_UNORM;
    swapChainDesc.vsync = true;
    swapChainDesc.clear_color[0] = 0.2f;
    swapChainDesc.clear_color[1] = 0.2f;
    swapChainDesc.clear_color[2] = 0.3f;
    swapChainDesc.clear_color[3] = 1.0f;

    if (!_device->CreateSwapChain(&swapChainDesc, (__bridge void*)contentView, &_swapChain))
    {
        NSLog(@"Failed to create swap chain");
        [NSApp terminate:nil];
        return;
    }

    // Create vertex buffer with triangle data
    // Triangle vertices: top (red), bottom-left (green), bottom-right (blue)
    Vertex vertices[] = {
        { {  0.0f,  0.5f }, { 1.0f, 0.0f, 0.0f } },  // Top - Red
        { { -0.5f, -0.5f }, { 0.0f, 1.0f, 0.0f } },  // Bottom Left - Green
        { {  0.5f, -0.5f }, { 0.0f, 0.0f, 1.0f } },  // Bottom Right - Blue
    };

    GPUBufferDesc bufferDesc = {};
    bufferDesc.size = sizeof(vertices);
    bufferDesc.usage = Usage::UPLOAD;
    bufferDesc.bind_flags = BindFlag::VERTEX_BUFFER;

    if (!_device->CreateBuffer(&bufferDesc, vertices, &_vertexBuffer))
    {
        NSLog(@"Failed to create vertex buffer");
        [NSApp terminate:nil];
        return;
    }

    // Create shaders
    if (!_device->CreateShader(ShaderStage::VS, g_ShaderSource, strlen(g_ShaderSource), &_vertexShader))
    {
        NSLog(@"Failed to create vertex shader");
        [NSApp terminate:nil];
        return;
    }

    if (!_device->CreateShader(ShaderStage::PS, g_ShaderSource, strlen(g_ShaderSource), &_pixelShader))
    {
        NSLog(@"Failed to create pixel shader");
        [NSApp terminate:nil];
        return;
    }

    // Create input layout
    InputLayout inputLayout;
    inputLayout.elements.resize(2);

    // Position attribute
    inputLayout.elements[0].semantic_name = "POSITION";
    inputLayout.elements[0].semantic_index = 0;
    inputLayout.elements[0].format = Format::R32G32_FLOAT;
    inputLayout.elements[0].input_slot = 0;
    inputLayout.elements[0].aligned_byte_offset = offsetof(Vertex, position);

    // Color attribute
    inputLayout.elements[1].semantic_name = "COLOR";
    inputLayout.elements[1].semantic_index = 0;
    inputLayout.elements[1].format = Format::R32G32B32_FLOAT;
    inputLayout.elements[1].input_slot = 0;
    inputLayout.elements[1].aligned_byte_offset = offsetof(Vertex, color);

    // Create pipeline state
    RenderPassInfo renderPassInfo = {};
    renderPassInfo.rt_count = 1;
    renderPassInfo.rt_formats[0] = Format::B8G8R8A8_UNORM;
    renderPassInfo.sample_count = 1;

    PipelineStateDesc psoDesc = {};
    psoDesc.vs = &_vertexShader;
    psoDesc.ps = &_pixelShader;
    psoDesc.il = &inputLayout;
    psoDesc.pt = PrimitiveTopology::TRIANGLELIST;

    if (!_device->CreatePipelineState(&psoDesc, &_pipelineState, &renderPassInfo))
    {
        NSLog(@"Failed to create pipeline state");
        [NSApp terminate:nil];
        return;
    }

    _initialized = true;
    NSLog(@"Graphics initialization complete");

    // Start render timer (60 FPS)
    self.renderTimer = [NSTimer scheduledTimerWithTimeInterval:1.0/60.0
                                                        target:self
                                                      selector:@selector(render)
                                                      userInfo:nil
                                                       repeats:YES];
}

- (void)render
{
    if (!_initialized)
        return;

    @autoreleasepool
    {
        // Begin command list
        CommandList cmd = _device->BeginCommandList(QUEUE_GRAPHICS);

        // Begin render pass with swap chain
        _device->RenderPassBegin(&_swapChain, cmd);

        // Set viewport
        Viewport viewport = {};
        viewport.width = (float)_swapChain.desc.width;
        viewport.height = (float)_swapChain.desc.height;
        viewport.min_depth = 0.0f;
        viewport.max_depth = 1.0f;
        _device->BindViewports(1, &viewport, cmd);

        // Set scissor rect
        vz::graphics::Rect scissorRect = {};
        scissorRect.right = _swapChain.desc.width;
        scissorRect.bottom = _swapChain.desc.height;
        _device->BindScissorRects(1, &scissorRect, cmd);

        // Bind pipeline
        _device->BindPipelineState(&_pipelineState, cmd);

        // Bind vertex buffer
        const GPUBuffer* vertexBuffers[] = { &_vertexBuffer };
        uint32_t strides[] = { sizeof(Vertex) };
        uint64_t offsets[] = { 0 };
        _device->BindVertexBuffers(vertexBuffers, 0, 1, strides, offsets, cmd);

        // Draw triangle
        _device->Draw(3, 0, cmd);

        // End render pass
        _device->RenderPassEnd(cmd);

        // Submit command lists and present
        _device->SubmitCommandLists();
    }
}

- (void)applicationWillTerminate:(NSNotification*)notification
{
    [self.renderTimer invalidate];
    self.renderTimer = nil;

    if (_device)
    {
        _device->WaitForGPU();
        delete _device;
        _device = nullptr;
    }
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication*)sender
{
    return YES;
}

@end

int main(int argc, const char* argv[])
{
    @autoreleasepool
    {
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
