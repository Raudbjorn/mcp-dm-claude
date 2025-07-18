import asyncio
import logging
from typing import Dict, List, Any, Optional
import json
from pathlib import Path

from mcp import Server, types
from mcp.server import NotificationOptions, stdio

from ..pdf_parser.pdf_parser import PDFParser
from ..embedding_service.embedding_service import EmbeddingService
from ..redis_manager.redis_manager import RedisDataManager
from ..personality_service.personality_manager import PersonalityManager
from ..utils.config import Config


class TTRPGMCPServer:
    """Main MCP server for TTRPG Assistant"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.pdf_parser = PDFParser(
            preserve_formatting=config.pdf_processing.preserve_formatting,
            ocr_enabled=config.pdf_processing.ocr_enabled
        )
        
        self.embedding_service = EmbeddingService(
            model_name=config.embedding.model,
            cache_embeddings=config.embedding.cache_embeddings
        )
        
        self.redis_manager = RedisDataManager(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password
        )
        
        self.personality_manager = PersonalityManager(self.redis_manager)
        
        # Initialize MCP server
        self.server = Server(config.mcp.server_name)
        self._setup_tools()
    
    def _setup_tools(self):
        """Set up MCP tools"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            return [
                types.Tool(
                    name="search_rulebook",
                    description="Search TTRPG rulebooks for rules, spells, monsters, etc.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "rulebook": {
                                "type": "string",
                                "description": "Optional specific rulebook to search in"
                            },
                            "content_type": {
                                "type": "string",
                                "enum": ["rule", "spell", "monster", "item", "any"],
                                "description": "Type of content to search for"
                            },
                            "max_results": {
                                "type": "integer",
                                "default": 5,
                                "description": "Maximum number of results to return"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="manage_campaign",
                    description="Store, retrieve, or update campaign data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["create", "read", "update", "delete", "list"],
                                "description": "Action to perform"
                            },
                            "campaign_id": {
                                "type": "string",
                                "description": "Campaign identifier"
                            },
                            "data_type": {
                                "type": "string",
                                "enum": ["character", "npc", "location", "plot", "session"],
                                "description": "Type of campaign data"
                            },
                            "data_id": {
                                "type": "string",
                                "description": "Specific data ID (for update/delete operations)"
                            },
                            "data": {
                                "type": "object",
                                "description": "Campaign data payload"
                            }
                        },
                        "required": ["action", "campaign_id"]
                    }
                ),
                types.Tool(
                    name="add_rulebook",
                    description="Process and add a new PDF rulebook to the system",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pdf_path": {
                                "type": "string",
                                "description": "Path to PDF file"
                            },
                            "rulebook_name": {
                                "type": "string",
                                "description": "Display name for the rulebook"
                            },
                            "system": {
                                "type": "string",
                                "description": "Game system (D&D 5e, Pathfinder, etc.)"
                            }
                        },
                        "required": ["pdf_path", "rulebook_name", "system"]
                    }
                ),
                types.Tool(
                    name="manage_personality",
                    description="Manage RPG personality profiles and vernacular",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["get", "list", "summary", "vernacular", "compare", "stats"],
                                "description": "Action to perform"
                            },
                            "system_name": {
                                "type": "string",
                                "description": "RPG system name"
                            },
                            "systems": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of systems for comparison"
                            }
                        },
                        "required": ["action"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle tool calls"""
            try:
                if name == "search_rulebook":
                    return await self._handle_search_rulebook(arguments)
                elif name == "manage_campaign":
                    return await self._handle_manage_campaign(arguments)
                elif name == "add_rulebook":
                    return await self._handle_add_rulebook(arguments)
                elif name == "manage_personality":
                    return await self._handle_manage_personality(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            
            except Exception as e:
                self.logger.error(f"Error handling tool call {name}: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    async def _handle_search_rulebook(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle search_rulebook tool calls"""
        query = arguments.get("query", "")
        rulebook = arguments.get("rulebook")
        content_type = arguments.get("content_type", "any")
        max_results = arguments.get("max_results", self.config.search.default_max_results)
        
        if not query:
            return [types.TextContent(
                type="text",
                text="Error: Query parameter is required"
            )]
        
        # Build filters
        filters = {}
        if rulebook:
            filters["rulebook"] = rulebook
        if content_type != "any":
            filters["content_type"] = content_type
        
        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query)
        
        # Perform vector search
        vector_results = []
        if query_embedding:
            vector_results = self.redis_manager.vector_search(
                query_embedding=query_embedding,
                filters=filters,
                max_results=max_results,
                similarity_threshold=self.config.search.similarity_threshold
            )
        
        # Perform keyword search as fallback
        keyword_results = []
        if self.config.search.enable_keyword_fallback and not vector_results:
            keyword_results = self.redis_manager.keyword_search(
                query=query,
                filters=filters
            )[:max_results]
        
        # Combine results
        all_results = vector_results + keyword_results
        
        # Format response with personality awareness
        if not all_results:
            # Try to get personality for no-results message
            no_results_msg = f"No results found for query: '{query}'"
            
            # If we have results, get the system from the first result to add personality
            if all_results:
                system_name = all_results[0].content_chunk.system
                personality_prompt = self.personality_manager.generate_personality_prompt(
                    system_name, query, "No results found"
                )
                if personality_prompt:
                    personality_summary = self.personality_manager.get_personality_summary(system_name)
                    if personality_summary:
                        no_results_msg = f"I regret to inform you that my search through the {system_name} archives has yielded no results for '{query}'. Perhaps you might try a different approach or terminology?"
            
            return [types.TextContent(
                type="text",
                text=no_results_msg
            )]
        
        # Get system name from first result for personality context
        system_name = all_results[0].content_chunk.system
        personality_summary = self.personality_manager.get_personality_summary(system_name)
        
        # Build response with personality awareness
        response_parts = []
        
        # Add personality-aware introduction
        if personality_summary:
            if personality_summary["tone"] == "mysterious":
                response_parts.append(f"The ancient texts reveal {len(all_results)} secrets regarding '{query}'...\\n")
            elif personality_summary["tone"] == "authoritative":
                response_parts.append(f"I have located {len(all_results)} relevant entries for '{query}' in the official records:\\n")
            elif personality_summary["tone"] == "formal":
                response_parts.append(f"According to the documented sources, {len(all_results)} references to '{query}' have been found:\\n")
            else:
                response_parts.append(f"Found {len(all_results)} results for: '{query}'\\n")
        else:
            response_parts.append(f"Found {len(all_results)} results for: '{query}'\\n")
        
        for i, result in enumerate(all_results[:max_results], 1):
            chunk = result.content_chunk
            
            # Format entry with personality awareness
            if personality_summary and personality_summary["tone"] == "mysterious":
                response_parts.append(f"**{i}. {chunk.title}** (From the {chunk.rulebook} tome)")
            elif personality_summary and personality_summary["tone"] == "formal":
                response_parts.append(f"**{i}. {chunk.title}** (Reference: {chunk.rulebook})")
            else:
                response_parts.append(f"**{i}. {chunk.title}** ({chunk.rulebook})")
            
            response_parts.append(f"   Page {chunk.page_number} | {chunk.system} | {chunk.content_type}")
            response_parts.append(f"   Relevance: {result.relevance_score:.2f} ({result.match_type})")
            response_parts.append(f"   Section: {' > '.join(chunk.section_path)}")
            response_parts.append("")
            
            # Add content preview
            content_preview = chunk.content[:300] + "..." if len(chunk.content) > 300 else chunk.content
            response_parts.append(f"   {content_preview}")
            response_parts.append("")
        
        # Add personality-aware conclusion
        if personality_summary:
            vernacular = self.personality_manager.get_vernacular_for_system(system_name)
            if vernacular and len(vernacular) > 0:
                response_parts.append("\\n**Relevant Terminology:**")
                for term in vernacular[:3]:  # Show top 3 relevant terms
                    if term["term"].lower() in query.lower():
                        response_parts.append(f"- {term['term']}: {term['definition']}")
        
        return [types.TextContent(
            type="text",
            text="\\n".join(response_parts)
        )]
    
    async def _handle_manage_campaign(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle manage_campaign tool calls"""
        action = arguments.get("action")
        campaign_id = arguments.get("campaign_id")
        data_type = arguments.get("data_type")
        data_id = arguments.get("data_id")
        data = arguments.get("data", {})
        
        if not action or not campaign_id:
            return [types.TextContent(
                type="text",
                text="Error: action and campaign_id are required"
            )]
        
        try:
            if action == "create":
                if not data_type or not data:
                    return [types.TextContent(
                        type="text",
                        text="Error: data_type and data are required for create action"
                    )]
                
                created_id = self.redis_manager.store_campaign_data(
                    campaign_id=campaign_id,
                    data_type=data_type,
                    data=data
                )
                
                return [types.TextContent(
                    type="text",
                    text=f"Created {data_type} with ID: {created_id}"
                )]
            
            elif action == "read":
                campaign_data = self.redis_manager.get_campaign_data(
                    campaign_id=campaign_id,
                    data_type=data_type
                )
                
                if not campaign_data:
                    return [types.TextContent(
                        type="text",
                        text=f"No data found for campaign: {campaign_id}"
                    )]
                
                response = f"Campaign data for: {campaign_id}\\n\\n"
                for item in campaign_data:
                    response += f"**{item['data_type']}: {item['name']}** (ID: {item['id']})\\n"
                    response += f"Created: {item['created_at']}\\n"
                    response += f"Updated: {item['updated_at']}\\n"
                    response += f"Content: {json.dumps(item['content'], indent=2)}\\n\\n"
                
                return [types.TextContent(
                    type="text",
                    text=response
                )]
            
            elif action == "update":
                if not data_id:
                    return [types.TextContent(
                        type="text",
                        text="Error: data_id is required for update action"
                    )]
                
                success = self.redis_manager.update_campaign_data(
                    campaign_id=campaign_id,
                    data_id=data_id,
                    updates=data
                )
                
                if success:
                    return [types.TextContent(
                        type="text",
                        text=f"Updated campaign data: {data_id}"
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"Failed to update campaign data: {data_id}"
                    )]
            
            elif action == "delete":
                if not data_id:
                    return [types.TextContent(
                        type="text",
                        text="Error: data_id is required for delete action"
                    )]
                
                success = self.redis_manager.delete_campaign_data(
                    campaign_id=campaign_id,
                    data_id=data_id
                )
                
                if success:
                    return [types.TextContent(
                        type="text",
                        text=f"Deleted campaign data: {data_id}"
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"Failed to delete campaign data: {data_id}"
                    )]
            
            elif action == "list":
                campaign_data = self.redis_manager.get_campaign_data(
                    campaign_id=campaign_id,
                    data_type=data_type
                )
                
                if not campaign_data:
                    return [types.TextContent(
                        type="text",
                        text=f"No data found for campaign: {campaign_id}"
                    )]
                
                response = f"Campaign data summary for: {campaign_id}\\n\\n"
                for item in campaign_data:
                    response += f"- {item['data_type']}: {item['name']} (ID: {item['id']})\\n"
                
                return [types.TextContent(
                    type="text",
                    text=response
                )]
            
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Error: Unknown action: {action}"
                )]
        
        except Exception as e:
            self.logger.error(f"Error in manage_campaign: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
    
    async def _handle_add_rulebook(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle add_rulebook tool calls"""
        pdf_path = arguments.get("pdf_path")
        rulebook_name = arguments.get("rulebook_name")
        system = arguments.get("system")
        
        if not pdf_path or not rulebook_name or not system:
            return [types.TextContent(
                type="text",
                text="Error: pdf_path, rulebook_name, and system are required"
            )]
        
        try:
            # Check if PDF exists
            if not Path(pdf_path).exists():
                return [types.TextContent(
                    type="text",
                    text=f"Error: PDF file not found: {pdf_path}"
                )]
            
            # Check file size
            file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
            if file_size_mb > self.config.pdf_processing.max_file_size_mb:
                return [types.TextContent(
                    type="text",
                    text=f"Error: PDF file too large: {file_size_mb:.1f}MB (max: {self.config.pdf_processing.max_file_size_mb}MB)"
                )]
            
            # Extract text from PDF
            self.logger.info(f"Processing PDF: {pdf_path}")
            extracted_data = self.pdf_parser.extract_text(pdf_path)
            
            # Identify sections
            sections = self.pdf_parser.identify_sections(extracted_data)
            
            # Create content chunks
            chunks = self.pdf_parser.create_chunks(sections, rulebook_name, system)
            
            # Generate embeddings
            self.logger.info(f"Generating embeddings for {len(chunks)} chunks")
            texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_service.batch_embed(texts)
            
            # Assign embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
            
            # Store in Redis
            self.logger.info(f"Storing {len(chunks)} chunks in Redis")
            self.redis_manager.store_rulebook_content(chunks)
            
            # Extract and store personality profile
            self.logger.info(f"Extracting personality profile for {system}")
            personality = self.personality_manager.extract_and_store_personality(chunks, system)
            
            # Get statistics
            stats = self.redis_manager.get_rulebook_stats()
            
            personality_info = ""
            if personality:
                personality_info = f"\\n- Personality extracted: {personality.personality_name} ({personality.tone} tone)\\n- Vernacular terms found: {len(personality.vernacular_patterns)}"
            
            return [types.TextContent(
                type="text",
                text=f"Successfully processed rulebook: {rulebook_name}\\n"
                     f"- System: {system}\\n"
                     f"- Chunks created: {len(chunks)}\\n"
                     f"- Pages processed: {extracted_data.get('total_pages', 0)}\\n"
                     f"- Total chunks in database: {stats.get('total_chunks', 0)}"
                     f"{personality_info}"
            )]
        
        except Exception as e:
            self.logger.error(f"Error processing rulebook: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error processing rulebook: {str(e)}"
            )]
    
    async def _handle_manage_personality(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle manage_personality tool calls"""
        action = arguments.get("action")
        system_name = arguments.get("system_name")
        systems = arguments.get("systems", [])
        
        if not action:
            return [types.TextContent(
                type="text",
                text="Error: action parameter is required"
            )]
        
        try:
            if action == "get":
                if not system_name:
                    return [types.TextContent(
                        type="text",
                        text="Error: system_name is required for get action"
                    )]
                
                personality = self.personality_manager.get_personality(system_name)
                if not personality:
                    return [types.TextContent(
                        type="text",
                        text=f"No personality profile found for {system_name}"
                    )]
                
                response = f"**Personality Profile: {personality.personality_name}**\\n"
                response += f"System: {personality.system_name}\\n"
                response += f"Description: {personality.description}\\n\\n"
                response += f"**Traits:**\\n"
                response += f"- Tone: {personality.tone}\\n"
                response += f"- Perspective: {personality.perspective}\\n"
                response += f"- Formality: {personality.formality_level}\\n"
                response += f"- Confidence: {personality.confidence_score:.2f}\\n\\n"
                response += f"**Context:** {personality.system_context}\\n\\n"
                
                if personality.example_phrases:
                    response += f"**Example Phrases:**\\n"
                    for phrase in personality.example_phrases[:5]:
                        response += f"- {phrase}\\n"
                
                return [types.TextContent(
                    type="text",
                    text=response
                )]
            
            elif action == "list":
                personalities = self.personality_manager.list_personalities()
                
                if not personalities:
                    return [types.TextContent(
                        type="text",
                        text="No personality profiles found"
                    )]
                
                response = f"**Available Personality Profiles ({len(personalities)}):**\\n\\n"
                for system in personalities:
                    summary = self.personality_manager.get_personality_summary(system)
                    if summary:
                        response += f"**{system}:** {summary['personality_name']}\\n"
                        response += f"  - {summary['description']}\\n"
                        response += f"  - Tone: {summary['tone']}, Formality: {summary['formality_level']}\\n"
                        response += f"  - Vernacular terms: {summary['vernacular_count']}\\n\\n"
                
                return [types.TextContent(
                    type="text",
                    text=response
                )]
            
            elif action == "summary":
                if not system_name:
                    return [types.TextContent(
                        type="text",
                        text="Error: system_name is required for summary action"
                    )]
                
                summary = self.personality_manager.get_personality_summary(system_name)
                if not summary:
                    return [types.TextContent(
                        type="text",
                        text=f"No personality profile found for {system_name}"
                    )]
                
                response = f"**{summary['personality_name']}** ({summary['system_name']})\\n"
                response += f"{summary['description']}\\n\\n"
                response += f"**Style:** {summary['tone']} tone, {summary['formality_level']} formality\\n"
                response += f"**Perspective:** {summary['perspective']}\\n"
                response += f"**Confidence:** {summary['confidence_score']:.2f}\\n"
                response += f"**Vernacular terms:** {summary['vernacular_count']}\\n"
                response += f"**Context:** {summary['system_context']}\\n\\n"
                
                if summary['example_phrases']:
                    response += f"**Example phrases:**\\n"
                    for phrase in summary['example_phrases']:
                        response += f"- {phrase}\\n"
                
                return [types.TextContent(
                    type="text",
                    text=response
                )]
            
            elif action == "vernacular":
                if not system_name:
                    return [types.TextContent(
                        type="text",
                        text="Error: system_name is required for vernacular action"
                    )]
                
                vernacular = self.personality_manager.get_vernacular_for_system(system_name)
                if not vernacular:
                    return [types.TextContent(
                        type="text",
                        text=f"No vernacular found for {system_name}"
                    )]
                
                response = f"**Vernacular for {system_name} ({len(vernacular)} terms):**\\n\\n"
                
                # Group by category
                categories = {}
                for term in vernacular:
                    category = term['category']
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(term)
                
                for category, terms in categories.items():
                    response += f"**{category.title()} Terms:**\\n"
                    for term in terms[:10]:  # Limit to 10 per category
                        response += f"- **{term['term']}**: {term['definition']}\\n"
                        if term['examples']:
                            response += f"  Example: {term['examples'][0][:100]}...\\n"
                    response += "\\n"
                
                return [types.TextContent(
                    type="text",
                    text=response
                )]
            
            elif action == "compare":
                if not systems or len(systems) < 2:
                    return [types.TextContent(
                        type="text",
                        text="Error: at least 2 systems are required for comparison"
                    )]
                
                comparison = self.personality_manager.create_personality_comparison(systems)
                
                response = f"**Personality Comparison:**\\n\\n"
                
                # Create comparison table
                response += "| System | Personality | Tone | Perspective | Formality | Vernacular |\\n"
                response += "|--------|-------------|------|-------------|-----------|------------|\\n"
                
                for system in systems:
                    if system in comparison["comparison_matrix"]:
                        data = comparison["comparison_matrix"][system]
                        summary = self.personality_manager.get_personality_summary(system)
                        personality_name = summary["personality_name"] if summary else "Unknown"
                        
                        response += f"| {system} | {personality_name} | {data['tone']} | {data['perspective']} | {data['formality']} | {data['vernacular_count']} |\\n"
                
                return [types.TextContent(
                    type="text",
                    text=response
                )]
            
            elif action == "stats":
                stats = self.personality_manager.get_personality_stats()
                
                response = f"**Personality Statistics:**\\n\\n"
                response += f"Total personalities: {stats.get('total_personalities', 0)}\\n"
                response += f"Average confidence: {stats.get('average_confidence', 0):.2f}\\n"
                response += f"Total vernacular terms: {stats.get('total_vernacular_terms', 0)}\\n\\n"
                
                if stats.get('personalities_by_tone'):
                    response += "**By Tone:**\\n"
                    for tone, count in stats['personalities_by_tone'].items():
                        response += f"- {tone}: {count}\\n"
                    response += "\\n"
                
                if stats.get('personalities_by_formality'):
                    response += "**By Formality:**\\n"
                    for formality, count in stats['personalities_by_formality'].items():
                        response += f"- {formality}: {count}\\n"
                
                return [types.TextContent(
                    type="text",
                    text=response
                )]
            
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Error: Unknown action: {action}"
                )]
        
        except Exception as e:
            self.logger.error(f"Error in manage_personality: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
    
    async def run(self):
        """Run the MCP server"""
        try:
            self.logger.info("Starting TTRPG MCP Server...")
            
            # Setup vector index
            self.redis_manager.setup_vector_index(
                self.redis_manager.RULEBOOK_INDEX,
                {}  # Schema would be defined here for full Redis Stack
            )
            
            # Run server
            async with stdio.stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name=self.config.mcp.server_name,
                        server_version=self.config.mcp.version,
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={}
                        )
                    )
                )
        
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            raise


# For backwards compatibility
from mcp.server.models import InitializationOptions