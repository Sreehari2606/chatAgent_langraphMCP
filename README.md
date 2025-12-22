# WillOfCode AI
- AI Coding Assistant

A simple AI-powered coding assistant with MCP (Model Context Protocol) integration.

## Project Structure

```
coding-agent/
├── agent/                  # Core agent logic
│   ├── graph.py           # LangGraph workflow (20 lines)
│   ├── llm.py             # LLM wrapper for Gemini
│   ├── nodes.py           # Intent detection & tool handlers
│   └── state.py           # State type definition
├── static/                 # Frontend files
│   ├── index.html         # UI markup
│   ├── script.js          # UI logic
│   └── styles.css         # Styling
├── mymcp.py               # MCP server (file operations)
├── server.py              # Flask API server
└── pyproject.toml         # Dependencies
```

## Features

- **MCP Tools**: read_file, write_file, delete_file, list_files
- **AI Operations**: generate, debug, explain, review, refactor, test, document, optimize
- **File Browser**: Browse and edit files in the UI

## Quick Start

```bash
# Activate virtual environment
.\.venv\Scripts\activate

# Run server
python server.py
```

Open http://localhost:5000

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message to agent |
| `/api/mcp/tools` | GET | List MCP tools |
| `/api/files` | GET | List directory contents |
| `/api/file/read` | GET | Read file |
| `/api/file/write` | POST | Write file |
