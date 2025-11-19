# Agents Collection MCP Server

A Model Context Protocol (MCP) server that manages AI agent prompts stored in the avila-roffe/agents-collection GitHub repository. All modifications are done via Pull Requests for review.

## Purpose

This MCP server provides a secure interface for AI assistants to browse, create, update, and delete agent prompts stored in your GitHub repository. All changes go through Pull Requests to maintain code review and approval workflows.

## Features

### Current Implementation

- **`list_agents`** - List all agents with optional filters for tags, project, category, or text search
- **`get_agent`** - Retrieve a specific agent's full details including metadata and prompt content
- **`create_agent`** - Create a new agent via Pull Request with full metadata support
- **`update_agent`** - Update an existing agent via Pull Request (partial updates supported)
- **`delete_agent`** - Delete an agent via Pull Request with required reason
- **`list_categories`** - List all available categories (top-level folders) with agent counts

## Prerequisites

- Docker Desktop with MCP Toolkit enabled
- Docker MCP CLI plugin (`docker mcp` command)
- GitHub Personal Access Token with repo permissions
- Access to the avila-roffe/agents-collection repository

### Creating a GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Set a note like "Agents Collection MCP"
4. Select scopes:
   - `repo` (Full control of private repositories)
5. Click "Generate token" and copy it immediately

## Installation

See the step-by-step instructions provided with the files.

## Usage Examples

In Claude Desktop, you can ask:

- "List all agents with the tag 'kubernetes'"
- "Show me all agents in the home-lab project"
- "Get the JARVIS agent details"
- "Create a new agent for Docker management in the home-lab category"
- "Update the network agent to add automation tag"
- "List all available categories"
- "Search for agents about infrastructure"

## Agent File Format

Agents are stored as markdown files with YAML frontmatter:

```markdown
---
id: jarvis-homelab-assistant
title: JARVIS - Home Lab Infrastructure Assistant
type: agent
tags: [homelab, infrastructure, kubernetes, docker]
project: home-lab
version: 2.0.0
description: Expert AI assistant for home lab infrastructure
llm_provider: anthropic
suggested_models: claude-sonnet-4
---

Your prompt content goes here...
```

## Architecture

```
Claude Desktop → MCP Gateway → Agents Collection MCP Server → GitHub API
                                                                  ↓
                                                          Pull Requests
                                                                  ↓
                                                    avila-roffe/agents-collection
```

## Development

### Local Testing

```bash
# Create and activate virtual environment (required on macOS)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables for testing
export GITHUB_TOKEN="your-token-here"

# Run directly
python3 agents_collection_server.py

# Test MCP protocol
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python3 agents_collection_server.py
```

### Adding New Tools

1. Add the function to `agents_collection_server.py`
2. Decorate with `@mcp.tool()`
3. Update the catalog entry with the new tool name
4. Rebuild the Docker image

## Troubleshooting

### Tools Not Appearing
- Verify Docker image built successfully
- Check catalog and registry files
- Ensure Claude Desktop config includes custom catalog
- Restart Claude Desktop

### Authentication Errors
- Verify token with `docker mcp secret list`
- Ensure GITHUB_TOKEN has repo permissions
- Check token hasn't expired

### PR Creation Fails
- Verify repository access
- Check branch protection rules
- Ensure token has write permissions

## Security Considerations

- GitHub token stored in Docker Desktop secrets
- Never hardcode credentials
- Running as non-root user
- All changes require PR approval
- Sensitive data never logged

## License

MIT License
