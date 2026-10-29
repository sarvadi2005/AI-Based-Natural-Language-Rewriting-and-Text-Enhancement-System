from __future__ import annotations

import re

from app.preprocessing import correct_grammar, normalize_text
from app.schemas import RewriteMode


ENGINE_NAME = "deterministic_rule_based"

LEGACY_MODE_MAP: dict[str, str] = {
    "improve": "paraphrase",
    "simplify": "simple",
    "creative": "expand",
    "persuasive": "professional",
}

_CONTRACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bcan't\b", re.IGNORECASE), "cannot"),
    (re.compile(r"\bwon't\b", re.IGNORECASE), "will not"),
    (re.compile(r"\bn't\b", re.IGNORECASE), " not"),
    (re.compile(r"\bI'm\b", re.IGNORECASE), "I am"),
    (re.compile(r"\b(we|they|you|he|she|it)'re\b", re.IGNORECASE), r"\1 are"),
    (re.compile(r"\b(we|they|you|he|she|it)'ve\b", re.IGNORECASE), r"\1 have"),
    (re.compile(r"\b(we|they|you|he|she|it)'ll\b", re.IGNORECASE), r"\1 will"),
    (re.compile(r"\b(we|they|you|he|she|it)'d\b", re.IGNORECASE), r"\1 would"),
)

_PHRASES: dict[str, tuple[tuple[str, str], ...]] = {
    "paraphrase": (
        ("because of the fact that", "because"),
        ("in order to", "to"),
        ("make a decision", "decide"),
        ("give an explanation", "explain"),
        ("a lot of", "many"),
        ("important", "significant"),
        ("help", "support"),
        ("shows", "demonstrates"),
        ("use", "apply"),
    ),
    "academic": (
        ("a lot of", "a substantial number of"),
        ("shows", "demonstrates"),
        ("says", "argues"),
        ("get", "obtain"),
        ("big", "substantial"),
        ("good", "beneficial"),
        ("bad", "adverse"),
        ("about", "regarding"),
    ),
    "professional": (
        ("ASAP", "as soon as possible"),
        ("a lot of", "many"),
        ("get", "receive"),
        ("help", "support"),
        ("need", "require"),
        ("gonna", "going to"),
        ("wanna", "want to"),
    ),
    "simple": (
        ("in the event that", "if"),
        ("approximately", "about"),
        ("demonstrate", "show"),
        ("commence", "start"),
        ("subsequent", "next"),
        ("individuals", "people"),
        ("assistance", "help"),
        ("utilize", "use"),
    ),
    "friendly": (
        ("please be advised that", "just so you know,"),
        ("regarding", "about"),
        ("assist", "help"),
        ("request", "ask"),
        ("therefore", "so"),
    ),
    "concise": (
        ("due to the fact that", "because"),
        ("for the purpose of", "to"),
        ("at this point in time", "now"),
        ("in the near future", "soon"),
        ("in order to", "to"),
        ("a large number of", "many"),
        ("the majority of", "most"),
        ("in my opinion", ""),
        ("it is important to note that", ""),
        ("very", ""),
        ("really", ""),
    ),
    "expand": (
        ("e.g.", "for example"),
        ("i.e.", "that is"),
        ("etc.", "and other related items"),
        ("can't", "cannot"),
        ("won't", "will not"),
    ),
}

_FALLBACK_PREFIX: dict[str, str] = {
    "paraphrase": "Put another way, ",
    "academic": "Stated more formally, ",
    "professional": "For clarity, ",
    "simple": "Put simply, ",
    "friendly": "A friendly way to put it is: ",
    "expand": "To spell out the point, ",
}


def canonical_mode(mode: str | RewriteMode) -> str:
    identifier = mode.value if isinstance(mode, RewriteMode) else str(mode)
    return LEGACY_MODE_MAP.get(identifier, identifier)


def _preserve_case(source: str, replacement: str) -> str:
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _replace_phrases(text: str, mode: str) -> tuple[str, bool]:
    changed = False
    for source, replacement in _PHRASES.get(mode, ()):
        pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", re.IGNORECASE)

        def replace(match: re.Match[str]) -> str:
            nonlocal changed
            changed = True
            return _preserve_case(match.group(0), replacement)

        text = pattern.sub(replace, text)
    text = re.sub(r"\s+([,.;!?])", r"\1", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip(), changed


def _expand_contractions(text: str) -> tuple[str, bool]:
    changed = False
    for pattern, replacement in _CONTRACTIONS:
        text, count = pattern.subn(replacement, text)
        changed = changed or count > 0
    return text, changed


def rewrite_text(text: str, mode: str | RewriteMode) -> tuple[str, str, list[str]]:
    requested_mode = mode.value if isinstance(mode, RewriteMode) else str(mode)
    selected_mode = canonical_mode(requested_mode)
    normalized = normalize_text(text)
    changes: list[str] = []

    if selected_mode == "grammar":
        enhanced, corrections = correct_grammar(normalized)
        changes.extend(corrections)
        if not changes:
            changes.append("No grammar corrections were needed; the original wording was preserved.")
        return enhanced, selected_mode, changes

    enhanced = normalized
    if selected_mode in {"academic", "professional"}:
        enhanced, changed = _expand_contractions(enhanced)
        if changed:
            changes.append("Expanded contractions for a more formal tone.")

    enhanced, replaced = _replace_phrases(enhanced, selected_mode)
    if replaced:
        changes.append(f"Applied deterministic {selected_mode}-mode phrase refinements.")

    if selected_mode == "expand" and enhanced == normalized:
        enhanced, changed = _expand_contractions(enhanced)
        if changed:
            changes.append("Expanded contractions and abbreviations without adding new facts.")

    if enhanced == normalized:
        prefix = _FALLBACK_PREFIX.get(selected_mode)
        if prefix:
            enhanced = prefix + normalized[0].lower() + normalized[1:]
            changes.append(
                f"Added a meaning-preserving {selected_mode}-mode framing phrase; "
                "no domain facts were introduced."
            )
        elif selected_mode == "concise":
            changes.append("No supported filler phrases were present to remove.")

    if not enhanced:
        enhanced = normalized
    return enhanced, selected_mode, changes
