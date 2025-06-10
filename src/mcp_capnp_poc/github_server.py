#!/usr/bin/env python3
"""
GitHub MCP Server using Cap'n Proto.
Direct replacement for JSON-RPC GitHub server for benchmarking.
"""

import asyncio
import capnp
import os
import aiohttp
import json
from pathlib import Path

# Load GitHub schema
SCHEMA_PATH = Path(__file__).parent / "github_mcp.capnp"
github_schema = capnp.load(str(SCHEMA_PATH))

class GitHubMcpServerImpl(github_schema.GitHubMcpServer.Server):
    """GitHub MCP server using Cap'n Proto transport."""
    
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_repo = os.getenv('GITHUB_REPO')
        
        if not self.github_token or not self.github_repo:
            raise ValueError("GITHUB_TOKEN and GITHUB_REPO environment variables required")
        
        self.base_url = "https://api.github.com"
        self.repo_url = f"{self.base_url}/repos/{self.github_repo}"
        
        print(f"[GITHUB_SERVER] Initialized for repo: {self.github_repo}")
    
    async def createIssue_context(self, context, **kwargs):
        """Create GitHub issue via API."""
        request = context.params.request
        title = request.title
        body = request.body
        
        print(f"[GITHUB_SERVER] Creating issue: '{title}'")
        
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
                    raise Exception(f"GitHub API error: {response.status}")
                
                issue_data = await response.json()
                
                # Convert to Cap'n Proto struct
                issue = self._create_github_issue(issue_data)
                context.results.issue = issue
    
    async def listIssues_context(self, context, **kwargs):
        """List GitHub issues."""
        request = context.params.request
        state = request.state if request.state else "open"
        limit = request.limit if request.limit else 30
        
        print(f"[GITHUB_SERVER] Listing {state} issues (limit: {limit})")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            params = {
                'state': state,
                'per_page': min(limit, 100)  # GitHub API limit
            }
            
            async with session.get(f"{self.repo_url}/issues", 
                                 headers=headers, 
                                 params=params) as response:
                if response.status != 200:
                    raise Exception(f"GitHub API error: {response.status}")
                
                issues_data = await response.json()
                
                # Convert to Cap'n Proto structs
                issues_list = []
                for issue_data in issues_data:
                    issue = self._create_github_issue(issue_data)
                    issues_list.append(issue)

                context.results.issues = issues_list
    
    async def getIssue_context(self, context, **kwargs):
        """Get specific GitHub issue."""
        request = context.params.request
        number = request.number
        
        print(f"[GITHUB_SERVER] Getting issue #{number}")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            async with session.get(f"{self.repo_url}/issues/{number}",
                                 headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"GitHub API error: {response.status}")
                
                issue_data = await response.json()
                
                # Convert to Cap'n Proto struct
                issue = self._create_github_issue(issue_data)
                context.results.issue = issue
    
    async def ping_context(self, context, **kwargs):
        """Health check."""
        context.results.pong = f"GitHub MCP Server - {self.github_repo}"

    def _create_github_issue(self, issue_data):
        """Convert GitHub API response to Cap'n Proto GitHubIssue."""
        issue = github_schema.GitHubIssue.new_message()
        issue.number = issue_data['number']
        issue.title = issue_data['title']
        issue.body = issue_data.get('body', '') or ''
        issue.state = issue_data['state']
        issue.url = issue_data['html_url']
        issue.createdAt = issue_data['created_at']
        issue.updatedAt = issue_data['updated_at']
        return issue

async def new_connection(connection):
    """Handle new client connection."""
    print(f"[GITHUB_SERVER] New client connected")
    
    server_impl = GitHubMcpServerImpl()
    
    try:
        await capnp.TwoPartyServer(connection, bootstrap=server_impl).on_disconnect()
    except Exception as e:
        print(f"[GITHUB_SERVER] Connection error: {e}")
    finally:
        print(f"[GITHUB_SERVER] Client disconnected")

async def run_server(port=8080):
    """Start the GitHub Cap'n Proto server."""
    print(f"[GITHUB_SERVER] Starting GitHub MCP Cap'n Proto server on port {port}")
    
    server = await capnp.AsyncIoStream.create_server(
        new_connection, 'localhost', port
    )
    
    print(f"[GITHUB_SERVER] Ready! Connect to localhost:{port}")
    
    try:
        async with server:
            await server.serve_forever()
    except KeyboardInterrupt:
        print("[GITHUB_SERVER] Shutting down...")

if __name__ == "__main__":
    asyncio.run(capnp.run(run_server()))