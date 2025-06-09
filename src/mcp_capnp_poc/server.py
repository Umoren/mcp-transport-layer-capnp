#!/usr/bin/env python3
"""
MCP Server using Cap'n Proto instead of JSON-RPC.
Using correct pycapnp asyncio integration patterns.
"""

import asyncio
import capnp
import json
import time
import uuid
from pathlib import Path

# Load our schema
SCHEMA_PATH = Path(__file__).parent / "mcp.capnp"
mcp_schema = capnp.load(str(SCHEMA_PATH))

class McpServerImpl(mcp_schema.McpServer.Server):
    """Implementation following correct pycapnp patterns."""
    
    def __init__(self):
        self.tools = [
            {
                "name": "echo",
                "description": "Echo back the input text",
                "inputSchema": json.dumps({
                    "type": "object", 
                    "properties": {"text": {"type": "string"}}
                })
            },
            {
                "name": "slow_echo", 
                "description": "Echo with 100ms delay (for testing)",
                "inputSchema": json.dumps({
                    "type": "object", 
                    "properties": {"text": {"type": "string"}}
                })
            }
        ]
        print(f"[SERVER] Initialized with {len(self.tools)} tools")
    
    async def listTools_context(self, context, **kwargs):
        """Return available tools using context."""
        print(f"[SERVER] Client requesting tool list")
        
        # Create a list of ToolDef messages
        tools_list = []
        for tool in self.tools:
            tool_msg = mcp_schema.ToolDef.new_message()
            tool_msg.name = tool['name']
            tool_msg.description = tool['description']
            tool_msg.inputSchema = tool['inputSchema']
            tools_list.append(tool_msg)
        
        print(f"[SERVER] Returning {len(tools_list)} tools")

        # Set result through context
        context.results.tools = tools_list

    async def callTool_context(self, context, **kwargs):
        """Execute a tool call using context-based parameter access."""
        # Access parameters through context
        params = context.params
        call = params.call

        tool_name = call.name
        arguments_json = call.arguments
        call_id = call.callId
        
        print(f"[SERVER] Executing '{tool_name}' with call_id '{call_id}'")

        try:
            arguments = json.loads(arguments_json)
        except json.JSONDecodeError:
            result = self._create_tool_result(call_id, False, "Error: Invalid JSON arguments")
            context.results.result = result
            return
        
        # Route to handlers
        if tool_name == "echo":
            result = await self._handle_echo(call_id, arguments)
        elif tool_name == "slow_echo":
            result = await self._handle_slow_echo(call_id, arguments)
        else:
            result = self._create_tool_result(call_id, False, f"Error: Unknown tool: {tool_name}")

        # Set the result through context
        context.results.result = result
    
    async def ping_context(self, context, **kwargs):
        """Health check using context."""
        context.results.pong = "pong"

    def _create_tool_result(self, call_id: str, success: bool, content: str):
        """Helper to create proper ToolResult messages."""
        result = mcp_schema.ToolResult.new_message()
        result.callId = call_id
        result.success = success
        result.content = content
        return result

    async def _handle_echo(self, call_id: str, arguments: dict):
        """Handle echo tool - return proper ToolResult."""
        text = arguments.get("text", "")
        result_text = f"Echo: {text}"

        print(f"[SERVER] Echo result: {result_text}")
        return self._create_tool_result(call_id, True, result_text)

    async def _handle_slow_echo(self, call_id: str, arguments: dict):
        """Handle slow echo tool - return proper ToolResult."""
        text = arguments.get("text", "")
        await asyncio.sleep(0.1)  # 100ms delay

        result_text = f"Slow Echo: {text}"

        print(f"[SERVER] Slow echo result: {result_text}")
        return self._create_tool_result(call_id, True, result_text)

async def new_connection(connection):
    """Handle a new client connection - correct pycapnp pattern."""
    print(f"[SERVER] New client connected")

    # Create server instance for this connection
    server_impl = McpServerImpl()
    
    try:
        # Handle the connection with TwoPartyServer
        await capnp.TwoPartyServer(connection, bootstrap=server_impl).on_disconnect()
    except Exception as e:
        print(f"[SERVER] Connection error: {e}")
    finally:
        print(f"[SERVER] Client disconnected")

async def run_server(port=8080):
    """Start the Cap'n Proto RPC server using correct pycapnp patterns."""
    print(f"[SERVER] Starting MCP Cap'n Proto server on port {port}")
    
    # Use pycapnp's AsyncIoStream.create_server - handles KJ integration automatically
    server = await capnp.AsyncIoStream.create_server(
        new_connection, 'localhost', port
    )
    
    print(f"[SERVER] Server ready! Clients can connect to localhost:{port}")
    
    # Keep server running
    try:
        async with server:
            await server.serve_forever()
    except KeyboardInterrupt:
        print("[SERVER] Shutting down...")

if __name__ == "__main__":
    # KEY FIX: Use capnp.run() instead of asyncio.run()
    # This automatically handles the KJ event loop integration
    asyncio.run(capnp.run(run_server()))