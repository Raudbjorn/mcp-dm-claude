from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import numpy as np
import logging
from pathlib import Path
import json
import hashlib


class EmbeddingService:
    """Manages text-to-vector conversion and similarity search"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_embeddings: bool = True):
        self.model_name = model_name
        self.cache_embeddings = cache_embeddings
        self.logger = logging.getLogger(__name__)
        
        # Initialize model
        self.logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        # Set up cache if enabled
        self.cache_dir = Path("embeddings_cache")
        if cache_embeddings:
            self.cache_dir.mkdir(exist_ok=True)
            self.cache_file = self.cache_dir / f"{model_name.replace('/', '_')}_cache.json"
            self.cache = self._load_cache()
        else:
            self.cache = {}
    
    def _load_cache(self) -> Dict[str, List[float]]:
        """Load embedding cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Error loading embedding cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save embedding cache to disk"""
        if self.cache_embeddings:
            try:
                with open(self.cache_file, 'w') as f:
                    json.dump(self.cache, f)
            except Exception as e:
                self.logger.warning(f"Error saving embedding cache: {e}")
    
    def _get_text_hash(self, text: str) -> str:
        """Generate hash for text to use as cache key"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def generate_embedding(self, text: str) -> List[float]:
        """Convert text to vector embedding"""
        if not text or not text.strip():
            return []
        
        # Check cache first
        text_hash = self._get_text_hash(text)
        if text_hash in self.cache:
            return self.cache[text_hash]
        
        try:
            # Generate embedding
            embedding = self.model.encode(text.strip())
            embedding_list = embedding.tolist()
            
            # Cache the result
            if self.cache_embeddings:
                self.cache[text_hash] = embedding_list
                
            return embedding_list
            
        except Exception as e:
            self.logger.error(f"Error generating embedding for text: {e}")
            return []
    
    def batch_embed(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Efficiently process multiple texts"""
        if not texts:
            return []
        
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            if not text or not text.strip():
                embeddings.append([])
                continue
                
            text_hash = self._get_text_hash(text)
            if text_hash in self.cache:
                embeddings.append(self.cache[text_hash])
            else:
                embeddings.append(None)  # Placeholder
                uncached_texts.append(text.strip())
                uncached_indices.append(i)
        
        # Process uncached texts in batches
        if uncached_texts:
            try:
                # Process in batches to avoid memory issues
                for i in range(0, len(uncached_texts), batch_size):
                    batch_texts = uncached_texts[i:i + batch_size]
                    batch_indices = uncached_indices[i:i + batch_size]
                    
                    batch_embeddings = self.model.encode(batch_texts)
                    
                    # Store results
                    for j, embedding in enumerate(batch_embeddings):
                        embedding_list = embedding.tolist()
                        original_index = batch_indices[j]
                        embeddings[original_index] = embedding_list
                        
                        # Cache the result
                        if self.cache_embeddings:
                            text_hash = self._get_text_hash(batch_texts[j])
                            self.cache[text_hash] = embedding_list
                
                # Save cache after batch processing
                if self.cache_embeddings:
                    self._save_cache()
                    
            except Exception as e:
                self.logger.error(f"Error in batch embedding: {e}")
                # Fill remaining None values with empty lists
                for i, emb in enumerate(embeddings):
                    if emb is None:
                        embeddings[i] = []
        
        return embeddings
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        if not embedding1 or not embedding2:
            return 0.0
        
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm_vec1 = np.linalg.norm(vec1)
            norm_vec2 = np.linalg.norm(vec2)
            
            if norm_vec1 == 0 or norm_vec2 == 0:
                return 0.0
            
            return dot_product / (norm_vec1 * norm_vec2)
            
        except Exception as e:
            self.logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def find_most_similar(self, query_embedding: List[float], 
                         candidate_embeddings: List[List[float]], 
                         top_k: int = 5) -> List[tuple]:
        """Find top-k most similar embeddings"""
        if not query_embedding or not candidate_embeddings:
            return []
        
        similarities = []
        for i, candidate in enumerate(candidate_embeddings):
            sim = self.similarity(query_embedding, candidate)
            similarities.append((i, sim))
        
        # Sort by similarity (descending) and return top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        return self.model.get_sentence_embedding_dimension()
    
    def cleanup_cache(self, max_size: int = 10000):
        """Clean up cache if it gets too large"""
        if len(self.cache) > max_size:
            self.logger.info(f"Cleaning up embedding cache (size: {len(self.cache)})")
            # Keep only the most recent entries (simple approach)
            cache_items = list(self.cache.items())
            self.cache = dict(cache_items[-max_size//2:])
            self._save_cache()
    
    def __del__(self):
        """Save cache when object is destroyed"""
        if hasattr(self, 'cache_embeddings') and self.cache_embeddings:
            self._save_cache()