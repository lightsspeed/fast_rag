import re
from typing import List, Dict, Any

class StructureAnalyzer:
    """Anaylzes text to detect structural elements like headings, tables, and boundaries."""
    
    def __init__(self):
        # Regex for Markdown headings: # H1, ## H2, etc.
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.*)$', re.MULTILINE)
        
        # Regex for potential tables (lines containing multiple pipes or tabs)
        self.table_row_pattern = re.compile(r'^(\s*\|.*\||.*\t.*)\s*$', re.MULTILINE)
        
        # Boundary detectors (e.g., horizontal rules, multiple newlines)
        self.boundary_pattern = re.compile(r'^(\s*([-*_])\s*\2\s*\2\s*)$|(\n{3,})', re.MULTILINE)

    def analyze(self, text: str) -> Dict[str, Any]:
        """Performs full structural analysis of the text."""
        headings = self.detect_headings(text)
        tables = self.detect_tables(text)
        boundaries = self.detect_boundaries(text)
        
        return {
            "headings": headings,
            "tables": tables,
            "boundaries": boundaries
        }

    def detect_headings(self, text: str) -> List[Dict[str, Any]]:
        """Identifies headings and their hierarchical level."""
        headings = []
        for match in self.heading_pattern.finditer(text):
            headings.append({
                "level": len(match.group(1)),
                "text": match.group(2).strip(),
                "start": match.start(),
                "end": match.end()
            })
        return headings

    def detect_tables(self, text: str) -> List[Dict[str, Any]]:
        """Identifies potential table blocks."""
        tables = []
        lines = text.split('\n')
        in_table = False
        table_start_line = -1
        
        for i, line in enumerate(lines):
            is_table_row = bool(self.table_row_pattern.match(line))
            
            if is_table_row and not in_table:
                in_table = True
                table_start_line = i
            elif not is_table_row and in_table:
                in_table = False
                tables.append({
                    "start_line": table_start_line,
                    "end_line": i - 1,
                    "content": "\n".join(lines[table_start_line:i])
                })
        
        # Handle table at the end of text
        if in_table:
            tables.append({
                "start_line": table_start_line,
                "end_line": len(lines) - 1,
                "content": "\n".join(lines[table_start_line:])
            })
            
        return tables

    def detect_boundaries(self, text: str) -> List[Dict[str, Any]]:
        """Identifies logical boundaries like horizontal rules or large gaps."""
        boundaries = []
        for match in self.boundary_pattern.finditer(text):
            boundaries.append({
                "type": "hr" if match.group(1) else "gap",
                "start": match.start(),
                "end": match.end()
            })
        return boundaries

structure_analyzer = StructureAnalyzer()
