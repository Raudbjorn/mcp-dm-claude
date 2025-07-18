#!/usr/bin/env python3
"""
TTRPG Assistant MCP Server
Main entry point for the MCP server
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.mcp_server.mcp_server import TTRPGMCPServer
from src.utils.config import ConfigManager, setup_logging


async def main():
    """Main entry point"""
    try:
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # Setup logging
        setup_logging(config.logging)
        
        # Create and run server
        server = TTRPGMCPServer(config)
        await server.run()
        
    except KeyboardInterrupt:
        print("\\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())