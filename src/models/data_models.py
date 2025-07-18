from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class Table:
    """Represents a table extracted from a PDF"""
    title: str
    headers: List[str]
    rows: List[List[str]]
    page_number: int
    metadata: Dict[str, Any] = None


@dataclass
class ContentChunk:
    """Represents a chunk of content from a rulebook"""
    id: str
    rulebook: str
    system: str  # D&D 5e, Pathfinder, etc.
    content_type: str  # rule, spell, monster, item
    title: str
    content: str
    page_number: int
    section_path: List[str]  # ["Chapter 1", "Combat", "Attack Rolls"]
    embedding: List[float]
    metadata: Dict[str, Any]
    tables: Optional[List[Table]] = None


@dataclass
class CampaignData:
    """Represents campaign-specific data"""
    id: str
    campaign_id: str
    data_type: str  # character, npc, location, plot, session
    name: str
    content: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    version: int
    tags: Optional[List[str]] = None


@dataclass
class SearchResult:
    """Represents a search result with relevance information"""
    content_chunk: ContentChunk
    relevance_score: float
    match_type: str  # "semantic", "keyword", "exact"
    highlighted_text: Optional[str] = None


@dataclass
class Section:
    """Represents a section identified during PDF parsing"""
    title: str
    content: str
    page_start: int
    page_end: int
    level: int  # Heading level (1, 2, 3, etc.)
    parent_sections: List[str]  # Path to this section
    subsections: List['Section'] = None