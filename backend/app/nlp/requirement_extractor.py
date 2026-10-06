from dataclasses import dataclass
import re
from typing import Any
import spacy


@dataclass
class Requirement:
    req_id: str
    text: str
    source_layer: str
    confidence: float
    char_start: int
    char_end: int
    section: str | None = None


# Compile common patterns
LAYER1_ID_PATTERN = re.compile(
    r"^(?P<id>(?:REQ|FR|NFR|BR|UR|SR|CR|R)[-_]?[0-9]+(?:\.[0-9]+)*|\d+\.\d+(?:\.\d+)*)\s*[:.\-–—]\s*(?P<text>.+)$",
    re.IGNORECASE,
)

BULLET_LIST_PATTERN = re.compile(
    r"^(?:[-*•]|\(\d+\)|\d+[.)])\s+(?P<text>.+)$"
)

CAPTION_PATTERN = re.compile(
    r"^(?:Figure|Fig\.|Table)\s+\d+[:.]", re.IGNORECASE
)

TOC_DOTS_PATTERN = re.compile(r"\.{3,}\s*\d+$")
TOC_PAGE_END_PATTERN = re.compile(r"\s+\d+$")

HEADING_PATTERN = re.compile(
    r"^(?:#+\s*|(?:Section\s+)?\d+(?:\.\d+)*\s+)([A-Z][^\n.]+?)$"
)

ALL_CAPS_HEADING = re.compile(r"^[A-Z0-9\s\-_]{3,50}$")

REQUIREMENT_SECTION_KEYWORDS = {
    "requirement",
    "requirements",
    "functional",
    "non-functional",
    "system features",
    "specifications",
    "shall",
}

MODAL_WORDS = {"shall", "must", "should", "will"}

# Load spaCy pipeline once
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = spacy.blank("en")
    if "sentencizer" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")


def is_table_of_contents_line(line: str, current_section: str | None) -> bool:
    if current_section and "table of contents" in current_section.lower():
        return True
    if TOC_DOTS_PATTERN.search(line):
        return True
    # Line starting with section number and ending with page number (e.g. "1.1 Scope    5")
    if re.match(r"^\d+(?:\.\d+)*\s+[A-Za-z\s]+", line) and TOC_PAGE_END_PATTERN.search(line):
        parts = line.rsplit(None, 1)
        if len(parts) == 2 and parts[1].isdigit():
            return True
    return False


def is_caption_or_glossary(line: str, current_section: str | None) -> bool:
    if CAPTION_PATTERN.match(line):
        return True
    if current_section and "glossary" in current_section.lower():
        # Glossary entries often look like: Term - Definition or Term: Definition
        if re.match(r"^[A-Za-z0-9\s]{1,30}[:\-–—]\s+[A-Za-z]", line):
            return True
    return False


def is_heading(line: str) -> tuple[bool, str]:
    cleaned = line.strip()
    if not cleaned:
        return False, ""
    if cleaned.startswith("#"):
        title = cleaned.lstrip("#").strip()
        return True, title
    if HEADING_PATTERN.match(cleaned):
        match = HEADING_PATTERN.match(cleaned)
        return True, match.group(1).strip()
    if ALL_CAPS_HEADING.match(cleaned) and not cleaned.endswith("."):
        # e.g., "ONLINE BANKING SYSTEM"
        return True, cleaned
    return False, ""


def find_offsets(text: str, target: str, search_from: int = 0) -> tuple[int, int]:
    idx = text.find(target, search_from)
    if idx != -1:
        return idx, idx + len(target)
    # fallback to whole string search
    idx = text.find(target)
    if idx != -1:
        return idx, idx + len(target)
    return 0, len(target)


def extract_requirements(text: str) -> list[Requirement]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    requirements: list[Requirement] = []
    claimed_line_indices: set[int] = set()

    current_section = "General"
    sections_per_line: list[str] = []

    # First pass: Track sections and filter non-requirement structures
    for idx, line in enumerate(lines):
        heading_flag, heading_title = is_heading(line)
        if heading_flag:
            current_section = heading_title
        sections_per_line.append(current_section)

    # Helper filter for minimum quality
    def is_eligible(line_text: str, line_idx: int) -> bool:
        if len(line_text.split()) < 4:
            return False
        sec = sections_per_line[line_idx]
        if is_table_of_contents_line(line_text, sec):
            return False
        if is_caption_or_glossary(line_text, sec):
            return False
        h_flag, _ = is_heading(line_text)
        if h_flag:
            return False
        return True

    search_cursor = 0

    # LAYER 1 - Explicit ID patterns
    for idx, line in enumerate(lines):
        if not is_eligible(line, idx):
            continue
        match = LAYER1_ID_PATTERN.match(line)
        if match:
            req_key = match.group("id").strip()
            content = match.group("text").strip()
            if len(content.split()) >= 3:
                start_c, end_c = find_offsets(text, line, search_cursor)
                search_cursor = max(search_cursor, end_c)
                requirements.append(
                    Requirement(
                        req_id=req_key,
                        text=content,
                        source_layer="layer_1_explicit_id",
                        confidence=0.95,
                        char_start=start_c,
                        char_end=end_c,
                        section=sections_per_line[idx],
                    )
                )
                claimed_line_indices.add(idx)

    # LAYER 2 - Structural cues (lists/bullets inside requirement-focused sections)
    layer2_counter = 1
    for idx, line in enumerate(lines):
        if idx in claimed_line_indices or not is_eligible(line, idx):
            continue

        sec = sections_per_line[idx].lower()
        is_req_section = any(k in sec for k in REQUIREMENT_SECTION_KEYWORDS)

        if is_req_section:
            match = BULLET_LIST_PATTERN.match(line)
            if match:
                content = match.group("text").strip()
                if len(content.split()) >= 4:
                    start_c, end_c = find_offsets(text, line, search_cursor)
                    search_cursor = max(search_cursor, end_c)
                    req_key = f"REQ-STRUC-{layer2_counter:03d}"
                    layer2_counter += 1
                    requirements.append(
                        Requirement(
                            req_id=req_key,
                            text=content,
                            source_layer="layer_2_structural_cue",
                            confidence=0.85,
                            char_start=start_c,
                            char_end=end_c,
                            section=sections_per_line[idx],
                        )
                    )
                    claimed_line_indices.add(idx)

    # LAYER 3 - Modal verb sentences with actor/system subject
    layer3_counter = 1
    unclaimed_lines = [
        (idx, line)
        for idx, line in enumerate(lines)
        if idx not in claimed_line_indices and is_eligible(line, idx)
    ]

    MODAL_HINT_PATTERN = re.compile(
        r"\b(shall|must|should|will|required\s+to|needs\s+to)\b",
        re.IGNORECASE,
    )
    candidate_unclaimed = [
        (idx, line)
        for idx, line in unclaimed_lines
        if MODAL_HINT_PATTERN.search(line)
    ]

    if candidate_unclaimed:
        candidate_texts = [line for _, line in candidate_unclaimed]
        pipe_kwargs = {"batch_size": 256}
        if nlp.has_pipe("ner"):
            pipe_kwargs["disable"] = ["ner"]

        docs = nlp.pipe(candidate_texts, **pipe_kwargs)

        for (idx, line), doc in zip(candidate_unclaimed, docs):
            for sent in doc.sents:
                sent_text = sent.text.strip()
                if len(sent_text.split()) < 4:
                    continue

                has_modal = False
                has_subject = False

                # Check tokens using spaCy parsing
                for token in sent:
                    text_lower = token.text.lower()

                    # Modal check
                    if text_lower in MODAL_WORDS or (
                        token.pos_ == "AUX" and text_lower in {"shall", "must", "should", "will"}
                    ):
                        has_modal = True

                    # Check multi-word modals ("is required to", "needs to")
                    if "required to" in sent_text.lower() or "needs to" in sent_text.lower():
                        has_modal = True

                    # Subject check
                    if token.dep_ in ("nsubj", "nsubjpass", "csubj", "csubjpass"):
                        has_subject = True

                # If sent has modal and subject (or fallback modal check if parser isn't loaded)
                if has_modal and (has_subject or not nlp.has_pipe("parser")):
                    start_c, end_c = find_offsets(text, sent_text, search_cursor)
                    search_cursor = max(search_cursor, end_c)
                    req_key = f"REQ-MOD-{layer3_counter:03d}"
                    layer3_counter += 1
                    requirements.append(
                        Requirement(
                            req_id=req_key,
                            text=sent_text,
                            source_layer="layer_3_modal_verb",
                            confidence=0.70,
                            char_start=start_c,
                            char_end=end_c,
                            section=sections_per_line[idx],
                        )
                    )
                    claimed_line_indices.add(idx)

    # LAYER 4 - Fallback: If no requirements extracted by Layers 1-3
    if not requirements:
        layer4_counter = 1
        for idx, line in enumerate(lines):
            if not is_eligible(line, idx):
                continue
            doc = nlp(line)
            for sent in doc.sents:
                sent_text = sent.text.strip()
                if len(sent_text.split()) >= 4:
                    start_c, end_c = find_offsets(text, sent_text, search_cursor)
                    search_cursor = max(search_cursor, end_c)
                    req_key = f"REQ-FBK-{layer4_counter:03d}"
                    layer4_counter += 1
                    requirements.append(
                        Requirement(
                            req_id=req_key,
                            text=sent_text,
                            source_layer="layer_4_fallback",
                            confidence=0.40,
                            char_start=start_c,
                            char_end=end_c,
                            section=sections_per_line[idx],
                        )
                    )

    return requirements
