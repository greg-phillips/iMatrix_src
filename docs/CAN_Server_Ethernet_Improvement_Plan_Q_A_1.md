1. Configuration Persistence & Initialization
The source code file can_process.c handles the setup and restarting of the the CAN Server.
When the device boots for the first time, should the eth0 IP be dynamically read and saved to config, or should it query eth0 on every server start?
query eth0 on every server start.
2. Memory Allocation Strategy
The plan changes rx_buf from stack allocation to malloc(). Should I use imx_malloc() instead (as per iMatrix conventions in the System Reference)?
Yes
Same question for the rate limiting and other dynamic buffers?
Yes
3. Frame Validation Scope
Not part of the servers responisibily. The CAN Processing code handles all exceptions.
Where should CLI commands be registered? 
None- CLI is indepedant. Do not extend scope.
5. Testing Environment
ALready handled. DO not extend scope.
6. Backward Compatibility Verification
No backward compatibilty. Do not extend scope.
7. Build System
Should new files be added to iMatrix/CMakeLists.txt or Fleet-Connect-1/CMakeLists.txt?
yes.
The System Reference shows can_server.c in the iMatrix submodule - should all changes stay there?
yes.
8. Implementation Priority
Critical first
take incremental approach
9. Statistics Structure Location
Keep separate statistics for CAN data
10. Error Handling Philosophy
When rate limiting drops frames, validation fails, or timeouts occur - should these be:
Silent, just increment counters.
Logged only when debugging is enabled
