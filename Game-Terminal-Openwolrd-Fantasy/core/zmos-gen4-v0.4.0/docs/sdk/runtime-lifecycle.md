# SDK Runtime Lifecycle

When you invoke a command via the Z-MOS SDK, the following lifecycle occurs:

1. **Request Reception**: The SDK API (e.g., `verifyWorkspace()`) receives your `workspaceDir` and options.
2. **Environment Isolation**: A new `SpawnSyncOptions` object is built, copying `process.env` but overriding the working directory to precisely match your target workspace.
3. **CLI Invocation**: The Node.js binary executes `bin/zcl.js` with the corresponding command (`preflight`, `sync`, `stabilize`).
4. **Execution & Blocking**: Z-MOS runs its internal handlers. If it encounters a governance violation, it prints the diagnostic tree to `stdout` and throws `process.exit(1)`.
5. **Result Aggregation**: The `spawnSync` wrapper catches the exit. It packages `stdout`, `stderr`, and the `exitCode` into a typed `SdkCommandResult` and returns it to the host process safely.

## Handling Transport Timeouts

By default, all SDK commands have a `30000ms` timeout. If Z-MOS hangs or takes too long, the OS will terminate the child process, and the SDK will return `success: false` with the timeout error, preventing your host from hanging indefinitely.
