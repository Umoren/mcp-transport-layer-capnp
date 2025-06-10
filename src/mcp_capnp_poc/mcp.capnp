@0xbb4471d26387f4ba;

# Tool definition - what the server can do
struct ToolDef {
  name @0 :Text;           # "echo", "create_issue", etc
  description @1 :Text;    # Human readable description  
  inputSchema @2 :Text;    # JSON Schema as string (for compatibility)
}

# Tool call request - when client wants to execute something
struct ToolCall {
  name @0 :Text;           # Which tool to call
  arguments @1 :Text;      # JSON arguments (keeping compatibility for now)
  callId @2 :Text;         # Unique ID to match responses
}

# Tool execution result
struct ToolResult {
  callId @0 :Text;         # Matches the ToolCall.callId
  success @1 :Bool;        # Did it work?
  content @2 :Text;        # Result data or error message
}

# The main server interface - this is what clients connect to
interface McpServer {
  # Discovery: what tools are available?
  listTools @0 () -> (tools :List(ToolDef));
  
  # Execution: run a tool and get result  
  callTool @1 (call :ToolCall) -> (result :ToolResult);
  
  # Health check for benchmarking
  ping @2 () -> (pong :Text);
}
