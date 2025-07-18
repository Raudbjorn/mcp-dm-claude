# TTRPG Assistant MCP Server

A Model Context Protocol (MCP) server that enables LLMs to search TTRPG rulebooks and manage campaign data. The system parses PDF rulebooks into searchable content, creates vector embeddings for semantic search, and stores both rulebook content and campaign data in Redis.

## Features

- **PDF Rulebook Processing**: Extract and parse PDF rulebooks with structure preservation
- **Semantic Search**: Vector-based similarity search using sentence transformers
- **Campaign Management**: Store and manage campaign data (characters, NPCs, locations, plot points)
- **🎭 Personality Extraction**: Automatically extracts personality profiles from rulebooks
  - Detects writing style, tone, and perspective
  - Extracts vernacular and neologisms specific to each RPG system
  - Configures response personality (e.g., "Wise Sage" for D&D, "Shadowy Informant" for Blades in the Dark)
- **MCP Integration**: Exposes four main tools for LLM interaction:
  - `search_rulebook`: Search rulebooks with personality-aware responses
  - `manage_campaign`: CRUD operations for campaign data
  - `add_rulebook`: Add new PDF rulebooks and extract personality profiles
  - `manage_personality`: View and manage RPG personality profiles
- **Hybrid Search**: Combines vector search with keyword fallback
- **Table Extraction**: Preserves tabular data from PDFs
- **Configurable**: YAML configuration with environment variable overrides

## Quick Start

### 🚀 Automated Setup (Recommended)

The easiest way to get started is using the bootstrap script:

```bash
# Clone the repository
git clone <repository-url>
cd dnd

# Run the bootstrap script (sets up everything and starts the server)
./bootstrap.sh
```

The bootstrap script will:
1. Install Redis if not present
2. Start Redis server
3. Create Python virtual environment
4. Install all dependencies
5. Run basic tests
6. Start the MCP server

### Bootstrap Options

```bash
./bootstrap.sh --help          # Show help
./bootstrap.sh --no-server     # Setup environment but don't start server
./bootstrap.sh --test-only     # Run tests only
```

### 🔧 Manual Setup

If you prefer manual setup or need to troubleshoot:

1. **Prerequisites**:
   - Python 3.8 or higher
   - Redis server

2. **Install Redis**:
   ```bash
   # Ubuntu/Debian
   sudo apt install redis-server
   
   # macOS
   brew install redis
   
   # Or use Docker
   docker run -d -p 6379:6379 redis:latest
   ```

3. **Setup Python Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Start Redis**:
   ```bash
   redis-server
   ```

5. **Run Tests**:
   ```bash
   python test_basic.py
   ```

6. **Start MCP Server**:
   ```bash
   python main.py
   ```

## Usage

### Adding Your First Rulebook

Once the server is running, you can add a PDF rulebook:

```bash
# In a new terminal (with venv activated)
python cli.py add-rulebook "path/to/your/rulebook.pdf" "D&D 5e Player's Handbook" "D&D 5e"
```

### Searching Rulebooks

```bash
# Basic search
python cli.py search "fireball spell"

# Search specific rulebook
python cli.py search "combat rules" --rulebook "D&D 5e Player's Handbook"

# Search for specific content type
python cli.py search "dragon" --content-type monster --max-results 10
```

### Managing Campaign Data

```bash
# Add a character
python cli.py add-campaign-data "my_campaign" "character" "Gandalf" --data '{"class": "wizard", "level": 20}'

# Add an NPC
python cli.py add-campaign-data "my_campaign" "npc" "Innkeeper Joe" --data '{"location": "Prancing Pony", "attitude": "friendly"}'

# List all campaign data
python cli.py list-campaign-data "my_campaign"

# List specific data type
python cli.py list-campaign-data "my_campaign" --data-type character
```

### 🎭 Managing Personality Profiles

```bash
# View all personality profiles
python cli.py list-personalities

# Show detailed personality profile
python cli.py show-personality "D&D 5e"

# Show vernacular terms for a system
python cli.py show-vernacular "Blades in the Dark"

# Compare personalities across systems
python cli.py compare-personalities "D&D 5e" "Call of Cthulhu" "Delta Green"

# View personality statistics
python cli.py personality-stats
```

### Viewing Statistics

```bash
python cli.py stats
```

## MCP Integration

The server exposes four MCP tools for LLM interaction:

### 1. search_rulebook

Search for rules, spells, monsters, and items with personality-aware responses:

```json
{
  "tool": "search_rulebook",
  "arguments": {
    "query": "fireball spell",
    "content_type": "spell",
    "max_results": 3
  }
}
```

**Example Response (D&D 5e):**
> "The ancient texts reveal 3 secrets regarding 'fireball spell'...
> 
> **1. Fireball** (From the Player's Handbook tome)
> Page 241 | D&D 5e | spell
> Relevance: 0.95 (semantic)
> 
> **Relevant Terminology:**
> - Spell Save DC: The difficulty class for resisting spell effects
> - Spell Attack Roll: Roll made to hit a target with a spell"

### 2. manage_campaign

Manage campaign data with full CRUD operations:

```json
{
  "tool": "manage_campaign",
  "arguments": {
    "action": "create",
    "campaign_id": "my_campaign",
    "data_type": "character",
    "data": {
      "name": "Aragorn",
      "class": "ranger",
      "level": 15,
      "background": "Heir of Isildur"
    }
  }
}
```

### 3. add_rulebook

Add new PDF rulebooks to the system and extract personality profiles:

```json
{
  "tool": "add_rulebook",
  "arguments": {
    "pdf_path": "/path/to/rulebook.pdf",
    "rulebook_name": "Monster Manual",
    "system": "D&D 5e"
  }
}
```

### 4. manage_personality

View and manage RPG personality profiles:

```json
{
  "tool": "manage_personality",
  "arguments": {
    "action": "get",
    "system_name": "Blades in the Dark"
  }
}
```

**Available Actions:**
- `get`: Get full personality profile
- `list`: List all personality profiles
- `summary`: Get personality summary
- `vernacular`: Get vernacular terms for a system
- `compare`: Compare personalities across systems
- `stats`: Get personality statistics

## 🎭 Personality System

The TTRPG Assistant automatically extracts personality profiles from rulebooks to provide immersive, system-appropriate responses. Each RPG system gets its own personality based on the writing style and tone of its rulebooks.

### Predefined Personality Examples

**D&D 5e - "Wise Sage"**
- **Tone**: Authoritative
- **Perspective**: Omniscient
- **Style**: Academic with magical terminology
- **Example**: "In the ancient texts, it is written that fireballs channel the elemental forces of destruction..."

**Blades in the Dark - "Shadowy Informant"**
- **Tone**: Mysterious
- **Perspective**: Conspiratorial
- **Style**: Victorian criminal underworld
- **Example**: "Word on the street is that the Dimmer Sisters have been seen in the shadows of Doskvol..."

**Delta Green - "Classified Handler"**
- **Tone**: Formal
- **Perspective**: Authoritative
- **Style**: Government/military briefings
- **Example**: "According to classified reports, field agents should be advised that the following information is compartmentalized..."

**Call of Cthulhu - "Antiquarian Scholar"**
- **Tone**: Scholarly
- **Perspective**: Ominous
- **Style**: Academic with eldritch undertones
- **Example**: "In my research of forbidden texts, I have uncovered disturbing evidence that the implications are most unsettling..."

### What Gets Extracted

- **Vernacular Terms**: System-specific terminology and neologisms
- **Writing Style**: Formal vs. casual, mysterious vs. straightforward
- **Tone Patterns**: Authoritative, scholarly, conspiratorial, etc.
- **Perspective**: First-person, instructional, omniscient
- **Example Phrases**: Common expressions and speech patterns
- **Context Clues**: Setting information and thematic elements

### Personality-Aware Responses

When you search for information, the assistant will:
- Use appropriate terminology from the rulebook
- Match the tone and style of the original text
- Include relevant vernacular in context
- Format responses according to the system's conventions
- Provide immersive, character-appropriate explanations

## Configuration

The system uses `config.yaml` for configuration. You can override settings with environment variables:

```yaml
redis:
  host: localhost
  port: 6379
  db: 0
  password: null

embedding:
  model: "all-MiniLM-L6-v2"
  batch_size: 32
  cache_embeddings: true

pdf_processing:
  max_file_size_mb: 100
  ocr_enabled: true
  preserve_formatting: true

search:
  default_max_results: 5
  similarity_threshold: 0.7
  enable_keyword_fallback: true

mcp:
  server_name: "ttrpg-assistant"
  version: "1.0.0"
```

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Embedding
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE=32
EMBEDDING_CACHE=true

# PDF Processing
PDF_MAX_SIZE_MB=100
PDF_OCR_ENABLED=true
PDF_PRESERVE_FORMAT=true

# Search
SEARCH_MAX_RESULTS=5
SEARCH_SIMILARITY_THRESHOLD=0.7
SEARCH_KEYWORD_FALLBACK=true

# Logging
LOG_LEVEL=INFO
```

## Architecture

The system consists of four main components:

1. **PDF Parser** (`src/pdf_parser/`): Extracts text and tables from PDF files while preserving structure
2. **Embedding Service** (`src/embedding_service/`): Generates vector embeddings using sentence transformers
3. **Redis Manager** (`src/redis_manager/`): Handles data storage and vector similarity search
4. **MCP Server** (`src/mcp_server/`): Provides the protocol interface for LLM interaction

## Performance

- **Search latency**: Target <2 seconds for typical queries
- **Memory efficient**: Handles large PDF files with streaming processing
- **Concurrent users**: Supports multiple simultaneous queries
- **Caching**: Embedding cache for improved performance

## Project Structure

```
dnd/
├── bootstrap.sh          # Automated setup script
├── main.py              # MCP server entry point
├── cli.py               # Command line interface
├── test_basic.py        # Basic component tests
├── config.yaml          # Configuration file
├── requirements.txt     # Python dependencies
├── src/
│   ├── models/          # Data models
│   ├── pdf_parser/      # PDF processing
│   ├── embedding_service/ # Vector embeddings
│   ├── redis_manager/   # Data storage
│   ├── mcp_server/      # MCP protocol
│   └── utils/           # Configuration and utilities
└── README.md           # This file
```

## Troubleshooting

### Common Issues

1. **Redis Connection Error**: 
   - Ensure Redis is running: `redis-server`
   - Check Redis status: `redis-cli ping`

2. **PDF Processing Error**: 
   - Check file permissions and path
   - Verify file size is under the limit (default 100MB)

3. **Memory Issues**: 
   - Reduce `batch_size` in embedding configuration
   - Process smaller PDF files

4. **Search Returns No Results**: 
   - Try adjusting `similarity_threshold` in configuration
   - Enable keyword fallback in search settings

5. **Python Virtual Environment Issues**:
   - Ensure you're using Python 3.8+
   - Activate virtual environment: `source venv/bin/activate`

### Logs

Check the `ttrpg_assistant.log` file for detailed error messages and debugging information.

### Testing

Run the basic test suite to verify everything is working:

```bash
python test_basic.py
```

## Development

### Adding New Features

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Update documentation
6. Submit a pull request

### Running in Development Mode

```bash
# Setup development environment
./bootstrap.sh --no-server

# Run tests
python test_basic.py

# Start server manually
python main.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue in the GitHub repository.

---

**Happy Gaming! 🎲**