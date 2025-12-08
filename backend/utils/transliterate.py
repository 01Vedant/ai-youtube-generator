"""
Indic transliteration & normalization utilities.
Handles IAST ↔ Devanagari conversion, input sanitization, and title normalization.
"""

import re
import html
from typing import Tuple, Optional

# Devanagari character ranges and basic mappings
DEVANAGARI_VOWELS = 'अआइईउऊऋएऐओऔ'
DEVANAGARI_CONSONANTS = 'कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह'

# Simple IAST to Devanagari mapping (subset for common transliteration)
IAST_TO_DEVANAGARI: dict[str, str] = {
    'a': 'अ', 'ā': 'आ', 'i': 'इ', 'ī': 'ई', 'u': 'उ', 'ū': 'ऊ',
    'ṛ': 'ऋ', 'e': 'ए', 'ai': 'ऐ', 'o': 'ओ', 'au': 'औ',
    'k': 'क', 'kh': 'ख', 'g': 'ग', 'gh': 'घ', 'ṅ': 'ङ',
    'c': 'च', 'ch': 'छ', 'j': 'ज', 'jh': 'झ', 'ñ': 'ञ',
    'ṭ': 'ट', 'ṭh': 'ठ', 'ḍ': 'ड', 'ḍh': 'ढ', 'ṇ': 'ण',
    't': 'त', 'th': 'थ', 'd': 'द', 'dh': 'ध', 'n': 'न',
    'p': 'प', 'ph': 'फ', 'b': 'ब', 'bh': 'भ', 'm': 'म',
    'y': 'य', 'r': 'र', 'l': 'ल', 'v': 'व',
    'ś': 'श', 'ṣ': 'ष', 's': 'स', 'h': 'ह',
}

# Reverse mapping for Devanagari to IAST
DEVANAGARI_TO_IAST: dict[str, str] = {v: k for k, v in IAST_TO_DEVANAGARI.items()}


def sanitize_text(text: str, max_length: int = 5000) -> str:
    """
    Sanitize user input: strip HTML, decode entities, remove control chars, truncate.
    
    Args:
        text: Raw user input
        max_length: Maximum allowed length (default 5000)
    
    Returns:
        Sanitized text safe for display
    """
    if not text:
        return ""
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove control characters (keep newlines, tabs)
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
    
    # Normalize whitespace (multiple spaces → single space, leading/trailing)
    text = ' '.join(text.split())
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length].rstrip()
    
    return text


def normalize_title(title: str, max_length: int = 100) -> str:
    """
    Normalize title for video metadata: sanitize, truncate, ensure uniqueness.
    
    Args:
        title: Raw title
        max_length: Maximum title length (default 100 for YouTube limit)
    
    Returns:
        Normalized title
    """
    title = sanitize_text(title, max_length=max_length)
    
    # Remove extra punctuation but keep basic marks
    title = re.sub(r'[^\w\s।॰\-:.,;!?]', '', title, flags=re.UNICODE)
    
    # Collapse multiple punctuation marks
    title = re.sub(r'([।॰\-:.,;!?])\1+', r'\1', title)
    
    return title.strip()


def transliterate_iast_to_devanagari(text: str) -> str:
    """
    Convert IAST (ASCII International Alphabet of Sanskrit) to Devanagari.
    Simple phonetic approximation; not a full transliterator.
    
    Args:
        text: IAST text (e.g., "Prahlad")
    
    Returns:
        Devanagari approximation (e.g., "प्रह्लाद")
    """
    if not text:
        return ""
    
    result = []
    i = 0
    while i < len(text):
        # Try two-character matches first
        if i + 1 < len(text):
            bigram = text[i:i+2].lower()
            if bigram in IAST_TO_DEVANAGARI:
                result.append(IAST_TO_DEVANAGARI[bigram])
                i += 2
                continue
        
        # Try single character
        char = text[i].lower()
        if char in IAST_TO_DEVANAGARI:
            result.append(IAST_TO_DEVANAGARI[char])
        else:
            # Keep as-is if not in mapping
            result.append(text[i])
        
        i += 1
    
    return ''.join(result)


def transliterate_devanagari_to_iast(text: str) -> str:
    """
    Convert Devanagari to IAST (ASCII International Alphabet of Sanskrit).
    Simple phonetic approximation; not a full transliterator.
    
    Args:
        text: Devanagari text (e.g., "प्रह्लाद")
    
    Returns:
        IAST approximation (e.g., "Prahlad")
    """
    if not text:
        return ""
    
    result = []
    for char in text:
        if char in DEVANAGARI_TO_IAST:
            result.append(DEVANAGARI_TO_IAST[char])
        else:
            result.append(char)
    
    return ''.join(result)


def detect_script(text: str) -> str:
    """
    Detect if text is primarily Devanagari, IAST, or other.
    
    Args:
        text: Text to analyze
    
    Returns:
        'devanagari', 'iast', or 'other'
    """
    if not text:
        return 'other'
    
    devanagari_count = sum(1 for c in text if c in DEVANAGARI_VOWELS + DEVANAGARI_CONSONANTS)
    total_chars = len([c for c in text if c.isalpha()])
    
    if total_chars == 0:
        return 'other'
    
    if devanagari_count / total_chars > 0.5:
        return 'devanagari'
    
    # Check for diacritics common in IAST
    if any(c in text for c in 'āīūṛṅñṭḍṇśṣ'):
        return 'iast'
    
    return 'other'


def ensure_unicode_normalization(text: str, form: str = 'NFC') -> str:
    """
    Normalize Unicode to NFC (composed) or NFD (decomposed) form.
    Ensures consistent representation of Devanagari characters.
    
    Args:
        text: Text to normalize
        form: 'NFC', 'NFD', 'NFKC', or 'NFKD'
    
    Returns:
        Normalized text
    """
    import unicodedata
    return unicodedata.normalize(form, text)


def validate_indic_text(text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate text for use in Indic contexts (Devanagari, IAST, etc).
    
    Returns:
        (is_valid, error_message)
    """
    if not text or not isinstance(text, str):
        return False, "Text must be a non-empty string"
    
    if len(text) > 5000:
        return False, "Text exceeds maximum length of 5000 characters"
    
    # Check for excessive control characters
    control_chars = sum(1 for c in text if ord(c) < 32 and c not in '\n\r\t')
    if control_chars > len(text) * 0.1:
        return False, "Text contains too many control characters"
    
    # Check for valid UTF-8
    try:
        text.encode('utf-8')
    except UnicodeEncodeError:
        return False, "Text contains invalid UTF-8 characters"
    
    return True, None
