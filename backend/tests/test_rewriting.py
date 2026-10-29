from __future__ import annotations

import pytest

from app.quality import evaluate_text
from app.rewriting import canonical_mode, rewrite_text


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("paraphrase", "significant"),
        ("academic", "demonstrates"),
        ("professional", "require"),
        ("simple", "show"),
        ("friendly", "about"),
        ("concise", "because"),
        ("expand", "for example"),
        ("grammar", "I"),
    ],
)
def test_modes_apply_deterministic_mode_specific_rules(mode, expected):
    source_by_mode = {
        "paraphrase": "This is important.",
        "academic": "The report shows results.",
        "professional": "We need help.",
        "simple": "They demonstrate the result.",
        "friendly": "Please be advised that this is regarding your request.",
        "concise": "We did this due to the fact that it mattered.",
        "expand": "Use e.g. this option.",
        "grammar": "i could of done it",
    }

    rewritten, effective_mode, changes = rewrite_text(source_by_mode[mode], mode)

    assert expected.lower() in rewritten.lower()
    assert effective_mode == mode
    assert changes


@pytest.mark.parametrize(
    ("legacy", "canonical"),
    [
        ("improve", "paraphrase"),
        ("simplify", "simple"),
        ("creative", "expand"),
        ("persuasive", "professional"),
    ],
)
def test_legacy_modes_map_to_canonical_modes(legacy, canonical):
    assert canonical_mode(legacy) == canonical


def test_phrase_fallbacks_are_deterministic_and_do_not_invent_domain_facts():
    source = "The schedule changed."
    first = rewrite_text(source, "academic")
    second = rewrite_text(source, "academic")

    assert first == second
    assert first[0] != source
    assert "no domain facts were introduced" in first[2][0]


def test_grammar_mode_corrects_usage_and_sentence_punctuation():
    rewritten, _, changes = rewrite_text("i could of done this", "grammar")

    assert rewritten == "I could have done this."
    assert len(changes) >= 2


def test_quality_metrics_are_bounded_and_explain_their_limits():
    metrics = evaluate_text("This is a clear sentence. It uses familiar words.")

    assert metrics.word_count == 9
    assert metrics.sentence_count == 2
    assert metrics.average_sentence_length == 4.5
    assert metrics.readability is not None
    assert 0 <= metrics.quality_score <= 100
    assert "does not measure factual" in metrics.quality_score_basis


def test_non_english_text_has_no_english_readability_estimate():
    metrics = evaluate_text("你好世界。")

    assert metrics.readability is None
    assert metrics.readability_label is None
