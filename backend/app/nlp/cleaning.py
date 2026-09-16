from collections import Counter
from dataclasses import dataclass, field
import re
from typing import Any


@dataclass
class CleanedDocument:
    raw_text: str
    cleaned_text: str
    meta: dict[str, Any] = field(default_factory=dict)


def remove_repeated_headers_footers(
    pages: list[str], threshold: float = 0.6
) -> list[str]:
    if len(pages) < 2:
        return pages

    top_candidates: list[str] = []
    bottom_candidates: list[str] = []

    for page in pages:
        lines = [line.strip() for line in page.splitlines() if line.strip()]
        if not lines:
            continue
        # Check top 2 lines for headers
        for line in lines[:2]:
            top_candidates.append(line)
        # Check bottom 2 lines for footers
        for line in lines[-2:]:
            bottom_candidates.append(line)

    total_pages = len(pages)
    min_count = max(2, int(total_pages * threshold))

    header_counts = Counter(top_candidates)
    footer_counts = Counter(bottom_candidates)

    repeated_headers = {
        line for line, count in header_counts.items() if count >= min_count
    }
    repeated_footers = {
        line for line, count in footer_counts.items() if count >= min_count
    }
    repeated_lines = repeated_headers | repeated_footers

    cleaned_pages: list[str] = []
    for page in pages:
        page_lines = page.splitlines()
        filtered = [
            line for line in page_lines if line.strip() not in repeated_lines
        ]
        cleaned_pages.append("\n".join(filtered))

    return cleaned_pages


def remove_standalone_page_numbers(text: str) -> str:
    # Matches patterns like: "Page 1", "Page 1 of 10", "1", "- 1 -", "[ 1 ]"
    pattern = r"(?mi)^\s*(?:page\s+\d+(?:\s+(?:of|\/)\s+\d+)?|[-–—\[\(]?\s*\d+\s*[-–—\]\)]?)\s*$"
    cleaned = re.sub(pattern, "", text)
    return cleaned


def repair_hyphenated_line_breaks(text: str) -> str:
    # Matches: word hyphen at end of line followed by word on next line (e.g. "require-\nment")
    pattern = r"(\b[a-zA-Z]+)-\s*\r?\n\s*([a-zA-Z]+\b)"
    return re.sub(pattern, r"\1\2", text)


def join_wrapped_lines(text: str) -> str:
    # Pattern to identify structured line starts that must NOT be merged with previous line
    # e.g., REQ-001, FR-1, 1.1, Bullets (- , * , •), Section headers
    structured_prefix_pattern = re.compile(
        r"^(?:[A-Z]{2,10}[-_]\d+|[0-9]+(?:\.[0-9]+)*[.:)]|[-*•]\s+|\([0-9a-zA-Z]+\)\s+|Section\s+\d+|Chapter\s+\d+)",
        re.IGNORECASE,
    )

    paragraphs = text.split("\n\n")
    processed_paragraphs: list[str] = []

    for para in paragraphs:
        lines = [line.strip() for line in para.splitlines() if line.strip()]
        if not lines:
            continue

        merged_lines: list[str] = [lines[0]]

        for current_line in lines[1:]:
            prev_line = merged_lines[-1]

            # Condition to keep separate:
            # 1. current_line is an explicit requirement ID or bullet/numbered list
            # 2. prev_line ends with a colon or strong sentence ending and current_line starts with capital letter
            is_structured = bool(structured_prefix_pattern.match(current_line))
            is_prev_colon = prev_line.endswith(":")

            if is_structured or is_prev_colon:
                merged_lines.append(current_line)
            else:
                # If prev_line ends with a hyphen (not caught earlier), join directly
                if prev_line.endswith("-"):
                    merged_lines[-1] = prev_line[:-1] + current_line
                else:
                    merged_lines[-1] = f"{prev_line} {current_line}"

        processed_paragraphs.append("\n".join(merged_lines))

    return "\n\n".join(processed_paragraphs)


def collapse_excess_whitespace(text: str) -> str:
    # Collapse multiple spaces or tabs into a single space
    text = re.sub(r"[ \t]+", " ", text)
    # Strip whitespace on individual lines
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)
    # Collapse 3 or more newlines into exactly 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_text(
    raw_text: str, pages: list[str] | None = None
) -> CleanedDocument:
    # Step 1: Remove repeated headers and footers across pages if page breakdown is available
    if pages and len(pages) > 1:
        cleaned_pages = remove_repeated_headers_footers(pages)
        working_text = "\n\n".join(cleaned_pages)
    else:
        working_text = raw_text

    # Step 2: Remove standalone page numbers
    working_text = remove_standalone_page_numbers(working_text)

    # Step 3: Repair hyphenated line breaks
    working_text = repair_hyphenated_line_breaks(working_text)

    # Step 4: Join wrapped lines preserving structured list / requirement items
    working_text = join_wrapped_lines(working_text)

    # Step 5: Collapse excess whitespace
    cleaned_text = collapse_excess_whitespace(working_text)

    return CleanedDocument(
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        meta={
            "raw_length": len(raw_text),
            "cleaned_length": len(cleaned_text),
            "page_count": len(pages) if pages else 1,
        },
    )
