import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..models.personality_models import RPGPersonality, PersonalityPrompt
from ..redis_manager.redis_manager import RedisDataManager
from .personality_extractor import PersonalityExtractor


class PersonalityManager:
    """Manages RPG personality profiles and prompt generation"""
    
    def __init__(self, redis_manager: RedisDataManager):
        self.redis_manager = redis_manager
        self.extractor = PersonalityExtractor()
        self.logger = logging.getLogger(__name__)
        
        # Redis keys
        self.PERSONALITY_PREFIX = "personality:"
        self.SYSTEM_PERSONALITIES = "system_personalities"
        
        # Local cache for frequently accessed personalities
        self.personality_cache: Dict[str, RPGPersonality] = {}
    
    def store_personality(self, personality: RPGPersonality) -> bool:
        """Store a personality profile in Redis"""
        try:
            personality_key = f"{self.PERSONALITY_PREFIX}{personality.system_name}"
            
            # Store personality data
            personality_data = personality.to_dict()
            self.redis_manager.redis_client.hset(
                personality_key,
                mapping={"data": json.dumps(personality_data)}
            )
            
            # Add to system personalities index
            self.redis_manager.redis_client.sadd(
                self.SYSTEM_PERSONALITIES,
                personality.system_name
            )
            
            # Update cache
            self.personality_cache[personality.system_name] = personality
            
            self.logger.info(f"Stored personality profile for {personality.system_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing personality for {personality.system_name}: {e}")
            return False
    
    def get_personality(self, system_name: str) -> Optional[RPGPersonality]:
        """Get personality profile for a system"""
        # Check cache first
        if system_name in self.personality_cache:
            return self.personality_cache[system_name]
        
        try:
            personality_key = f"{self.PERSONALITY_PREFIX}{system_name}"
            personality_data = self.redis_manager.redis_client.hget(personality_key, "data")
            
            if personality_data:
                data = json.loads(personality_data)
                personality = RPGPersonality.from_dict(data)
                
                # Cache for future use
                self.personality_cache[system_name] = personality
                return personality
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving personality for {system_name}: {e}")
            return None
    
    def list_personalities(self) -> List[str]:
        """List all available personality profiles"""
        try:
            return list(self.redis_manager.redis_client.smembers(self.SYSTEM_PERSONALITIES))
        except Exception as e:
            self.logger.error(f"Error listing personalities: {e}")
            return []
    
    def extract_and_store_personality(self, chunks: List, system_name: str) -> Optional[RPGPersonality]:
        """Extract personality from rulebook chunks and store it"""
        try:
            self.logger.info(f"Extracting personality profile for {system_name}")
            
            # Extract personality
            personality = self.extractor.extract_personality(chunks, system_name)
            
            # Store in Redis
            if self.store_personality(personality):
                return personality
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting personality for {system_name}: {e}")
            return None
    
    def generate_personality_prompt(self, system_name: str, query: str, context: str = "") -> Optional[PersonalityPrompt]:
        """Generate a personality-aware prompt for a query"""
        personality = self.get_personality(system_name)
        
        if not personality:
            self.logger.warning(f"No personality found for {system_name}, using default")
            return None
        
        return self.extractor.generate_personality_prompt(personality, query, context)
    
    def update_personality_from_usage(self, system_name: str, feedback: Dict[str, Any]) -> bool:
        """Update personality profile based on usage feedback"""
        try:
            personality = self.get_personality(system_name)
            if not personality:
                return False
            
            # Update confidence score based on feedback
            if feedback.get("helpful", False):
                personality.confidence_score = min(1.0, personality.confidence_score + 0.1)
            elif feedback.get("unhelpful", False):
                personality.confidence_score = max(0.1, personality.confidence_score - 0.1)
            
            # Store updated personality
            return self.store_personality(personality)
            
        except Exception as e:
            self.logger.error(f"Error updating personality for {system_name}: {e}")
            return False
    
    def get_personality_summary(self, system_name: str) -> Optional[Dict[str, Any]]:
        """Get a summary of personality traits for a system"""
        personality = self.get_personality(system_name)
        if not personality:
            return None
        
        return {
            "system_name": personality.system_name,
            "personality_name": personality.personality_name,
            "description": personality.description,
            "tone": personality.tone,
            "perspective": personality.perspective,
            "formality_level": personality.formality_level,
            "confidence_score": personality.confidence_score,
            "vernacular_count": len(personality.vernacular_patterns),
            "trait_count": len(personality.personality_traits),
            "example_phrases": personality.example_phrases[:3],  # First 3
            "system_context": personality.system_context
        }
    
    def get_vernacular_for_system(self, system_name: str) -> List[Dict[str, Any]]:
        """Get vernacular patterns for a system"""
        personality = self.get_personality(system_name)
        if not personality:
            return []
        
        return [
            {
                "term": vp.term,
                "definition": vp.definition,
                "category": vp.category,
                "frequency": vp.frequency,
                "examples": vp.examples[:2]  # First 2 examples
            }
            for vp in personality.vernacular_patterns
        ]
    
    def search_personalities_by_trait(self, trait: str) -> List[Dict[str, Any]]:
        """Search personalities by trait (tone, perspective, etc.)"""
        matching_personalities = []
        
        for system_name in self.list_personalities():
            personality = self.get_personality(system_name)
            if personality:
                if (trait.lower() in personality.tone.lower() or
                    trait.lower() in personality.perspective.lower() or
                    trait.lower() in personality.description.lower()):
                    matching_personalities.append(self.get_personality_summary(system_name))
        
        return matching_personalities
    
    def export_personality(self, system_name: str, file_path: str) -> bool:
        """Export personality profile to JSON file"""
        try:
            personality = self.get_personality(system_name)
            if not personality:
                return False
            
            with open(file_path, 'w') as f:
                json.dump(personality.to_dict(), f, indent=2)
            
            self.logger.info(f"Exported personality for {system_name} to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting personality for {system_name}: {e}")
            return False
    
    def import_personality(self, file_path: str) -> bool:
        """Import personality profile from JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            personality = RPGPersonality.from_dict(data)
            return self.store_personality(personality)
            
        except Exception as e:
            self.logger.error(f"Error importing personality from {file_path}: {e}")
            return False
    
    def delete_personality(self, system_name: str) -> bool:
        """Delete a personality profile"""
        try:
            personality_key = f"{self.PERSONALITY_PREFIX}{system_name}"
            
            # Delete from Redis
            self.redis_manager.redis_client.delete(personality_key)
            
            # Remove from index
            self.redis_manager.redis_client.srem(
                self.SYSTEM_PERSONALITIES,
                system_name
            )
            
            # Remove from cache
            if system_name in self.personality_cache:
                del self.personality_cache[system_name]
            
            self.logger.info(f"Deleted personality profile for {system_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting personality for {system_name}: {e}")
            return False
    
    def get_personality_stats(self) -> Dict[str, Any]:
        """Get statistics about stored personalities"""
        try:
            personalities = self.list_personalities()
            stats = {
                "total_personalities": len(personalities),
                "personalities_by_tone": {},
                "personalities_by_formality": {},
                "average_confidence": 0.0,
                "total_vernacular_terms": 0
            }
            
            total_confidence = 0.0
            for system_name in personalities:
                personality = self.get_personality(system_name)
                if personality:
                    # Count by tone
                    tone = personality.tone
                    stats["personalities_by_tone"][tone] = stats["personalities_by_tone"].get(tone, 0) + 1
                    
                    # Count by formality
                    formality = personality.formality_level
                    stats["personalities_by_formality"][formality] = stats["personalities_by_formality"].get(formality, 0) + 1
                    
                    # Sum confidence
                    total_confidence += personality.confidence_score
                    
                    # Count vernacular terms
                    stats["total_vernacular_terms"] += len(personality.vernacular_patterns)
            
            if len(personalities) > 0:
                stats["average_confidence"] = total_confidence / len(personalities)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting personality stats: {e}")
            return {}
    
    def create_personality_comparison(self, system_names: List[str]) -> Dict[str, Any]:
        """Compare personalities across multiple systems"""
        comparison = {
            "systems": system_names,
            "comparison_matrix": {},
            "unique_traits": {},
            "shared_traits": {}
        }
        
        personalities = {}
        for system_name in system_names:
            personality = self.get_personality(system_name)
            if personality:
                personalities[system_name] = personality
        
        # Compare traits
        for system_name, personality in personalities.items():
            comparison["comparison_matrix"][system_name] = {
                "tone": personality.tone,
                "perspective": personality.perspective,
                "formality": personality.formality_level,
                "vernacular_count": len(personality.vernacular_patterns),
                "confidence": personality.confidence_score
            }
        
        return comparison