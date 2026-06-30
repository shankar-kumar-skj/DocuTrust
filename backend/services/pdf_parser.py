import pdfplumber
from typing import List, Dict, Any
import logging
import re

logger = logging.getLogger(__name__)

def extract_pdf_structure(file_path: str) -> Dict[str, Any]:
    structure = {"pages": [], "tables": [], "metadata": {}}
    try:
        with pdfplumber.open(file_path) as pdf:
            structure["metadata"] = pdf.metadata or {}
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text is None:
                    text = ""
                # Extract tables and append as text
                tables = page.extract_tables()
                if tables:
                    table_text = ""
                    for table in tables:
                        for row in table:
                            table_text += " | ".join(str(cell) if cell else "" for cell in row) + "\n"
                    text += "\n[Table]\n" + table_text
                    structure["tables"].extend([{
                        "page": page_num,
                        "data": table
                    } for table in tables])
                lines = text.split('\n') if text else []
                sections = []
                for line in lines:
                    if re.match(r'^(?:\d+\.\s*|[A-Z][A-Z\s]+$)', line.strip()):
                        sections.append({"page": page_num, "heading": line.strip()})
                structure["pages"].append({
                    "page_num": page_num,
                    "text": text,
                    "sections": sections
                })
    except Exception as e:
        logger.error(f"PDF parsing error: {e}")
        raise
    return structure

def chunk_by_structure(structure: Dict[str, Any], chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
    chunks = []
    current_chunk = ""
    current_metadata = {"page": None, "section": "General"}
    for page in structure["pages"]:
        page_num = page["page_num"]
        text = page["text"]
        if not text:
            continue
        # Split by paragraphs (double newline)
        paragraphs = text.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            # Check if it's a heading (simplified)
            if re.match(r'^(?:\d+\.\s*|[A-Z][A-Z\s]+$)', para):
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "metadata": current_metadata.copy()
                    })
                    current_chunk = ""
                current_metadata = {"page": page_num, "section": para}
                continue
            # Append to current chunk
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "metadata": current_metadata.copy()
                })
                # Overlap: keep last few sentences
                overlap_text = current_chunk.split('.')[-2:] if '.' in current_chunk else []
                current_chunk = '. '.join(overlap_text) + '. ' if overlap_text else ""
            current_chunk += para + " "
        # End of page: finalize if chunk not empty
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "metadata": current_metadata.copy()
            })
            current_chunk = ""
    return chunks