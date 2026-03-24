"""
Smart text formatter for PPTX slides.
Auto-detects structure in plain text and converts to formatted block list.
"""
import re
from typing import Any


def parse_structured_text(raw_text: str) -> list[dict]:
    """
    Parse plain text into structured blocks.

    Detects:
    - Lines starting with - or • or * → bullet points
    - Lines starting with 1. 2. 3. → numbered list
    - Lines in ALL CAPS (2+ words) or ending with : → sub-headers
    - Empty lines → paragraph breaks
    - Regular text → body paragraphs

    Returns list of blocks:
    [
        {"type": "header", "text": "Strategy Overview"},
        {"type": "paragraph", "text": "We recommend..."},
        {"type": "bullet", "text": "Increase Meta budget by 20%"},
        {"type": "numbered", "number": 1, "text": "First action item"},
    ]
    """
    blocks = []
    lines = raw_text.strip().split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Numbered list: 1. or 1) or (1)
        num_match = re.match(r'^[\(\[]?(\d+)[.\)\]]?\s+(.+)', stripped)
        if num_match:
            blocks.append({
                "type": "numbered",
                "number": int(num_match.group(1)),
                "text": num_match.group(2).strip(),
            })
            continue

        # Bullet: - or • or * at start
        if len(stripped) > 2 and stripped[0] in '-•*' and stripped[1] == ' ':
            blocks.append({"type": "bullet", "text": stripped[2:].strip()})
            continue

        # Sub-header: ALL CAPS (2+ words) or ends with :
        words = stripped.split()
        if (
            stripped.isupper() and len(words) >= 2
        ) or (
            stripped.endswith(':') and len(stripped) < 80 and not stripped[0].isdigit()
        ):
            blocks.append({"type": "header", "text": stripped.rstrip(':')})
            continue

        # Regular paragraph
        blocks.append({"type": "paragraph", "text": stripped})

    return blocks


def blocks_to_plain(blocks: list[dict]) -> str:
    """Convert parsed blocks back to a clean plain-text string (for fallback)."""
    lines = []
    for block in blocks:
        t = block.get("type")
        text = block.get("text", "")
        if t == "header":
            lines.append(f"\n{text.upper()}")
        elif t == "bullet":
            lines.append(f"• {text}")
        elif t == "numbered":
            lines.append(f"{block.get('number', 1)}. {text}")
        else:
            lines.append(text)
    return "\n".join(lines)
