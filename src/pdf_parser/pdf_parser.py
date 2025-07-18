import PyPDF2
import pdfplumber
import re
from typing import Dict, List, Any, Optional, Tuple
from tqdm import tqdm
import logging
from pathlib import Path

from ..models.data_models import Section, Table, ContentChunk


class PDFParser:
    """Handles extraction and structuring of PDF content"""
    
    def __init__(self, preserve_formatting: bool = True, ocr_enabled: bool = False):
        self.preserve_formatting = preserve_formatting
        self.ocr_enabled = ocr_enabled
        self.logger = logging.getLogger(__name__)
    
    def extract_text(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text while preserving structure"""
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            # Check file size
            file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 100:  # configurable limit
                self.logger.warning(f"Large PDF file: {file_size_mb:.1f}MB")
            
            extracted_data = {
                "pages": [],
                "metadata": {},
                "toc": [],
                "total_pages": 0
            }
            
            # Extract metadata and table of contents
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                extracted_data["total_pages"] = len(pdf_reader.pages)
                
                # Extract metadata
                if pdf_reader.metadata:
                    extracted_data["metadata"] = {
                        "title": pdf_reader.metadata.get("/Title", ""),
                        "author": pdf_reader.metadata.get("/Author", ""),
                        "subject": pdf_reader.metadata.get("/Subject", ""),
                        "creator": pdf_reader.metadata.get("/Creator", "")
                    }
                
                # Extract table of contents
                if pdf_reader.outline:
                    extracted_data["toc"] = self._extract_toc(pdf_reader.outline)
            
            # Extract text content page by page
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(tqdm(pdf.pages, desc="Extracting text")):
                    page_data = {
                        "page_number": page_num + 1,
                        "text": "",
                        "tables": []
                    }
                    
                    # Extract text
                    if page.extract_text():
                        page_data["text"] = page.extract_text()
                    
                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        page_data["tables"] = self._process_tables(tables, page_num + 1)
                    
                    extracted_data["pages"].append(page_data)
            
            return extracted_data
            
        except Exception as e:
            self.logger.error(f"Error extracting text from {pdf_path}: {e}")
            raise
    
    def _extract_toc(self, outline: List) -> List[Dict[str, Any]]:
        """Extract table of contents from PDF outline"""
        toc = []
        
        def process_outline_item(item, level=0):
            if hasattr(item, 'title') and hasattr(item, 'page'):
                toc_entry = {
                    "title": item.title,
                    "page": item.page.idnum if hasattr(item.page, 'idnum') else None,
                    "level": level
                }
                toc.append(toc_entry)
            
            # Process children
            if hasattr(item, '__iter__') and not isinstance(item, str):
                for child in item:
                    process_outline_item(child, level + 1)
        
        for item in outline:
            process_outline_item(item)
        
        return toc
    
    def _process_tables(self, tables: List, page_number: int) -> List[Table]:
        """Process extracted tables into structured format"""
        processed_tables = []
        
        for i, table in enumerate(tables):
            if not table or len(table) < 2:  # Skip empty or single-row tables
                continue
            
            # Extract headers (first row)
            headers = [cell or f"Column {j+1}" for j, cell in enumerate(table[0])]
            
            # Extract data rows
            rows = []
            for row in table[1:]:
                if any(cell and cell.strip() for cell in row):  # Skip empty rows
                    rows.append([cell or "" for cell in row])
            
            if rows:  # Only add if there are data rows
                processed_table = Table(
                    title=f"Table {i+1} (Page {page_number})",
                    headers=headers,
                    rows=rows,
                    page_number=page_number,
                    metadata={"table_index": i}
                )
                processed_tables.append(processed_table)
        
        return processed_tables
    
    def identify_sections(self, extracted_data: Dict[str, Any]) -> List[Section]:
        """Use table of contents and text analysis to identify logical sections"""
        sections = []
        toc = extracted_data.get("toc", [])
        pages = extracted_data.get("pages", [])
        
        if not toc:
            # Fallback: identify sections using text patterns
            return self._identify_sections_from_text(pages)
        
        # Create sections based on TOC
        for i, toc_entry in enumerate(toc):
            section_title = toc_entry["title"]
            section_level = toc_entry["level"]
            start_page = toc_entry.get("page", 1)
            
            # Determine end page
            end_page = extracted_data["total_pages"]
            if i + 1 < len(toc):
                next_entry = toc[i + 1]
                if next_entry["level"] <= section_level:
                    end_page = next_entry.get("page", end_page) - 1
            
            # Extract content for this section
            section_content = self._extract_section_content(
                pages, start_page, end_page, section_title
            )
            
            if section_content:
                # Build parent section path
                parent_sections = []
                for j in range(i):
                    if toc[j]["level"] < section_level:
                        parent_sections.append(toc[j]["title"])
                
                section = Section(
                    title=section_title,
                    content=section_content,
                    page_start=start_page,
                    page_end=end_page,
                    level=section_level,
                    parent_sections=parent_sections
                )
                sections.append(section)
        
        return sections
    
    def _identify_sections_from_text(self, pages: List[Dict]) -> List[Section]:
        """Fallback method to identify sections from text patterns"""
        sections = []
        
        # Common heading patterns for TTRPG books
        heading_patterns = [
            r'^(Chapter\s+\d+[\.\:]?\s*.*?)$',
            r'^(CHAPTER\s+\d+[\.\:]?\s*.*?)$',
            r'^([A-Z][A-Z\s]{3,}?)$',  # ALL CAPS headings
            r'^(\d+\.\s+[A-Z].*?)$',   # Numbered headings
        ]
        
        current_section = None
        current_content = []
        
        for page in pages:
            text = page["text"]
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this line is a heading
                is_heading = False
                for pattern in heading_patterns:
                    if re.match(pattern, line):
                        is_heading = True
                        break
                
                if is_heading:
                    # Save previous section if exists
                    if current_section and current_content:
                        current_section.content = '\n'.join(current_content)
                        sections.append(current_section)
                    
                    # Start new section
                    current_section = Section(
                        title=line,
                        content="",
                        page_start=page["page_number"],
                        page_end=page["page_number"],
                        level=1,  # Default level
                        parent_sections=[]
                    )
                    current_content = []
                else:
                    # Add to current section content
                    if current_section:
                        current_content.append(line)
                        current_section.page_end = page["page_number"]
        
        # Add final section
        if current_section and current_content:
            current_section.content = '\n'.join(current_content)
            sections.append(current_section)
        
        return sections
    
    def _extract_section_content(self, pages: List[Dict], start_page: int, 
                                end_page: int, section_title: str) -> str:
        """Extract content for a specific section"""
        content_lines = []
        
        for page in pages:
            page_num = page["page_number"]
            if start_page <= page_num <= end_page:
                text = page["text"]
                if text:
                    content_lines.append(text)
        
        return '\n'.join(content_lines)
    
    def create_chunks(self, sections: List[Section], rulebook_name: str, 
                     system: str) -> List[ContentChunk]:
        """Create searchable chunks with metadata"""
        chunks = []
        
        for section in sections:
            # Split large sections into smaller chunks
            section_chunks = self._split_section_into_chunks(section)
            
            for i, chunk_content in enumerate(section_chunks):
                chunk_id = f"{rulebook_name}_{section.title}_{i}".replace(" ", "_")
                
                # Determine content type based on section title
                content_type = self._determine_content_type(section.title)
                
                chunk = ContentChunk(
                    id=chunk_id,
                    rulebook=rulebook_name,
                    system=system,
                    content_type=content_type,
                    title=section.title,
                    content=chunk_content,
                    page_number=section.page_start,
                    section_path=section.parent_sections + [section.title],
                    embedding=[],  # Will be populated by embedding service
                    metadata={
                        "section_level": section.level,
                        "page_range": f"{section.page_start}-{section.page_end}",
                        "chunk_index": i
                    }
                )
                chunks.append(chunk)
        
        return chunks
    
    def _split_section_into_chunks(self, section: Section, max_chunk_size: int = 1500) -> List[str]:
        """Split a section into appropriately sized chunks"""
        content = section.content
        
        if len(content) <= max_chunk_size:
            return [content]
        
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            para_size = len(paragraph)
            
            if current_size + para_size > max_chunk_size and current_chunk:
                # Save current chunk and start new one
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_size = para_size
            else:
                current_chunk.append(paragraph)
                current_size += para_size
        
        # Add final chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def _determine_content_type(self, title: str) -> str:
        """Determine content type based on section title"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['spell', 'magic', 'cantrip']):
            return "spell"
        elif any(word in title_lower for word in ['monster', 'creature', 'bestiary']):
            return "monster"
        elif any(word in title_lower for word in ['item', 'equipment', 'weapon', 'armor']):
            return "item"
        elif any(word in title_lower for word in ['rule', 'combat', 'action', 'mechanic']):
            return "rule"
        else:
            return "rule"  # Default to rule