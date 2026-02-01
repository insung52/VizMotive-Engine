// Test Metal Backend loading through VizMotive Engine
#include "HighAPIs/VzEngineAPIs.h"
#include "Utils/Backlog.h"
#include <cstdio>

int main(int argc, char* argv[])
{
    printf("=== VizMotive Metal Backend Test ===\n\n");

    // Initialize engine with Metal backend
    vzm::ParamMap<std::string> arguments;
    arguments.SetParam("API", std::string("METAL"));
    arguments.SetParam("ValidationMode", std::string("Disabled"));
    arguments.SetParam("GPUPreference", std::string("Discrete"));

    printf("Initializing engine with METAL backend...\n");

    bool success = vzm::InitEngineLib(arguments);

    if (success)
    {
        printf("SUCCESS: Engine initialized with Metal backend!\n\n");

        // Check log path
        const char* logPath = vz::backlog::GetLogPath();
        if (logPath)
        {
            printf("Log path: %s\n", logPath);
        }

        printf("\nDeinitializing...\n");
        vzm::DeinitEngineLib();
        printf("Done.\n");
    }
    else
    {
        printf("FAILED: Could not initialize engine\n");
        printf("\nMake sure libGBackendMetal.dylib is in the same directory as the executable.\n");
        return 1;
    }

    printf("\n=== Test Completed ===\n");
    return 0;
}
