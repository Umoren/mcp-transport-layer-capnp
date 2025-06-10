#!/usr/bin/env python3
"""
Benchmark comparing JSON-RPC vs Cap'n Proto GitHub servers.
"""

import asyncio
import capnp
import aiohttp
import json
import time
import statistics
from pathlib import Path
from dataclasses import dataclass
from typing import List

# Load GitHub schema
SCHEMA_PATH = Path(__file__).parent / "github_mcp.capnp"
github_schema = capnp.load(str(SCHEMA_PATH))

@dataclass
class BenchmarkResult:
    operation: str
    transport: str
    latency_ms: float
    success: bool
    data_size: int = 0

class CapnProtoGitHubClient:
    """Cap'n Proto client for GitHub operations."""
    
    def __init__(self):
        self.server = None
        self.client = None
    
    async def connect(self, host="localhost", port=8080):
        connection = await capnp.AsyncIoStream.create_connection(host=host, port=port)
        self.client = capnp.TwoPartyClient(connection)
        self.server = self.client.bootstrap().cast_as(github_schema.GitHubMcpServer)
    
    async def disconnect(self):
        if self.client:
            self.client.close()
    
    async def create_issue(self, title: str, body: str) -> BenchmarkResult:
        request = self.server.createIssue_request()
        request.request.title = title
        request.request.body = body
        
        start_time = time.time()
        response = await request.send()
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        return BenchmarkResult(
            operation="create_issue",
            transport="capnp",
            latency_ms=latency_ms,
            success=True,
            data_size=len(title) + len(body)
        )
    
    async def list_issues(self, state="open", limit=30) -> BenchmarkResult:
        request = self.server.listIssues_request()
        request.request.state = state
        request.request.limit = limit
        
        start_time = time.time()
        response = await request.send()
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        return BenchmarkResult(
            operation="list_issues",
            transport="capnp",
            latency_ms=latency_ms,
            success=True,
            data_size=len(response.issues)
        )
    
    async def get_issue(self, number: int) -> BenchmarkResult:
        request = self.server.getIssue_request()
        request.request.number = number
        
        start_time = time.time()
        response = await request.send()
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        return BenchmarkResult(
            operation="get_issue",
            transport="capnp",
            latency_ms=latency_ms,
            success=True,
            data_size=len(response.issue.title) + len(response.issue.body)
        )

class JsonRpcGitHubClient:
    """JSON-RPC client for comparison with existing server."""
    
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.session = None
    
    async def connect(self):
        self.session = aiohttp.ClientSession()
        
        # Test health endpoint
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status != 200:
                    raise Exception("JSON-RPC server not responding")
        except Exception as e:
            raise Exception(f"Cannot connect to JSON-RPC server: {e}")
    
    async def disconnect(self):
        if self.session:
            await self.session.close()
    
    async def create_issue(self, title: str, body: str) -> BenchmarkResult:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "create_github_issue",
                "arguments": {
                    "title": title,
                    "body": body
                }
            }
        }
        
        start_time = time.time()
        async with self.session.post(f"{self.base_url}/", json=payload) as response:
            result = await response.json()
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        return BenchmarkResult(
            operation="create_issue",
            transport="jsonrpc",
            latency_ms=latency_ms,
            success=response.status == 200 and "error" not in result,
            data_size=len(title) + len(body)
        )
    
    async def list_issues(self, state="open", limit=30) -> BenchmarkResult:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "list_github_issues",
                "arguments": {
                    "state": state
                }
            }
        }
        
        start_time = time.time()
        async with self.session.post(f"{self.base_url}/", json=payload) as response:
            result = await response.json()
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        return BenchmarkResult(
            operation="list_issues",
            transport="jsonrpc",
            latency_ms=latency_ms,
            success=response.status == 200 and "error" not in result,
            data_size=len(str(result))
        )
    
    async def get_issue(self, number: int) -> BenchmarkResult:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_github_issue",
                "arguments": {
                    "number": number
                }
            }
        }
        
        start_time = time.time()
        async with self.session.post(f"{self.base_url}/", json=payload) as response:
            result = await response.json()
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        return BenchmarkResult(
            operation="get_issue",
            transport="jsonrpc",
            latency_ms=latency_ms,
            success=response.status == 200 and "error" not in result,
            data_size=len(str(result))
        )

class GitHubBenchmark:
    """Main benchmark runner."""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
    
    async def run_benchmarks(self, iterations=10):
        """Run comprehensive benchmarks."""
        print("Starting GitHub MCP Transport Comparison")
        print(f"Running {iterations} iterations of each test...")
        
        # Initialize clients
        capnp_client = CapnProtoGitHubClient()
        jsonrpc_client = JsonRpcGitHubClient()
        
        try:
            # Connect both clients
            await capnp_client.connect()
            await jsonrpc_client.connect()
            
            print("Both servers connected")
            
            # Test 1: Issue creation
            print("\nTesting issue creation...")
            await self._benchmark_create_issues(capnp_client, jsonrpc_client, iterations)
            
            # Test 2: Issue listing
            print("Testing issue listing...")
            await self._benchmark_list_issues(capnp_client, jsonrpc_client, iterations)
            
            # Test 3: Issue retrieval
            print("Testing issue retrieval...")
            await self._benchmark_get_issues(capnp_client, jsonrpc_client, iterations)
            
            # Generate report
            self._generate_report()
            
        finally:
            await capnp_client.disconnect()
            await jsonrpc_client.disconnect()
    
    async def _benchmark_create_issues(self, capnp_client, jsonrpc_client, iterations):
        for i in range(iterations):
            title = f"Benchmark Issue {i}"
            body = f"This is benchmark issue #{i} created for performance testing."
            
            # Test Cap'n Proto
            result = await capnp_client.create_issue(title, body)
            self.results.append(result)
            
            # Test JSON-RPC
            result = await jsonrpc_client.create_issue(title, body)
            self.results.append(result)
    
    async def _benchmark_list_issues(self, capnp_client, jsonrpc_client, iterations):
        for i in range(iterations):
            # Test Cap'n Proto
            result = await capnp_client.list_issues()
            self.results.append(result)
            
            # Test JSON-RPC
            result = await jsonrpc_client.list_issues()
            self.results.append(result)
    
    async def _benchmark_get_issues(self, capnp_client, jsonrpc_client, iterations):
        # Use issue #1 for testing (assuming it exists)
        for i in range(iterations):
            issue_number = 1
            
            # Test Cap'n Proto
            result = await capnp_client.get_issue(issue_number)
            self.results.append(result)
            
            # Test JSON-RPC
            result = await jsonrpc_client.get_issue(issue_number)
            self.results.append(result)
    
    def _generate_report(self):
        """Generate performance comparison report."""
        print("\n" + "="*60)
        print("GITHUB MCP TRANSPORT COMPARISON RESULTS")
        print("="*60)
        
        # Group results by operation and transport
        operations = ["create_issue", "list_issues", "get_issue"]
        transports = ["capnp", "jsonrpc"]
        
        for operation in operations:
            print(f"\n{operation.upper()}")
            print("-" * 40)
            
            for transport in transports:
                filtered_results = [r for r in self.results 
                                  if r.operation == operation and r.transport == transport]
                
                if not filtered_results:
                    continue
                
                latencies = [r.latency_ms for r in filtered_results]
                avg_latency = statistics.mean(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                
                transport_name = "Cap'n Proto" if transport == "capnp" else "JSON-RPC"
                print(f"{transport_name:12}: {avg_latency:6.2f}ms avg ({min_latency:.2f}-{max_latency:.2f}ms)")
            
            # Calculate speedup
            capnp_results = [r.latency_ms for r in self.results 
                           if r.operation == operation and r.transport == "capnp"]
            jsonrpc_results = [r.latency_ms for r in self.results 
                             if r.operation == operation and r.transport == "jsonrpc"]
            
            if capnp_results and jsonrpc_results:
                speedup = statistics.mean(jsonrpc_results) / statistics.mean(capnp_results)
                print(f"{'Speedup:':12}  {speedup:.1f}x faster")
        
        print("\n" + "="*60)

async def main():
    benchmark = GitHubBenchmark()
    await benchmark.run_benchmarks(iterations=5)

if __name__ == "__main__":
    asyncio.run(capnp.run(main()))