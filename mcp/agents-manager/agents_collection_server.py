#!/usr/bin/env python3
"""
Agents Collection MCP Server - Manage AI agent prompts in GitHub repository via PRs
"""
import os
import sys
import logging
import re
import yaml
import base64
from datetime import datetime, timezone
from typing import Any
import httpx
from github import Github, GithubException
from mcp.server.fastmcp import FastMCP

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("agents-collection-server")

# Initialize MCP server - NO PROMPT PARAMETER!
mcp = FastMCP("agents-collection")

# Configuration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_NAME = "avila-roffe/agents-collection"
EXCLUDED_FOLDERS = ["knowledge-base", ".git", ".github"]

# === UTILITY FUNCTIONS ===

def get_github_client():
    """Get authenticated GitHub client."""
    if not GITHUB_TOKEN.strip():
        raise ValueError("GITHUB_TOKEN not configured")
    return Github(GITHUB_TOKEN)

def parse_agent_frontmatter(content):
    """Parse frontmatter from agent markdown file."""
    try:
        if not content.startswith("---"):
            return None, content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None, content

        frontmatter = yaml.safe_load(parts[1])
        body = parts[2].strip()
        return frontmatter, body
    except Exception as e:
        logger.error(f"Error parsing frontmatter: {e}")
        return None, content

def create_agent_content(metadata, body):
    """Create agent file content with frontmatter."""
    frontmatter = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
    return f"---\n{frontmatter}---\n\n{body}"

def sanitize_filename(name):
    """Convert name to valid filename."""
    name = re.sub(r'[^\w\s-]', '', name.lower())
    name = re.sub(r'[-\s]+', '-', name)
    return name.strip('-')

def should_include_path(path):
    """Check if path should be included in results."""
    parts = path.split('/')
    for folder in EXCLUDED_FOLDERS:
        if folder in parts:
            return False
    return path.endswith('.md')

def match_filters(frontmatter, body, tags=None, project=None, category=None, text=None):
    """Check if agent matches filter criteria."""
    if not frontmatter:
        return False

    # Tag filter
    if tags:
        agent_tags = frontmatter.get('tags', [])
        if isinstance(agent_tags, str):
            agent_tags = [agent_tags]
        tag_list = [t.strip().lower() for t in tags.split(',')]
        if not any(tag in [str(at).lower() for at in agent_tags] for tag in tag_list):
            return False

    # Project filter
    if project and frontmatter.get('project', '').lower() != project.lower():
        return False

    # Category filter (first folder in path)
    if category:
        # Category will be checked separately by path
        pass

    # Text search
    if text:
        search_text = text.lower()
        title = str(frontmatter.get('title', '')).lower()
        desc = str(frontmatter.get('description', '')).lower()
        if search_text not in title and search_text not in desc and search_text not in body.lower():
            return False

    return True

def match_query(frontmatter, body, agent_id=None, title=None, tags=None, project=None, 
                llm_provider=None, suggested_models=None, version=None, description=None, 
                text=None):
    """Check if agent matches query criteria - flexible matching by any markdown property."""
    if not frontmatter:
        return False

    # ID filter (exact match)
    if agent_id and frontmatter.get('id', '').lower() != agent_id.lower():
        return False

    # Title/Name filter (partial match, case-insensitive)
    if title:
        agent_title = str(frontmatter.get('title', '')).lower()
        if title.lower() not in agent_title:
            return False

    # Tag filter (any tag matches)
    if tags:
        agent_tags = frontmatter.get('tags', [])
        if isinstance(agent_tags, str):
            agent_tags = [agent_tags]
        tag_list = [t.strip().lower() for t in tags.split(',')]
        if not any(tag in [str(at).lower() for at in agent_tags] for tag in tag_list):
            return False

    # Project filter
    if project:
        agent_project = str(frontmatter.get('project', '')).lower()
        if project.lower() not in agent_project:
            return False

    # LLM Provider filter
    if llm_provider:
        agent_provider = str(frontmatter.get('llm_provider', '')).lower()
        if llm_provider.lower() not in agent_provider:
            return False

    # Suggested Models filter
    if suggested_models:
        agent_models = str(frontmatter.get('suggested_models', '')).lower()
        if suggested_models.lower() not in agent_models:
            return False

    # Version filter
    if version:
        agent_version = str(frontmatter.get('version', '')).lower()
        if version.lower() not in agent_version:
            return False

    # Description filter (partial match)
    if description:
        agent_desc = str(frontmatter.get('description', '')).lower()
        if description.lower() not in agent_desc:
            return False

    # General text search across all fields and body
    if text:
        search_text = text.lower()
        # Search in all frontmatter values
        found = False
        for key, value in frontmatter.items():
            if search_text in str(value).lower():
                found = True
                break
        # Also search in body
        if not found and search_text in body.lower():
            found = True
        if not found:
            return False

    return True

# === MCP TOOLS ===

@mcp.tool()
async def list_agents(tags: str = "", project: str = "", category: str = "", text: str = "") -> str:
    """List all agents with optional filters for tags (comma-separated), project, category (folder), or text search."""
    logger.info(f"Listing agents - tags:{tags}, project:{project}, category:{category}, text:{text}")

    try:
        g = get_github_client()
        repo = g.get_repo(REPO_NAME)

        # Get all markdown files
        contents = repo.get_contents("")
        agents = []

        def process_contents(items, current_path=""):
            for item in items:
                if item.type == "dir":
                    if item.name not in EXCLUDED_FOLDERS:
                        try:
                            sub_items = repo.get_contents(item.path)
                            process_contents(sub_items, item.path)
                        except Exception as e:
                            logger.error(f"Error processing directory {item.path}: {e}")
                elif item.path.endswith('.md') and should_include_path(item.path):
                    try:
                        # Category filter by path
                        if category and not item.path.startswith(f"{category}/"):
                            continue

                        file_content = repo.get_contents(item.path)
                        content = base64.b64decode(file_content.content).decode('utf-8')
                        frontmatter, body = parse_agent_frontmatter(content)

                        if frontmatter and match_filters(frontmatter, body, tags, project, category, text):
                            agents.append({
                                'path': item.path,
                                'id': frontmatter.get('id', 'unknown'),
                                'title': frontmatter.get('title', 'Untitled'),
                                'tags': frontmatter.get('tags', []),
                                'project': frontmatter.get('project', ''),
                                'description': frontmatter.get('description', '')
                            })
                    except Exception as e:
                        logger.error(f"Error processing file {item.path}: {e}")

        process_contents(contents)

        if not agents:
            return "📭 No agents found matching the filters"

        # Format output
        result = f"📚 **Found {len(agents)} agent(s):**\n\n"
        for agent in agents:
            result += f"**{agent['title']}** (`{agent['id']}`)\n"
            result += f"  📁 Path: `{agent['path']}`\n"
            if agent['project']:
                result += f"  🏷️ Project: {agent['project']}\n"
            if agent['tags']:
                tags_str = ', '.join([str(t) for t in agent['tags']])
                result += f"  🏷️ Tags: {tags_str}\n"
            if agent['description']:
                result += f"  📝 {agent['description']}\n"
            result += "\n"

        return result

    except GithubException as e:
        return f"❌ GitHub API Error: {e.data.get('message', str(e))}"
    except ValueError as e:
        return f"❌ Configuration Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def get_agent(path: str = "") -> str:
    """Retrieve a specific agent by its file path (e.g., 'home-lab/jarvis.md')."""
    logger.info(f"Getting agent: {path}")

    try:
        if not path.strip():
            return "❌ Error: Path is required"

        g = get_github_client()
        repo = g.get_repo(REPO_NAME)

        file_content = repo.get_contents(path.strip())
        content = base64.b64decode(file_content.content).decode('utf-8')
        frontmatter, body = parse_agent_frontmatter(content)

        if not frontmatter:
            return f"❌ Error: Invalid agent file format (no frontmatter found)"

        # Format output
        result = f"📄 **{frontmatter.get('title', 'Untitled')}**\n\n"
        result += f"**Metadata:**\n"
        result += f"- ID: `{frontmatter.get('id', 'unknown')}`\n"
        result += f"- Type: {frontmatter.get('type', 'agent')}\n"
        result += f"- Version: {frontmatter.get('version', 'N/A')}\n"
        if frontmatter.get('project'):
            result += f"- Project: {frontmatter['project']}\n"
        if frontmatter.get('tags'):
            tags_str = ', '.join([str(t) for t in frontmatter['tags']])
            result += f"- Tags: {tags_str}\n"
        if frontmatter.get('llm_provider'):
            result += f"- LLM Provider: {frontmatter['llm_provider']}\n"
        if frontmatter.get('suggested_models'):
            result += f"- Suggested Models: {frontmatter['suggested_models']}\n"
        if frontmatter.get('description'):
            result += f"\n**Description:**\n{frontmatter['description']}\n"
        result += f"\n**Prompt Content:**\n```\n{body}\n```"

        return result

    except GithubException as e:
        if e.status == 404:
            return f"❌ Error: Agent not found at path '{path}'"
        return f"❌ GitHub API Error: {e.data.get('message', str(e))}"
    except ValueError as e:
        return f"❌ Configuration Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def create_agent(category: str = "", title: str = "", description: str = "", tags: str = "", project: str = "", llm_provider: str = "", suggested_models: str = "", prompt_content: str = "") -> str:
    """Create a new agent via Pull Request - requires category (folder), title, description, tags (comma-separated), project, llm_provider, suggested_models, and prompt_content."""
    logger.info(f"Creating agent: {title} in {category}")

    try:
        if not all([category.strip(), title.strip(), description.strip(), prompt_content.strip()]):
            return "❌ Error: category, title, description, and prompt_content are required"

        g = get_github_client()
        repo = g.get_repo(REPO_NAME)

        # Generate agent ID and filename
        agent_id = sanitize_filename(title)
        filename = f"{agent_id}.md"
        filepath = f"{category.strip()}/{filename}"

        # Check if file already exists
        try:
            repo.get_contents(filepath)
            return f"❌ Error: Agent already exists at '{filepath}'"
        except GithubException as e:
            if e.status != 404:
                raise

        # Parse tags
        tag_list = [t.strip() for t in tags.split(',') if t.strip()] if tags.strip() else []

        # Create metadata
        metadata = {
            'id': agent_id,
            'title': title.strip(),
            'type': 'agent',
            'tags': tag_list,
            'description': description.strip()
        }

        if project.strip():
            metadata['project'] = project.strip()
        if llm_provider.strip():
            metadata['llm_provider'] = llm_provider.strip()
        if suggested_models.strip():
            metadata['suggested_models'] = suggested_models.strip()

        metadata['version'] = '1.0.0'

        # Create file content
        content = create_agent_content(metadata, prompt_content.strip())

        # Create branch
        default_branch = repo.default_branch
        base_sha = repo.get_branch(default_branch).commit.sha
        branch_name = f"add-agent-{agent_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)

        # Create file in branch
        repo.create_file(
            path=filepath,
            message=f"Add agent: {title}",
            content=content,
            branch=branch_name
        )

        # Create pull request
        pr = repo.create_pull(
            title=f"Add agent: {title}",
            body=f"## New Agent\n\n**Title:** {title}\n**Category:** {category}\n**Project:** {project or 'N/A'}\n**Tags:** {', '.join(tag_list) or 'None'}\n**LLM Provider:** {llm_provider or 'N/A'}\n\n**Description:**\n{description}\n\n---\n🤖 Generated via Agents Collection MCP Server",
            head=branch_name,
            base=default_branch
        )

        return f"✅ **Agent created successfully!**\n\n📁 File: `{filepath}`\n🔀 Pull Request: {pr.html_url}\n\nThe agent will be added once the PR is merged."

    except GithubException as e:
        return f"❌ GitHub API Error: {e.data.get('message', str(e))}"
    except ValueError as e:
        return f"❌ Configuration Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def update_agent(path: str = "", title: str = "", description: str = "", tags: str = "", project: str = "", llm_provider: str = "", suggested_models: str = "", prompt_content: str = "", version: str = "") -> str:
    """Update an existing agent via Pull Request - provide path and fields to update (leave empty to keep current value)."""
    logger.info(f"Updating agent: {path}")

    try:
        if not path.strip():
            return "❌ Error: Path is required"

        g = get_github_client()
        repo = g.get_repo(REPO_NAME)

        # Get current file
        file = repo.get_contents(path.strip())
        current_content = base64.b64decode(file.content).decode('utf-8')
        frontmatter, body = parse_agent_frontmatter(current_content)

        if not frontmatter:
            return "❌ Error: Invalid agent file format"

        # Update metadata with provided values
        updated = False
        changes = []

        if title.strip():
            frontmatter['title'] = title.strip()
            changes.append(f"Title: {title}")
            updated = True
        if description.strip():
            frontmatter['description'] = description.strip()
            changes.append(f"Description updated")
            updated = True
        if tags.strip():
            frontmatter['tags'] = [t.strip() for t in tags.split(',') if t.strip()]
            changes.append(f"Tags: {tags}")
            updated = True
        if project.strip():
            frontmatter['project'] = project.strip()
            changes.append(f"Project: {project}")
            updated = True
        if llm_provider.strip():
            frontmatter['llm_provider'] = llm_provider.strip()
            changes.append(f"LLM Provider: {llm_provider}")
            updated = True
        if suggested_models.strip():
            frontmatter['suggested_models'] = suggested_models.strip()
            changes.append(f"Suggested Models: {suggested_models}")
            updated = True
        if version.strip():
            frontmatter['version'] = version.strip()
            changes.append(f"Version: {version}")
            updated = True

        new_body = body
        if prompt_content.strip():
            new_body = prompt_content.strip()
            changes.append("Prompt content updated")
            updated = True

        if not updated:
            return "❌ Error: No changes provided"

        # Create new content
        new_content = create_agent_content(frontmatter, new_body)

        # Create branch
        default_branch = repo.default_branch
        base_sha = repo.get_branch(default_branch).commit.sha
        agent_id = frontmatter.get('id', 'agent')
        branch_name = f"update-agent-{agent_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)

        # Update file in branch
        repo.update_file(
            path=file.path,
            message=f"Update agent: {frontmatter['title']}",
            content=new_content,
            sha=file.sha,
            branch=branch_name
        )

        # Create pull request
        changes_list = '\n'.join([f"- {c}" for c in changes])
        pr = repo.create_pull(
            title=f"Update agent: {frontmatter['title']}",
            body=f"## Update Agent\n\n**File:** `{path}`\n\n**Changes:**\n{changes_list}\n\n---\n🤖 Generated via Agents Collection MCP Server",
            head=branch_name,
            base=default_branch
        )

        return f"✅ **Agent update PR created!**\n\n📁 File: `{path}`\n🔀 Pull Request: {pr.html_url}\n\n**Changes:**\n{changes_list}\n\nThe agent will be updated once the PR is merged."

    except GithubException as e:
        if e.status == 404:
            return f"❌ Error: Agent not found at path '{path}'"
        return f"❌ GitHub API Error: {e.data.get('message', str(e))}"
    except ValueError as e:
        return f"❌ Configuration Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def delete_agent(path: str = "", reason: str = "") -> str:
    """Delete an agent via Pull Request - requires path and reason for deletion."""
    logger.info(f"Deleting agent: {path}")

    try:
        if not path.strip():
            return "❌ Error: Path is required"
        if not reason.strip():
            return "❌ Error: Reason for deletion is required"

        g = get_github_client()
        repo = g.get_repo(REPO_NAME)

        # Get current file to verify it exists and get metadata
        file = repo.get_contents(path.strip())
        current_content = base64.b64decode(file.content).decode('utf-8')
        frontmatter, _ = parse_agent_frontmatter(current_content)

        if not frontmatter:
            return "❌ Error: Invalid agent file format"

        agent_title = frontmatter.get('title', 'Unknown')
        agent_id = frontmatter.get('id', 'unknown')

        # Create branch
        default_branch = repo.default_branch
        base_sha = repo.get_branch(default_branch).commit.sha
        branch_name = f"delete-agent-{agent_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)

        # Delete file in branch
        repo.delete_file(
            path=file.path,
            message=f"Delete agent: {agent_title}",
            sha=file.sha,
            branch=branch_name
        )

        # Create pull request
        pr = repo.create_pull(
            title=f"Delete agent: {agent_title}",
            body=f"## Delete Agent\n\n**File:** `{path}`\n**Agent:** {agent_title}\n**ID:** {agent_id}\n\n**Reason:**\n{reason}\n\n---\n🤖 Generated via Agents Collection MCP Server",
            head=branch_name,
            base=default_branch
        )

        return f"✅ **Agent deletion PR created!**\n\n📁 File: `{path}`\n🔀 Pull Request: {pr.html_url}\n\n**Reason:** {reason}\n\nThe agent will be deleted once the PR is merged."

    except GithubException as e:
        if e.status == 404:
            return f"❌ Error: Agent not found at path '{path}'"
        return f"❌ GitHub API Error: {e.data.get('message', str(e))}"
    except ValueError as e:
        return f"❌ Configuration Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def list_categories() -> str:
    """List all available categories (top-level folders) in the repository."""
    logger.info("Listing categories")

    try:
        g = get_github_client()
        repo = g.get_repo(REPO_NAME)

        contents = repo.get_contents("")
        categories = []

        for item in contents:
            if item.type == "dir" and item.name not in EXCLUDED_FOLDERS:
                # Count agents in category
                try:
                    cat_contents = repo.get_contents(item.path)
                    agent_count = sum(1 for f in cat_contents if f.path.endswith('.md'))
                    categories.append({
                        'name': item.name,
                        'path': item.path,
                        'count': agent_count
                    })
                except Exception as e:
                    logger.error(f"Error processing category {item.name}: {e}")

        if not categories:
            return "📭 No categories found"

        result = f"📂 **Found {len(categories)} categor{'y' if len(categories) == 1 else 'ies'}:**\n\n"
        for cat in sorted(categories, key=lambda x: x['name']):
            result += f"- **{cat['name']}** ({cat['count']} agent{'s' if cat['count'] != 1 else ''})\n"

        return result

    except GithubException as e:
        return f"❌ GitHub API Error: {e.data.get('message', str(e))}"
    except ValueError as e:
        return f"❌ Configuration Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def query_agent(agent_id: str = "", title: str = "", tags: str = "", project: str = "", 
                     llm_provider: str = "", suggested_models: str = "", version: str = "", 
                     description: str = "", text: str = "", path: str = "") -> str:
    """Query agents using any combination of markdown properties (id, title, tags, project, llm_provider, suggested_models, version, description, or general text search). Optionally provide path to narrow search scope."""
    logger.info(f"Querying agents - id:{agent_id}, title:{title}, tags:{tags}, project:{project}, path:{path}")

    try:
        g = get_github_client()
        repo = g.get_repo(REPO_NAME)

        # Get all markdown files
        contents = repo.get_contents("")
        agents = []

        def process_contents(items, current_path=""):
            for item in items:
                if item.type == "dir":
                    if item.name not in EXCLUDED_FOLDERS:
                        try:
                            sub_items = repo.get_contents(item.path)
                            process_contents(sub_items, item.path)
                        except Exception as e:
                            logger.error(f"Error processing directory {item.path}: {e}")
                elif item.path.endswith('.md') and should_include_path(item.path):
                    try:
                        # Path filter - check if path matches
                        if path.strip():
                            path_filter = path.strip().lower()
                            item_path_lower = item.path.lower()
                            # Check if path starts with filter or contains it
                            if not (item_path_lower.startswith(path_filter) or path_filter in item_path_lower):
                                continue

                        file_content = repo.get_contents(item.path)
                        content = base64.b64decode(file_content.content).decode('utf-8')
                        frontmatter, body = parse_agent_frontmatter(content)

                        if frontmatter and match_query(frontmatter, body, agent_id, title, tags, project,
                                                      llm_provider, suggested_models, version, description, text):
                            agents.append({
                                'path': item.path,
                                'id': frontmatter.get('id', 'unknown'),
                                'title': frontmatter.get('title', 'Untitled'),
                                'tags': frontmatter.get('tags', []),
                                'project': frontmatter.get('project', ''),
                                'llm_provider': frontmatter.get('llm_provider', ''),
                                'suggested_models': frontmatter.get('suggested_models', ''),
                                'version': frontmatter.get('version', ''),
                                'description': frontmatter.get('description', '')
                            })
                    except Exception as e:
                        logger.error(f"Error processing file {item.path}: {e}")

        process_contents(contents)

        if not agents:
            return "📭 No agents found matching the query criteria"

        # Format output
        result = f"🔍 **Found {len(agents)} agent(s) matching query:**\n\n"
        for agent in agents:
            result += f"**{agent['title']}** (`{agent['id']}`)\n"
            result += f"  📁 Path: `{agent['path']}`\n"
            if agent['project']:
                result += f"  🏷️ Project: {agent['project']}\n"
            if agent['tags']:
                tags_str = ', '.join([str(t) for t in agent['tags']])
                result += f"  🏷️ Tags: {tags_str}\n"
            if agent['llm_provider']:
                result += f"  🤖 LLM Provider: {agent['llm_provider']}\n"
            if agent['suggested_models']:
                result += f"  📊 Suggested Models: {agent['suggested_models']}\n"
            if agent['version']:
                result += f"  📌 Version: {agent['version']}\n"
            if agent['description']:
                result += f"  📝 {agent['description']}\n"
            result += "\n"

        return result

    except GithubException as e:
        return f"❌ GitHub API Error: {e.data.get('message', str(e))}"
    except ValueError as e:
        return f"❌ Configuration Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error: {str(e)}"

# === SERVER STARTUP ===
if __name__ == "__main__":
    logger.info("Starting Agents Collection MCP server...")

    if not GITHUB_TOKEN:
        logger.warning("GITHUB_TOKEN not set - server will not be able to authenticate")

    try:
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
