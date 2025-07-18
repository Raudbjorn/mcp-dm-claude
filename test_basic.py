#!/usr/bin/env python3
"""
Basic test script to verify the TTRPG Assistant components work
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.embedding_service.embedding_service import EmbeddingService
from src.utils.config import ConfigManager, setup_logging


def test_embedding_service():
    """Test the embedding service"""
    print("Testing Embedding Service...")
    
    try:
        # Create embedding service
        embedding_service = EmbeddingService(
            model_name="all-MiniLM-L6-v2",
            cache_embeddings=False
        )
        
        # Test single embedding
        text = "This is a test of the fireball spell"
        embedding = embedding_service.generate_embedding(text)
        
        print(f"✓ Generated embedding for text: '{text}'")
        print(f"  - Embedding dimension: {len(embedding)}")
        print(f"  - First 5 values: {embedding[:5]}")
        
        # Test batch embedding
        texts = [
            "Fireball is a 3rd level spell",
            "Dragons are powerful monsters",
            "Sword +1 is a magic item"
        ]
        
        embeddings = embedding_service.batch_embed(texts)
        print(f"✓ Generated {len(embeddings)} embeddings in batch")
        
        # Test similarity
        similarity = embedding_service.similarity(embeddings[0], embeddings[1])
        print(f"✓ Similarity between first two texts: {similarity:.3f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in embedding service: {e}")
        return False


def test_config():
    """Test configuration loading"""
    print("\\nTesting Configuration...")
    
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        print(f"✓ Loaded configuration")
        print(f"  - Redis host: {config.redis.host}")
        print(f"  - Embedding model: {config.embedding.model}")
        print(f"  - MCP server name: {config.mcp.server_name}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False


def test_pdf_parser():
    """Test PDF parser (without actual PDF)"""
    print("\\nTesting PDF Parser...")
    
    try:
        from src.pdf_parser.pdf_parser import PDFParser
        
        parser = PDFParser()
        print("✓ PDF parser initialized successfully")
        
        # Test chunk creation with dummy data
        from src.models.data_models import Section
        
        test_section = Section(
            title="Test Section",
            content="This is a test section about fireballs and dragons.",
            page_start=1,
            page_end=1,
            level=1,
            parent_sections=[]
        )
        
        chunks = parser.create_chunks([test_section], "Test Book", "Test System")
        print(f"✓ Created {len(chunks)} chunks from test section")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in PDF parser: {e}")
        return False


def main():
    """Run all tests"""
    print("TTRPG Assistant - Basic Component Tests")
    print("=" * 50)
    
    # Setup basic logging
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    tests = [
        test_config,
        test_embedding_service,
        test_pdf_parser
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("✓ All tests passed! The system is ready to use.")
        print("\\nNext steps:")
        print("1. Start Redis server: redis-server")
        print("2. Add a rulebook: python cli.py add-rulebook <pdf_path> <name> <system>")
        print("3. Search: python cli.py search <query>")
        print("4. Start MCP server: python main.py")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()