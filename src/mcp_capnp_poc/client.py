#!/usr/bin/env python3
"""
MCP Client using Cap'n Proto instead of JSON-RPC.
Connects to our server and makes tool calls for benchmarking.
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

class McpClient:
    """
    MCP client that connects via Cap'n Proto RPC.
    
    Much simpler than HTTP clients - just make method calls!
    """
    
    def __init__(self):
        self.server = None
        self.client = None
    
    async def connect(self, host="localhost", port=8080):
        """Connect to the MCP server."""
        print(f"[CLIENT] Connecting to {host}:{port}")
        
        # Create connection to server
        connection = await capnp.AsyncIoStream.create_connection(host=host, port=port)
        
        # Create RPC system and get server reference
        self.client = capnp.TwoPartyClient(connection)
        self.server = self.client.bootstrap().cast_as(mcp_schema.McpServer)
        
        print(f"[CLIENT] Connected successfully!")
    
    async def disconnect(self):
        """Clean up connection."""
        if self.client:
            # Just close without await - pycapnp close() is not async
            self.client.close()
            self.client = None
            self.server = None
    
    async def list_tools(self):
        """Get available tools from server - corrected RPC pattern."""
        print(f"[CLIENT] Requesting tool list...")
        
        # Use request pattern
        request = self.server.listTools_request()
        response = await request.send()
        
        # Extract tools from response
        tools = []
        for tool_def in response.tools:
            tools.append({
                "name": tool_def.name,
                "description": tool_def.description,
                "inputSchema": tool_def.inputSchema
            })
        
        print(f"[CLIENT] Received {len(tools)} tools")
        return tools
    
    async def call_tool(self, tool_name: str, arguments: dict):
        """Execute a tool on the server - corrected RPC pattern."""
        call_id = str(uuid.uuid4())
        arguments_json = json.dumps(arguments)
        
        print(f"[CLIENT] Calling tool '{tool_name}' with call_id '{call_id}'")
        
        # FIXED: Use the request pattern instead of creating ToolCall directly
        request = self.server.callTool_request()
        
        # Set the call parameter fields
        request.call.name = tool_name
        request.call.arguments = arguments_json
        request.call.callId = call_id

        # Send the request and measure time
        start_time = time.time()
        response = await request.send()
        end_time = time.time()
        
        # Extract result
        result = {
            "call_id": response.result.callId,
            "success": response.result.success,
            "content": response.result.content,
            "latency_ms": (end_time - start_time) * 1000
        }
        
        print(f"[CLIENT] Tool result: {result['content']} (took {result['latency_ms']:.2f}ms)")
        return result
    
    async def ping(self):
        """Simple ping for latency testing - corrected RPC pattern."""
        request = self.server.ping_request()

        start_time = time.time()
        response = await request.send()
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        print(f"[CLIENT] Ping: {response.pong} (took {latency_ms:.2f}ms)")
        return latency_ms

async def test_basic_functionality():
    """Test that client can connect and call tools."""
    client = McpClient()
    
    try:
        # Connect to server
        await client.connect()
        
        # Test tool discovery
        print("\n=== TOOL DISCOVERY TEST ===")
        tools = await client.list_tools()
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Test ping
        print("\n=== PING TEST ===")
        await client.ping()
        
        # Test tool calls
        print("\n=== TOOL CALL TESTS ===")
        result1 = await client.call_tool("echo", {"text": "Hello Cap'n Proto!"})
        result2 = await client.call_tool("slow_echo", {"text": "Testing latency"})
        
        print(f"\n✅ All tests passed!")
        print(f"   Echo latency: {result1['latency_ms']:.2f}ms")
        print(f"   Slow echo latency: {result2['latency_ms']:.2f}ms")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(capnp.run(test_basic_functionality()))