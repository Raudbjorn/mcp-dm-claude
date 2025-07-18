#!/usr/bin/env python3
"""
TTRPG Assistant CLI
Command-line interface for testing and managing the TTRPG Assistant
"""

import click
import sys
import asyncio
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.pdf_parser.pdf_parser import PDFParser
from src.embedding_service.embedding_service import EmbeddingService
from src.redis_manager.redis_manager import RedisDataManager
from src.personality_service.personality_manager import PersonalityManager
from src.utils.config import ConfigManager, setup_logging


@click.group()
@click.option('--config', default='config.yaml', help='Configuration file path')
@click.pass_context
def cli(ctx, config):
    """TTRPG Assistant CLI"""
    ctx.ensure_object(dict)
    
    # Load configuration
    config_manager = ConfigManager(config)
    ctx.obj['config'] = config_manager.load_config()
    
    # Setup logging
    setup_logging(ctx.obj['config'].logging)


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True))
@click.argument('rulebook_name')
@click.argument('system')
@click.pass_context
def add_rulebook(ctx, pdf_path, rulebook_name, system):
    """Add a new rulebook to the database"""
    config = ctx.obj['config']
    
    try:
        # Initialize components
        pdf_parser = PDFParser(
            preserve_formatting=config.pdf_processing.preserve_formatting,
            ocr_enabled=config.pdf_processing.ocr_enabled
        )
        
        embedding_service = EmbeddingService(
            model_name=config.embedding.model,
            cache_embeddings=config.embedding.cache_embeddings
        )
        
        redis_manager = RedisDataManager(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password
        )
        
        # Process PDF
        click.echo(f"Processing PDF: {pdf_path}")
        extracted_data = pdf_parser.extract_text(pdf_path)
        
        # Identify sections
        click.echo("Identifying sections...")
        sections = pdf_parser.identify_sections(extracted_data)
        
        # Create chunks
        click.echo("Creating content chunks...")
        chunks = pdf_parser.create_chunks(sections, rulebook_name, system)
        
        # Generate embeddings
        click.echo(f"Generating embeddings for {len(chunks)} chunks...")
        texts = [chunk.content for chunk in chunks]
        embeddings = embedding_service.batch_embed(texts)
        
        # Assign embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        # Store in Redis
        click.echo("Storing in database...")
        redis_manager.store_rulebook_content(chunks)
        
        # Extract personality profile
        click.echo("Extracting personality profile...")
        personality_manager = PersonalityManager(redis_manager)
        personality = personality_manager.extract_and_store_personality(chunks, system)
        
        # Get statistics
        stats = redis_manager.get_rulebook_stats()
        
        click.echo(f"✓ Successfully processed rulebook: {rulebook_name}")
        click.echo(f"  - System: {system}")
        click.echo(f"  - Chunks created: {len(chunks)}")
        click.echo(f"  - Pages processed: {extracted_data.get('total_pages', 0)}")
        click.echo(f"  - Total chunks in database: {stats.get('total_chunks', 0)}")
        
        if personality:
            click.echo(f"  - Personality extracted: {personality.personality_name} ({personality.tone} tone)")
            click.echo(f"  - Vernacular terms found: {len(personality.vernacular_patterns)}")
            click.echo(f"  - Confidence score: {personality.confidence_score:.2f}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('query')
@click.option('--rulebook', help='Specific rulebook to search')
@click.option('--content-type', help='Content type filter')
@click.option('--max-results', default=5, help='Maximum results to return')
@click.pass_context
def search(ctx, query, rulebook, content_type, max_results):
    """Search rulebooks for content"""
    config = ctx.obj['config']
    
    try:
        # Initialize components
        embedding_service = EmbeddingService(
            model_name=config.embedding.model,
            cache_embeddings=config.embedding.cache_embeddings
        )
        
        redis_manager = RedisDataManager(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password
        )
        
        # Build filters
        filters = {}
        if rulebook:
            filters["rulebook"] = rulebook
        if content_type:
            filters["content_type"] = content_type
        
        # Generate query embedding
        query_embedding = embedding_service.generate_embedding(query)
        
        # Perform search
        results = []
        if query_embedding:
            results = redis_manager.vector_search(
                query_embedding=query_embedding,
                filters=filters,
                max_results=max_results,
                similarity_threshold=config.search.similarity_threshold
            )
        
        # Fallback to keyword search
        if not results and config.search.enable_keyword_fallback:
            results = redis_manager.keyword_search(
                query=query,
                filters=filters
            )[:max_results]
        
        # Display results
        if not results:
            click.echo(f"No results found for: '{query}'")
            return
        
        click.echo(f"Found {len(results)} results for: '{query}'\\n")
        
        for i, result in enumerate(results, 1):
            chunk = result.content_chunk
            click.echo(f"{i}. {chunk.title} ({chunk.rulebook})")
            click.echo(f"   Page {chunk.page_number} | {chunk.system} | {chunk.content_type}")
            click.echo(f"   Relevance: {result.relevance_score:.2f} ({result.match_type})")
            click.echo(f"   Section: {' > '.join(chunk.section_path)}")
            click.echo()
            
            # Content preview
            content_preview = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
            click.echo(f"   {content_preview}")
            click.echo()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def stats(ctx):
    """Show database statistics"""
    config = ctx.obj['config']
    
    try:
        redis_manager = RedisDataManager(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password
        )
        
        stats = redis_manager.get_rulebook_stats()
        
        click.echo("Database Statistics:")
        click.echo(f"  Total chunks: {stats.get('total_chunks', 0)}")
        click.echo()
        
        click.echo("Rulebooks:")
        for rulebook, count in stats.get('rulebooks', {}).items():
            click.echo(f"  - {rulebook}: {count} chunks")
        click.echo()
        
        click.echo("Systems:")
        for system, count in stats.get('systems', {}).items():
            click.echo(f"  - {system}: {count} chunks")
        click.echo()
        
        click.echo("Content Types:")
        for content_type, count in stats.get('content_types', {}).items():
            click.echo(f"  - {content_type}: {count} chunks")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('campaign_id')
@click.argument('data_type')
@click.argument('name')
@click.option('--data', help='JSON data for the campaign item')
@click.pass_context
def add_campaign_data(ctx, campaign_id, data_type, name, data):
    """Add campaign data"""
    config = ctx.obj['config']
    
    try:
        import json
        
        redis_manager = RedisDataManager(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password
        )
        
        # Parse data
        data_dict = {"name": name}
        if data:
            data_dict.update(json.loads(data))
        
        # Store campaign data
        data_id = redis_manager.store_campaign_data(
            campaign_id=campaign_id,
            data_type=data_type,
            data=data_dict
        )
        
        click.echo(f"✓ Added {data_type} '{name}' to campaign {campaign_id}")
        click.echo(f"  ID: {data_id}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('campaign_id')
@click.option('--data-type', help='Filter by data type')
@click.pass_context
def list_campaign_data(ctx, campaign_id, data_type):
    """List campaign data"""
    config = ctx.obj['config']
    
    try:
        redis_manager = RedisDataManager(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password
        )
        
        # Get campaign data
        campaign_data = redis_manager.get_campaign_data(
            campaign_id=campaign_id,
            data_type=data_type
        )
        
        if not campaign_data:
            click.echo(f"No data found for campaign: {campaign_id}")
            return
        
        click.echo(f"Campaign data for: {campaign_id}\\n")
        
        for item in campaign_data:
            click.echo(f"• {item['data_type']}: {item['name']} (ID: {item['id']})")
            click.echo(f"  Created: {item['created_at']}")
            click.echo(f"  Updated: {item['updated_at']}")
            click.echo()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('system_name')
@click.pass_context
def show_personality(ctx, system_name):
    """Show personality profile for a system"""
    config = ctx.obj['config']
    
    try:
        redis_manager = RedisDataManager(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password
        )
        
        personality_manager = PersonalityManager(redis_manager)
        personality = personality_manager.get_personality(system_name)
        
        if not personality:
            click.echo(f"No personality profile found for {system_name}")
            return
        
        click.echo(f"Personality Profile: {personality.personality_name}")
        click.echo(f"System: {personality.system_name}")
        click.echo(f"Description: {personality.description}")
        click.echo()
        click.echo(f"Traits:")
        click.echo(f"  - Tone: {personality.tone}")
        click.echo(f"  - Perspective: {personality.perspective}")
        click.echo(f"  - Formality: {personality.formality_level}")
        click.echo(f"  - Confidence: {personality.confidence_score:.2f}")
        click.echo()
        click.echo(f"Context: {personality.system_context}")
        click.echo()
        
        if personality.example_phrases:
            click.echo("Example Phrases:")
            for phrase in personality.example_phrases[:5]:
                click.echo(f"  - {phrase}")
        
        if personality.vernacular_patterns:
            click.echo(f"\\nVernacular Terms ({len(personality.vernacular_patterns)}):")
            for pattern in personality.vernacular_patterns[:10]:
                click.echo(f"  - {pattern.term}: {pattern.definition}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def list_personalities(ctx):
    """List all personality profiles"""
    config = ctx.obj['config']
    
    try:
        redis_manager = RedisDataManager(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password
        )
        
        personality_manager = PersonalityManager(redis_manager)
        personalities = personality_manager.list_personalities()
        
        if not personalities:
            click.echo("No personality profiles found")
            return
        
        click.echo(f"Available Personality Profiles ({len(personalities)}):")
        click.echo()
        
        for system in personalities:
            summary = personality_manager.get_personality_summary(system)
            if summary:
                click.echo(f"{system}: {summary['personality_name']}")
                click.echo(f"  - {summary['description']}")
                click.echo(f"  - Tone: {summary['tone']}, Formality: {summary['formality_level']}")
                click.echo(f"  - Vernacular terms: {summary['vernacular_count']}")
                click.echo()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('system_name')
@click.pass_context
def show_vernacular(ctx, system_name):
    """Show vernacular terms for a system"""
    config = ctx.obj['config']
    
    try:
        redis_manager = RedisDataManager(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password
        )
        
        personality_manager = PersonalityManager(redis_manager)
        vernacular = personality_manager.get_vernacular_for_system(system_name)
        
        if not vernacular:
            click.echo(f"No vernacular found for {system_name}")
            return
        
        click.echo(f"Vernacular for {system_name} ({len(vernacular)} terms):")
        click.echo()
        
        # Group by category
        categories = {}
        for term in vernacular:
            category = term['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(term)
        
        for category, terms in categories.items():
            click.echo(f"{category.title()} Terms:")
            for term in terms[:10]:  # Limit to 10 per category
                click.echo(f"  - {term['term']}: {term['definition']}")
                if term['examples']:
                    click.echo(f"    Example: {term['examples'][0][:100]}...")
            click.echo()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('systems', nargs=-1, required=True)
@click.pass_context
def compare_personalities(ctx, systems):
    """Compare personality profiles across systems"""
    config = ctx.obj['config']
    
    if len(systems) < 2:
        click.echo("At least 2 systems are required for comparison")
        sys.exit(1)
    
    try:
        redis_manager = RedisDataManager(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password
        )
        
        personality_manager = PersonalityManager(redis_manager)
        comparison = personality_manager.create_personality_comparison(systems)
        
        click.echo("Personality Comparison:")
        click.echo()
        
        # Print comparison table
        click.echo("| System | Personality | Tone | Perspective | Formality | Vernacular |")
        click.echo("|--------|-------------|------|-------------|-----------|------------|")
        
        for system in systems:
            if system in comparison["comparison_matrix"]:
                data = comparison["comparison_matrix"][system]
                summary = personality_manager.get_personality_summary(system)
                personality_name = summary["personality_name"] if summary else "Unknown"
                
                click.echo(f"| {system} | {personality_name} | {data['tone']} | {data['perspective']} | {data['formality']} | {data['vernacular_count']} |")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def personality_stats(ctx):
    """Show personality statistics"""
    config = ctx.obj['config']
    
    try:
        redis_manager = RedisDataManager(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password
        )
        
        personality_manager = PersonalityManager(redis_manager)
        stats = personality_manager.get_personality_stats()
        
        click.echo("Personality Statistics:")
        click.echo()
        click.echo(f"Total personalities: {stats.get('total_personalities', 0)}")
        click.echo(f"Average confidence: {stats.get('average_confidence', 0):.2f}")
        click.echo(f"Total vernacular terms: {stats.get('total_vernacular_terms', 0)}")
        click.echo()
        
        if stats.get('personalities_by_tone'):
            click.echo("By Tone:")
            for tone, count in stats['personalities_by_tone'].items():
                click.echo(f"  - {tone}: {count}")
            click.echo()
        
        if stats.get('personalities_by_formality'):
            click.echo("By Formality:")
            for formality, count in stats['personalities_by_formality'].items():
                click.echo(f"  - {formality}: {count}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def server(ctx):
    """Start the MCP server"""
    config = ctx.obj['config']
    
    try:
        from src.mcp_server.mcp_server import TTRPGMCPServer
        
        async def run_server():
            server = TTRPGMCPServer(config)
            await server.run()
        
        asyncio.run(run_server())
        
    except KeyboardInterrupt:
        click.echo("\\nServer stopped by user")
    except Exception as e:
        click.echo(f"Server error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()