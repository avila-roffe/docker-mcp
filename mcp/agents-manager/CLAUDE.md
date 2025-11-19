# CLAUDE.md - Agents Collection MCP Server

This file provides guidance when using the Agents Collection MCP Server.

## Purpose

Manage AI agent prompts in the avila-roffe/agents-collection GitHub repository through a structured MCP interface. All modifications create Pull Requests for review.

## Key Concepts

### Agent Structure

All agents are markdown files with YAML frontmatter containing:
- `id`: Unique identifier (auto-generated from title)
- `title`: Human-readable name
- `type`: Always "agent"
- `tags`: Array of categorization tags
- `project`: Optional project association
- `version`: Semantic version
- `description`: What the agent does
- `llm_provider`: Optional (e.g., "anthropic", "openai")
- `suggested_models`: Optional recommended models

### Folder Structure

The repository uses a multi-level structure:
- First level: Application name (e.g., `home-lab`, `mytaible`, `openweb-ui`, `shared`)
- Variable depth for subcategories
- `knowledge-base` folder is excluded from agent listings

### Workflow

All modifications (create, update, delete) generate Pull Requests:
1. Tool creates a new branch
2. Makes the change in that branch
3. Opens a PR with descriptive title and body
4. Returns the PR URL to the user
5. Changes take effect after PR is merged

## Available Tools

### Querying

- **list_agents**: Filter by tags, project, category, or text. All filters are optional and can be combined.
- **get_agent**: Retrieve full agent details by path (e.g., `home-lab/jarvis.md`)
- **list_categories**: See all top-level folders and agent counts

### Modifications

- **create_agent**: Requires category, title, description, and prompt_content. Optional: tags, project, llm_provider, suggested_models
- **update_agent**: Requires path. All other fields optional (only update what's provided)
- **delete_agent**: Requires path and reason

## Best Practices

1. Always use `list_agents` first to avoid duplicates
2. Provide descriptive titles and tags for discoverability
3. Include project association for organization-specific agents
4. Use semantic versioning when updating agents
5. Provide clear reasons for deletions
6. Review PRs before merging to catch issues

## Example Workflows

### Finding an Agent
```
User: "Find agents about Kubernetes"
Assistant: Uses list_agents with tags="kubernetes"
```

### Creating an Agent
```
User: "Create a Docker management agent for home-lab"
Assistant:
1. Uses list_categories to verify "home-lab" exists
2. Uses create_agent with appropriate metadata
3. Returns PR URL for review
```

### Updating an Agent
```
User: "Add the 'monitoring' tag to the JARVIS agent"
Assistant:
1. Uses list_agents or get_agent to find path
2. Uses update_agent with path and new tags
3. Returns PR URL
```

## Error Handling

- Missing GITHUB_TOKEN: Configure via Docker secrets
- 404 errors: Agent path doesn't exist
- Duplicate agents: File already exists at that path
- API rate limits: GitHub API has rate limits (5000/hour authenticated)

## Integration Notes

This server uses GitHub API exclusively (no local git operations) for simplicity and reliability. All file operations go through the GitHub REST API via PyGithub library.
