"""
SSML (Speech Synthesis Markup Language) utilities for Hindi narration
Generates prosody-enhanced SSML for soothing devotional content
"""
from typing import List


def build_hindi_ssml(
    sentences: List[str],
    rate_pct: int = -5,
    pitch_semitones: int = -2,
    break_ms: int = 300
) -> str:
    """
    Build SSML string with prosody controls for Hindi devotional narration.
    
    Args:
        sentences: List of Hindi text sentences (Devanagari script)
        rate_pct: Speech rate adjustment (-5 = 5% slower for calm delivery)
        pitch_semitones: Pitch adjustment in semitones (-2 = slightly lower, soothing)
        break_ms: Pause duration between sentences in milliseconds
    
    Returns:
        SSML string with <prosody> and <break> tags
    
    Example:
        >>> build_hindi_ssml(["पहली किरण", "शांति"])
        '<speak><prosody rate="-5%" pitch="-2st">पहली किरण<break time="300ms"/>शांति</prosody></speak>'
    """
    if not sentences:
        return "<speak></speak>"
    
    # Format rate and pitch
    rate_str = f"{rate_pct:+d}%" if rate_pct != 0 else "medium"
    pitch_str = f"{pitch_semitones:+d}st" if pitch_semitones != 0 else "medium"
    
    # Build SSML with prosody wrapper
    ssml_parts = ['<speak>']
    ssml_parts.append(f'<prosody rate="{rate_str}" pitch="{pitch_str}">')
    
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Escape XML special characters
        sentence = (sentence
                   .replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&apos;'))
        
        ssml_parts.append(sentence)
        
        # Add break between sentences (but not after last one)
        if i < len(sentences) - 1:
            ssml_parts.append(f'<break time="{break_ms}ms"/>')
    
    ssml_parts.append('</prosody>')
    ssml_parts.append('</speak>')
    
    return ''.join(ssml_parts)


def segment_devotional_text(text: str, max_chars: int = 120) -> List[str]:
    """
    Segment Hindi devotional text into natural phrase boundaries.
    Respects sentence endings (।, ।।) and keeps phrases under max_chars.
    
    Args:
        text: Hindi text in Devanagari script
        max_chars: Maximum characters per segment
    
    Returns:
        List of text segments (phrases/sentences)
    """
    if not text:
        return []
    
    # Split on Devanagari sentence endings
    segments = []
    current = []
    
    # Split by Devanagari full stop (।) or double (।।)
    parts = text.replace('।।', '।').split('।')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # If part is too long, split on ellipsis or comma
        if len(part) > max_chars:
            sub_parts = part.replace('…', ',').split(',')
            for sub in sub_parts:
                sub = sub.strip()
                if sub:
                    segments.append(sub)
        else:
            segments.append(part)
    
    return segments
