import re
import logging

logger = logging.getLogger(__name__)

class OCRValidator:
    """Utility to validate OCR output quality."""

    @staticmethod
    def is_gibberish(text: str) -> bool:
        """
        Detects if text looks like OCR gibberish (high percentage of symbols/non-alphanumeric).
        """
        if not text.strip():
            return True
        
        # Count alphanumeric characters vs total characters
        total_chars = len(text)
        alnum_chars = sum(1 for c in text if c.isalnum() or c.isspace())
        
        ratio = alnum_chars / total_chars
        
        # If less than 70% of chars are alphanumeric/space, it's likely gibberish
        if ratio < 0.7:
            return True
            
        # Check for repetitive non-sense symbols
        if re.search(r'[^a-zA-Z0-9\s]{4,}', text):
            return True
            
        return False

    @staticmethod
    def is_too_short(text: str, min_length: int = 20) -> bool:
        """Checks if extracted text is too short to be useful."""
        return len(text.strip()) < min_length

    @staticmethod
    def calculate_gibberish_ratio(text: str) -> float:
        """
        Calculates the ratio of 'gibberish' words vs readable words.
        Heuristic: A word is 'readable' if it contains only alphabetic characters.
        """
        words = text.split()
        if not words:
            return 1.0
            
        readable_count = 0
        for word in words:
            # Simple heuristic for a "readable" word
            if word.isalpha() and len(word) > 1:
                readable_count += 1
            # Also allow common technical symbols if mixed with letters
            elif re.search(r'[a-zA-Z]', word) and not re.search(r'[^a-zA-Z0-9]', word):
                 readable_count += 0.5 # Partial credit for alphanum
                 
        gibberish_ratio = 1 - (readable_count / len(words))
        return round(max(0.0, min(1.0, gibberish_ratio)), 2)

ocr_validator = OCRValidator()
