# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Docker MCP Tutorial repository that teaches users how to build and deploy MCP (Model Context Protocol) servers using Docker. It was created for NetworkChuck's YouTube tutorial and contains:

- Complete working example: Dice Roller MCP server
- MCP Builder Prompt: An AI prompt template to generate new MCP servers
- Comprehensive documentation for installation and custom server development
- Quick-start guides for getting up and running in 5 minutes

## Key Architecture Concepts

### MCP Server Flow
```
Claude Desktop/Cursor → Docker MCP Gateway → MCP Server Container → External APIs/Services
                              ↓
                        Docker Desktop Secrets
```

**Docker MCP Gateway** acts as a centralized orchestrator that:
- Aggregates multiple MCP servers into one connection
- Manages Docker containers on-demand (containers only run when tools are used)
- Handles authentication and secrets centrally
- Provides unified access to all tools

### Critical MCP Server Rules

When working with MCP servers in this repository, **strictly follow these rules** (from mcp-builder-prompt/mcp-builder-prompt.md:96-116):

1. **NO `@mcp.prompt()` decorators** - They break Claude Desktop
2. **NO `prompt` parameter to FastMCP()** - It breaks Claude Desktop
3. **NO type hints from typing module** - No `Optional`, `Union`, `List[str]`, etc.
4. **NO complex parameter types** - Use `param: str = ""` not `param: str = None`
5. **SINGLE-LINE DOCSTRINGS ONLY** - Multi-line docstrings cause gateway panic errors
6. **DEFAULT TO EMPTY STRINGS** - Use `param: str = ""` never `param: str = None`
7. **ALWAYS return strings from tools** - All tools must return formatted strings
8. **ALWAYS use Docker** - The server must run in a Docker container
9. **ALWAYS log to stderr** - Use the logging configuration from dice_server.py
10. **ALWAYS handle errors gracefully** - Return user-friendly error messages

### MCP Server File Structure

Every MCP server requires these 5 files:
1. `Dockerfile` - Container configuration (Python 3.11-slim base, non-root user)
2. `requirements.txt` - Python dependencies (minimum: `mcp[cli]>=1.2.0`)
3. `[name]_server.py` - Main server implementation using FastMCP
4. `readme.txt` - Documentation
5. `CLAUDE.md` - Integration guide (for generated servers)

## Common Development Commands

### Building and Testing MCP Servers

```bash
# Build a Docker image for an MCP server
cd examples/dice-roller
docker build -t dice-mcp-server .

# Test server locally (without Docker)
python dice_server.py

# Test MCP protocol compliance
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python dice_server.py

# View running MCP containers
docker ps | grep mcp

# View logs for a specific container
docker logs [container-name]
```

### Docker MCP CLI Commands

```bash
# List registered MCP servers
docker mcp server list

# Manage secrets
docker mcp secret set API_KEY="value"
docker mcp secret list

# Run gateway manually (stdio transport for local)
docker mcp gateway run --transport stdio

# Run gateway for network access (SSE transport)
docker mcp gateway run --transport sse --port 8811
```

### Configuration Files

MCP configuration lives in `~/.docker/mcp/`:
- `catalogs/custom.yaml` - Custom server definitions
- `catalogs/docker-mcp.yaml` - Official Docker servers
- `registry.yaml` - Installed servers registry
- `config.yaml` - Gateway configuration

## Example MCP Tool Implementation

Reference examples/dice-roller/dice_server.py:64-93 for the correct pattern:

```python
@mcp.tool()
async def flip_coin(count: str = "1") -> str:
    """Flip one or more coins and show results as heads or tails."""
    logger.info(f"Flipping {count} coin(s)")

    try:
        num_coins = int(count) if count.strip() else 1
        if num_coins < 1:
            return "❌ Error: Must flip at least 1 coin"

        # Implementation...
        return f"🪙 Result: {result}"
    except ValueError:
        return f"❌ Error: Invalid count: {count}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error: {str(e)}"
```

**Key patterns:**
- Single-line docstring (multi-line causes panic errors!)
- Empty string defaults (`count: str = "1"`)
- Check for empty strings with `.strip()` not just truthiness
- Convert string params as needed (`int(count)`)
- Comprehensive error handling with user-friendly messages
- Return formatted strings with emojis (✅ ❌ 🎲 etc.)
- Log to stderr for debugging

## Using the MCP Builder Prompt

To generate a new MCP server:

1. Read `mcp-builder-prompt/mcp-builder-prompt.md`
2. Provide requirements at the INITIAL CLARIFICATIONS section:
   - Service/Tool Name
   - API Documentation (if integrating with external APIs)
   - Required Features/Tools
   - Authentication needs
   - Data sources
3. Pass the prompt to an LLM (Claude, ChatGPT)
4. The LLM generates all 5 required files following the strict MCP rules
5. The output includes installation instructions for catalog/registry setup

## Installation Flow for New Servers

After building a Docker image for a new server:

1. Add to `~/.docker/mcp/catalogs/custom.yaml` (version 2 format)
2. Add entry to `~/.docker/mcp/registry.yaml` under `registry:` key with `ref: ""`
3. Update Claude Desktop config to include custom catalog: `--catalog=/mcp/catalogs/custom.yaml`
4. Restart Claude Desktop
5. Verify with `docker mcp server list`

See quick-start/setup-guide.md:32-66 for the exact catalog YAML structure.

## Important Notes

- Transport modes: `stdio` for local clients, `sse` for network/remote access
- Secrets are managed via Docker Desktop, accessed via `os.environ.get("VAR_NAME")`
- Containers run on-demand when tools are called, then stop automatically
- Multiple catalogs can be loaded: official Docker catalog + custom catalogs
- The dice-roller example is fully functional and demonstrates all patterns

## Repository Structure

```
docker-mcp-tutorial/
├── examples/
│   └── dice-roller/          # Complete working example (Python FastMCP)
├── mcp-builder-prompt/       # AI prompt to generate MCP servers
├── quick-start/              # 5-minute setup guide
├── docs/
│   ├── installation.md       # Platform-specific setup
│   ├── custom-servers.md     # Build custom servers guide
│   ├── docker-gateway.md     # Gateway architecture deep dive
│   └── troubleshooting.md    # Common issues and fixes
└── resources/                # Links and additional resources
```

## References

- [Docker Desktop MCP Toolkit](https://docs.docker.com/desktop/)
- [Model Context Protocol Spec](https://modelcontextprotocol.io/)
- All critical rules come from the MCP Builder Prompt (mcp-builder-prompt/mcp-builder-prompt.md)
- Dice roller example is the canonical implementation reference (examples/dice-roller/dice_server.py)