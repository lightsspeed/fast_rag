"""
PII Detection and Redaction Service
Detects and redacts personally identifiable information from OCR text
"""
import re
from typing import Dict, List
from dataclasses import dataclass

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False


@dataclass
class PIIEntity:
    """Detected PII entity"""
    entity_type: str
    start: int
    end: int
    score: float
    text: str


class PIIDetector:
    """
    Detect and redact PII from OCR text results
    Uses Presidio if available, falls back to regex patterns
    """
    
    # Regex patterns for common PII types
    PATTERNS = {
        "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "PHONE_US": r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
        "PHONE_INTL": r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
        "SSN": r'\b\d{3}-\d{2}-\d{4}\b',
        "CREDIT_CARD": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        "IP_ADDRESS": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        "EMPLOYEE_ID": r'\b[EMP|EID|E]\d{5,8}\b',
        "TICKET_NUMBER": r'\b(?:INC|REQ|CHG|RITM)\d{7,10}\b',
        "MAC_ADDRESS": r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b',
    }
    
    def __init__(self):
        """Initialize PII detector with Presidio if available"""
        self.use_presidio = PRESIDIO_AVAILABLE
        
        if self.use_presidio:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
        else:
            print("Warning: Presidio not available, using regex fallback")
    
    def detect_pii(self, text: str) -> List[PIIEntity]:
        """
        Detect PII entities in text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of detected PII entities
        """
        if self.use_presidio:
            return self._detect_with_presidio(text)
        else:
            return self._detect_with_regex(text)
    
    def _detect_with_presidio(self, text: str) -> List[PIIEntity]:
        """Use Presidio for PII detection"""
        results = self.analyzer.analyze(
            text=text,
            language='en',
            entities=[
                "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
                "CREDIT_CARD", "IP_ADDRESS", "US_SSN",
                "IBAN_CODE", "DATE_TIME", "LOCATION",
                "MEDICAL_LICENSE", "US_PASSPORT"
            ]
        )
        
        entities = []
        for result in results:
            entities.append(PIIEntity(
                entity_type=result.entity_type,
                start=result.start,
                end=result.end,
                score=result.score,
                text=text[result.start:result.end]
            ))
        
        # Add custom patterns
        entities.extend(self._detect_custom_patterns(text))
        
        return entities
    
    def _detect_with_regex(self, text: str) -> List[PIIEntity]:
        """Fallback regex-based detection"""
        entities = []
        
        for entity_type, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(PIIEntity(
                    entity_type=entity_type,
                    start=match.start(),
                    end=match.end(),
                    score=0.85,
                    text=match.group(0)
                ))
        
        return entities
    
    def _detect_custom_patterns(self, text: str) -> List[PIIEntity]:
        """Detect enterprise-specific PII patterns"""
        entities = []
        
        # Employee IDs
        for match in re.finditer(self.PATTERNS["EMPLOYEE_ID"], text, re.IGNORECASE):
            entities.append(PIIEntity(
                entity_type="EMPLOYEE_ID",
                start=match.start(),
                end=match.end(),
                score=0.9,
                text=match.group(0)
            ))
        
        # Ticket/Incident numbers
        for match in re.finditer(self.PATTERNS["TICKET_NUMBER"], text, re.IGNORECASE):
            entities.append(PIIEntity(
                entity_type="TICKET_NUMBER",
                start=match.start(),
                end=match.end(),
                score=0.85,
                text=match.group(0)
            ))
        
        return entities
    
    def redact_pii(self, text: str, redaction_char: str = "*") -> Dict:
        """
        Detect and redact PII from text
        
        Args:
            text: Input text
            redaction_char: Character to use for redaction
            
        Returns:
            Dictionary with original, redacted text, and metadata
        """
        if not text or len(text.strip()) == 0:
            return {
                "original": text,
                "redacted": text,
                "has_pii": False,
                "pii_types": [],
                "pii_count": 0,
                "entities": []
            }
        
        entities = self.detect_pii(text)
        
        if not entities:
            return {
                "original": text,
                "redacted": text,
                "has_pii": False,
                "pii_types": [],
                "pii_count": 0,
                "entities": []
            }
        
        # Redact by replacing with asterisks
        redacted = text
        # Sort entities by start position (reverse) to maintain indices
        for entity in sorted(entities, key=lambda e: e.start, reverse=True):
            replacement = redaction_char * (entity.end - entity.start)
            redacted = redacted[:entity.start] + replacement + redacted[entity.end:]
        
        pii_types = list(set(e.entity_type for e in entities))
        
        return {
            "original": text,
            "redacted": redacted,
            "has_pii": True,
            "pii_types": pii_types,
            "pii_count": len(entities),
            "entities": [
                {
                    "type": e.entity_type,
                    "text": e.text,
                    "score": e.score
                }
                for e in entities
            ]
        }
    
    def should_flag_for_review(self, pii_result: Dict) -> bool:
        """
        Determine if content should be flagged for review based on PII
        
        Args:
            pii_result: Result from redact_pii()
            
        Returns:
            True if content should be reviewed by human
        """
        if not pii_result['has_pii']:
            return False
        
        # High-risk PII types that require review
        high_risk_types = {
            "CREDIT_CARD", "US_SSN", "MEDICAL_LICENSE",
            "US_PASSPORT", "IBAN_CODE"
        }
        
        detected_types = set(pii_result['pii_types'])
        
        # Flag if high-risk PII detected
        if detected_types & high_risk_types:
            return True
        
        # Flag if more than 5 PII entities detected
        if pii_result['pii_count'] > 5:
            return True
        
        return False


# Global instance
pii_detector = PIIDetector()
