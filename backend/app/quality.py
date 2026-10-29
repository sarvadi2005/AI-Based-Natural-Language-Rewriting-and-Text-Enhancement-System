from __future__ import annotations

import re
from typing import Any

from app.preprocessing import normalize_text
from app.schemas import TextMetrics


_WORD_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
_SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)")
_ENGLISH_MARKERS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "for",
    "from", "had", "has", "have", "he", "her", "his", "i", "in", "is", "it",
    "of", "on", "or", "our", "she", "that", "the", "their", "they", "this",
    "to", "was", "we", "were", "with", "you", "your",
}


def count_words(text: str) -> int:
    return len(_WORD_RE.findall(text))


def split_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in _SENTENCE_RE.findall(text) if sentence.strip()]


def _syllable_count(word: str) -> int:
    normalized = re.sub(r"[^a-z]", "", word.lower())
    if not normalized:
        return 0
    groups = re.findall(r"[aeiouy]+", normalized)
    count = len(groups)
    if normalized.endswith("e") and count > 1 and not normalized.endswith(("le", "ye")):
        count -= 1
    if normalized.endswith("es") and count > 1 and normalized[-3] not in "s":
        count -= 1
    return max(1, count)


def _flesch_reading_ease(words: list[str], sentence_count: int) -> float | None:
    if not words or sentence_count == 0:
        return None
    alphabetic_words = [word for word in words if word.isalpha()]
    if not alphabetic_words:
        return None
    latin_words = sum(bool(re.fullmatch(r"[A-Za-z]+", word)) for word in alphabetic_words)
    markers = sum(word.lower() in _ENGLISH_MARKERS for word in alphabetic_words)
    if latin_words / len(alphabetic_words) < 0.8 or markers == 0:
        return None
    syllables = sum(_syllable_count(word) for word in alphabetic_words)
    score = 206.835 - 1.015 * (len(words) / sentence_count) - 84.6 * (syllables / len(words))
    return round(max(0.0, min(100.0, score)), 2)


def evaluate_text(text: str) -> TextMetrics:
    normalized = normalize_text(text)
    words = _WORD_RE.findall(normalized)
    sentences = split_sentences(normalized)
    sentence_count = len(sentences)
    average_length = len(words) / sentence_count if sentence_count else float(len(words))
    readability = _flesch_reading_ease(words, sentence_count)

    if words:
        long_word_ratio = sum(len(re.sub(r"[^A-Za-z]", "", word)) >= 12 for word in words) / len(words)
        unique_ratio = len({word.casefold() for word in words}) / len(words)
        length_penalty = min(28.0, abs(average_length - 18.0) * 0.85)
        long_word_penalty = min(16.0, long_word_ratio * 40.0)
        repetition_penalty = min(12.0, max(0.0, 0.45 - unique_ratio) * 24.0)
        punctuation_penalty = 0.0 if normalized.rstrip().endswith((".", "!", "?")) else 9.0
        score = round(max(0.0, min(
            100.0,
            100.0 - length_penalty - long_word_penalty - repetition_penalty - punctuation_penalty,
        )))
    else:
        score = 0

    return TextMetrics(
        word_count=len(words),
        sentence_count=sentence_count,
        average_sentence_length=round(average_length, 2),
        readability=readability,
        readability_label="Estimated Flesch Reading Ease (English text)" if readability is not None else None,
        quality_score=score,
        quality_score_basis=(
            "Transparent heuristic based on sentence length, long-word frequency, "
            "lexical repetition, and terminal punctuation; it does not measure factual "
            "or semantic accuracy or plagiarism."
        ),
    )


def metrics_for_api(metrics: TextMetrics) -> dict[str, Any]:
    return metrics.model_dump()
