#!/usr/bin/env python3
"""
Simple HTTP-based GitHub MCP server for benchmarking.
Provides the same GitHub operations as the stdio version.
"""

import asyncio
import aiohttp
import json
import os
from aiohttp import web

class GitHubHttpMcpServer:
    """Simple HTTP MCP server that mimics GitHub operations."""
    
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_repo = os.getenv('GITHUB_REPO')
        
        if not self.github_token or not self.github_repo:
            raise ValueError("GITHUB_TOKEN and GITHUB_REPO environment variables required")
        
        self.base_url = "https://api.github.com"
        self.repo_url = f"{self.base_url}/repos/{self.github_repo}"
        
        print(f"[HTTP_SERVER] Initialized for repo: {self.github_repo}")
    
    async def handle_jsonrpc(self, request):
        """Handle JSON-RPC requests."""
        try:
            data = await request.json()
            
            method = data.get('method')
            params = data.get('params', {})
            request_id = data.get('id')
            
            if method == 'tools/call':
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                
                if tool_name == 'create_github_issue':
                    result = await self._create_issue(arguments)
                elif tool_name == 'list_github_issues':
                    result = await self._list_issues(arguments)
                elif tool_name == 'get_github_issue':
                    result = await self._get_issue(arguments)
                else:
                    raise ValueError(f"Unknown tool: {tool_name}")
                
                return web.json_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                })
            
            elif method == 'tools/list':
                return web.json_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "create_github_issue",
                                "description": "Create a new GitHub issue",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "body": {"type": "string"}
                                    },
                                    "required": ["title"]
                                }
                            },
                            {
                                "name": "list_github_issues",
                                "description": "List GitHub issues",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "state": {"type": "string"}
                                    }
                                }
                            },
                            {
                                "name": "get_github_issue",
                                "description": "Get a specific GitHub issue",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "issue_number": {"type": "number"}
                                    },
                                    "required": ["issue_number"]
                                }
                            }
                        ]
                    }
                })
            
            else:
                raise ValueError(f"Unknown method: {method}")
                
        except Exception as e:
            return web.json_response({
                "jsonrpc": "2.0",
                "id": data.get('id') if 'data' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }, status=500)
    
    async def _create_issue(self, arguments):
        """Create GitHub issue via API."""
        title = arguments.get('title')
        body = arguments.get('body', '')
        
        print(f"[HTTP_SERVER] Creating issue: '{title}'")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'title': title,
                'body': body
            }
            
            async with session.post(f"{self.repo_url}/issues", 
                                  headers=headers, 
                                  json=payload) as response:
                if response.status != 201:
                    error_text = await response.text()
                    raise Exception(f"GitHub API error: {response.status} - {error_text}")
                
                issue_data = await response.json()
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Created issue #{issue_data['number']}: {issue_data['title']}"
                        }
                    ]
                }
    
    async def _list_issues(self, arguments):
        """List GitHub issues."""
        state = arguments.get('state', 'open')
        
        print(f"[HTTP_SERVER] Listing {state} issues")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            params = {
                'state': state,
                'per_page': 30
            }
            
            async with session.get(f"{self.repo_url}/issues", 
                                 headers=headers, 
                                 params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"GitHub API error: {response.status} - {error_text}")
                
                issues_data = await response.json()
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Found {len(issues_data)} issues"
                        }
                    ]
                }
    
    async def _get_issue(self, arguments):
        """Get specific GitHub issue."""
        issue_number = arguments.get('issue_number')
        
        print(f"[HTTP_SERVER] Getting issue #{issue_number}")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            async with session.get(f"{self.repo_url}/issues/{issue_number}", 
                                 headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"GitHub API error: {response.status} - {error_text}")
                
                issue_data = await response.json()
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Issue #{issue_data['number']}: {issue_data['title']}"
                        }
                    ]
                }
    
    async def health(self, request):
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": "github-http-mcp-server",
            "repo": self.github_repo
        })

async def main():
    """Start the HTTP server."""
    server = GitHubHttpMcpServer()
    
    app = web.Application()
    app.router.add_post('/', server.handle_jsonrpc)
    app.router.add_get('/health', server.health)
    
    print("[HTTP_SERVER] Starting GitHub HTTP MCP server on port 8001")
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, 'localhost', 8001)
    await site.start()
    
    print("[HTTP_SERVER] Server ready at http://localhost:8001")
    print("[HTTP_SERVER] Press Ctrl+C to stop")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("[HTTP_SERVER] Shutting down...")
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())