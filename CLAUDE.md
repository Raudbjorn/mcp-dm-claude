# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a TTRPG (Tabletop Role-Playing Game) Assistant MCP (Model Context Protocol) tool that enables LLMs to look up information from TTRPG rulebooks and manage campaign data. The system parses PDF rulebooks into searchable content, creates vector embeddings for semantic search, and stores both rulebook content and campaign data in Redis.

## Architecture

The system follows a modular design with four main layers:

1. **MCP Server Layer**: Handles protocol communication and request routing
2. **Service Layer**: Business logic for search, parsing, and campaign management  
3. **Data Layer**: Redis-based storage with vector and traditional data capabilities
4. **Processing Layer**: PDF parsing and embedding generation

### Key Components

- **MCP Server**: Exposes three main tools to LLMs:
  - `search_rulebook`: Search TTRPG rulebooks with semantic similarity matching
  - `manage_campaign`: Store/retrieve campaign data (characters, NPCs, locations, plot points)
  - `add_rulebook`: Process and add new PDF rulebooks to the system

- **PDF Parser**: Extracts text from PDFs while preserving structure, handles tables, uses table of contents for section identification

- **Vector Embedding Service**: Uses sentence-transformers (all-MiniLM-L6-v2) for text-to-vector conversion and semantic search

- **Redis Data Manager**: Handles both vector search indices and traditional campaign data storage

## Data Models

### ContentChunk
- Contains parsed rulebook content with embeddings
- Includes metadata: rulebook name, system (D&D 5e, Pathfinder), content type, page numbers, section hierarchy
- Preserves table structure where applicable

### CampaignData  
- Stores campaign-specific information organized by campaign ID and data type
- Includes versioning and history tracking
- Supports characters, NPCs, locations, plot points, and session data

## Development Status

This project has been fully implemented with a complete working system. The repository contains:

- **Core Implementation**: All components from the design document have been implemented
- **PDF Parser**: Extracts text and tables from PDF files with structure preservation
- **Embedding Service**: Uses sentence-transformers for semantic search
- **Redis Manager**: Handles data storage and vector similarity search
- **MCP Server**: Fully functional MCP protocol implementation
- **CLI Interface**: Command-line tools for testing and management
- **Configuration**: Flexible YAML config with environment variable overrides

## Key Files

- `main.py`: MCP server entry point
- `cli.py`: Command-line interface for testing
- `src/`: Main implementation directory
  - `models/`: Data models (ContentChunk, CampaignData, etc.)
  - `pdf_parser/`: PDF processing components
  - `embedding_service/`: Vector embedding generation
  - `redis_manager/`: Data storage and search
  - `mcp_server/`: MCP protocol implementation
  - `utils/`: Configuration management
- `config.yaml`: Default configuration
- `requirements.txt`: Python dependencies
- `test_basic.py`: Basic component tests

## Target Performance

- Search latency: Target <2 seconds for typical queries
- Memory efficient processing of large PDF files
- Concurrent user support during gaming sessions
- Vector embedding optimization for storage and query speed

## Dependencies

- Python 3.8+ with sentence-transformers library
- Redis server for data storage
- PDF processing libraries (PyPDF2, pdfplumber)
- MCP protocol implementation
- Additional dependencies in requirements.txt

## Common Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt

# Start Redis (required)
redis-server

# Run tests
python test_basic.py

# Add a rulebook
python cli.py add-rulebook "path/to/book.pdf" "Book Name" "D&D 5e"

# Search rulebooks
python cli.py search "fireball spell"
python cli.py search "combat rules" --rulebook "Book Name"

# Manage campaign data
python cli.py add-campaign-data "campaign1" "character" "Gandalf"
python cli.py list-campaign-data "campaign1"

# Start MCP server
python main.py
```

## User Experience Goals

The system is designed to be accessible to non-technical users while providing powerful search capabilities for game masters and players. It emphasizes simplicity in setup and usage while maintaining high performance during active gaming sessions.