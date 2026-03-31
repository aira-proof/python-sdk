# Aira MCP Server

Expose Aira as MCP tools for any MCP-compatible AI agent.

## Setup

```bash
pip install aira-sdk[mcp]
```

## Run

```bash
export AIRA_API_KEY="aira_live_xxx"
aira-mcp
```

## Tools Exposed

- **notarize_action** -- Create a cryptographic receipt for an AI action
- **verify_action** -- Verify a notarized action
- **get_receipt** -- Retrieve a receipt by ID

## Claude Desktop Config

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "aira": {
      "command": "aira-mcp",
      "env": { "AIRA_API_KEY": "aira_live_xxx" }
    }
  }
}
```

## Usage

Once configured, any MCP-compatible agent (Claude Desktop, etc.) can call `notarize_action` to create tamper-proof receipts for AI actions, `verify_action` to check receipt integrity, and `get_receipt` to retrieve past receipts by ID.
