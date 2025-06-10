#!/bin/bash
set -e

echo "MCP Transport Layer Benchmark"
echo "============================="

# Check environment variables
if [ -z "$GITHUB_TOKEN" ] || [ -z "$GITHUB_REPO" ]; then
    echo "Error: GITHUB_TOKEN and GITHUB_REPO environment variables required"
    echo ""
    echo "Set them like this:"
    echo "export GITHUB_TOKEN=ghp_your_token_here"
    echo "export GITHUB_REPO=username/repo-name"
    exit 1
fi

echo "Environment configured:"
echo "  GITHUB_REPO: $GITHUB_REPO"
echo "  GITHUB_TOKEN: ${GITHUB_TOKEN:0:8}..."

# Start HTTP GitHub server in background
echo ""
echo "Starting HTTP GitHub MCP server..."
python src/mcp_capnp_poc/github_http_server.py &
HTTP_PID=$!

# Wait for HTTP server to start
sleep 3

# Start Cap'n Proto server in background
echo "Starting Cap'n Proto GitHub server..."
python src/mcp_capnp_poc/github_server.py &
CAPNP_PID=$!

# Wait for Cap'n Proto server to start
sleep 3

# Run benchmark
echo "Running performance comparison..."
echo ""
python src/mcp_capnp_poc/benchmark.py

# Cleanup
echo ""
echo "Cleaning up..."
kill $HTTP_PID 2>/dev/null || true
kill $CAPNP_PID 2>/dev/null || true

echo "Benchmark complete."