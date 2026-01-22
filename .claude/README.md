# Claude Desktop Configuration

This directory contains configuration for Claude Desktop's MCP (Model Context Protocol) servers.

## mcp.json

This file defines the MCP servers that Claude Desktop will run.

- **memory**: persistent memory for Claude using `@modelcontextprotocol/server-memory`.
- **filesystem**: file system access for Claude using `@modelcontextprotocol/server-filesystem`.
- **fetch**: web fetching capabilities using `mcp-server-fetch`.

## Prerequisites

To use these servers, you need to have the following installed on your system:

1. **Node.js & npm**: Required for `memory` and `filesystem` servers.
   - Install from [nodejs.org](https://nodejs.org/)
   - Verify with: `node -v` and `npm -v`

2. **uv**: Required for the `fetch` server.
   - Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Verify with: `uv --version`
