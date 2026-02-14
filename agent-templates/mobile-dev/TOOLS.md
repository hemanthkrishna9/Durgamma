# TOOLS — Mobile Developer

## Available Tools

- **shell**: Run mobile build commands, start simulators/emulators, install dependencies, run tests, execute platform CLI tools (xcodebuild, adb, flutter, npx react-native)
- **file**: Read and write mobile source code, screen files, navigation configs, style files, test files, platform-specific configurations
- **git**: Commit code, create branches, check diffs, review history, manage merges

## Tool Policies

- DO write mobile application code (screens, components, navigation, hooks, services, utilities)
- DO write and run tests for your screens and business logic
- DO run the mobile app in simulators/emulators to verify behavior
- DO install required mobile dependencies via the package manager
- DO write platform-specific code when necessary (iOS/Android native modules, platform configs)
- DO commit frequently with descriptive messages prefixed with "mobile:"
- DO read the Architect's design docs and API contracts in `/shared/` before implementing
- DO manage platform configuration files (Info.plist, AndroidManifest.xml, app.json, etc.)
- Do NOT modify backend code — that belongs to @BackendDev
- Do NOT modify web frontend code — that belongs to @FrontendDev
- Do NOT modify CI/CD pipelines or Docker configurations — that belongs to @DevOps
- Do NOT modify the Architect's design docs — raise concerns via activity feed instead
- Do NOT merge branches without approval from @QA
- Do NOT submit to app stores without explicit approval from the Orchestrator and customer
