import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


@dataclass
class EmbeddingConfig:
    model: str = "all-MiniLM-L6-v2"
    batch_size: int = 32
    cache_embeddings: bool = True


@dataclass
class PDFProcessingConfig:
    max_file_size_mb: int = 100
    ocr_enabled: bool = True
    preserve_formatting: bool = True


@dataclass
class SearchConfig:
    default_max_results: int = 5
    similarity_threshold: float = 0.7
    enable_keyword_fallback: bool = True


@dataclass
class MCPConfig:
    server_name: str = "ttrpg-assistant"
    version: str = "1.0.0"


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class Config:
    redis: RedisConfig
    embedding: EmbeddingConfig
    pdf_processing: PDFProcessingConfig
    search: SearchConfig
    mcp: MCPConfig
    logging: LoggingConfig


class ConfigManager:
    """Manages configuration loading from YAML files and environment variables"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        load_dotenv()  # Load environment variables from .env file
    
    def load_config(self) -> Config:
        """Load configuration from YAML file and environment variables"""
        # Load from YAML file
        config_data = {}
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        
        # Override with environment variables
        config_data = self._apply_env_overrides(config_data)
        
        # Create config objects
        redis_config = RedisConfig(**config_data.get("redis", {}))
        embedding_config = EmbeddingConfig(**config_data.get("embedding", {}))
        pdf_config = PDFProcessingConfig(**config_data.get("pdf_processing", {}))
        search_config = SearchConfig(**config_data.get("search", {}))
        mcp_config = MCPConfig(**config_data.get("mcp", {}))
        logging_config = LoggingConfig(**config_data.get("logging", {}))
        
        return Config(
            redis=redis_config,
            embedding=embedding_config,
            pdf_processing=pdf_config,
            search=search_config,
            mcp=mcp_config,
            logging=logging_config
        )
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to config data"""
        env_mappings = {
            # Redis configuration
            "REDIS_HOST": ("redis", "host"),
            "REDIS_PORT": ("redis", "port"),
            "REDIS_DB": ("redis", "db"),
            "REDIS_PASSWORD": ("redis", "password"),
            
            # Embedding configuration
            "EMBEDDING_MODEL": ("embedding", "model"),
            "EMBEDDING_BATCH_SIZE": ("embedding", "batch_size"),
            "EMBEDDING_CACHE": ("embedding", "cache_embeddings"),
            
            # PDF processing configuration
            "PDF_MAX_SIZE_MB": ("pdf_processing", "max_file_size_mb"),
            "PDF_OCR_ENABLED": ("pdf_processing", "ocr_enabled"),
            "PDF_PRESERVE_FORMAT": ("pdf_processing", "preserve_formatting"),
            
            # Search configuration
            "SEARCH_MAX_RESULTS": ("search", "default_max_results"),
            "SEARCH_SIMILARITY_THRESHOLD": ("search", "similarity_threshold"),
            "SEARCH_KEYWORD_FALLBACK": ("search", "enable_keyword_fallback"),
            
            # MCP configuration
            "MCP_SERVER_NAME": ("mcp", "server_name"),
            "MCP_VERSION": ("mcp", "version"),
            
            # Logging configuration
            "LOG_LEVEL": ("logging", "level"),
            "LOG_FORMAT": ("logging", "format")
        }
        
        for env_var, (section, key) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                if section not in config_data:
                    config_data[section] = {}
                
                # Type conversion
                if key in ["port", "db", "batch_size", "max_file_size_mb", "default_max_results"]:
                    config_data[section][key] = int(env_value)
                elif key in ["similarity_threshold"]:
                    config_data[section][key] = float(env_value)
                elif key in ["ocr_enabled", "preserve_formatting", "cache_embeddings", "enable_keyword_fallback"]:
                    config_data[section][key] = env_value.lower() in ("true", "1", "yes", "on")
                else:
                    config_data[section][key] = env_value
        
        return config_data
    
    def save_config(self, config: Config):
        """Save configuration to YAML file"""
        config_data = {
            "redis": {
                "host": config.redis.host,
                "port": config.redis.port,
                "db": config.redis.db,
                "password": config.redis.password
            },
            "embedding": {
                "model": config.embedding.model,
                "batch_size": config.embedding.batch_size,
                "cache_embeddings": config.embedding.cache_embeddings
            },
            "pdf_processing": {
                "max_file_size_mb": config.pdf_processing.max_file_size_mb,
                "ocr_enabled": config.pdf_processing.ocr_enabled,
                "preserve_formatting": config.pdf_processing.preserve_formatting
            },
            "search": {
                "default_max_results": config.search.default_max_results,
                "similarity_threshold": config.search.similarity_threshold,
                "enable_keyword_fallback": config.search.enable_keyword_fallback
            },
            "mcp": {
                "server_name": config.mcp.server_name,
                "version": config.mcp.version
            },
            "logging": {
                "level": config.logging.level,
                "format": config.logging.format
            }
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)


def setup_logging(config: LoggingConfig):
    """Setup logging configuration"""
    import logging
    
    # Set logging level
    level = getattr(logging, config.level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format=config.format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("ttrpg_assistant.log")
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)