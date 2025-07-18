import redis
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import time
from dataclasses import asdict

from ..models.data_models import ContentChunk, CampaignData, SearchResult


class RedisDataManager:
    """Handles all Redis operations for both vector and traditional data"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, 
                 password: Optional[str] = None, max_retries: int = 3):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        
        # Initialize Redis connection
        self.redis_client = self._create_connection()
        
        # Index names
        self.RULEBOOK_INDEX = "rulebooks_idx"
        self.CAMPAIGN_PREFIX = "campaign:"
        self.CHUNK_PREFIX = "chunk:"
    
    def _create_connection(self) -> redis.Redis:
        """Create Redis connection with retry logic"""
        for attempt in range(self.max_retries):
            try:
                client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    socket_timeout=10,
                    socket_connect_timeout=10
                )
                
                # Test connection
                client.ping()
                self.logger.info("Successfully connected to Redis")
                return client
                
            except redis.ConnectionError as e:
                self.logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        
        raise redis.ConnectionError("Failed to connect to Redis after maximum retries")
    
    def setup_vector_index(self, index_name: str, schema: Dict) -> None:
        """Create vector search index"""
        try:
            # Check if index already exists
            try:
                self.redis_client.ft(index_name).info()
                self.logger.info(f"Vector index '{index_name}' already exists")
                return
            except:
                pass  # Index doesn't exist, create it
            
            # Create index for vector search
            # Note: This is a simplified implementation
            # In a real Redis Stack deployment, you would use redis-py's search module
            # For now, we'll store embeddings as JSON and implement similarity search manually
            
            self.logger.info(f"Vector index '{index_name}' would be created here")
            # In a full implementation, you would use:
            # self.redis_client.ft(index_name).create_index(schema)
            
        except Exception as e:
            self.logger.error(f"Error setting up vector index: {e}")
            raise
    
    def store_rulebook_content(self, content: List[ContentChunk]) -> None:
        """Store parsed rulebook with embeddings"""
        try:
            pipe = self.redis_client.pipeline()
            
            for chunk in content:
                chunk_key = f"{self.CHUNK_PREFIX}{chunk.id}"
                
                # Convert chunk to dictionary for storage
                chunk_data = {
                    "id": chunk.id,
                    "rulebook": chunk.rulebook,
                    "system": chunk.system,
                    "content_type": chunk.content_type,
                    "title": chunk.title,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "section_path": chunk.section_path,
                    "embedding": chunk.embedding,
                    "metadata": chunk.metadata,
                    "tables": [asdict(table) for table in chunk.tables] if chunk.tables else []
                }
                
                # Store chunk data
                pipe.hset(chunk_key, mapping={
                    "data": json.dumps(chunk_data),
                    "rulebook": chunk.rulebook,
                    "system": chunk.system,
                    "content_type": chunk.content_type,
                    "title": chunk.title
                })
                
                # Add to rulebook index
                pipe.sadd(f"rulebook:{chunk.rulebook}", chunk_key)
                pipe.sadd(f"system:{chunk.system}", chunk_key)
                pipe.sadd(f"content_type:{chunk.content_type}", chunk_key)
            
            pipe.execute()
            self.logger.info(f"Stored {len(content)} content chunks")
            
        except Exception as e:
            self.logger.error(f"Error storing rulebook content: {e}")
            raise
    
    def vector_search(self, query_embedding: List[float], 
                     filters: Optional[Dict] = None, 
                     max_results: int = 10,
                     similarity_threshold: float = 0.7) -> List[SearchResult]:
        """Perform semantic search"""
        try:
            # Get all chunks that match filters
            chunk_keys = self._get_filtered_chunks(filters)
            
            if not chunk_keys:
                return []
            
            # Calculate similarities
            similarities = []
            
            for chunk_key in chunk_keys:
                chunk_data = self.redis_client.hget(chunk_key, "data")
                if chunk_data:
                    chunk_dict = json.loads(chunk_data)
                    chunk_embedding = chunk_dict.get("embedding", [])
                    
                    if chunk_embedding:
                        similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                        
                        if similarity >= similarity_threshold:
                            similarities.append((chunk_key, chunk_dict, similarity))
            
            # Sort by similarity and limit results
            similarities.sort(key=lambda x: x[2], reverse=True)
            similarities = similarities[:max_results]
            
            # Convert to SearchResult objects
            results = []
            for chunk_key, chunk_dict, similarity in similarities:
                chunk = self._dict_to_content_chunk(chunk_dict)
                result = SearchResult(
                    content_chunk=chunk,
                    relevance_score=similarity,
                    match_type="semantic"
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error performing vector search: {e}")
            return []
    
    def _get_filtered_chunks(self, filters: Optional[Dict]) -> List[str]:
        """Get chunk keys that match the given filters"""
        if not filters:
            # Return all chunks
            return list(self.redis_client.scan_iter(match=f"{self.CHUNK_PREFIX}*"))
        
        # Start with all chunks
        result_keys = set(self.redis_client.scan_iter(match=f"{self.CHUNK_PREFIX}*"))
        
        # Apply filters
        for filter_key, filter_value in filters.items():
            if filter_key == "rulebook":
                filtered_keys = set(self.redis_client.smembers(f"rulebook:{filter_value}"))
                result_keys &= filtered_keys
            elif filter_key == "system":
                filtered_keys = set(self.redis_client.smembers(f"system:{filter_value}"))
                result_keys &= filtered_keys
            elif filter_key == "content_type":
                filtered_keys = set(self.redis_client.smembers(f"content_type:{filter_value}"))
                result_keys &= filtered_keys
        
        return list(result_keys)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        try:
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(b * b for b in vec2) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
        except:
            return 0.0
    
    def _dict_to_content_chunk(self, chunk_dict: Dict) -> ContentChunk:
        """Convert dictionary back to ContentChunk object"""
        return ContentChunk(
            id=chunk_dict["id"],
            rulebook=chunk_dict["rulebook"],
            system=chunk_dict["system"],
            content_type=chunk_dict["content_type"],
            title=chunk_dict["title"],
            content=chunk_dict["content"],
            page_number=chunk_dict["page_number"],
            section_path=chunk_dict["section_path"],
            embedding=chunk_dict["embedding"],
            metadata=chunk_dict["metadata"],
            tables=chunk_dict.get("tables", [])
        )
    
    def store_campaign_data(self, campaign_id: str, data_type: str, data: Dict) -> str:
        """Store campaign information"""
        try:
            # Generate unique ID
            data_id = str(uuid.uuid4())
            
            # Create campaign data object
            campaign_data = CampaignData(
                id=data_id,
                campaign_id=campaign_id,
                data_type=data_type,
                name=data.get("name", ""),
                content=data,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                version=1,
                tags=data.get("tags", [])
            )
            
            # Store in Redis
            campaign_key = f"{self.CAMPAIGN_PREFIX}{campaign_id}:{data_type}:{data_id}"
            
            campaign_dict = {
                "id": campaign_data.id,
                "campaign_id": campaign_data.campaign_id,
                "data_type": campaign_data.data_type,
                "name": campaign_data.name,
                "content": json.dumps(campaign_data.content),
                "created_at": campaign_data.created_at.isoformat(),
                "updated_at": campaign_data.updated_at.isoformat(),
                "version": campaign_data.version,
                "tags": json.dumps(campaign_data.tags or [])
            }
            
            self.redis_client.hset(campaign_key, mapping=campaign_dict)
            
            # Add to indexes
            self.redis_client.sadd(f"campaign_index:{campaign_id}", campaign_key)
            self.redis_client.sadd(f"campaign_type:{campaign_id}:{data_type}", campaign_key)
            
            self.logger.info(f"Stored campaign data: {campaign_id}:{data_type}:{data_id}")
            return data_id
            
        except Exception as e:
            self.logger.error(f"Error storing campaign data: {e}")
            raise
    
    def get_campaign_data(self, campaign_id: str, data_type: Optional[str] = None) -> List[Dict]:
        """Retrieve campaign information"""
        try:
            if data_type:
                # Get specific data type
                campaign_keys = self.redis_client.smembers(f"campaign_type:{campaign_id}:{data_type}")
            else:
                # Get all data for campaign
                campaign_keys = self.redis_client.smembers(f"campaign_index:{campaign_id}")
            
            results = []
            for key in campaign_keys:
                data = self.redis_client.hgetall(key)
                if data:
                    # Parse JSON fields
                    data["content"] = json.loads(data["content"])
                    data["tags"] = json.loads(data["tags"])
                    results.append(data)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error retrieving campaign data: {e}")
            return []
    
    def update_campaign_data(self, campaign_id: str, data_id: str, updates: Dict) -> bool:
        """Update existing campaign data"""
        try:
            # Find the campaign data
            campaign_keys = self.redis_client.smembers(f"campaign_index:{campaign_id}")
            target_key = None
            
            for key in campaign_keys:
                data = self.redis_client.hget(key, "id")
                if data == data_id:
                    target_key = key
                    break
            
            if not target_key:
                self.logger.warning(f"Campaign data not found: {campaign_id}:{data_id}")
                return False
            
            # Get current data
            current_data = self.redis_client.hgetall(target_key)
            if not current_data:
                return False
            
            # Update fields
            current_content = json.loads(current_data["content"])
            current_content.update(updates.get("content", {}))
            
            updated_data = {
                "name": updates.get("name", current_data["name"]),
                "content": json.dumps(current_content),
                "updated_at": datetime.now().isoformat(),
                "version": int(current_data["version"]) + 1,
                "tags": json.dumps(updates.get("tags", json.loads(current_data["tags"])))
            }
            
            # Update in Redis
            self.redis_client.hset(target_key, mapping=updated_data)
            
            self.logger.info(f"Updated campaign data: {campaign_id}:{data_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating campaign data: {e}")
            return False
    
    def delete_campaign_data(self, campaign_id: str, data_id: str) -> bool:
        """Delete campaign data"""
        try:
            # Find and delete the campaign data
            campaign_keys = self.redis_client.smembers(f"campaign_index:{campaign_id}")
            
            for key in campaign_keys:
                data = self.redis_client.hget(key, "id")
                if data == data_id:
                    # Remove from indexes
                    self.redis_client.srem(f"campaign_index:{campaign_id}", key)
                    
                    data_type = self.redis_client.hget(key, "data_type")
                    if data_type:
                        self.redis_client.srem(f"campaign_type:{campaign_id}:{data_type}", key)
                    
                    # Delete the data
                    self.redis_client.delete(key)
                    
                    self.logger.info(f"Deleted campaign data: {campaign_id}:{data_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting campaign data: {e}")
            return False
    
    def keyword_search(self, query: str, filters: Optional[Dict] = None) -> List[SearchResult]:
        """Perform keyword-based search"""
        try:
            chunk_keys = self._get_filtered_chunks(filters)
            results = []
            
            query_lower = query.lower()
            
            for chunk_key in chunk_keys:
                chunk_data = self.redis_client.hget(chunk_key, "data")
                if chunk_data:
                    chunk_dict = json.loads(chunk_data)
                    
                    # Search in title and content
                    title_lower = chunk_dict.get("title", "").lower()
                    content_lower = chunk_dict.get("content", "").lower()
                    
                    score = 0.0
                    if query_lower in title_lower:
                        score += 1.0  # Higher score for title matches
                    if query_lower in content_lower:
                        score += 0.5  # Lower score for content matches
                    
                    if score > 0:
                        chunk = self._dict_to_content_chunk(chunk_dict)
                        result = SearchResult(
                            content_chunk=chunk,
                            relevance_score=score,
                            match_type="keyword"
                        )
                        results.append(result)
            
            # Sort by relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            return results
            
        except Exception as e:
            self.logger.error(f"Error performing keyword search: {e}")
            return []
    
    def get_rulebook_stats(self) -> Dict[str, Any]:
        """Get statistics about stored rulebooks"""
        try:
            stats = {
                "total_chunks": 0,
                "rulebooks": {},
                "systems": {},
                "content_types": {}
            }
            
            # Count total chunks
            chunk_keys = list(self.redis_client.scan_iter(match=f"{self.CHUNK_PREFIX}*"))
            stats["total_chunks"] = len(chunk_keys)
            
            # Count by categories
            for key in chunk_keys:
                data = self.redis_client.hgetall(key)
                if data:
                    rulebook = data.get("rulebook", "unknown")
                    system = data.get("system", "unknown")
                    content_type = data.get("content_type", "unknown")
                    
                    stats["rulebooks"][rulebook] = stats["rulebooks"].get(rulebook, 0) + 1
                    stats["systems"][system] = stats["systems"].get(system, 0) + 1
                    stats["content_types"][content_type] = stats["content_types"].get(content_type, 0) + 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting rulebook stats: {e}")
            return {}
    
    def cleanup_old_data(self, days_old: int = 30) -> int:
        """Clean up old campaign data"""
        try:
            cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            deleted_count = 0
            
            # This is a simplified cleanup - in practice, you'd want more sophisticated logic
            campaign_keys = list(self.redis_client.scan_iter(match=f"{self.CAMPAIGN_PREFIX}*"))
            
            for key in campaign_keys:
                updated_at = self.redis_client.hget(key, "updated_at")
                if updated_at:
                    try:
                        updated_timestamp = datetime.fromisoformat(updated_at).timestamp()
                        if updated_timestamp < cutoff_date:
                            self.redis_client.delete(key)
                            deleted_count += 1
                    except:
                        pass  # Skip invalid timestamps
            
            self.logger.info(f"Cleaned up {deleted_count} old campaign data entries")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
            return 0