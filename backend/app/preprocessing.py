from __future__ import annotations

import re
import unicodedata


_GRAMMAR_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\balot\b", re.IGNORECASE), "a lot"),
    (re.compile(r"\birregardless\b", re.IGNORECASE), "regardless"),
    (re.compile(r"\bbetween you and I\b", re.IGNORECASE), "between you and me"),
    (
        re.compile(r"\b(can|could|would|should|might|must|may) of\b", re.IGNORECASE),
        r"\1 have",
    ),
    (re.compile(r"\bdoesn't has\b", re.IGNORECASE), "doesn't have"),
    (re.compile(r"\bdidn't went\b", re.IGNORECASE), "didn't go"),
)


def normalize_text(text: str) -> str:
    """Normalize Unicode and whitespace without joining separate paragraphs."""
    normalized = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in normalized.split("\n")]
    paragraphs: list[str] = []
    for line in lines:
        if line:
            paragraphs.append(line)
        elif paragraphs and paragraphs[-1] != "":
            paragraphs.append("")
    while paragraphs and paragraphs[-1] == "":
        paragraphs.pop()
    return "\n".join(paragraphs)


def _capitalize_sentences(text: str) -> str:
    text = text[:1].upper() + text[1:] if text else text
    return re.sub(
        r"([.!?]\s+)([a-z])",
        lambda match: match.group(1) + match.group(2).upper(),
        text,
    )


def _ensure_terminal_punctuation(text: str) -> str:
    if not text:
        return text
    match = re.search(r"""[)"'\]}]*$""", text)
    suffix = match.group(0) if match else ""
    body = text[: -len(suffix)] if suffix else text
    if body and body[-1] not in ".!?":
        body += "."
    return body + suffix


def correct_grammar(text: str) -> tuple[str, list[str]]:
    corrected = normalize_text(text)
    applied: list[str] = []
    for pattern, replacement in _GRAMMAR_REPLACEMENTS:
        updated, count = pattern.subn(replacement, corrected)
        if count:
            corrected = updated
            applied.append(f"Corrected {count} common grammar or usage issue(s).")

    updated = re.sub(r"\bi\b", "I", corrected)
    if updated != corrected:
        applied.append("Capitalized the first-person pronoun.")
        corrected = updated

    updated = _capitalize_sentences(corrected)
    if updated != corrected:
        applied.append("Capitalized sentence beginnings.")
        corrected = updated

    updated = _ensure_terminal_punctuation(corrected)
    if updated != corrected:
        applied.append("Added missing terminal punctuation.")
        corrected = updated

    return corrected, applied
